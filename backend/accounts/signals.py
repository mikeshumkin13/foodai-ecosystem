from __future__ import annotations

import json
from typing import Any, cast

from django.apps import AppConfig
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from accounts.models import AdminAuditLog
from accounts.rbac import ensure_role_groups


@receiver(post_migrate)
def sync_role_groups(sender: AppConfig, using: str, **kwargs: Any) -> None:
    if sender.label != "accounts":
        return

    ensure_role_groups(using=using)


@receiver(post_save, sender=LogEntry)
def mirror_admin_log_entry(
    sender: type[LogEntry],
    instance: LogEntry,
    created: bool,
    using: str,
    **kwargs: Any,
) -> None:
    if not created:
        return

    AdminAuditLog.objects.using(using).get_or_create(
        source_log_entry_id=instance.pk,
        defaults={
            "actor_id": instance.user_id,
            "action": _admin_action(instance.action_flag),
            "model_label": _model_label(instance),
            "content_type": instance.content_type,
            "object_id": str(instance.object_id or "")[:255],
            "object_repr": _safe_object_repr(instance),
            "change_message": _change_message_as_json(instance.change_message),
            "created_at": instance.action_time,
        },
    )


def _admin_action(action_flag: int) -> AdminAuditLog.Action:
    action_by_flag = {
        ADDITION: AdminAuditLog.Action.ADDITION,
        CHANGE: AdminAuditLog.Action.CHANGE,
        DELETION: AdminAuditLog.Action.DELETION,
    }
    return action_by_flag.get(action_flag, AdminAuditLog.Action.UNKNOWN)


def _model_label(log_entry: LogEntry) -> str:
    content_type = cast(ContentType | None, log_entry.content_type)
    if content_type is None:
        return ""
    return f"{content_type.app_label}.{content_type.model}"


def _safe_object_repr(log_entry: LogEntry) -> str:
    model_label = _model_label(log_entry)
    if model_label in {
        "accounts.user",
        "accounts.userprofile",
        "accounts.nutritionprofile",
        "accounts.nutritionsensitiverestriction",
        "accounts.emailverificationtoken",
        "accounts.passwordresettoken",
    }:
        object_id = str(log_entry.object_id or "unknown")
        return f"{model_label}:{object_id}"[:255]
    return str(log_entry.object_repr or "")[:255]


def _change_message_as_json(raw_change_message: str) -> list[Any]:
    if not raw_change_message:
        return []

    try:
        parsed_message = json.loads(raw_change_message)
    except json.JSONDecodeError:
        return [{"message": raw_change_message[:255]}]

    if isinstance(parsed_message, list):
        return parsed_message
    return [{"message": parsed_message}]
