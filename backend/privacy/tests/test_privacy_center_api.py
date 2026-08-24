from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from accounts.rbac import (
    CHANGE_OWN_PRIVACY_SETTINGS_PERMISSION,
    DELETE_OWN_DATA_PERMISSION,
    EXPORT_OWN_DATA_PERMISSION,
    VIEW_OWN_PRIVACY_SETTINGS_PERMISSION,
    Role,
    assign_role,
)
from accounts.tests.factories import make_nutrition_profile, make_user, make_user_profile
from ai_coach.models import AICoachMessage
from diary.models import Meal
from food_scans.models import FoodScan
from food_scans.storage import get_private_object_storage
from food_scans.tasks import process_food_scan_analysis_task
from privacy.models import PrivacySettings
from wellbeing.models import WellbeingAssistantMessage

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def privacy_storage_settings(settings: Any, tmp_path: Path) -> None:
    settings.FOOD_SCAN_PRIVATE_STORAGE_BACKEND = "local"
    settings.FOOD_SCAN_PRIVATE_MEDIA_ROOT = str(tmp_path / "private")


def test_user_role_receives_privacy_permissions_by_default() -> None:
    user = make_user()

    assert user.has_perm(VIEW_OWN_PRIVACY_SETTINGS_PERMISSION) is True
    assert user.has_perm(CHANGE_OWN_PRIVACY_SETTINGS_PERMISSION) is True
    assert user.has_perm(EXPORT_OWN_DATA_PERMISSION) is True
    assert user.has_perm(DELETE_OWN_DATA_PERMISSION) is True


@pytest.mark.parametrize("role", [Role.SUPPORT, Role.CONTENT_MANAGER, Role.ADMIN])
def test_non_user_business_roles_do_not_receive_privacy_center_api_access(
    api_client: APIClient,
    role: Role,
) -> None:
    actor = make_user()
    assign_role(actor, role)
    api_client.force_authenticate(user=actor)

    response = api_client.get(reverse("privacy-data-summary"))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_privacy_summary_defaults_model_training_consent_to_false(
    api_client: APIClient,
) -> None:
    user = make_user()
    make_user_profile(user=user)
    make_nutrition_profile(user=user)
    Meal.objects.create(user=user, meal_type=Meal.MealType.LUNCH, logged_at=timezone.now())
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("privacy-data-summary"))

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    categories = {category["code"]: category for category in payload["categories"]}
    assert categories["account"]["count"] == 1
    assert categories["nutrition_profile"]["contains_sensitive_data"] is True
    assert categories["meals"]["count"] == 1
    assert payload["privacy_settings"]["model_improvement_enabled"] is False
    assert payload["privacy_settings"]["food_photo_training_enabled"] is False


def test_user_can_grant_and_revoke_model_improvement_and_photo_training_consent(
    api_client: APIClient,
) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    accept_response = api_client.patch(
        reverse("privacy-consent"),
        {
            "model_improvement_consent_accepted": True,
            "food_photo_training_consent_accepted": True,
        },
        format="json",
    )
    revoke_response = api_client.patch(
        reverse("privacy-consent"),
        {"model_improvement_consent_revoked": True},
        format="json",
    )

    assert accept_response.status_code == status.HTTP_200_OK
    assert accept_response.json()["model_improvement_enabled"] is True
    assert accept_response.json()["food_photo_training_enabled"] is True
    assert revoke_response.status_code == status.HTTP_200_OK
    assert revoke_response.json()["model_improvement_enabled"] is False
    assert revoke_response.json()["food_photo_training_enabled"] is False


def test_food_photo_training_consent_requires_model_improvement_consent(
    api_client: APIClient,
) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse("privacy-consent"),
        {"food_photo_training_consent_accepted": True},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["non_field_errors"] == ["model_improvement_consent_required_for_photos"]


def test_data_export_downloads_own_data_without_password_or_private_object_key(
    api_client: APIClient,
) -> None:
    user = make_user(password="SafePassword123!")
    make_user_profile(user=user, display_name="Owner")
    make_nutrition_profile(user=user)
    scan = _make_food_scan(user=user, object_key="food-scans/export/test.jpg")
    _make_ai_message(user=user, request_text="How did I do today?")
    _make_wellbeing_message(user=user, request_text="Help me plan a habit")
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("privacy-data-export"))

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["Content-Disposition"].startswith("attachment;")
    body = response.content.decode("utf-8")
    assert "Owner" in body
    assert "How did I do today?" in body
    assert "SafePassword123!" not in body
    assert "password" not in body.lower()
    assert scan.object_key not in body
    assert "has_private_photo" in body


def test_user_can_delete_own_food_photo_from_postgresql_and_private_storage(
    api_client: APIClient,
) -> None:
    user = make_user()
    food_scan = _make_food_scan(user=user)
    storage = get_private_object_storage()
    storage.save(food_scan.object_key, b"private-image")
    assert storage.exists(food_scan.object_key) is True
    api_client.force_authenticate(user=user)

    response = api_client.delete(
        reverse("privacy-food-photo-delete", kwargs={"scan_id": food_scan.id})
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"code": "food_photo_deleted", "deleted": {"food_photos": 1}}
    assert FoodScan.objects.filter(id=food_scan.id).exists() is False
    assert storage.exists(food_scan.object_key) is False


