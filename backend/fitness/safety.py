from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FitnessSafetyDecision:
    blocked: bool
    code: str
    categories: tuple[str, ...] = ()
    reason: str = ""

    @classmethod
    def passed(cls) -> FitnessSafetyDecision:
        return cls(blocked=False, code="passed")

    def to_payload(self) -> dict[str, object]:
        return {
            "blocked": self.blocked,
            "code": self.code,
            "categories": list(self.categories),
            "reason": self.reason,
        }


_INJURY_OR_ACUTE_PAIN_TERMS = (
    "injury",
    "injured",
    "acute pain",
    "sharp pain",
    "severe pain",
    "chest pain",
    "dizziness",
    "faint",
    "numbness",
    "swelling",
    "trauma",
    "травм",
    "острая боль",
    "резкая боль",
    "сильная боль",
    "боль в груди",
    "головокруж",
    "обморок",
    "онемение",
    "отёк",
    "отек",
    "поврежден",
    "повреждён",
)

_MEDICAL_DECISION_TERMS = (
    "diagnose",
    "diagnosis",
    "prescribe",
    "medication",
    "medicine",
    "doctor said",
    "after surgery",
    "диагноз",
    "назначь",
    "лекарств",
    "таблет",
    "после операции",
    "врач сказал",
)


def moderate_fitness_request(message: str) -> FitnessSafetyDecision:
    normalized_message = _normalize(message)
    categories = _matched_categories(normalized_message)
    if not categories:
        return FitnessSafetyDecision.passed()
    return FitnessSafetyDecision(
        blocked=True,
        code="unsafe_fitness_coach_request",
        categories=categories,
        reason="request_matches_injury_or_medical_safety_rules",
    )


def moderate_provider_text(text: str) -> FitnessSafetyDecision:
    normalized_text = _normalize(text)
    categories = _matched_categories(normalized_text)
    if not categories:
        return FitnessSafetyDecision.passed()
    return FitnessSafetyDecision(
        blocked=True,
        code="unsafe_fitness_coach_output",
        categories=categories,
        reason="provider_output_matches_injury_or_medical_safety_rules",
    )


def fitness_safety_refusal_message(*, locale: str) -> str:
    if locale == "en":
        return (
            "I cannot continue or intensify training guidance when you mention injury, acute pain, "
            "chest pain, numbness, dizziness, or similar warning signs. Stop the workout and get "
            "help from a qualified professional; use emergency services if the situation may be "
            "urgent."
        )
    return (
        "Я не могу продолжать или усиливать тренировочные рекомендации, когда есть травма, "
        "острая боль, боль в груди, онемение, головокружение или похожие тревожные признаки. "
        "Остановите тренировку и обратитесь к квалифицированному специалисту; при срочной "
        "ситуации используйте экстренную помощь."
    )


def _matched_categories(normalized_text: str) -> tuple[str, ...]:
    categories: list[str] = []
    if _contains_any(normalized_text, _INJURY_OR_ACUTE_PAIN_TERMS):
        categories.append("injury_or_acute_pain")
    if _contains_any(normalized_text, _MEDICAL_DECISION_TERMS):
        categories.append("medical_decision")
    return tuple(categories)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())
