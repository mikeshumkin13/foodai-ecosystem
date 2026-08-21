from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from accounts.models import User, UserProfile

_DEFAULT_LOCALE = "ru"
_ALLOWED_FOCUS_AREAS = (
    "habit_formation",
    "adherence",
    "routine",
    "motivation_strategy",
    "reflection",
    "small_action_planning",
)


@dataclass(frozen=True)
class WellbeingAssistantContext:
    locale: str
    date: date
    allowed_focus_areas: tuple[str, ...]
    user_request: str

    def to_provider_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "wellbeing_assistant_context_v1",
            "locale": self.locale,
            "date": self.date.isoformat(),
            "allowed_focus_areas": list(self.allowed_focus_areas),
            "user_request": self.user_request,
        }


def build_wellbeing_context(
    *,
    user: User,
    message: str,
    context_date: date,
) -> WellbeingAssistantContext:
    return WellbeingAssistantContext(
        locale=_preferred_locale(user),
        date=context_date,
        allowed_focus_areas=_ALLOWED_FOCUS_AREAS,
        user_request=message,
    )


def _preferred_locale(user: User) -> str:
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        return _DEFAULT_LOCALE
    if profile.preferred_language in {"ru", "en"}:
        return profile.preferred_language
    return _DEFAULT_LOCALE
