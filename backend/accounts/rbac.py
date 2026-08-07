from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

if TYPE_CHECKING:
    from accounts.models import User


class Role(StrEnum):
    USER = "user"
    SUPPORT = "support"
    CONTENT_MANAGER = "content_manager"
    ADMIN = "admin"


@dataclass(frozen=True)
class PermissionDefinition:
    codename: str
    model: str
    name: str

    @property
    def code(self) -> str:
        return f"accounts.{self.codename}"


@dataclass(frozen=True)
class RoleDefinition:
    role: Role
    group_name: str
    permissions: frozenset[str]


VIEW_OWN_PROFILE_PERMISSION = "accounts.view_own_userprofile"
CHANGE_OWN_PROFILE_PERMISSION = "accounts.change_own_userprofile"
ADMINISTER_ACCOUNTS_PERMISSION = "accounts.administer_accounts"

PERMISSION_DEFINITIONS: tuple[PermissionDefinition, ...] = (
    PermissionDefinition(
        codename="add_user",
        model="user",
        name="Can add user",
    ),
    PermissionDefinition(
        codename="view_user",
        model="user",
        name="Can view user",
    ),
    PermissionDefinition(
        codename="change_user",
        model="user",
        name="Can change user",
    ),
    PermissionDefinition(
        codename="delete_user",
        model="user",
        name="Can delete user",
    ),
    PermissionDefinition(
        codename="add_userprofile",
        model="userprofile",
        name="Can add user profile",
    ),
    PermissionDefinition(
        codename="view_userprofile",
        model="userprofile",
        name="Can view user profile",
    ),
    PermissionDefinition(
        codename="change_userprofile",
        model="userprofile",
        name="Can change user profile",
    ),
    PermissionDefinition(
        codename="delete_userprofile",
        model="userprofile",
        name="Can delete user profile",
    ),
    PermissionDefinition(
        codename="view_own_userprofile",
        model="userprofile",
        name="Can view own user profile",
    ),
    PermissionDefinition(
        codename="change_own_userprofile",
        model="userprofile",
        name="Can change own user profile",
    ),
    PermissionDefinition(
        codename="access_support_tools",
        model="rolepermission",
        name="Can access support tools without private user data",
    ),
    PermissionDefinition(
        codename="manage_catalog_content",
        model="rolepermission",
        name="Can manage nutrition catalog content",
    ),
    PermissionDefinition(
        codename="administer_accounts",
        model="rolepermission",
        name="Can administer accounts",
    ),
)

ROLE_DEFINITIONS: dict[Role, RoleDefinition] = {
    Role.USER: RoleDefinition(
        role=Role.USER,
        group_name=Role.USER.value,
        permissions=frozenset(
            {
                VIEW_OWN_PROFILE_PERMISSION,
                CHANGE_OWN_PROFILE_PERMISSION,
            }
        ),
    ),
    Role.SUPPORT: RoleDefinition(
        role=Role.SUPPORT,
        group_name=Role.SUPPORT.value,
        permissions=frozenset({"accounts.access_support_tools"}),
    ),
    Role.CONTENT_MANAGER: RoleDefinition(
        role=Role.CONTENT_MANAGER,
        group_name=Role.CONTENT_MANAGER.value,
        permissions=frozenset({"accounts.manage_catalog_content"}),
    ),
    Role.ADMIN: RoleDefinition(
        role=Role.ADMIN,
        group_name=Role.ADMIN.value,
        permissions=frozenset(
            {
                "accounts.add_user",
                "accounts.view_user",
                "accounts.change_user",
                "accounts.delete_user",
                "accounts.add_userprofile",
                "accounts.view_userprofile",
                "accounts.change_userprofile",
                "accounts.delete_userprofile",
                "accounts.access_support_tools",
                "accounts.manage_catalog_content",
                ADMINISTER_ACCOUNTS_PERMISSION,
            }
        ),
    ),
}


def role_group_names() -> set[str]:
    return {definition.group_name for definition in ROLE_DEFINITIONS.values()}


def normalize_role(role: Role | str) -> Role:
    if isinstance(role, Role):
        return role
    return Role(role)


def ensure_role_groups(*, using: str = "default") -> None:
    permission_by_code = _ensure_permissions(using=using)

    with transaction.atomic(using=using):
        for definition in ROLE_DEFINITIONS.values():
            group, _created = Group.objects.using(using).get_or_create(
                name=definition.group_name,
            )
            permissions = [permission_by_code[code] for code in definition.permissions]
            group.permissions.set(permissions)


def assign_role(user: User, role: Role | str, *, using: str = "default") -> None:
    resolved_role = normalize_role(role)
    ensure_role_groups(using=using)

    role_group = Group.objects.using(using).get(name=ROLE_DEFINITIONS[resolved_role].group_name)
    existing_non_role_groups = user.groups.exclude(name__in=role_group_names())
    user.groups.set([*existing_non_role_groups, role_group])
    _clear_permission_cache(user)


def user_has_role(user: User, role: Role | str) -> bool:
    resolved_role = normalize_role(role)
    return user.groups.filter(name=ROLE_DEFINITIONS[resolved_role].group_name).exists()


def _ensure_permissions(*, using: str) -> dict[str, Permission]:
    permission_by_code: dict[str, Permission] = {}
    content_type_by_model: dict[str, ContentType] = {}

    for definition in PERMISSION_DEFINITIONS:
        content_type = content_type_by_model.get(definition.model)
        if content_type is None:
            content_type, _created = ContentType.objects.db_manager(using).get_or_create(
                app_label="accounts",
                model=definition.model,
            )
            content_type_by_model[definition.model] = content_type

        permission, _created = Permission.objects.db_manager(using).get_or_create(
            content_type=content_type,
            codename=definition.codename,
            defaults={"name": definition.name},
        )
        permission_by_code[definition.code] = permission

    return permission_by_code


def _clear_permission_cache(user: User) -> None:
    for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
        if hasattr(user, cache_name):
            delattr(user, cache_name)
