from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.contrib.auth import logout
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from accounts.models import NutritionSensitiveRestriction, User
from ai_coach.models import AICoachMessage
from diary.models import Meal
from fitness.models import WorkoutLog, WorkoutPlan
from food_scans.models import FoodScan
from food_scans.storage import get_private_object_storage
from privacy.models import PrivacySettings
from wellbeing.models import WellbeingAssistantMessage

USER_DELETED_FAILURE_CODE = "user_deleted"


class PrivacyServiceError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PrivacyObjectNotFound(PrivacyServiceError):
    pass


class PrivacyAuthenticationError(PrivacyServiceError):
    pass


@dataclass(frozen=True)
class AccountDeletionResult:
    deleted_objects: dict[str, int]


def get_privacy_settings(*, user: User) -> PrivacySettings:
    privacy_settings, _created = PrivacySettings.objects.get_or_create(user=user)
    return privacy_settings


def build_privacy_data_summary(*, user: User) -> dict[str, Any]:
    privacy_settings = get_privacy_settings(user=user)
    return {
        "code": "privacy_data_summary",
        "categories": [
            _category("account", "Account", 1, False, "postgresql", "account_delete"),
            _category(
                "profile",
                "User profile",
                _one_to_one_exists(user, "profile"),
                False,
                "postgresql",
                "account_delete",
            ),
            _category(
                "nutrition_profile",
                "Nutrition profile",
                _one_to_one_exists(user, "nutrition_profile"),
                True,
                "postgresql",
                "account_delete",
            ),
            _category(
                "nutrition_sensitive_restrictions",
                "Sensitive nutrition restrictions",
                NutritionSensitiveRestriction.objects.filter(user=user).count(),
                True,
                "postgresql",
                "account_delete",
            ),
            _category(
                "meals",
                "Food diary",
                Meal.objects.filter(user=user).count(),
                True,
                "postgresql",
                "account_delete",
            ),
            _category(
                "food_photos",
                "Food photos",
                FoodScan.objects.filter(user=user).count(),
                True,
                "postgresql+private_object_storage",
                "individual_delete_or_account_delete",
            ),
            _category(
                "ai_chat_history",
                "AI chat history",
                AICoachMessage.objects.filter(user=user).count()
                + WellbeingAssistantMessage.objects.filter(user=user).count(),
                True,
                "postgresql",
                "ai_history_delete_or_account_delete",
            ),
            _category(
                "workout_plans",
                "Workout plans",
                WorkoutPlan.objects.filter(user=user).count(),
                True,
                "postgresql",
                "account_delete",
            ),
            _category(
                "workout_logs",
                "Workout logs",
                WorkoutLog.objects.filter(user=user).count(),
                True,
                "postgresql",
                "account_delete",
            ),
            _category(
                "privacy_settings",
                "Privacy settings",
                1,
                False,
                "postgresql",
                "account_delete",
            ),
        ],
        "privacy_settings": privacy_settings,
    }


def build_user_data_export(*, user: User) -> dict[str, Any]:
    return {
        "schema_version": "foodai_user_export_v1",
        "exported_at": timezone.now().isoformat(),
        "account": _user_payload(user),
        "profile": _optional_model_payload(
            user,
            "profile",
            ("id", "display_name", "preferred_language"),
        ),
        "nutrition_profile": _optional_model_payload(
            user,
            "nutrition_profile",
            (
                "id",
                "goal",
                "height_cm",
                "mass_kg",
                "age_category",
                "activity_level",
                "preferred_units",
                "dietary_preferences",
                "consent_version",
                "consent_granted_at",
                "consent_revoked_at",
                "created_at",
                "updated_at",
            ),
        ),
        "nutrition_sensitive_restrictions": [
            _model_payload(
                restriction,
                (
                    "id",
                    "restriction_type",
                    "label",
                    "is_active",
                    "consent_version",
                    "consent_granted_at",
                    "created_at",
                    "updated_at",
                ),
            )
            for restriction in user.nutrition_sensitive_restrictions.order_by("created_at", "id")
        ],
        "meals": [_meal_payload(meal) for meal in user.meals.prefetch_related("items").all()],
        "food_scans": [
            _food_scan_payload(scan)
            for scan in user.food_scans.prefetch_related("detected_items").all()
        ],
        "ai_chat_history": [
            _ai_message_payload(message)
            for message in AICoachMessage.objects.filter(user=user).order_by("-created_at")
        ],
        "wellbeing_history": [
            _wellbeing_message_payload(message)
            for message in WellbeingAssistantMessage.objects.filter(user=user).order_by(
                "-created_at"
            )
        ],
        "workout_plans": [
            _workout_plan_payload(plan)
            for plan in user.workout_plans.prefetch_related("workouts__exercises__exercise").all()
        ],
        "workout_logs": [_workout_log_payload(log) for log in user.workout_logs.all()],
        "privacy_settings": _privacy_settings_payload(get_privacy_settings(user=user)),
    }


