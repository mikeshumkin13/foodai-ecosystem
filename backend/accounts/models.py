from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
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


class NutritionProfile(models.Model):
    class Goal(models.TextChoices):
        MAINTAIN_WEIGHT = "maintain_weight", "Maintain weight"
        LOSE_WEIGHT = "lose_weight", "Lose weight"
        GAIN_WEIGHT = "gain_weight", "Gain weight"
        IMPROVE_HABITS = "improve_habits", "Improve eating habits"

    class AgeCategory(models.TextChoices):
        UNDER_18 = "under_18", "Under 18"
        AGE_18_29 = "18_29", "18-29"
        AGE_30_39 = "30_39", "30-39"
        AGE_40_49 = "40_49", "40-49"
        AGE_50_64 = "50_64", "50-64"
        AGE_65_PLUS = "65_plus", "65+"
        PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

    class ActivityLevel(models.TextChoices):
        SEDENTARY = "sedentary", "Sedentary"
        LIGHT = "light", "Light"
        MODERATE = "moderate", "Moderate"
        ACTIVE = "active", "Active"
        VERY_ACTIVE = "very_active", "Very active"

    class PreferredUnits(models.TextChoices):
        METRIC = "metric", "Metric"
        IMPERIAL = "imperial", "Imperial"

    CONSENT_VERSION = "nutrition_profile_mvp_v1"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="nutrition_profile",
    )
    goal = models.CharField(
        max_length=32,
        choices=Goal.choices,
        default=Goal.MAINTAIN_WEIGHT,
    )
    height_cm = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(80), MaxValueValidator(250)],
    )
    mass_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(20), MaxValueValidator(400)],
    )
    age_category = models.CharField(
        max_length=32,
        choices=AgeCategory.choices,
        default=AgeCategory.PREFER_NOT_TO_SAY,
    )
    activity_level = models.CharField(
        max_length=32,
        choices=ActivityLevel.choices,
        default=ActivityLevel.MODERATE,
    )
    preferred_units = models.CharField(
        max_length=16,
        choices=PreferredUnits.choices,
        default=PreferredUnits.METRIC,
    )
    dietary_preferences = models.JSONField(default=list, blank=True)
    consent_version = models.CharField(max_length=64, default=CONSENT_VERSION)
    consent_granted_at = models.DateTimeField(null=True, blank=True)
    consent_revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user_id"]
        permissions = [
            ("view_own_nutritionprofile", "Can view own nutrition profile"),
            ("change_own_nutritionprofile", "Can change own nutrition profile"),
        ]

    def __str__(self) -> str:
        return f"Nutrition profile for user {self.user_id}"


class NutritionSensitiveRestriction(models.Model):
    class RestrictionType(models.TextChoices):
        ALLERGY = "allergy", "Allergy"
        INTOLERANCE = "intolerance", "Intolerance"
        MEDICAL_RESTRICTION = "medical_restriction", "Medical restriction"

    CONSENT_VERSION = "nutrition_sensitive_restrictions_mvp_v1"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="nutrition_sensitive_restrictions",
    )
    restriction_type = models.CharField(max_length=32, choices=RestrictionType.choices)
    label = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    consent_version = models.CharField(max_length=64, default=CONSENT_VERSION)
    consent_granted_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["label", "id"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]
        permissions = [
            (
                "view_own_nutritionsensitiverestriction",
                "Can view own nutrition sensitive restriction",
            ),
            (
                "change_own_nutritionsensitiverestriction",
                "Can change own nutrition sensitive restriction",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.restriction_type} for user {self.user_id}"


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
