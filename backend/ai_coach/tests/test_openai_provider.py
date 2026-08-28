from __future__ import annotations

import json
from datetime import date

import httpx
import pytest
from django.test import override_settings

from ai_coach.context import AICoachContext
from ai_coach.providers import (
    AICoachProviderConfigurationError,
    AICoachProviderInvalidResponseError,
    AICoachProviderRequest,
    AICoachProviderTimeoutError,
    AICoachProviderUnavailableError,
    OpenAIAICoachProvider,
    get_ai_coach_provider,
)


def _provider_request() -> AICoachProviderRequest:
    return AICoachProviderRequest(
        context=AICoachContext(
            locale="ru",
            date=date(2026, 8, 28),
            goal="maintain_weight",
            diary_aggregates={
                "totals": {
                    "calories": "900.0000",
                    "protein": "55.0000",
                    "fat": "30.0000",
                    "carbs": "100.0000",
                },
                "micronutrient_totals": {},
            },
            dietary_preferences=("vegetarian",),
            user_request="Как сбалансировать ужин?",
        ),
        output_schema_version="ai_nutrition_coach_response_v1",
    )


def _response_payload() -> dict[str, object]:
    return {
        "answer": "Добавьте к ужину источник белка и овощи.",
        "suggestions": ["Выберите бобовые или тофу."],
        "nutrition_notes": [
            {"code": "protein", "message": "Распределяйте белок между приёмами пищи."}
        ],
        "warnings": [],
    }


def _provider(*, client: httpx.Client, timeout_seconds: float = 3.5) -> OpenAIAICoachProvider:
    return OpenAIAICoachProvider(
        api_key="test-api-key",
        model="gpt-5.6-luna",
        endpoint="https://api.openai.test/v1/responses",
        timeout_seconds=timeout_seconds,
        max_output_tokens=1200,
        client=client,
    )


def test_openai_provider_sends_minimized_stateless_structured_request() -> None:
    captured_request: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["authorization"] = request.headers["Authorization"]
        captured_request["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"status": "completed", "output_text": json.dumps(_response_payload())},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = _provider(client=client).generate(_provider_request())

    payload = captured_request["payload"]
    assert isinstance(payload, dict)
    provider_input = json.loads(str(payload["input"]))
    assert payload["model"] == "gpt-5.6-luna"
    assert payload["store"] is False
    assert payload["reasoning"] == {"effort": "none"}
    assert payload["max_output_tokens"] == 1200
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True
    assert set(provider_input["context"]) == {
        "schema_version",
        "locale",
        "date",
        "goal",
        "diary_aggregates",
        "dietary_preferences",
        "user_request",
    }
    assert "email" not in json.dumps(provider_input)
    assert captured_request["authorization"] == "Bearer test-api-key"
    assert result.answer == "Добавьте к ужину источник белка и овощи."
    assert result.suggestions == ("Выберите бобовые или тофу.",)
    assert result.nutrition_notes[0].code == "protein"


def test_openai_provider_normalizes_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("provider timed out", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AICoachProviderTimeoutError, match="openai_request_timeout"):
            _provider(client=client).generate(_provider_request())


def test_openai_provider_normalizes_http_failure_without_response_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "sensitive provider detail"}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AICoachProviderUnavailableError, match="openai_request_failed") as exc:
            _provider(client=client).generate(_provider_request())

    assert "sensitive provider detail" not in str(exc.value)


@pytest.mark.parametrize(
    "response_payload",
    [
        {"status": "failed", "output_text": json.dumps(_response_payload())},
        {"status": "completed", "output_text": "not-json"},
        {
            "status": "completed",
            "output_text": json.dumps({**_response_payload(), "answer": ""}),
        },
    ],
)
def test_openai_provider_rejects_invalid_response(response_payload: dict[str, object]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_payload)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AICoachProviderInvalidResponseError):
            _provider(client=client).generate(_provider_request())


@override_settings(
    AI_COACH_PROVIDER="openai",
    OPENAI_API_KEY="test-api-key",
    AI_COACH_OPENAI_MODEL="gpt-5.6-luna",
    OPENAI_RESPONSES_API_URL="https://api.openai.com/v1/responses",
    AI_COACH_PROVIDER_TIMEOUT_SECONDS=4.0,
    AI_COACH_PROVIDER_MAX_OUTPUT_TOKENS=1200,
)
def test_provider_factory_builds_openai_adapter() -> None:
    provider = get_ai_coach_provider()

    assert isinstance(provider, OpenAIAICoachProvider)


@override_settings(
    AI_COACH_PROVIDER="openai",
    OPENAI_API_KEY="",
    AI_COACH_OPENAI_MODEL="gpt-5.6-luna",
    OPENAI_RESPONSES_API_URL="https://api.openai.com/v1/responses",
    AI_COACH_PROVIDER_TIMEOUT_SECONDS=4.0,
    AI_COACH_PROVIDER_MAX_OUTPUT_TOKENS=1200,
)
def test_provider_factory_rejects_missing_openai_key() -> None:
    with pytest.raises(AICoachProviderConfigurationError, match="openai_api_key_missing"):
        get_ai_coach_provider()