def build_user_data_export_bytes(*, user: User) -> bytes:
    payload = build_user_data_export(user=user)
    return json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default).encode("utf-8")


def delete_food_scan_photo(*, user: User, food_scan_id: uuid.UUID) -> dict[str, int]:
    try:
        with transaction.atomic():
            food_scan = FoodScan.objects.select_for_update().get(id=food_scan_id, user=user)
            object_key = food_scan.object_key
            food_scan.analysis_run_id = uuid.uuid4()
            food_scan.status = FoodScan.Status.FAILED
            food_scan.failure_code = USER_DELETED_FAILURE_CODE
            food_scan.analysis_task_id = ""
            food_scan.save(
                update_fields=[
                    "analysis_run_id",
                    "status",
                    "failure_code",
                    "analysis_task_id",
                    "updated_at",
                ],
            )
            food_scan.delete()
    except FoodScan.DoesNotExist as exc:
        raise PrivacyObjectNotFound("food_photo_not_found") from exc

    get_private_object_storage().delete(object_key)
    _clear_user_privacy_cache(user_id=user.id)
    return {"food_photos": 1}


def delete_ai_chat_history(*, user: User) -> dict[str, int]:
    ai_deleted, _ai_by_model = AICoachMessage.objects.filter(user=user).delete()
    wellbeing_deleted, _wellbeing_by_model = WellbeingAssistantMessage.objects.filter(
        user=user,
    ).delete()
    _clear_user_privacy_cache(user_id=user.id)
    return {
        "ai_coach_messages": ai_deleted,
        "wellbeing_messages": wellbeing_deleted,
    }


def delete_user_account(
    *,
    user: User,
    current_password: str,
    request: HttpRequest | None = None,
) -> AccountDeletionResult:
    if not user.check_password(current_password):
        raise PrivacyAuthenticationError("invalid_current_password")

    deleted_photo_count = _delete_food_scan_objects_for_user(user=user)
    _delete_user_sessions(user=user)

    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(id=user.id)
        locked_user.is_active = False
        locked_user.save(update_fields=["is_active", "updated_at"])
        deleted_total, deleted_by_model = locked_user.delete()

    if request is not None:
        logout(request)
    _clear_user_privacy_cache(user_id=user.id)
    return AccountDeletionResult(
        deleted_objects={
            "food_photo_objects": deleted_photo_count,
            "postgresql_objects": deleted_total,
            **{label: count for label, count in deleted_by_model.items()},
        }
    )


def _category(
    code: str,
    label: str,
    count: int,
    contains_sensitive_data: bool,
    storage: str,
    deletion: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "label": label,
        "count": count,
        "contains_sensitive_data": contains_sensitive_data,
        "storage": storage,
        "deletion": deletion,
    }


def _one_to_one_exists(user: User, attribute_name: str) -> int:
    try:
        getattr(user, attribute_name)
    except ObjectDoesNotExist:
        return 0
    return 1


def _delete_food_scan_objects_for_user(*, user: User) -> int:
    object_keys = list(FoodScan.objects.filter(user=user).values_list("object_key", flat=True))
    storage = get_private_object_storage()
    for object_key in object_keys:
        storage.delete(object_key)
    FoodScan.objects.filter(user=user).update(
        analysis_run_id=uuid.uuid4(),
        status=FoodScan.Status.FAILED,
        failure_code=USER_DELETED_FAILURE_CODE,
        analysis_task_id="",
        updated_at=timezone.now(),
    )
    return len(object_keys)


def _delete_user_sessions(*, user: User) -> None:
    user_id = str(user.id)
    for session in Session.objects.filter(expire_date__gte=timezone.now()).iterator():
        try:
            session_user_id = session.get_decoded().get("_auth_user_id")
        except Exception:
            continue
        if str(session_user_id) == user_id:
            session.delete()


def _clear_user_privacy_cache(*, user_id: uuid.UUID) -> None:
    cache.delete_many(
        [
            f"privacy:{user_id}:summary",
            f"privacy:{user_id}:export",
            f"user:{user_id}:privacy",
        ]
    )


def _user_payload(user: User) -> dict[str, Any]:
    return _model_payload(
        user,
        ("id", "email", "is_active", "is_staff", "created_at", "updated_at"),
    )


def _optional_model_payload(
    user: User,
    attribute_name: str,
    fields: tuple[str, ...],
) -> dict[str, Any] | None:
    try:
        instance = getattr(user, attribute_name)
    except ObjectDoesNotExist:
        return None
    return _model_payload(instance, fields)


def _model_payload(instance: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: _json_value(getattr(instance, field)) for field in fields}


