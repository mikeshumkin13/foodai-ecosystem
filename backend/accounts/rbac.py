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
    app_label: str = "accounts"

    @property
    def code(self) -> str:
        return f"{self.app_label}.{self.codename}"


@dataclass(frozen=True)
class RoleDefinition:
    role: Role
    group_name: str
    permissions: frozenset[str]


VIEW_OWN_PROFILE_PERMISSION = "accounts.view_own_userprofile"
CHANGE_OWN_PROFILE_PERMISSION = "accounts.change_own_userprofile"
VIEW_OWN_NUTRITION_PROFILE_PERMISSION = "accounts.view_own_nutritionprofile"
CHANGE_OWN_NUTRITION_PROFILE_PERMISSION = "accounts.change_own_nutritionprofile"
VIEW_OWN_NUTRITION_RESTRICTION_PERMISSION = "accounts.view_own_nutritionsensitiverestriction"
CHANGE_OWN_NUTRITION_RESTRICTION_PERMISSION = "accounts.change_own_nutritionsensitiverestriction"
ADMINISTER_ACCOUNTS_PERMISSION = "accounts.administer_accounts"
VIEW_ADMIN_AUDIT_LOG_PERMISSION = "accounts.view_adminauditlog"
VIEW_SUPPORT_ADMIN_PERMISSION = "accounts.view_support_admin"
MANAGE_REFERENCE_DATA_PERMISSION = "accounts.manage_reference_data"
MANAGE_FOOD_CATALOG_PERMISSION = "accounts.manage_food_catalog"
VIEW_ROLE_GROUP_PERMISSION = "auth.view_group"
CHANGE_ROLE_GROUP_PERMISSION = "auth.change_group"
VIEW_OWN_MEAL_PERMISSION = "diary.view_own_meal"
CHANGE_OWN_MEAL_PERMISSION = "diary.change_own_meal"
VIEW_OWN_FOOD_SCAN_PERMISSION = "food_scans.view_own_foodscan"
CHANGE_OWN_FOOD_SCAN_PERMISSION = "food_scans.change_own_foodscan"
USE_AI_COACH_PERMISSION = "ai_coach.use_ai_nutrition_coach"
VIEW_OWN_AI_COACH_SETTINGS_PERMISSION = "ai_coach.view_own_aicoachsettings"
CHANGE_OWN_AI_COACH_SETTINGS_PERMISSION = "ai_coach.change_own_aicoachsettings"
NUTRITION_CATALOG_MODEL_PERMISSIONS = frozenset(
    {
        "nutrition.add_foodcategory",
        "nutrition.view_foodcategory",
        "nutrition.change_foodcategory",
        "nutrition.delete_foodcategory",
        "nutrition.add_fooddatasource",
        "nutrition.view_fooddatasource",
        "nutrition.change_fooddatasource",
        "nutrition.delete_fooddatasource",
        "nutrition.add_nutrient",
        "nutrition.view_nutrient",
        "nutrition.change_nutrient",
        "nutrition.delete_nutrient",
        "nutrition.add_fooditem",
        "nutrition.view_fooditem",
        "nutrition.change_fooditem",
        "nutrition.delete_fooditem",
        "nutrition.add_foodnutrient",
        "nutrition.view_foodnutrient",
        "nutrition.change_foodnutrient",
        "nutrition.delete_foodnutrient",
    }
)

