from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.conf import settings

from ai_coach.context import AICoachContext


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


class AICoachProviderConfigurationError(RuntimeError):
    pass


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
    raise AICoachProviderConfigurationError("unsupported_ai_coach_provider")


def _total_value(totals: object, key: str) -> str:
    if not isinstance(totals, dict):
        return "0.0000"
    value = totals.get(key, "0.0000")
    return str(value)
