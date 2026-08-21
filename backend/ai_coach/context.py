from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from accounts.models import NutritionProfile, User, UserProfile
from diary.aggregation import aggregate_meals
from diary.models import Meal

_DEFAULT_LOCALE = "ru"
_ALLOWED_DIETARY_PREFERENCES = frozenset(
    {
        "none",
        "vegetarian",
        "vegan",
        "pescatarian",
        "halal",
        "kosher",
        "high_protein",
        "low_carb",
    }
)


@dataclass(frozen=True)
class AICoachContext:
    locale: str
    date: date
    goal: str
    diary_aggregates: Mapping[str, Any]
    dietary_preferences: tuple[str, ...]
    user_request: str

    def to_provider_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "ai_coach_context_v1",
            "locale": self.locale,
            "date": self.date.isoformat(),
            "goal": self.goal,
            "diary_aggregates": self.diary_aggregates,
            "dietary_preferences": list(self.dietary_preferences),
            "user_request": self.user_request,
        }


def build_ai_coach_context(
    *,
    user: User,
    message: str,
    context_date: date,
) -> AICoachContext:
    nutrition_profile = NutritionProfile.objects.filter(user=user).first()
    meals = (
        Meal.objects.filter(user=user, logged_at__date=context_date)
        .prefetch_related("items")
        .order_by("logged_at", "created_at")
    )

    return AICoachContext(
        locale=_preferred_locale(user),
        date=context_date,
        goal=_nutrition_goal(nutrition_profile),
        diary_aggregates=aggregate_meals(meals),
        dietary_preferences=_dietary_preferences(nutrition_profile),
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


def _nutrition_goal(nutrition_profile: NutritionProfile | None) -> str:
    if nutrition_profile is None:
        return NutritionProfile.Goal.MAINTAIN_WEIGHT
    return nutrition_profile.goal


def _dietary_preferences(nutrition_profile: NutritionProfile | None) -> tuple[str, ...]:
    if nutrition_profile is None:
        return ()
    preferences = nutrition_profile.dietary_preferences
    if not isinstance(preferences, list):
        return ()
    allowed_preferences = [
        str(preference).strip()
        for preference in preferences
        if str(preference).strip() in _ALLOWED_DIETARY_PREFERENCES
    ]
    return tuple(dict.fromkeys(allowed_preferences))