PERMISSION_DEFINITIONS: tuple[PermissionDefinition, ...] = (
    PermissionDefinition(
        codename="view_group",
        model="group",
        name="Can view group",
        app_label="auth",
    ),
    PermissionDefinition(
        codename="change_group",
        model="group",
        name="Can change group",
        app_label="auth",
    ),
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
        codename="view_own_nutritionprofile",
        model="nutritionprofile",
        name="Can view own nutrition profile",
    ),
    PermissionDefinition(
        codename="change_own_nutritionprofile",
        model="nutritionprofile",
        name="Can change own nutrition profile",
    ),
    PermissionDefinition(
        codename="view_own_nutritionsensitiverestriction",
        model="nutritionsensitiverestriction",
        name="Can view own nutrition sensitive restriction",
    ),
    PermissionDefinition(
        codename="change_own_nutritionsensitiverestriction",
        model="nutritionsensitiverestriction",
        name="Can change own nutrition sensitive restriction",
    ),
    PermissionDefinition(
        codename="view_adminauditlog",
        model="adminauditlog",
        name="Can view admin audit log",
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
        codename="view_support_admin",
        model="rolepermission",
        name="Can view support admin tools without private user data",
    ),
    PermissionDefinition(
        codename="manage_reference_data",
        model="rolepermission",
        name="Can manage shared reference data",
    ),
    PermissionDefinition(
        codename="manage_food_catalog",
        model="rolepermission",
        name="Can manage future food catalog content",
    ),
    PermissionDefinition(
        codename="administer_accounts",
        model="rolepermission",
        name="Can administer accounts",
    ),
    PermissionDefinition(
        codename="add_foodcategory",
        model="foodcategory",
        name="Can add food category",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="view_foodcategory",
        model="foodcategory",
        name="Can view food category",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="change_foodcategory",
        model="foodcategory",
        name="Can change food category",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="delete_foodcategory",
        model="foodcategory",
        name="Can delete food category",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="add_fooddatasource",
        model="fooddatasource",
        name="Can add food data source",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="view_fooddatasource",
        model="fooddatasource",
        name="Can view food data source",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="change_fooddatasource",
        model="fooddatasource",
        name="Can change food data source",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="delete_fooddatasource",
        model="fooddatasource",
        name="Can delete food data source",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="add_nutrient",
        model="nutrient",
        name="Can add nutrient",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="view_nutrient",
        model="nutrient",
        name="Can view nutrient",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="change_nutrient",
        model="nutrient",
        name="Can change nutrient",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="delete_nutrient",
        model="nutrient",
        name="Can delete nutrient",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="add_fooditem",
        model="fooditem",
        name="Can add food item",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="view_fooditem",
        model="fooditem",
        name="Can view food item",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="change_fooditem",
        model="fooditem",
        name="Can change food item",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="delete_fooditem",
        model="fooditem",
        name="Can delete food item",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="add_foodnutrient",
        model="foodnutrient",
        name="Can add food nutrient",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="view_foodnutrient",
        model="foodnutrient",
        name="Can view food nutrient",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="change_foodnutrient",
        model="foodnutrient",
        name="Can change food nutrient",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="delete_foodnutrient",
        model="foodnutrient",
        name="Can delete food nutrient",
        app_label="nutrition",
    ),
    PermissionDefinition(
        codename="view_own_meal",
        model="meal",
        name="Can view own meal",
        app_label="diary",
    ),
    PermissionDefinition(
        codename="change_own_meal",
        model="meal",
        name="Can change own meal",
        app_label="diary",
    ),
    PermissionDefinition(
        codename="view_own_foodscan",
        model="foodscan",
        name="Can view own food scan",
        app_label="food_scans",
    ),
    PermissionDefinition(
        codename="change_own_foodscan",
        model="foodscan",
        name="Can change own food scan",
        app_label="food_scans",
    ),
    PermissionDefinition(
        codename="use_ai_nutrition_coach",
        model="aicoachsettings",
        name="Can use AI nutrition coach",
        app_label="ai_coach",
    ),
    PermissionDefinition(
        codename="view_own_aicoachsettings",
        model="aicoachsettings",
        name="Can view own AI coach settings",
        app_label="ai_coach",
    ),
    PermissionDefinition(
        codename="change_own_aicoachsettings",
        model="aicoachsettings",
        name="Can change own AI coach settings",
        app_label="ai_coach",
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
                VIEW_OWN_NUTRITION_PROFILE_PERMISSION,
                CHANGE_OWN_NUTRITION_PROFILE_PERMISSION,
                VIEW_OWN_NUTRITION_RESTRICTION_PERMISSION,
                CHANGE_OWN_NUTRITION_RESTRICTION_PERMISSION,
                VIEW_OWN_MEAL_PERMISSION,
                CHANGE_OWN_MEAL_PERMISSION,
                VIEW_OWN_FOOD_SCAN_PERMISSION,
                CHANGE_OWN_FOOD_SCAN_PERMISSION,
                USE_AI_COACH_PERMISSION,
                VIEW_OWN_AI_COACH_SETTINGS_PERMISSION,
                CHANGE_OWN_AI_COACH_SETTINGS_PERMISSION,
            }
        ),
    ),
    Role.SUPPORT: RoleDefinition(
        role=Role.SUPPORT,
        group_name=Role.SUPPORT.value,
        permissions=frozenset(
            {
                "accounts.access_support_tools",
                VIEW_SUPPORT_ADMIN_PERMISSION,
            }
        ),
    ),
    Role.CONTENT_MANAGER: RoleDefinition(
        role=Role.CONTENT_MANAGER,
        group_name=Role.CONTENT_MANAGER.value,
        permissions=frozenset(
            {
                "accounts.manage_catalog_content",
                MANAGE_REFERENCE_DATA_PERMISSION,
                MANAGE_FOOD_CATALOG_PERMISSION,
                *NUTRITION_CATALOG_MODEL_PERMISSIONS,
            }
        ),
    ),
    Role.ADMIN: RoleDefinition(
        role=Role.ADMIN,
        group_name=Role.ADMIN.value,
        permissions=frozenset(
            {
                VIEW_ROLE_GROUP_PERMISSION,
                CHANGE_ROLE_GROUP_PERMISSION,
                "accounts.add_user",
                "accounts.view_user",
                "accounts.change_user",
                "accounts.delete_user",
                "accounts.add_userprofile",
                "accounts.view_userprofile",
                "accounts.change_userprofile",
                "accounts.delete_userprofile",
                VIEW_ADMIN_AUDIT_LOG_PERMISSION,
                "accounts.access_support_tools",
                "accounts.manage_catalog_content",
                VIEW_SUPPORT_ADMIN_PERMISSION,
                MANAGE_REFERENCE_DATA_PERMISSION,
                MANAGE_FOOD_CATALOG_PERMISSION,
                *NUTRITION_CATALOG_MODEL_PERMISSIONS,
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
    content_type_by_model: dict[tuple[str, str], ContentType] = {}

    for definition in PERMISSION_DEFINITIONS:
        content_type_key = (definition.app_label, definition.model)
        content_type = content_type_by_model.get(content_type_key)
        if content_type is None:
            content_type, _created = ContentType.objects.db_manager(using).get_or_create(
                app_label=definition.app_label,
                model=definition.model,
            )
            content_type_by_model[content_type_key] = content_type

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
