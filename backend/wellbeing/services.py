from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.utils import timezone

from accounts.models import User
from wellbeing.context import WellbeingAssistantContext, build_wellbeing_context
from wellbeing.models import WellbeingAssistantMessage, WellbeingAssistantSettings
from wellbeing.providers import (
    WellbeingAssistantProvider,
    WellbeingAssistantProviderRequest,
    WellbeingAssistantProviderResponse,
    get_wellbeing_assistant_provider,
)
from wellbeing.safety import (
    WellbeingSafetyDecision,
    detect_sensitive_message_for_storage,
    moderate_provider_text,
    moderate_user_request,
    wellbeing_safety_refusal_message,
)

WELLBEING_ASSISTANT_OUTPUT_SCHEMA_VERSION = "ai_wellbeing_assistant_response_v1"


@dataclass(frozen=True)
class WellbeingAssistantResult:
    code: str
    schema_version: str
    context_date: date
    answer: str
    focus_area: str
    small_actions: tuple[dict[str, str], ...]
    reflection_prompts: tuple[str, ...]
    adherence_strategy: str
    warnings: tuple[str, ...]
    safety: WellbeingSafetyDecision
    provider_name: str
    stored: bool
    storage_reason: str

    def to_response_payload(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "schema_version": self.schema_version,
            "context_date": self.context_date.isoformat(),
            "answer": self.answer,
            "focus_area": self.focus_area,
            "small_actions": list(self.small_actions),
            "reflection_prompts": list(self.reflection_prompts),
            "adherence_strategy": self.adherence_strategy,
            "warnings": list(self.warnings),
            "safety": self.safety.to_payload(),
            "provider": self.provider_name,
            "stored": self.stored,
            "storage_reason": self.storage_reason,
        }


def get_wellbeing_assistant_settings(*, user: User) -> WellbeingAssistantSettings:
    assistant_settings, _created = WellbeingAssistantSettings.objects.get_or_create(user=user)
    return assistant_settings


def ask_wellbeing_assistant(
    *,
    user: User,
    message: str,
    context_date: date | None = None,
    store_response: bool = False,
    provider: WellbeingAssistantProvider | None = None,
) -> WellbeingAssistantResult:
    resolved_context_date = context_date or timezone.localdate()
    normalized_message = message.strip()
    context = build_wellbeing_context(
        user=user,
        message=normalized_message,
        context_date=resolved_context_date,
    )

    input_safety = moderate_user_request(normalized_message)
    if input_safety.blocked:
        return _safety_result(
            context=context,
            safety=input_safety,
            provider_name="safety_layer",
            storage_reason="safety_blocked",
        )

    resolved_provider = provider or get_wellbeing_assistant_provider()
    provider_request = WellbeingAssistantProviderRequest(
        context=context,
        output_schema_version=WELLBEING_ASSISTANT_OUTPUT_SCHEMA_VERSION,
    )
    provider_response = resolved_provider.generate(provider_request)
    output_safety = moderate_provider_text(_provider_response_text(provider_response))
    if output_safety.blocked:
        return _safety_result(
            context=context,
            safety=output_safety,
            provider_name=resolved_provider.name,
            storage_reason="safety_blocked",
        )

    storage_reason = _resolve_storage_reason(
        user=user,
        request_text=normalized_message,
        response_text=_provider_response_text(provider_response),
        store_response=store_response,
    )
    should_store = storage_reason == "stored"
    result = _provider_result(
        context=context,
        provider_name=resolved_provider.name,
        provider_response=provider_response,
        safety=WellbeingSafetyDecision.passed(),
        stored=should_store,
        storage_reason=storage_reason,
    )
    if should_store:
        _store_successful_response(user=user, context=context, result=result)
    return result


def _provider_result(
    *,
    context: WellbeingAssistantContext,
    provider_name: str,
    provider_response: WellbeingAssistantProviderResponse,
    safety: WellbeingSafetyDecision,
    stored: bool,
    storage_reason: str,
) -> WellbeingAssistantResult:
    return WellbeingAssistantResult(
        code="wellbeing_assistant_response",
        schema_version=WELLBEING_ASSISTANT_OUTPUT_SCHEMA_VERSION,
        context_date=context.date,
        answer=provider_response.answer,
        focus_area=provider_response.focus_area,
        small_actions=tuple(action.to_payload() for action in provider_response.small_actions),
        reflection_prompts=tuple(provider_response.reflection_prompts),
        adherence_strategy=provider_response.adherence_strategy,
        warnings=tuple(provider_response.warnings),
        safety=safety,
        provider_name=provider_name,
        stored=stored,
        storage_reason=storage_reason,
    )


def _safety_result(
    *,
    context: WellbeingAssistantContext,
    safety: WellbeingSafetyDecision,
    provider_name: str,
    storage_reason: str,
) -> WellbeingAssistantResult:
    return WellbeingAssistantResult(
        code="wellbeing_assistant_safety_blocked",
        schema_version=WELLBEING_ASSISTANT_OUTPUT_SCHEMA_VERSION,
        context_date=context.date,
        answer=wellbeing_safety_refusal_message(
            locale=context.locale,
            urgent_support_recommended=safety.urgent_support_recommended,
        ),
        focus_area="safety",
        small_actions=(),
        reflection_prompts=(),
        adherence_strategy="",
        warnings=("wellbeing_assistant_safety_boundary",),
        safety=safety,
        provider_name=provider_name,
        stored=False,
        storage_reason=storage_reason,
    )


def _resolve_storage_reason(
    *,
    user: User,
    request_text: str,
    response_text: str,
    store_response: bool,
) -> str:
    if not store_response:
        return "not_requested"
    if not get_wellbeing_assistant_settings(user=user).has_history_consent:
        return "consent_required"
    if detect_sensitive_message_for_storage(request_text):
        return "sensitive_content_not_stored"
    if detect_sensitive_message_for_storage(response_text):
        return "sensitive_content_not_stored"
    return "stored"


def _store_successful_response(
    *,
    user: User,
    context: WellbeingAssistantContext,
    result: WellbeingAssistantResult,
) -> None:
    WellbeingAssistantMessage.objects.create(
        user=user,
        context_date=context.date,
        request_text=context.user_request,
        response_payload=result.to_response_payload(),
        context_snapshot=context.to_provider_payload(),
        provider_name=result.provider_name,
        output_schema_version=result.schema_version,
        safety_status=WellbeingAssistantMessage.SafetyStatus.PASSED,
    )


def _provider_response_text(provider_response: WellbeingAssistantProviderResponse) -> str:
    chunks: Iterable[str] = (
        provider_response.answer,
        provider_response.focus_area,
        *(action.title for action in provider_response.small_actions),
        *(action.description for action in provider_response.small_actions),
        *provider_response.reflection_prompts,
        provider_response.adherence_strategy,
        *provider_response.warnings,
    )
    return "\n".join(chunks)
