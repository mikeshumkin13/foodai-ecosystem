from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.rbac import (
    CHANGE_OWN_WORKOUT_LOG_PERMISSION,
    CHANGE_OWN_WORKOUT_PLAN_PERMISSION,
    MANAGE_FITNESS_CATALOG_PERMISSION,
    USE_AI_FITNESS_COACH_PERMISSION,
    VIEW_OWN_WORKOUT_LOG_PERMISSION,
    VIEW_OWN_WORKOUT_PLAN_PERMISSION,
    Role,
    assign_role,
)
from accounts.tests.factories import make_superuser, make_user
from fitness.models import Exercise, WorkoutLog, WorkoutPlan
from fitness.providers import FitnessCoachProviderRequest, FitnessCoachProviderResponse
from fitness.services import generate_workout_plan
from fitness.tests.factories import (
    make_workout,
    make_workout_exercise,
    make_workout_log,
    make_workout_plan,
)

pytestmark = pytest.mark.django_db


class CapturingFitnessProvider:
    name = "capturing"

    def __init__(self) -> None:
        self.requests: list[FitnessCoachProviderRequest] = []

    def explain(self, request: FitnessCoachProviderRequest) -> FitnessCoachProviderResponse:
        self.requests.append(request)
        return FitnessCoachProviderResponse(
            summary="Structured explanation.",
            rationale=("The plan uses structured workout entities.",),
            safety_notes=("General fitness guidance only.",),
        )


class FailingFitnessProvider:
    name = "failing"

    def explain(self, request: FitnessCoachProviderRequest) -> FitnessCoachProviderResponse:
        raise AssertionError("provider_must_not_be_called")


def _plan_detail_url(plan_id: object) -> str:
    return reverse("fitness-plan-detail", kwargs={"id": plan_id})


def _plan_adapt_url(plan_id: object) -> str:
    return reverse("fitness-plan-adapt", kwargs={"id": plan_id})


def _workout_log_detail_url(log_id: object) -> str:
    return reverse("fitness-workout-log-detail", kwargs={"id": log_id})


def _generate_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "goal": WorkoutPlan.Goal.STRENGTH,
        "experience_level": WorkoutPlan.ExperienceLevel.BEGINNER,
        "duration_minutes": 35,
        "sessions_per_week": 2,
        "available_equipment": ["bodyweight", "dumbbells"],
        "message": "Собери план на неделю",
        "locale": "ru",
    }
    payload.update(overrides)
    return payload


def test_user_role_has_fitness_permissions() -> None:
    user = make_user()

    assert user.has_perm(USE_AI_FITNESS_COACH_PERMISSION) is True
    assert user.has_perm(VIEW_OWN_WORKOUT_PLAN_PERMISSION) is True
    assert user.has_perm(CHANGE_OWN_WORKOUT_PLAN_PERMISSION) is True
    assert user.has_perm(VIEW_OWN_WORKOUT_LOG_PERMISSION) is True
    assert user.has_perm(CHANGE_OWN_WORKOUT_LOG_PERMISSION) is True
    assert user.has_perm(MANAGE_FITNESS_CATALOG_PERMISSION) is False


def test_fitness_coach_context_is_structured_and_minimal() -> None:
    user = make_user(email="fitness-private@example.com")
    provider = CapturingFitnessProvider()

    result = generate_workout_plan(
        user=user,
        goal=WorkoutPlan.Goal.STRENGTH,
        experience_level=WorkoutPlan.ExperienceLevel.BEGINNER,
        duration_minutes=35,
        available_equipment=["bodyweight", "dumbbells"],
        sessions_per_week=2,
        message="Please adapt a weekly plan.",
        locale="en",
        provider=provider,
    )

    assert result.code == "fitness_coach_plan_created"
    assert len(provider.requests) == 1
    provider_payload = provider.requests[0].to_payload()
    plan_payload = cast(dict[str, Any], provider_payload["plan"])
    workouts_payload = cast(list[dict[str, Any]], plan_payload["workouts"])
    serialized_payload = json.dumps(provider_payload, ensure_ascii=False)
    assert plan_payload["goal"] == WorkoutPlan.Goal.STRENGTH
    assert plan_payload["experience_level"] == WorkoutPlan.ExperienceLevel.BEGINNER
    assert plan_payload["duration_minutes"] == 35
    assert len(workouts_payload) == 2
    assert "exercise_slug" in workouts_payload[0]["exercises"][0]
    assert user.email not in serialized_payload
    assert str(user.id) not in serialized_payload
    assert "photo" not in serialized_payload
    assert "health" not in serialized_payload


