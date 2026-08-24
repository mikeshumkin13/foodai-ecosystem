from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    class Action(models.TextChoices):
        ADMIN_USER_CHANGED = "admin_user_changed", "Administrative user change"
        ROLE_CHANGED = "role_changed", "Role changed"
        SUPPORT_ACCESS = "support_access", "Support access"
        ACCOUNT_DELETED = "account_deleted", "Account deleted"
        DATA_EXPORTED = "data_exported", "Data exported"
        PRIVACY_CONSENT_CHANGED = "privacy_consent_changed", "Privacy consent changed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_audit_logs",
    )
    actor_id_snapshot = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=64, choices=Action.choices)
    target_type = models.CharField(max_length=120)
    target_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    request_correlation_id = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        default_permissions = ("view",)
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["request_correlation_id", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.target_type} {self.target_id}".strip()
