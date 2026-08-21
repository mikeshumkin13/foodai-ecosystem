from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.conf import settings

from wellbeing.context import WellbeingAssistantContext


@dataclass(frozen=True)
class WellbeingSmallAction:
    title: str
    description: str
    timeframe: str

    def to_payload(self) -> dict[str, str]:
        return {
            "title": self.title,
            "description": self.description,
            "timeframe": self.timeframe,
        }


@dataclass(frozen=True)
class WellbeingAssistantProviderRequest:
    context: WellbeingAssistantContext
    output_schema_version: str

    def to_payload(self) -> dict[str, object]:
        return {
            "output_schema_version": self.output_schema_version,
            "context": self.context.to_provider_payload(),
        }


@dataclass(frozen=True)
class WellbeingAssistantProviderResponse:
    answer: str
    focus_area: str
    small_actions: tuple[WellbeingSmallAction, ...]
    reflection_prompts: tuple[str, ...]
    adherence_strategy: str
    warnings: tuple[str, ...] = ()


class WellbeingAssistantProvider(Protocol):
    name: str

    def generate(
        self,
        request: WellbeingAssistantProviderRequest,
    ) -> WellbeingAssistantProviderResponse: ...


class WellbeingAssistantProviderConfigurationError(RuntimeError):
    pass


class MockWellbeingAssistantProvider:
    name = "mock"

    def generate(
        self,
        request: WellbeingAssistantProviderRequest,
    ) -> WellbeingAssistantProviderResponse:
        context = request.context
        if context.locale == "en":
            return WellbeingAssistantProviderResponse(
                answer=(
                    "I can help turn this into a small, trackable habit step. "
                    "This is general wellbeing and adherence support, not clinical care."
                ),
                focus_area="small_action_planning",
                small_actions=(
                    WellbeingSmallAction(
                        title="Choose one tiny action",
                        description="Pick an action that takes less than five minutes today.",
                        timeframe="today",
                    ),
                    WellbeingSmallAction(
                        title="Attach it to an existing cue",
                        description="Run it right after a routine you already do.",
                        timeframe="next_24_hours",
                    ),
                ),
                reflection_prompts=(
                    "What made this habit easier on your best recent day?",
                    "What is one obstacle you can remove before tomorrow?",
                ),
                adherence_strategy=(
                    "Use a minimum viable version of the habit first, then increase only after "
                    "it feels repeatable."
                ),
                warnings=("general_wellbeing_support_only",),
            )

        return WellbeingAssistantProviderResponse(
            answer=(
                "Я могу помочь превратить это в маленький отслеживаемый шаг привычки. "
                "Это общая поддержка по привычкам и adherence, а не клиническая помощь."
            ),
            focus_area="small_action_planning",
            small_actions=(
                WellbeingSmallAction(
                    title="Выберите одно маленькое действие",
                    description="Выберите действие, которое займёт меньше пяти минут сегодня.",
                    timeframe="today",
                ),
                WellbeingSmallAction(
                    title="Привяжите шаг к существующему сигналу",
                    description="Сделайте его сразу после привычного действия дня.",
                    timeframe="next_24_hours",
                ),
            ),
            reflection_prompts=(
                "Что помогло этой привычке в самый удачный недавний день?",
                "Какое одно препятствие можно убрать до завтра?",
            ),
            adherence_strategy=(
                "Сначала используйте минимальную версию привычки, а увеличивайте нагрузку "
                "только когда действие стало повторяемым."
            ),
            warnings=("general_wellbeing_support_only",),
        )


def get_wellbeing_assistant_provider(
    provider_name: str | None = None,
) -> WellbeingAssistantProvider:
    resolved_provider_name = provider_name or settings.WELLBEING_ASSISTANT_PROVIDER
    if resolved_provider_name == "mock":
        return MockWellbeingAssistantProvider()
    raise WellbeingAssistantProviderConfigurationError("unsupported_wellbeing_assistant_provider")
