from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    actions = None
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_select_related = ("actor",)
    list_display = (
        "created_at",
        "actor_identifier",
        "action",
        "target_type",
        "target_identifier",
        "request_correlation_id",
    )
    list_filter = ("action", "target_type", "created_at")
    search_fields = (
        "actor_id_snapshot",
        "target_type",
        "target_id",
        "request_correlation_id",
    )
    readonly_fields = (
        "id",
        "actor",
        "actor_id_snapshot",
        "action",
        "target_type",
        "target_id",
        "metadata",
        "request_correlation_id",
        "created_at",
    )
    fields = readonly_fields

    @admin.display(description=_("Actor ID"))
    def actor_identifier(self, obj: AuditLog) -> str:
        return obj.actor_id_snapshot or "-"

    @admin.display(description=_("Target ID"))
    def target_identifier(self, obj: AuditLog) -> str:
        return obj.target_id or "-"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: AuditLog | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: AuditLog | None = None) -> bool:
        return False