def test_generate_plan_denies_anonymous_user(api_client: APIClient) -> None:
    response = api_client.post(
        reverse("fitness-plan-generate"),
        _generate_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_generate_plan_denies_user_without_role(api_client: APIClient) -> None:
    user = make_user()
    user.groups.clear()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("fitness-plan-generate"),
        _generate_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("role", [Role.SUPPORT, Role.CONTENT_MANAGER, Role.ADMIN])
def test_business_roles_cannot_use_fitness_coach_by_default(
    role: Role,
    api_client: APIClient,
) -> None:
    actor = make_user()
    assign_role(actor, role)
    api_client.force_authenticate(user=actor)

    response = api_client.post(
        reverse("fitness-plan-generate"),
        _generate_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_user_can_generate_structured_workout_plan(api_client: APIClient) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("fitness-plan-generate"),
        _generate_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    plan = payload["plan"]
    assert payload["code"] == "fitness_coach_plan_created"
    assert payload["schema_version"] == "ai_fitness_coach_plan_response_v1"
    assert payload["provider"] == "mock"
    assert payload["safety"]["blocked"] is False
    assert plan["user_id"] == str(user.id)
    assert plan["goal"] == WorkoutPlan.Goal.STRENGTH
    assert plan["experience_level"] == WorkoutPlan.ExperienceLevel.BEGINNER
    assert plan["available_equipment"] == ["bodyweight", "dumbbells"]
    assert len(plan["workouts"]) == 2
    assert plan["workouts"][0]["exercises"]
    first_prescription = plan["workouts"][0]["exercises"][0]
    assert first_prescription["exercise"]["id"]
    assert first_prescription["target_sets"] == 2
    assert "free_text_plan" not in payload
    assert WorkoutPlan.objects.filter(user=user).count() == 1


def test_injury_message_returns_safety_response_without_creating_plan(
    api_client: APIClient,
) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("fitness-plan-generate"),
        _generate_payload(message="У меня острая боль в колене, продолжай нагрузку"),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["code"] == "fitness_coach_safety_blocked"
    assert payload["plan"] is None
    assert payload["safety"]["blocked"] is True
    assert payload["safety"]["categories"] == ["injury_or_acute_pain"]
    assert WorkoutPlan.objects.filter(user=user).count() == 0


def test_user_lists_only_own_plans_and_idor_returns_404(api_client: APIClient) -> None:
    user_a = make_user()
    user_b = make_user()
    own_plan = make_workout_plan(user=user_a)
    other_plan = make_workout_plan(user=user_b)
    api_client.force_authenticate(user=user_a)

    list_response = api_client.get(reverse("fitness-plan-list"))
    detail_response = api_client.get(_plan_detail_url(other_plan.id))

    assert list_response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in list_response.json()] == [str(own_plan.id)]
    assert detail_response.status_code == status.HTTP_404_NOT_FOUND


def test_user_can_adapt_own_plan_without_free_text_replacement(api_client: APIClient) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)
    create_response = api_client.post(
        reverse("fitness-plan-generate"),
        _generate_payload(duration_minutes=35),
        format="json",
    )
    plan_id = create_response.json()["plan"]["id"]

    response = api_client.post(
        _plan_adapt_url(plan_id),
        {
            "duration_minutes": 50,
            "available_equipment": ["bodyweight", "dumbbells", "mat"],
            "message": "Сделай чуть длиннее",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["code"] == "fitness_coach_plan_adapted"
    assert payload["plan"]["id"] == plan_id
    assert payload["plan"]["duration_minutes"] == 50
    assert payload["plan"]["workouts"][0]["exercises"]
    assert "free_text_plan" not in payload


def test_adapt_plan_safety_response_does_not_change_existing_plan(api_client: APIClient) -> None:
    user = make_user()
    plan = make_workout_plan(user=user, duration_minutes=30)
    make_workout_exercise(workout=make_workout(plan=plan))
    api_client.force_authenticate(user=user)

    response = api_client.post(
        _plan_adapt_url(plan.id),
        {"duration_minutes": 60, "message": "Есть резкая боль в груди, продолжай"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["plan"] is None
    assert response.json()["safety"]["blocked"] is True
    plan.refresh_from_db()
    assert plan.duration_minutes == 30


@pytest.mark.parametrize("role", [Role.SUPPORT, Role.CONTENT_MANAGER, Role.ADMIN])
def test_business_roles_cannot_access_private_workout_plans_by_default(
    role: Role,
    api_client: APIClient,
) -> None:
    actor = make_user()
    assign_role(actor, role)
    plan = make_workout_plan()
    api_client.force_authenticate(user=actor)

    list_response = api_client.get(reverse("fitness-plan-list"))
    detail_response = api_client.get(_plan_detail_url(plan.id))

    assert list_response.status_code == status.HTTP_403_FORBIDDEN
    assert detail_response.status_code == status.HTTP_403_FORBIDDEN


def test_superuser_can_read_workout_plan_as_technical_override(api_client: APIClient) -> None:
    superuser = make_superuser()
    plan = make_workout_plan()
    api_client.force_authenticate(user=superuser)

    response = api_client.get(_plan_detail_url(plan.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(plan.id)


def test_user_can_create_workout_log_for_own_workout(api_client: APIClient) -> None:
    user = make_user()
    plan = make_workout_plan(user=user)
    workout = make_workout(plan=plan)
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("fitness-workout-log-list"),
        {
            "workout_id": str(workout.id),
            "performed_at": datetime(2026, 8, 21, 9, 0, tzinfo=UTC).isoformat(),
            "duration_minutes": 28,
            "perceived_exertion": "6.5",
            "completed": True,
            "notes": "Felt controlled.",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["user_id"] == str(user.id)
    assert payload["workout_id"] == str(workout.id)
    assert payload["duration_minutes"] == 28
    assert WorkoutLog.objects.filter(user=user).count() == 1


def test_workout_log_idor_and_cross_user_workout_reference(api_client: APIClient) -> None:
    user_a = make_user()
    user_b = make_user()
    plan_b = make_workout_plan(user=user_b)
    workout_b = make_workout(plan=plan_b)
    log_b = make_workout_log(user=user_b, workout=workout_b)
    api_client.force_authenticate(user=user_a)

    read_response = api_client.get(_workout_log_detail_url(log_b.id))
    create_response = api_client.post(
        reverse("fitness-workout-log-list"),
        {
            "workout_id": str(workout_b.id),
            "performed_at": datetime(2026, 8, 21, 9, 0, tzinfo=UTC).isoformat(),
            "duration_minutes": 30,
        },
        format="json",
    )

    assert read_response.status_code == status.HTTP_404_NOT_FOUND
    assert create_response.status_code == status.HTTP_400_BAD_REQUEST
    assert create_response.json()["workout_id"] == ["invalid_workout"]


def test_exercise_catalog_is_read_only_for_user_and_writable_for_content_manager(
    api_client: APIClient,
) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)
    list_response = api_client.get(reverse("fitness-exercise-list"))
    user_write_response = api_client.post(
        reverse("fitness-exercise-list"),
        {
            "slug": "user_created_exercise",
            "name": "User exercise",
            "equipment": ["bodyweight"],
            "training_goals": [WorkoutPlan.Goal.GENERAL_FITNESS],
        },
        format="json",
    )

    content_manager = make_user()
    assign_role(content_manager, Role.CONTENT_MANAGER)
    api_client.force_authenticate(user=content_manager)
    manager_write_response = api_client.post(
        reverse("fitness-exercise-list"),
        {
            "slug": "content_manager_exercise",
            "name": "Content manager exercise",
            "equipment": ["bodyweight"],
            "training_goals": [WorkoutPlan.Goal.GENERAL_FITNESS],
        },
        format="json",
    )

    assert list_response.status_code == status.HTTP_200_OK
    assert user_write_response.status_code == status.HTTP_403_FORBIDDEN
    assert manager_write_response.status_code == status.HTTP_201_CREATED
    assert Exercise.objects.filter(slug="content_manager_exercise").exists() is True
