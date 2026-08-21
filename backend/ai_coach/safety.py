from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyDecision:
    blocked: bool
    code: str
    categories: tuple[str, ...] = ()
    reason: str = ""

    @classmethod
    def passed(cls) -> SafetyDecision:
        return cls(blocked=False, code="passed")

    def to_payload(self) -> dict[str, object]:
        return {
            "blocked": self.blocked,
            "code": self.code,
            "categories": list(self.categories),
            "reason": self.reason,
        }


_MEDICAL_TERMS = (
    "diagnos",
    "diagnos",
    "диагноз",
    "симптом",
    "symptom",
    "disease",
    "болезн",
    "treat diabetes",
    "вылечить диабет",
    "insulin",
    "инсулин",
    "medication",
    "medicine",
    "лекарств",
    "таблет",
    "prescribe",
    "назначь лекар",
    "отменить назначение",
    "stop taking",
    "отмени препарат",
)

_EXTREME_DIET_TERMS = (
    "500 kcal",
    "500 calories",
    "500 кал",
    "300 kcal",
    "300 кал",
    "zero calorie",
    "ничего не есть",
    "голодать",
    "голодов",
    "water fast",
    "dry fast",
    "экстремальн",
    "extreme diet",
    "purge",
    "рвот",
    "laxative",
    "слабительн",
    "быстро похудеть на 10",
)


def moderate_user_request(message: str) -> SafetyDecision:
    normalized_message = _normalize(message)
    categories = _matched_categories(normalized_message)
    if not categories:
        return SafetyDecision.passed()
    return SafetyDecision(
        blocked=True,
        code="unsafe_nutrition_coach_request",
        categories=categories,
        reason="request_matches_medical_or_extreme_diet_safety_rules",
    )


def moderate_provider_text(text: str) -> SafetyDecision:
    normalized_text = _normalize(text)
    categories = _matched_categories(normalized_text)
    if not categories:
        return SafetyDecision.passed()
    return SafetyDecision(
        blocked=True,
        code="unsafe_nutrition_coach_output",
        categories=categories,
        reason="provider_output_matches_medical_or_extreme_diet_safety_rules",
    )


def safety_refusal_message(*, locale: str) -> str:
    if locale == "en":
        return (
            "I cannot help with diagnoses, medication decisions, or dangerous diet plans. "
            "I can discuss general nutrition balance and suggest safer food options to review "
            "with a qualified professional when needed."
        )
    return (
        "Я не могу помогать с диагнозами, решениями по лекарствам или опасными диетами. "
        "Могу обсудить общий баланс питания и предложить более безопасные варианты еды, "
        "а в медицинских вопросах стоит обратиться к квалифицированному специалисту."
    )


def _matched_categories(normalized_text: str) -> tuple[str, ...]:
    categories: list[str] = []
    if _contains_any(normalized_text, _MEDICAL_TERMS):
        categories.append("medical_decision")
    if _contains_any(normalized_text, _EXTREME_DIET_TERMS):
        categories.append("extreme_diet")
    return tuple(categories)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())