def test_user_cannot_delete_another_users_food_photo_by_uuid(api_client: APIClient) -> None:
    user = make_user()
    other_user = make_user()
    food_scan = _make_food_scan(user=other_user)
    storage = get_private_object_storage()
    storage.save(food_scan.object_key, b"private-image")
    api_client.force_authenticate(user=user)

    response = api_client.delete(
        reverse("privacy-food-photo-delete", kwargs={"scan_id": food_scan.id})
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert FoodScan.objects.filter(id=food_scan.id).exists() is True
    assert storage.exists(food_scan.object_key) is True


def test_stale_background_task_skips_after_food_photo_deletion(
    api_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    run_id = uuid.uuid4()
    task_id = f"food-scan-analysis-test-{run_id}"
    food_scan = _make_food_scan(user=user, analysis_run_id=run_id, analysis_task_id=task_id)
    get_private_object_storage().save(food_scan.object_key, b"private-image")

    def fail_process_scan(*args: object, **kwargs: object) -> None:
        raise AssertionError("deleted scan must not call Vision or orchestration")

    monkeypatch.setattr("food_scans.tasks.process_scan_analysis", fail_process_scan)
    api_client.force_authenticate(user=user)

    delete_response = api_client.delete(
        reverse("privacy-food-photo-delete", kwargs={"scan_id": food_scan.id})
    )
    task_result = process_food_scan_analysis_task.apply(
        args=[str(food_scan.id), str(run_id)],
        task_id=task_id,
    ).get()

    assert delete_response.status_code == status.HTTP_200_OK
    assert task_result == {"status": "skipped", "reason": "stale_or_confirmed_scan"}


def test_delete_ai_chat_history_removes_only_current_users_messages(
    api_client: APIClient,
) -> None:
    user = make_user()
    other_user = make_user()
    _make_ai_message(user=user, request_text="Owner nutrition")
    _make_ai_message(user=other_user, request_text="Other nutrition")
    _make_wellbeing_message(user=user, request_text="Owner habit")
    _make_wellbeing_message(user=other_user, request_text="Other habit")
    api_client.force_authenticate(user=user)

    response = api_client.delete(reverse("privacy-ai-chat-history-delete"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["deleted"] == {"ai_coach_messages": 1, "wellbeing_messages": 1}
    assert AICoachMessage.objects.filter(user=user).exists() is False
    assert WellbeingAssistantMessage.objects.filter(user=user).exists() is False
    assert AICoachMessage.objects.filter(user=other_user).count() == 1
    assert WellbeingAssistantMessage.objects.filter(user=other_user).count() == 1


def test_account_deletion_requires_current_password(api_client: APIClient) -> None:
    user = make_user(password="SafePassword123!")
    api_client.force_authenticate(user=user)

    response = api_client.delete(
        reverse("privacy-account-delete"),
        {"current_password": "wrong-password"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert User.objects.filter(id=user.id).exists() is True


def test_account_deletion_removes_database_rows_storage_sessions_and_cache(
    api_client: APIClient,
) -> None:
    user = make_user(password="SafePassword123!")
    make_user_profile(user=user)
    make_nutrition_profile(user=user)
    PrivacySettings.objects.create(user=user)
    food_scan = _make_food_scan(user=user)
    storage = get_private_object_storage()
    storage.save(food_scan.object_key, b"private-image")
    _make_ai_message(user=user, request_text="Delete this AI history")
    _make_wellbeing_message(user=user, request_text="Delete this wellbeing history")
    session_key = _create_authenticated_session(user)
    cache_key = f"user:{user.id}:privacy"
    cache.set(cache_key, "cached", timeout=60)
    api_client.force_authenticate(user=user)

    response = api_client.delete(
        reverse("privacy-account-delete"),
        {"current_password": "SafePassword123!"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["code"] == "account_deleted"
    assert User.objects.filter(id=user.id).exists() is False
    assert AICoachMessage.objects.filter(user_id=user.id).exists() is False
    assert WellbeingAssistantMessage.objects.filter(user_id=user.id).exists() is False
    assert FoodScan.objects.filter(id=food_scan.id).exists() is False
    assert storage.exists(food_scan.object_key) is False
    assert Session.objects.filter(session_key=session_key).exists() is False
    assert cache.get(cache_key) is None


def _make_food_scan(
    *,
    user: User,
    object_key: str | None = None,
    analysis_run_id: uuid.UUID | None = None,
    analysis_task_id: str = "",
) -> FoodScan:
    scan_id = uuid.uuid4()
    return FoodScan.objects.create(
        id=scan_id,
        user=user,
        status=FoodScan.Status.UPLOADED,
        storage_backend="local",
        object_key=object_key or f"food-scans/privacy/{scan_id.hex}.jpg",
        image_format=FoodScan.ImageFormat.JPEG,
        content_type="image/jpeg",
        uploaded_byte_size=128,
        stored_byte_size=120,
        width=12,
        height=10,
        checksum_sha256="c" * 64,
        analysis_run_id=analysis_run_id,
        analysis_task_id=analysis_task_id,
    )


def _make_ai_message(*, user: User, request_text: str) -> AICoachMessage:
    return AICoachMessage.objects.create(
        user=user,
        context_date=timezone.localdate(),
        request_text=request_text,
        response_payload={"answer": "ok"},
        context_snapshot={"goal": "maintain_weight"},
        provider_name="mock",
        output_schema_version="ai_nutrition_coach_response_v1",
    )


def _make_wellbeing_message(*, user: User, request_text: str) -> WellbeingAssistantMessage:
    return WellbeingAssistantMessage.objects.create(
        user=user,
        context_date=timezone.localdate(),
        request_text=request_text,
        response_payload={"answer": "ok"},
        context_snapshot={"focus_areas": ["habits"]},
        provider_name="mock",
        output_schema_version="ai_wellbeing_assistant_response_v1",
    )


def _create_authenticated_session(user: User) -> str:
    session = SessionStore()
    session["_auth_user_id"] = str(user.id)
    session.save()
    return str(session.session_key)