def _meal_payload(meal: Meal) -> dict[str, Any]:
    payload = _model_payload(
        meal,
        ("id", "meal_type", "logged_at", "name", "created_at", "updated_at"),
    )
    payload["items"] = [
        _model_payload(
            item,
            (
                "id",
                "food_id",
                "food_name_snapshot",
                "food_source_reference_snapshot",
                "mass_g",
                "calories_kcal",
                "protein_g",
                "fat_g",
                "carbs_g",
                "micronutrient_snapshot",
                "nutrient_snapshot",
                "source",
                "confidence",
                "manually_corrected",
                "created_at",
                "updated_at",
            ),
        )
        for item in meal.items.all()
    ]
    return payload


def _food_scan_payload(food_scan: FoodScan) -> dict[str, Any]:
    payload = _model_payload(
        food_scan,
        (
            "id",
            "status",
            "image_format",
            "content_type",
            "uploaded_byte_size",
            "stored_byte_size",
            "width",
            "height",
            "exif_stripped",
            "failure_code",
            "created_at",
            "updated_at",
        ),
    )
    payload["has_private_photo"] = True
    payload["detected_items"] = [
        _model_payload(
            item,
            (
                "id",
                "matched_food_id",
                "label",
                "confidence",
                "estimated_mass_g",
                "portion_estimated_volume_ml",
                "portion_estimated_mass_g",
                "portion_min_mass_g",
                "portion_max_mass_g",
                "portion_confidence",
                "portion_estimation_method",
                "manual_mass_g",
                "food_name_snapshot",
                "calories_kcal",
                "protein_g",
                "fat_g",
                "carbs_g",
                "micronutrient_snapshot",
                "nutrient_snapshot",
                "source",
                "is_removed",
                "manually_corrected",
                "created_at",
                "updated_at",
            ),
        )
        for item in food_scan.detected_items.all()
    ]
    return payload


def _ai_message_payload(message: AICoachMessage) -> dict[str, Any]:
    return _model_payload(
        message,
        (
            "id",
            "context_date",
            "request_text",
            "response_payload",
            "context_snapshot",
            "provider_name",
            "output_schema_version",
            "safety_status",
            "created_at",
        ),
    )


def _wellbeing_message_payload(message: WellbeingAssistantMessage) -> dict[str, Any]:
    return _model_payload(
        message,
        (
            "id",
            "context_date",
            "request_text",
            "response_payload",
            "context_snapshot",
            "provider_name",
            "output_schema_version",
            "safety_status",
            "created_at",
        ),
    )


def _workout_plan_payload(plan: WorkoutPlan) -> dict[str, Any]:
    payload = _model_payload(
        plan,
        (
            "id",
            "title",
            "goal",
            "experience_level",
            "duration_minutes",
            "sessions_per_week",
            "available_equipment",
            "ai_explanation",
            "safety_warnings",
            "status",
            "created_at",
            "updated_at",
        ),
    )
    payload["workouts"] = [
        {
            **_model_payload(
                workout,
                (
                    "id",
                    "week_number",
                    "day_number",
                    "order",
                    "title",
                    "focus",
                    "estimated_duration_minutes",
                    "created_at",
                    "updated_at",
                ),
            ),
            "exercises": [
                _model_payload(
                    workout_exercise,
                    (
                        "id",
                        "exercise_id",
                        "order",
                        "target_sets",
                        "target_reps_min",
                        "target_reps_max",
                        "target_duration_seconds",
                        "rest_seconds",
                        "intensity",
                        "coaching_notes",
                        "created_at",
                        "updated_at",
                    ),
                )
                for workout_exercise in workout.exercises.all()
            ],
        }
        for workout in plan.workouts.all()
    ]
    return payload


def _workout_log_payload(log: WorkoutLog) -> dict[str, Any]:
    return _model_payload(
        log,
        (
            "id",
            "workout_id",
            "performed_at",
            "duration_minutes",
            "perceived_exertion",
            "completed",
            "notes",
            "created_at",
            "updated_at",
        ),
    )


def _privacy_settings_payload(privacy_settings: PrivacySettings) -> dict[str, Any]:
    return {
        **_model_payload(
            privacy_settings,
            (
                "id",
                "model_improvement_consent_version",
                "model_improvement_consent_granted_at",
                "model_improvement_consent_revoked_at",
                "food_photo_training_consent_version",
                "food_photo_training_consent_granted_at",
                "food_photo_training_consent_revoked_at",
                "created_at",
                "updated_at",
            ),
        ),
        "model_improvement_enabled": privacy_settings.has_model_improvement_consent,
        "food_photo_training_enabled": privacy_settings.has_food_photo_training_consent,
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID | datetime | date | Decimal):
        return str(value)
    return value


def _json_default(value: Any) -> str:
    if isinstance(value, uuid.UUID | datetime | date | Decimal):
        return str(value)
    msg = f"Object of type {type(value).__name__} is not JSON serializable"
    raise TypeError(msg)
