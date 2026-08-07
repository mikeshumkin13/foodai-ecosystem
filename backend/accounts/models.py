from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from accounts.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects: ClassVar[UserManager] = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        ordering = ["email"]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.email = type(self).objects.normalize_email(self.email).lower()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.email


class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=150, blank=True)
    preferred_language = models.CharField(max_length=2, choices=settings.LANGUAGES, default="ru")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__email"]
        permissions = [
            ("view_own_userprofile", "Can view own user profile"),
            ("change_own_userprofile", "Can change own user profile"),
        ]

    def __str__(self) -> str:
        return f"Profile for {self.user.email}"


class RolePermission(models.Model):
    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ("access_support_tools", "Can access support tools without private user data"),
            ("manage_catalog_content", "Can manage nutrition catalog content"),
            ("view_support_admin", "Can view support admin tools without private user data"),
            ("manage_reference_data", "Can manage shared reference data"),
            ("manage_food_catalog", "Can manage future food catalog content"),
            ("administer_accounts", "Can administer accounts"),
        ]

    def __str__(self) -> str:
        return "Role permission namespace"


class AdminAuditLog(models.Model):
    class Action(models.TextChoices):
        ADDITION = "addition", "Addition"
        CHANGE = "change", "Change"
        DELETION = "deletion", "Deletion"
        UNKNOWN = "unknown", "Unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_log_entry_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_audit_logs",
    )
    action = models.CharField(max_length=16, choices=Action.choices, default=Action.UNKNOWN)
    model_label = models.CharField(max_length=120, blank=True)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    object_id = models.CharField(max_length=255, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    change_message = models.JSONField(default=list, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at", "action"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["model_label", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.model_label} {self.object_id}".strip()


class EmailVerificationToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token_hash = models.CharField(max_length=64)
    sent_to_email = models.EmailField()
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "used_at", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"Email verification token for {self.sent_to_email}"


class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token_hash = models.CharField(max_length=64)
    sent_to_email = models.EmailField()
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "used_at", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"Password reset token for {self.sent_to_email}"
