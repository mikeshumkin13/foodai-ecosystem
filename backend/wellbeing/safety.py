from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WellbeingSafetyDecision:
    blocked: bool
    code: str
    categories: tuple[str, ...] = ()
    reason: str = ""
    urgent_support_recommended: bool = False

    @classmethod
    def passed(cls) -> WellbeingSafetyDecision:
        return cls(blocked=False, code="passed")

    def to_payload(self) -> dict[str, object]:
        return {
            "blocked": self.blocked,
            "code": self.code,
            "categories": list(self.categories),
            "reason": self.reason,
            "urgent_support_recommended": self.urgent_support_recommended,
        }


_SELF_HARM_TERMS = (
    "suicide",
    "suicidal",
    "kill myself",
    "end my life",
    "want to die",
    "self harm",
    "self-harm",
    "harm myself",
    "hurt myself",
    "cut myself",
    "суицид",
    "покончить с собой",
    "убить себя",
    "не хочу жить",
    "хочу умереть",
    "навредить себе",
    "причинить себе вред",
    "порезать себя",
    "самоповреж",
)
_HARM_TO_OTHERS_TERMS = (
    "kill someone",
    "hurt someone",
    "harm someone",
    "attack someone",
    "убить кого",
    "навредить кому",
    "причинить вред другому",
    "напасть на",
)
_IMMEDIATE_DANGER_TERMS = (
    "unsafe at home",
    "domestic violence",
    "being abused",
    "i am in danger",
    "someone is threatening me",
    "опасно дома",
    "домашнее насилие",
    "меня бьют",
    "мне угрожают",
    "я в опасности",
)
_MEDICAL_OR_CLINICAL_TERMS = (
    "diagnose",
    "diagnosis",
    "do i have depression",
    "do i have bipolar",
    "you have depression",
    "you have bipolar",
    "prescribe",
    "antidepressant",
    "medication",
    "medicine",
    "clinical treatment",
    "поставь диагноз",
    "диагноз",
    "у меня депрессия",
    "у меня биполяр",
    "у вас депресс",
    "у тебя депресс",
    "у вас биполяр",
    "у тебя биполяр",
    "назначь лекар",
    "антидепресс",
    "таблет",
    "лекарств",
    "лечение депресс",
)
_UNSAFE_BEHAVIOR_TERMS = (
    "sleep 3 hours",
    "sleep three hours",
    "do not sleep",
    "stop sleeping",
    "punish myself",
    "punishment habit",
    "не спать",
    "спать 3 часа",
    "спать три часа",
    "накажи меня",
    "наказывать себя",
)
_SENSITIVE_STORAGE_TERMS = (
    "depression",
    "depressed",
    "anxiety",
    "panic attack",
    "trauma",
    "abuse",
    "addiction",
    "eating disorder",
    "burnout",
    "grief",
    "депресс",
    "тревог",
    "паническ",
    "паник",
    "травмир",
    "насили",
    "зависим",
    "расстройств",
    "выгорание",
    "горе",
)


def moderate_user_request(message: str) -> WellbeingSafetyDecision:
    normalized_message = _normalize(message)
    categories = _matched_blocked_categories(normalized_message)
    if not categories:
        return WellbeingSafetyDecision.passed()

    urgent_categories = {
        "self_harm_or_suicidal_ideation",
        "harm_to_others",
        "immediate_danger",
    }
    return WellbeingSafetyDecision(
        blocked=True,
        code="unsafe_wellbeing_assistant_request",
        categories=categories,
        reason="request_matches_wellbeing_safety_rules",
        urgent_support_recommended=bool(urgent_categories.intersection(categories)),
    )


def moderate_provider_text(text: str) -> WellbeingSafetyDecision:
    normalized_text = _normalize(text)
    categories = _matched_blocked_categories(normalized_text)
    if not categories:
        return WellbeingSafetyDecision.passed()
    return WellbeingSafetyDecision(
        blocked=True,
        code="unsafe_wellbeing_assistant_output",
        categories=categories,
        reason="provider_output_matches_wellbeing_safety_rules",
        urgent_support_recommended=False,
    )


def detect_sensitive_message_for_storage(text: str) -> tuple[str, ...]:
    normalized_text = _normalize(text)
    categories = list(_matched_blocked_categories(normalized_text))
    if _contains_any(normalized_text, _SENSITIVE_STORAGE_TERMS):
        categories.append("mental_health_sensitive")
    return tuple(dict.fromkeys(categories))


def wellbeing_safety_refusal_message(
    *,
    locale: str,
    urgent_support_recommended: bool,
) -> str:
    if locale == "en":
        if urgent_support_recommended:
            return (
                "I cannot help plan harmful actions or replace urgent support. If you or someone "
                "else may be in immediate danger, contact local emergency services or a trusted "
                "person now. I can help with small habit steps again once the immediate risk is "
                "handled."
            )
        return (
            "I cannot diagnose, prescribe treatment, or replace qualified professional support. "
            "I can help with general habit formation, reflection, routines, adherence strategies, "
            "and small safe actions."
        )
    if urgent_support_recommended:
        return (
            "Я не могу помогать планировать опасные действия или заменять срочную поддержку. "
            "Если вы или кто-то рядом может быть в непосредственной опасности, обратитесь в "
            "местные экстренные службы или к доверенному человеку сейчас. Я смогу помочь с "
            "маленькими шагами привычек, когда непосредственный риск будет снят."
        )
    return (
        "Я не могу ставить диагнозы, назначать лечение или заменять квалифицированную поддержку. "
        "Могу помочь с формированием привычек, reflection, режимом, adherence-стратегиями и "
        "маленькими безопасными действиями."
    )


def _matched_blocked_categories(normalized_text: str) -> tuple[str, ...]:
    categories: list[str] = []
    if _contains_any(normalized_text, _SELF_HARM_TERMS):
        categories.append("self_harm_or_suicidal_ideation")
    if _contains_any(normalized_text, _HARM_TO_OTHERS_TERMS):
        categories.append("harm_to_others")
    if _contains_any(normalized_text, _IMMEDIATE_DANGER_TERMS):
        categories.append("immediate_danger")
    if _contains_any(normalized_text, _MEDICAL_OR_CLINICAL_TERMS):
        categories.append("medical_or_clinical_decision")
    if _contains_any(normalized_text, _UNSAFE_BEHAVIOR_TERMS):
        categories.append("unsafe_behavior_plan")
    return tuple(categories)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())
