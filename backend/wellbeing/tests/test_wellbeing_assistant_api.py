from __future__ import annotations

import json
from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.rbac import (
    CHANGE_OWN_WELLBEING_ASSISTANT_SETTINGS_PERMISSION,
    USE_WELLBEING_ASSISTANT_PERMISSION,
    VIEW_OWN_WELLBEING_ASSISTANT_SETTINGS_PERMISSION,
    Role,
    assign_role,
)
from accounts.tests.factories import make_user, make_user_profile
from wellbeing.models import WellbeingAssistantMessage
from wellbeing.providers import (
    WellbeingAssistantProviderRequest,
    WellbeingAssistantProviderResponse,
    WellbeingSmallAction,
)
from wellbeing.services import ask_wellbeing_assistant, get_wellbeing_assistant_settings

pytestmark = pytest.mark.django_db


class CapturingWellbeingProvider:
    name = "capturing"

    def __init__(self, response: WellbeingAssistantProviderResponse | None = None) -> None:
        self.requests: list[WellbeingAssistantProviderRequest] = []
        self.response = response or WellbeingAssistantProviderResponse(
            answer="General habit support response.",
            focus_area="habit_formation",
            small_actions=(
                WellbeingSmallAction(
                    title="Tiny action",
                    description="Do one small repeatable action today.",
                    timeframe="today",
                ),
            ),
            reflection_prompts=("What made this easier before?",),
            adherence_strategy="Attach the action to an existing daily cue.",
            warnings=("general_wellbeing_support_only",),
        )

    def generate(
        self,
        request: WellbeingAssistantProviderRequest,
    ) -> WellbeingAssistantProviderResponse:
        self.requests.append(request)
        return self.response


class FailingWellbeingProvider:
    name = "failing"

    def generate(
        self,
        request: WellbeingAssistantProviderRequest,
    ) -> WellbeingAssistantProviderResponse:
        raise AssertionError("provider_must_not_be_called")


def _ask_url() -> str:
    return reverse("wellbeing-ask")


def _settings_url() -> str:
    return reverse("wellbeing-settings")


def test_user_role_has_wellbeing_assistant_permissions() -> None:
    user = make_user()

    assert user.has_perm(USE_WELLBEING_ASSISTANT_PERMISSION) is True
    assert user.has_perm(VIEW_OWN_WELLBEING_ASSISTANT_SETTINGS_PERMISSION) is True
    assert user.has_perm(CHANGE_OWN_WELLBEING_ASSISTANT_SETTINGS_PERMISSION) is True


def test_wellbeing_provider_context_is_minimal_and_structured() -> None:
    user = make_user(email="wellbeing-private@example.com")
    make_user_profile(user=user, display_name="Private Name", preferred_language="en")
    provider = CapturingWellbeingProvider()

    result = ask_wellbeing_assistant(
        user=user,
        message="Help me make my evening walk habit stick.",
        context_date=date(2026, 8, 21),
        provider=provider,
    )

    assert result.code == "wellbeing_assistant_response"
    assert len(provider.requests) == 1
    provider_payload = provider.requests[0].to_payload()
    serialized_payload = json.dumps(provider_payload, ensure_ascii=False)
    assert provider_payload == {
        "output_schema_version": "ai_wellbeing_assistant_response_v1",
        "context": {
            "schema_version": "wellbeing_assistant_context_v1",
            "locale": "en",
            "date": "2026-08-21",
            "allowed_focus_areas": [
                "habit_formation",
                "adherence",
                "routine",
                "motivation_strategy",
                "reflection",
                "small_action_planning",
            ],
            "user_request": "Help me make my evening walk habit stick.",
        },
    }
    assert user.email not in serialized_payload
    assert str(user.id) not in serialized_payload
    assert "Private Name" not in serialized_payload
    assert "display_name" not in serialized_payload
    assert "photo" not in serialized_payload
    assert "health" not in serialized_payload
    assert "diary" not in serialized_payload


