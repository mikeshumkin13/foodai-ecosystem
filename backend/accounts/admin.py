from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from accounts.models import AdminAuditLog, User, UserProfile
from accounts.rbac import role_group_names


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fields = ("id", "display_name", "preferred_language", "created_at", "updated_at")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    actions = None
    ordering = ("email",)
    date_hierarchy = "created_at"
    list_display = ("email", "role_names", "is_active", "is_staff", "is_superuser", "created_at")
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("email",)
    filter_horizontal = ("groups", "user_permissions")
    inlines = (UserProfileInline,)

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            _("Permissions"),
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        (_("Important dates"), {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_active", "is_staff"),
            },
        ),
    )
    readonly_fields = ("id", "last_login", "created_at", "updated_at")

    @admin.display(description=_("Roles"))
    def role_names(self, obj: User) -> str:
        role_names_queryset = obj.groups.filter(name__in=role_group_names()).values_list(
            "name",
            flat=True,
        )
        return ", ".join(role_names_queryset) or "-"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    actions = None
    ordering = ("user__email",)
    date_hierarchy = "created_at"
    list_display = ("id", "user_identifier", "preferred_language", "created_at", "updated_at")
    list_filter = ("preferred_language", "created_at", "updated_at")
    search_fields = ("user__email", "display_name")
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "user", "display_name", "preferred_language", "created_at", "updated_at")

    @admin.display(description=_("User ID"))
    def user_identifier(self, obj: UserProfile) -> str:
        return str(obj.user_id)


if Group in admin.site._registry:
    admin.site.unregister(Group)


@admin.register(Group)
class RoleGroupAdmin(DjangoGroupAdmin):
    actions = None
    ordering = ("name",)
    list_display = ("name", "permission_count")
    search_fields = ("name",)
    filter_horizontal = ("permissions",)

    @admin.display(description=_("Permissions"))
    def permission_count(self, obj: Group) -> int:
        return obj.permissions.count()

    def has_delete_permission(self, request: HttpRequest, obj: Group | None = None) -> bool:
        return False


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    actions = None
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_select_related = ("actor", "content_type")
    list_display = (
        "created_at",
        "actor_identifier",
        "action",
        "model_label",
        "object_identifier",
        "source_log_entry_id",
    )
    list_filter = ("action", "model_label", "created_at")
    search_fields = ("actor__email", "actor__id", "model_label", "object_id")
    readonly_fields = (
        "id",
        "source_log_entry_id",
        "actor",
        "action",
        "model_label",
        "content_type",
        "object_id",
        "object_repr",
        "change_message",
        "ip_address",
        "user_agent",
        "created_at",
    )
    fields = readonly_fields

    @admin.display(description=_("Actor ID"))
    def actor_identifier(self, obj: AdminAuditLog) -> str:
        if obj.actor_id is None:
            return "-"
        return str(obj.actor_id)

    @admin.display(description=_("Object ID"))
    def object_identifier(self, obj: AdminAuditLog) -> str:
        return obj.object_id or "-"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: AdminAuditLog | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: AdminAuditLog | None = None,
    ) -> bool:
        return False
