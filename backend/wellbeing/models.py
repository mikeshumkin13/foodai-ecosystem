from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class WellbeingAssistantSettings(models.Model):
    HISTORY_CONSENT_VERSION = "wellbeing_assistant_history_mvp_v1"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wellbeing_assistant_settings",
    )
    history_consent_version = models.CharField(
        max_length=80,
        default=HISTORY_CONSENT_VERSION,
    )
    history_consent_granted_at = models.DateTimeField(null=True, blank=True)
    history_consent_revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions = ()
        ordering = ["user_id"]
        permissions = [
            ("use_wellbeing_assistant", "Can use wellbeing assistant"),
            (
                "view_own_wellbeingassistantsettings",
                "Can view own wellbeing assistant settings",
            ),
            (
                "change_own_wellbeingassistantsettings",
                "Can change own wellbeing assistant settings",
            ),
        ]

    def __str__(self) -> str:
        return f"Wellbeing assistant settings for user {self.user_id}"

    @property
    def has_history_consent(self) -> bool:
        return (
            self.history_consent_granted_at is not None
            and self.history_consent_revoked_at is None
        )

    def grant_history_consent(self) -> None:
        self.history_consent_version = self.HISTORY_CONSENT_VERSION
        self.history_consent_granted_at = timezone.now()
        self.history_consent_revoked_at = None

    def revoke_history_consent(self) -> None:
        self.history_consent_revoked_at = timezone.now()


class WellbeingAssistantMessage(models.Model):
    class SafetyStatus(models.TextChoices):
        PASSED = "passed", "Passed"
        INPUT_BLOCKED = "input_blocked", "Input blocked"
        OUTPUT_BLOCKED = "output_blocked", "Output blocked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wellbeing_assistant_messages",
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
            models.Index(
                fields=["user", "created_at"],
                name="wellbeing_msg_user_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Wellbeing assistant message {self.id}"