def test_wellbeing_ask_denies_anonymous_user(api_client: APIClient) -> None:
    response = api_client.post(_ask_url(), {"message": "Помоги с привычкой"}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_wellbeing_ask_denies_user_without_role(api_client: APIClient) -> None:
    user = make_user()
    user.groups.clear()
    api_client.force_authenticate(user=user)

    response = api_client.post(_ask_url(), {"message": "Помоги с привычкой"}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("role", [Role.SUPPORT, Role.CONTENT_MANAGER, Role.ADMIN])
def test_business_roles_cannot_use_wellbeing_assistant_by_default(
    role: Role,
    api_client: APIClient,
) -> None:
    actor = make_user()
    assign_role(actor, role)
    api_client.force_authenticate(user=actor)

    response = api_client.post(_ask_url(), {"message": "Помоги с привычкой"}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_user_can_ask_wellbeing_assistant_without_storage_by_default(
    api_client: APIClient,
) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        _ask_url(),
        {"message": "Как закрепить вечернюю прогулку?", "date": "2026-08-21"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["code"] == "wellbeing_assistant_response"
    assert payload["schema_version"] == "ai_wellbeing_assistant_response_v1"
    assert payload["context_date"] == "2026-08-21"
    assert payload["provider"] == "mock"
    assert payload["stored"] is False
    assert payload["storage_reason"] == "not_requested"
    assert payload["safety"] == {
        "blocked": False,
        "code": "passed",
        "categories": [],
        "reason": "",
        "urgent_support_recommended": False,
    }
    assert payload["small_actions"]
    assert payload["reflection_prompts"]
    assert WellbeingAssistantMessage.objects.count() == 0


def test_store_response_request_without_consent_does_not_persist_message(
    api_client: APIClient,
) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        _ask_url(),
        {
            "message": "Помоги выбрать маленький шаг для режима",
            "date": "2026-08-21",
            "store_response": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["stored"] is False
    assert response.json()["storage_reason"] == "consent_required"
    assert WellbeingAssistantMessage.objects.count() == 0


def test_user_can_grant_and_revoke_wellbeing_history_consent(api_client: APIClient) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    initial_response = api_client.get(_settings_url())
    grant_response = api_client.patch(
        _settings_url(),
        {"history_consent_accepted": True},
        format="json",
    )
    revoke_response = api_client.patch(
        _settings_url(),
        {"history_consent_revoked": True},
        format="json",
    )

    assert initial_response.status_code == status.HTTP_200_OK
    assert initial_response.json()["history_enabled"] is False
    assert "user_id" not in initial_response.json()
    assert grant_response.status_code == status.HTTP_200_OK
    assert grant_response.json()["history_enabled"] is True
    assert grant_response.json()["history_consent_version"] == (
        "wellbeing_assistant_history_mvp_v1"
    )
    assert revoke_response.status_code == status.HTTP_200_OK
    assert revoke_response.json()["history_enabled"] is False


def test_safe_response_is_stored_only_after_history_consent(api_client: APIClient) -> None:
    user = make_user(email="consented-wellbeing@example.com")
    assistant_settings = get_wellbeing_assistant_settings(user=user)
    assistant_settings.grant_history_consent()
    assistant_settings.save()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        _ask_url(),
        {
            "message": "Помоги закрепить привычку пить воду после завтрака",
            "date": "2026-08-21",
            "store_response": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["stored"] is True
    assert response.json()["storage_reason"] == "stored"
    message = WellbeingAssistantMessage.objects.get()
    serialized_context = json.dumps(message.context_snapshot, ensure_ascii=False)
    assert message.request_text == "Помоги закрепить привычку пить воду после завтрака"
    assert message.response_payload["stored"] is True
    assert message.provider_name == "mock"
    assert message.safety_status == WellbeingAssistantMessage.SafetyStatus.PASSED
    assert "consented-wellbeing@example.com" not in serialized_context
    assert str(user.id) not in serialized_context


def test_sensitive_non_crisis_message_is_not_persisted_even_with_consent() -> None:
    user = make_user()
    assistant_settings = get_wellbeing_assistant_settings(user=user)
    assistant_settings.grant_history_consent()
    assistant_settings.save()
    provider = CapturingWellbeingProvider()

    result = ask_wellbeing_assistant(
        user=user,
        message="У меня тревога, помоги выбрать маленький шаг для режима",
        context_date=date(2026, 8, 21),
        store_response=True,
        provider=provider,
    )

    assert len(provider.requests) == 1
    assert result.code == "wellbeing_assistant_response"
    assert result.safety.blocked is False
    assert result.stored is False
    assert result.storage_reason == "sensitive_content_not_stored"
    assert WellbeingAssistantMessage.objects.count() == 0


def test_self_harm_message_returns_safety_response_without_provider_or_storage() -> None:
    user = make_user()

    result = ask_wellbeing_assistant(
        user=user,
        message="Я не хочу жить и хочу убить себя",
        context_date=date(2026, 8, 21),
        store_response=True,
        provider=FailingWellbeingProvider(),
    )

    assert result.code == "wellbeing_assistant_safety_blocked"
    assert result.safety.blocked is True
    assert result.safety.categories == ("self_harm_or_suicidal_ideation",)
    assert result.safety.urgent_support_recommended is True
    assert result.provider_name == "safety_layer"
    assert result.stored is False
    assert result.storage_reason == "safety_blocked"
    assert WellbeingAssistantMessage.objects.count() == 0


def test_medical_or_clinical_diagnosis_request_is_blocked_before_provider() -> None:
    user = make_user()

    result = ask_wellbeing_assistant(
        user=user,
        message="Поставь диагноз, у меня депрессия, и назначь лекарство",
        context_date=date(2026, 8, 21),
        provider=FailingWellbeingProvider(),
    )

    assert result.code == "wellbeing_assistant_safety_blocked"
    assert result.safety.blocked is True
    assert result.safety.categories == ("medical_or_clinical_decision",)
    assert result.provider_name == "safety_layer"
    assert result.stored is False
    assert WellbeingAssistantMessage.objects.count() == 0


def test_unsafe_provider_output_is_blocked_and_not_stored() -> None:
    user = make_user()
    assistant_settings = get_wellbeing_assistant_settings(user=user)
    assistant_settings.grant_history_consent()
    assistant_settings.save()
    provider = CapturingWellbeingProvider(
        response=WellbeingAssistantProviderResponse(
            answer="You have depression and should take antidepressant medication.",
            focus_area="reflection",
            small_actions=(),
            reflection_prompts=(),
            adherence_strategy="",
        )
    )

    result = ask_wellbeing_assistant(
        user=user,
        message="Give me habit feedback",
        context_date=date(2026, 8, 21),
        store_response=True,
        provider=provider,
    )

    assert len(provider.requests) == 1
    assert result.code == "wellbeing_assistant_safety_blocked"
    assert result.safety.blocked is True
    assert result.safety.categories == ("medical_or_clinical_decision",)
    assert result.stored is False
    assert result.storage_reason == "safety_blocked"
    assert WellbeingAssistantMessage.objects.count() == 0
