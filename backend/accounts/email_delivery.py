from __future__ import annotations

from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail

from accounts.auth_tokens import IssuedToken
from accounts.models import User


def send_email_verification(user: User, issued_token: IssuedToken) -> None:
    verification_url = _build_frontend_url(
        "/auth/email/verify",
        {
            "token_id": str(issued_token.token_id),
            "token": issued_token.token,
        },
    )
    send_mail(
        subject="Verify your FoodAI email",
        message=(
            "Verify your FoodAI account email using this link:\n"
            f"{verification_url}\n\n"
            "If you did not create a FoodAI account, ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_password_reset(user: User, issued_token: IssuedToken) -> None:
    reset_url = _build_frontend_url(
        "/auth/password/reset",
        {
            "token_id": str(issued_token.token_id),
            "token": issued_token.token,
        },
    )
    send_mail(
        subject="Reset your FoodAI password",
        message=(
            "Reset your FoodAI password using this link:\n"
            f"{reset_url}\n\n"
            "If you did not request a password reset, ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def _build_frontend_url(path: str, query: dict[str, str]) -> str:
    base_url = settings.FRONTEND_BASE_URL.rstrip("/")
    return f"{base_url}{path}?{urlencode(query)}"
