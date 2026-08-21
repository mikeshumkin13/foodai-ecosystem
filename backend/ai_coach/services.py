from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.utils import timezone

from accounts.models import User
from ai_coach.context import AICoachContext, build_ai_coach_context
from ai_coach.models import AICoachMessage, AICoachSettings
from ai_coach.providers import (
    AICoachProvider,
    AICoachProviderRequest,
    AICoachProviderResponse,
    get_ai_coach_provider,
)
from ai_coach.safety import (
    SafetyDecision,
    moderate_provider_text,
    moderate_user_request,
    safety_refusal_message,
)

AI_COACH_OUTPUT_SCHEMA_VERSION = "ai_nutrition_coach_response_v1"


@dataclass(frozen=True)
class AICoachResult:
    code: str
    schema_version: str
    context_date: date
    answer: str
    suggestions: tuple[str, ...]
    nutrition_notes: tuple[dict[str, str], ...]
    warnings: tuple[str, ...]
    safety: SafetyDecision
    provider_name: str
    stored: bool

    def to_response_payload(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "schema_version": self.schema_version,
            "context_date": self.context_date.isoformat(),
            "answer": self.answer,
            "suggestions": list(self.suggestions),
            "nutrition_notes": list(self.nutrition_notes),
            "warnings": list(self.warnings),
            "safety": self.safety.to_payload(),
            "provider": self.provider_name,
            "stored": self.stored,
        }


def get_ai_coach_settings(*, user: User) -> AICoachSettings:
    settings, _created = AICoachSettings.objects.get_or_create(user=user)
    return settings


def ask_nutrition_coach(
    *,
    user: User,
    message: str,
    context_date: date | None = None,
    store_response: bool = False,
    provider: AICoachProvider | None = None,
) -> AICoachResult:
    resolved_context_date = context_date or timezone.localdate()
    normalized_message = message.strip()
    context = build_ai_coach_context(
        user=user,
        message=normalized_message,
        context_date=resolved_context_date,
    )

    input_safety = moderate_user_request(normalized_message)
    if input_safety.blocked:
        return _safety_result(context=context, safety=input_safety, provider_name="safety_layer")

    resolved_provider = provider or get_ai_coach_provider()
    provider_request = AICoachProviderRequest(
        context=context,
        output_schema_version=AI_COACH_OUTPUT_SCHEMA_VERSION,
    )
    provider_response = resolved_provider.generate(provider_request)
    output_safety = moderate_provider_text(_provider_response_text(provider_response))
    if output_safety.blocked:
        return _safety_result(
            context=context,
            safety=output_safety,
            provider_name=resolved_provider.name,
        )

    result = _provider_result(
        context=context,
        provider_name=resolved_provider.name,
        provider_response=provider_response,
        safety=SafetyDecision.passed(),
        stored=False,
    )
    if store_response and get_ai_coach_settings(user=user).has_chat_history_consent:
        result = _provider_result(
            context=context,
            provider_name=resolved_provider.name,
            provider_response=provider_response,
            safety=SafetyDecision.passed(),
            stored=True,
        )
        _store_successful_response(user=user, context=context, result=result)
    return result


def _provider_result(
    *,
    context: AICoachContext,
    provider_name: str,
    provider_response: AICoachProviderResponse,
    safety: SafetyDecision,
    stored: bool,
) -> AICoachResult:
    return AICoachResult(
        code="ai_coach_response",
        schema_version=AI_COACH_OUTPUT_SCHEMA_VERSION,
        context_date=context.date,
        answer=provider_response.answer,
        suggestions=tuple(provider_response.suggestions),
        nutrition_notes=tuple(note.to_payload() for note in provider_response.nutrition_notes),
        warnings=tuple(provider_response.warnings),
        safety=safety,
        provider_name=provider_name,
        stored=stored,
    )


def _safety_result(
    *,
    context: AICoachContext,
    safety: SafetyDecision,
    provider_name: str,
) -> AICoachResult:
    return AICoachResult(
        code="ai_coach_safety_blocked",
        schema_version=AI_COACH_OUTPUT_SCHEMA_VERSION,
        context_date=context.date,
        answer=safety_refusal_message(locale=context.locale),
        suggestions=(),
        nutrition_notes=(),
        warnings=("ai_coach_safety_boundary",),
        safety=safety,
        provider_name=provider_name,
        stored=False,
    )


def _store_successful_response(
    *,
    user: User,
    context: AICoachContext,
    result: AICoachResult,
) -> None:
    AICoachMessage.objects.create(
        user=user,
        context_date=context.date,
        request_text=context.user_request,
        response_payload=result.to_response_payload(),
        context_snapshot=context.to_provider_payload(),
        provider_name=result.provider_name,
        output_schema_version=result.schema_version,
        safety_status=AICoachMessage.SafetyStatus.PASSED,
    )


def _provider_response_text(provider_response: AICoachProviderResponse) -> str:
    chunks: Iterable[str] = (
        provider_response.answer,
        *provider_response.suggestions,
        *(note.message for note in provider_response.nutrition_notes),
        *provider_response.warnings,
    )
    return "\n".join(chunks)
