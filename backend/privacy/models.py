from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class PrivacySettings(models.Model):
    MODEL_IMPROVEMENT_CONSENT_VERSION = "model_improvement_mvp_v1"
    FOOD_PHOTO_TRAINING_CONSENT_VERSION = "food_photo_training_mvp_v1"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="privacy_settings",
    )
    model_improvement_consent_version = models.CharField(
        max_length=80,
        default=MODEL_IMPROVEMENT_CONSENT_VERSION,
    )
    model_improvement_consent_granted_at = models.DateTimeField(null=True, blank=True)
    model_improvement_consent_revoked_at = models.DateTimeField(null=True, blank=True)
    food_photo_training_consent_version = models.CharField(
        max_length=80,
        default=FOOD_PHOTO_TRAINING_CONSENT_VERSION,
    )
    food_photo_training_consent_granted_at = models.DateTimeField(null=True, blank=True)
    food_photo_training_consent_revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions = ()
        ordering = ["user_id"]
        permissions = [
            ("view_own_privacysettings", "Can view own privacy settings"),
            ("change_own_privacysettings", "Can change own privacy settings"),
            ("export_own_data", "Can export own data"),
            ("delete_own_data", "Can delete own data"),
        ]

    def __str__(self) -> str:
        return f"Privacy settings for user {self.user_id}"

    @property
    def has_model_improvement_consent(self) -> bool:
        return (
            self.model_improvement_consent_granted_at is not None
            and self.model_improvement_consent_revoked_at is None
        )

    @property
    def has_food_photo_training_consent(self) -> bool:
        return (
            self.food_photo_training_consent_granted_at is not None
            and self.food_photo_training_consent_revoked_at is None
        )

    def grant_model_improvement_consent(self) -> None:
        self.model_improvement_consent_version = self.MODEL_IMPROVEMENT_CONSENT_VERSION
        self.model_improvement_consent_granted_at = timezone.now()
        self.model_improvement_consent_revoked_at = None

    def revoke_model_improvement_consent(self) -> None:
        self.model_improvement_consent_revoked_at = timezone.now()

    def grant_food_photo_training_consent(self) -> None:
        self.food_photo_training_consent_version = self.FOOD_PHOTO_TRAINING_CONSENT_VERSION
        self.food_photo_training_consent_granted_at = timezone.now()
        self.food_photo_training_consent_revoked_at = None

    def revoke_food_photo_training_consent(self) -> None:
        self.food_photo_training_consent_revoked_at = timezone.now()
