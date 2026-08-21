from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AICoachSettings(models.Model):
    CHAT_HISTORY_CONSENT_VERSION = "ai_coach_history_mvp_v1"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_coach_settings",
    )
    chat_history_consent_version = models.CharField(
        max_length=64,
        default=CHAT_HISTORY_CONSENT_VERSION,
    )
    chat_history_consent_granted_at = models.DateTimeField(null=True, blank=True)
    chat_history_consent_revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions = ()
        ordering = ["user_id"]
        permissions = [
            ("use_ai_nutrition_coach", "Can use AI nutrition coach"),
            ("view_own_aicoachsettings", "Can view own AI coach settings"),
            ("change_own_aicoachsettings", "Can change own AI coach settings"),
        ]

    def __str__(self) -> str:
        return f"AI coach settings for user {self.user_id}"

    @property
    def has_chat_history_consent(self) -> bool:
        return (
            self.chat_history_consent_granted_at is not None
            and self.chat_history_consent_revoked_at is None
        )

    def grant_chat_history_consent(self) -> None:
        self.chat_history_consent_version = self.CHAT_HISTORY_CONSENT_VERSION
        self.chat_history_consent_granted_at = timezone.now()
        self.chat_history_consent_revoked_at = None

    def revoke_chat_history_consent(self) -> None:
        self.chat_history_consent_revoked_at = timezone.now()


class AICoachMessage(models.Model):
    class SafetyStatus(models.TextChoices):
        PASSED = "passed", "Passed"
        INPUT_BLOCKED = "input_blocked", "Input blocked"
        OUTPUT_BLOCKED = "output_blocked", "Output blocked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_coach_messages",
    )
    context_date = models.DateField()
    request_text = models.TextField()
    response_payload = models.JSONField(default=dict)
    context_snapshot = models.JSONField(default=dict)
    provider_name = models.CharField(max_length=80)
    output_schema_version = models.CharField(max_length=80)
    safety_status = models.CharField(
        max_length=32,
        choices=SafetyStatus.choices,
        default=SafetyStatus.PASSED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        default_permissions = ()
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"], name="ai_coach_msg_user_created_idx"),
        ]

    def __str__(self) -> str:
        return f"AI coach message {self.id}"
