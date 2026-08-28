from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from django.conf import settings

from ai_coach.context import AICoachContext

_NUTRITION_NOTE_CODE_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")
_OPENAI_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "suggestions": {"type": "array", "items": {"type": "string"}},
        "nutrition_notes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["code", "message"],
                "additionalProperties": False,
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "suggestions", "nutrition_notes", "warnings"],
    "additionalProperties": False,
}
_OPENAI_INSTRUCTIONS = """You are FoodAI Nutrition Coach, a general nutrition assistant.
Use only the structured context supplied by the application and answer in context.locale.
Explain diary balance, suggest ordinary food options, and discuss nutrients conservatively.
Do not diagnose, prescribe treatment or medication, replace a clinician, or recommend extreme diets.
Do not infer personal facts that are absent from the context.
Keep the response concise and practical.
Return only the requested structured output."""


@dataclass(frozen=True)
class AICoachNutritionNote:
    code: str
    message: str

    def to_payload(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class AICoachProviderRequest:
    context: AICoachContext
    output_schema_version: str

    def to_payload(self) -> dict[str, object]:
        return {
            "output_schema_version": self.output_schema_version,
            "context": self.context.to_provider_payload(),
        }


@dataclass(frozen=True)
class AICoachProviderResponse:
    answer: str
    suggestions: tuple[str, ...]
    nutrition_notes: tuple[AICoachNutritionNote, ...]
    warnings: tuple[str, ...] = ()


class AICoachProvider(Protocol):
    name: str

    def generate(self, request: AICoachProviderRequest) -> AICoachProviderResponse: ...


class AICoachProviderError(RuntimeError):
    pass


class AICoachProviderConfigurationError(AICoachProviderError):
    pass


class AICoachProviderTimeoutError(AICoachProviderError):
    pass


class AICoachProviderUnavailableError(AICoachProviderError):
    pass


class AICoachProviderInvalidResponseError(AICoachProviderError):
    pass


class AICoachProviderRuntimeError(AICoachProviderError):
    pass


class OpenAIAICoachProvider:
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        endpoint: str,
        timeout_seconds: float,
        max_output_tokens: int,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key.strip():
            raise AICoachProviderConfigurationError("openai_api_key_missing")
        if not model.strip():
            raise AICoachProviderConfigurationError("openai_model_missing")
        if not endpoint.startswith("https://"):
            raise AICoachProviderConfigurationError("openai_endpoint_must_use_https")
        if timeout_seconds <= 0:
            raise AICoachProviderConfigurationError("openai_timeout_invalid")
        if max_output_tokens <= 0:
            raise AICoachProviderConfigurationError("openai_max_output_tokens_invalid")

        self._api_key = api_key
        self._model = model
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._client = client

    def generate(self, request: AICoachProviderRequest) -> AICoachProviderResponse:
        response = self._send_request(request)
        response_payload = _parse_http_response(response)
        output_text = _extract_output_text(response_payload)
        return _parse_provider_output(output_text)

    def _send_request(self, request: AICoachProviderRequest) -> httpx.Response:
        request_payload = {
            "model": self._model,
            "instructions": _OPENAI_INSTRUCTIONS,
            "input": json.dumps(request.to_payload(), ensure_ascii=False, separators=(",", ":")),
            "store": False,
            "reasoning": {"effort": "none"},
            "max_output_tokens": self._max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "foodai_nutrition_coach_response",
                    "strict": True,
                    "schema": _OPENAI_RESPONSE_SCHEMA,
                },
                "verbosity": "low",
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            if self._client is not None:
                response = self._client.post(
                    self._endpoint,
                    headers=headers,
                    json=request_payload,
                    timeout=self._timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.post(
                        self._endpoint,
                        headers=headers,
                        json=request_payload,
                    )
            response.raise_for_status()
            return response
        except httpx.TimeoutException as exc:
            raise AICoachProviderTimeoutError("openai_request_timeout") from exc
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            raise AICoachProviderUnavailableError("openai_request_failed") from exc


class MockAICoachProvider:
    name = "mock"

    def generate(self, request: AICoachProviderRequest) -> AICoachProviderResponse:
        context = request.context
        totals = context.diary_aggregates.get("totals", {})
        calories = _total_value(totals, "calories")
        protein = _total_value(totals, "protein")

        if context.locale == "en":
            return AICoachProviderResponse(
                answer=(
                    f"For {context.date.isoformat()}, your diary currently shows about "
                    f"{calories} kcal and {protein} g protein. I can help interpret this "
                    "against your goal, but this is general nutrition support, not medical care."
                ),
                suggestions=(
                    "Add a protein-rich option if protein is still below your target.",
                    "Use your dietary preferences when choosing meal ideas.",
                ),
                nutrition_notes=(
                    AICoachNutritionNote(
                        code="energy_balance",
                        message="Compare consumed calories with your personal target once set.",
                    ),
                    AICoachNutritionNote(
                        code="protein",
                        message="Protein can be distributed across meals instead of added at once.",
                    ),
                ),
            )

        return AICoachProviderResponse(
            answer=(
                f"За {context.date.isoformat()} в дневнике сейчас примерно {calories} ккал "
                f"и {protein} г белка. Я могу помочь интерпретировать это относительно цели, "
                "но это общая поддержка по питанию, а не медицинская помощь."
            ),
            suggestions=(
                "Добавьте белковый продукт, если белка пока меньше вашего ориентира.",
                "При выборе вариантов еды учитывайте ваши dietary preferences.",
            ),
            nutrition_notes=(
                AICoachNutritionNote(
                    code="energy_balance",
                    message="Сравнивайте потреблённые калории с личной целью, когда она задана.",
                ),
                AICoachNutritionNote(
                    code="protein",
                    message="Белок можно распределять по приёмам пищи, а не добирать за один раз.",
                ),
            ),
        )


def get_ai_coach_provider(provider_name: str | None = None) -> AICoachProvider:
    resolved_provider_name = provider_name or settings.AI_COACH_PROVIDER
    if resolved_provider_name == "mock":
        return MockAICoachProvider()
    if resolved_provider_name == "openai":
        return OpenAIAICoachProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.AI_COACH_OPENAI_MODEL,
            endpoint=settings.OPENAI_RESPONSES_API_URL,
            timeout_seconds=settings.AI_COACH_PROVIDER_TIMEOUT_SECONDS,
            max_output_tokens=settings.AI_COACH_PROVIDER_MAX_OUTPUT_TOKENS,
        )
    raise AICoachProviderConfigurationError("unsupported_ai_coach_provider")


def _parse_http_response(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise AICoachProviderInvalidResponseError("openai_response_not_json") from exc
    if not isinstance(payload, dict):
        raise AICoachProviderInvalidResponseError("openai_response_not_object")
    if payload.get("status") != "completed":
        raise AICoachProviderInvalidResponseError("openai_response_not_completed")
    return payload


def _extract_output_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if (
                    isinstance(content_item, dict)
                    and content_item.get("type") == "output_text"
                    and isinstance(content_item.get("text"), str)
                    and content_item["text"].strip()
                ):
                    return str(content_item["text"])
    raise AICoachProviderInvalidResponseError("openai_output_text_missing")


def _parse_provider_output(output_text: str) -> AICoachProviderResponse:
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise AICoachProviderInvalidResponseError("openai_output_not_json") from exc
    if not isinstance(payload, dict):
        raise AICoachProviderInvalidResponseError("openai_output_not_object")

    answer = _validated_text(payload.get("answer"), field="answer", max_length=4000)
    suggestions = _validated_text_list(
        payload.get("suggestions"),
        field="suggestions",
        max_items=6,
        max_length=500,
    )
    warnings = _validated_text_list(
        payload.get("warnings"),
        field="warnings",
        max_items=6,
        max_length=300,
    )
    raw_notes = payload.get("nutrition_notes")
    if not isinstance(raw_notes, list) or len(raw_notes) > 8:
        raise AICoachProviderInvalidResponseError("openai_nutrition_notes_invalid")

    nutrition_notes: list[AICoachNutritionNote] = []
    for raw_note in raw_notes:
        if not isinstance(raw_note, dict):
            raise AICoachProviderInvalidResponseError("openai_nutrition_note_invalid")
        code = _validated_text(raw_note.get("code"), field="note_code", max_length=64)
        if _NUTRITION_NOTE_CODE_PATTERN.fullmatch(code) is None:
            raise AICoachProviderInvalidResponseError("openai_nutrition_note_code_invalid")
        message = _validated_text(raw_note.get("message"), field="note_message", max_length=500)
        nutrition_notes.append(AICoachNutritionNote(code=code, message=message))

    return AICoachProviderResponse(
        answer=answer,
        suggestions=suggestions,
        nutrition_notes=tuple(nutrition_notes),
        warnings=warnings,
    )


def _validated_text(value: object, *, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise AICoachProviderInvalidResponseError(f"openai_{field}_invalid")
    normalized = value.strip()
    if not normalized or len(normalized) > max_length:
        raise AICoachProviderInvalidResponseError(f"openai_{field}_invalid")
    return normalized


def _validated_text_list(
    value: object,
    *,
    field: str,
    max_items: int,
    max_length: int,
) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > max_items:
        raise AICoachProviderInvalidResponseError(f"openai_{field}_invalid")
    return tuple(
        _validated_text(item, field=field, max_length=max_length) for item in value
    )


def _total_value(totals: object, key: str) -> str:
    if not isinstance(totals, dict):
        return "0.0000"
    value = totals.get(key, "0.0000")
    return str(value)
