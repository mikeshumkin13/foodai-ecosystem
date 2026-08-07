from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from accounts.models import EmailVerificationToken, PasswordResetToken, User

TokenModel = EmailVerificationToken | PasswordResetToken
TokenModelClass = type[EmailVerificationToken] | type[PasswordResetToken]


@dataclass(frozen=True)
class IssuedToken:
    token_id: UUID
    token: str


def issue_email_verification_token(user: User) -> IssuedToken:
    return _issue_token(
        model=EmailVerificationToken,
        user=user,
        max_age=timedelta(seconds=settings.AUTH_EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS),
    )


def issue_password_reset_token(user: User) -> IssuedToken:
    return _issue_token(
        model=PasswordResetToken,
        user=user,
        max_age=timedelta(seconds=settings.AUTH_PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS),
    )


def consume_email_verification_token(token_id: UUID, token: str) -> User | None:
    token_object = _get_usable_token(EmailVerificationToken, token_id, token)
    if token_object is None:
        return None

    now = timezone.now()
    token_object.used_at = now
    token_object.save(update_fields=["used_at"])

    user = token_object.user
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active", "updated_at"])
    return user


def consume_password_reset_token(token_id: UUID, token: str) -> User | None:
    token_object = _get_usable_token(PasswordResetToken, token_id, token)
    if token_object is None:
        return None

    token_object.used_at = timezone.now()
    token_object.save(update_fields=["used_at"])
    return token_object.user


def revoke_password_reset_tokens(user: User) -> None:
    PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(
        used_at=timezone.now(),
    )


def _issue_token(
    *,
    model: TokenModelClass,
    user: User,
    max_age: timedelta,
) -> IssuedToken:
    now = timezone.now()
    model.objects.filter(user=user, used_at__isnull=True).update(used_at=now)

    raw_token = secrets.token_urlsafe(32)
    token_object = model.objects.create(
        user=user,
        sent_to_email=user.email,
        token_hash=hash_token(raw_token),
        expires_at=now + max_age,
    )
    return IssuedToken(token_id=token_object.id, token=raw_token)


def _get_usable_token(
    model: TokenModelClass,
    token_id: UUID,
    raw_token: str,
) -> TokenModel | None:
    try:
        token_object = model.objects.select_related("user").get(
            id=token_id,
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
    except model.DoesNotExist:
        return None

    expected_hash = hash_token(raw_token)
    if not constant_time_compare(token_object.token_hash, expected_hash):
        return None
    return token_object


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
