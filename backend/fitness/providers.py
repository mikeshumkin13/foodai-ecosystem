from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from django.conf import settings


@dataclass(frozen=True)
class FitnessCoachProviderRequest:
    plan_payload: dict[str, Any]
    locale: str
    user_request: str
    output_schema_version: str

    def to_payload(self) -> dict[str, object]:
        return {
            "output_schema_version": self.output_schema_version,
            "locale": self.locale,
            "user_request": self.user_request,
            "plan": self.plan_payload,
        }


@dataclass(frozen=True)
class FitnessCoachProviderResponse:
    summary: str
    rationale: tuple[str, ...]
    safety_notes: tuple[str, ...] = ()


class FitnessCoachProvider(Protocol):
    name: str

    def explain(self, request: FitnessCoachProviderRequest) -> FitnessCoachProviderResponse: ...


class FitnessCoachProviderConfigurationError(RuntimeError):
    pass


class MockFitnessCoachProvider:
    name = "mock"

    def explain(self, request: FitnessCoachProviderRequest) -> FitnessCoachProviderResponse:
        plan = request.plan_payload
        goal = str(plan.get("goal", "general_fitness"))
        duration = str(plan.get("duration_minutes", ""))
        equipment = ", ".join(str(item) for item in plan.get("available_equipment", []))

        if request.locale == "en":
            return FitnessCoachProviderResponse(
                summary=(
                    f"This structured plan targets {goal} with sessions around {duration} minutes. "
                    "The explanation is AI-assisted, but the plan itself stays in workout entities."
                ),
                rationale=(
                    "Exercise choices are limited to the equipment declared by the user.",
                    "Sets, reps, rest and intensity are adjusted by experience level.",
                    f"Equipment considered: {equipment or 'bodyweight'}.",
                ),
                safety_notes=(
                    "This is general fitness guidance, not clinical care.",
                ),
            )

        return FitnessCoachProviderResponse(
            summary=(
                f"Структурированный план ориентирован на цель {goal} и занятия около "
                f"{duration} минут. Объяснение AI-assisted, но сам план хранится как "
                "структурированные workout-сущности."
            ),
            rationale=(
                "Упражнения ограничены оборудованием, которое указал пользователь.",
                "Подходы, повторы, отдых и интенсивность адаптированы под опыт.",
                f"Учитываемое оборудование: {equipment or 'bodyweight'}.",
            ),
            safety_notes=(
                "Это общая фитнес-поддержка, а не клиническая помощь.",
            ),
        )


def get_fitness_coach_provider(provider_name: str | None = None) -> FitnessCoachProvider:
    resolved_provider_name = provider_name or settings.FITNESS_COACH_PROVIDER
    if resolved_provider_name == "mock":
        return MockFitnessCoachProvider()
    raise FitnessCoachProviderConfigurationError("unsupported_fitness_coach_provider")
