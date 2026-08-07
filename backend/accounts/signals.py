from __future__ import annotations

from typing import Any

from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from accounts.rbac import ensure_role_groups


@receiver(post_migrate)
def sync_role_groups(sender: AppConfig, using: str, **kwargs: Any) -> None:
    if sender.label != "accounts":
        return

    ensure_role_groups(using=using)
