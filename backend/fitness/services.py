from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from accounts.models import User
from fitness.models import Exercise, Workout, WorkoutExercise, WorkoutPlan
from fitness.providers import (
    FitnessCoachProvider,
    FitnessCoachProviderRequest,
    FitnessCoachProviderResponse,
    get_fitness_coach_provider,
)
from fitness.safety import (
    FitnessSafetyDecision,
    fitness_safety_refusal_message,
    moderate_fitness_request,
    moderate_provider_text,
)
from observability.metrics import call_with_ai_provider_metrics

FITNESS_COACH_OUTPUT_SCHEMA_VERSION = "ai_fitness_coach_plan_response_v1"

ALLOWED_EQUIPMENT = frozenset(
    {
        "bodyweight",
        "mat",
        "dumbbells",
        "barbell",
        "kettlebell",
        "resistance_band",
        "machine",
        "pull_up_bar",
        "treadmill",
        "bike",
    }
)


class FitnessPlanCatalogError(RuntimeError):
    pass


@dataclass(frozen=True)
class FitnessCoachPlanResult:
    code: str
    schema_version: str
    plan: WorkoutPlan | None
    safety: FitnessSafetyDecision
    provider_name: str
    explanation: dict[str, Any]

    def to_response_payload(self, *, plan_payload: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "code": self.code,
            "schema_version": self.schema_version,
            "plan": plan_payload,
            "safety": self.safety.to_payload(),
            "provider": self.provider_name,
            "explanation": self.explanation,
        }


def generate_workout_plan(
    *,
    user: User,
    goal: str,
    experience_level: str,
    duration_minutes: int,
    available_equipment: list[str],
    sessions_per_week: int,
    message: str = "",
    locale: str = "ru",
    provider: FitnessCoachProvider | None = None,
) -> FitnessCoachPlanResult:
    normalized_equipment = normalize_equipment(available_equipment)
    normalized_message = message.strip()
    safety = moderate_fitness_request(normalized_message)
    if safety.blocked:
        return _safety_result(safety=safety, locale=locale, provider_name="safety_layer")

    plan_draft = _build_plan_draft(
        goal=goal,
        experience_level=experience_level,
        duration_minutes=duration_minutes,
        available_equipment=normalized_equipment,
        sessions_per_week=sessions_per_week,
    )
    explanation = _safe_provider_explanation(
        plan_draft=plan_draft,
        locale=locale,
        message=normalized_message,
        provider=provider,
    )
    if explanation.safety.blocked:
        return _safety_result(
            safety=explanation.safety,
            locale=locale,
            provider_name=explanation.provider_name,
        )

    with transaction.atomic():
        plan = _persist_plan_draft(
            user=user,
            plan_draft=plan_draft,
            provider_name=explanation.provider_name,
            explanation=explanation.payload,
        )

    return FitnessCoachPlanResult(
        code="fitness_coach_plan_created",
        schema_version=FITNESS_COACH_OUTPUT_SCHEMA_VERSION,
        plan=plan,
        safety=FitnessSafetyDecision.passed(),
        provider_name=explanation.provider_name,
        explanation=explanation.payload,
    )


def adapt_workout_plan(
    *,
    plan: WorkoutPlan,
    goal: str | None = None,
    experience_level: str | None = None,
    duration_minutes: int | None = None,
    available_equipment: list[str] | None = None,
    sessions_per_week: int | None = None,
    message: str = "",
    locale: str = "ru",
    provider: FitnessCoachProvider | None = None,
) -> FitnessCoachPlanResult:
    normalized_message = message.strip()
    safety = moderate_fitness_request(normalized_message)
    if safety.blocked:
        return _safety_result(safety=safety, locale=locale, provider_name="safety_layer")

    resolved_goal = goal or plan.goal
    resolved_experience_level = experience_level or plan.experience_level
    resolved_duration_minutes = duration_minutes or plan.duration_minutes
    resolved_sessions_per_week = sessions_per_week or plan.sessions_per_week
    resolved_equipment = normalize_equipment(
        available_equipment if available_equipment is not None else list(plan.available_equipment)
    )
    plan_draft = _build_plan_draft(
        goal=resolved_goal,
        experience_level=resolved_experience_level,
        duration_minutes=resolved_duration_minutes,
        available_equipment=resolved_equipment,
        sessions_per_week=resolved_sessions_per_week,
    )
    explanation = _safe_provider_explanation(
        plan_draft=plan_draft,
        locale=locale,
        message=normalized_message,
        provider=provider,
    )
    if explanation.safety.blocked:
        return _safety_result(
            safety=explanation.safety,
            locale=locale,
            provider_name=explanation.provider_name,
        )

    with transaction.atomic():
        _replace_plan_with_draft(
            plan=plan,
            plan_draft=plan_draft,
            provider_name=explanation.provider_name,
            explanation=explanation.payload,
        )

    return FitnessCoachPlanResult(
        code="fitness_coach_plan_adapted",
        schema_version=FITNESS_COACH_OUTPUT_SCHEMA_VERSION,
        plan=plan,
        safety=FitnessSafetyDecision.passed(),
        provider_name=explanation.provider_name,
        explanation=explanation.payload,
    )


def normalize_equipment(equipment: list[str]) -> list[str]:
    normalized_items: list[str] = []
    seen_items: set[str] = set()
    for raw_item in [*equipment, "bodyweight"]:
        item = str(raw_item).strip().casefold()
        if not item or item in seen_items:
            continue
        normalized_items.append(item)
        seen_items.add(item)
    return sorted(normalized_items)


@dataclass(frozen=True)
class _SafeExplanation:
    provider_name: str
    safety: FitnessSafetyDecision
    payload: dict[str, Any]


def _safe_provider_explanation(
    *,
    plan_draft: dict[str, Any],
    locale: str,
    message: str,
    provider: FitnessCoachProvider | None,
) -> _SafeExplanation:
    resolved_provider = provider or get_fitness_coach_provider()
    provider_request = FitnessCoachProviderRequest(
        plan_payload=plan_draft,
        locale=locale,
        user_request=message,
        output_schema_version=FITNESS_COACH_OUTPUT_SCHEMA_VERSION,
    )
    provider_response = call_with_ai_provider_metrics(
        assistant="fitness",
        provider=resolved_provider.name,
        operation=lambda: resolved_provider.explain(provider_request),
    )
    output_safety = moderate_provider_text(_provider_response_text(provider_response))
    if output_safety.blocked:
        return _SafeExplanation(
            provider_name=resolved_provider.name,
            safety=output_safety,
            payload={},
        )
    return _SafeExplanation(
        provider_name=resolved_provider.name,
        safety=FitnessSafetyDecision.passed(),
        payload=_provider_payload(provider_name=resolved_provider.name, response=provider_response),
    )


def _provider_payload(
    *,
    provider_name: str,
    response: FitnessCoachProviderResponse,
) -> dict[str, Any]:
    return {
        "schema_version": FITNESS_COACH_OUTPUT_SCHEMA_VERSION,
        "provider": provider_name,
        "summary": response.summary,
        "rationale": list(response.rationale),
        "safety_notes": list(response.safety_notes),
    }


def _provider_response_text(provider_response: FitnessCoachProviderResponse) -> str:
    return "\n".join(
        [
            provider_response.summary,
            *provider_response.rationale,
            *provider_response.safety_notes,
        ]
    )


def _safety_result(
    *,
    safety: FitnessSafetyDecision,
    locale: str,
    provider_name: str,
) -> FitnessCoachPlanResult:
    return FitnessCoachPlanResult(
        code="fitness_coach_safety_blocked",
        schema_version=FITNESS_COACH_OUTPUT_SCHEMA_VERSION,
        plan=None,
        safety=safety,
        provider_name=provider_name,
        explanation={
            "schema_version": FITNESS_COACH_OUTPUT_SCHEMA_VERSION,
            "provider": provider_name,
            "summary": fitness_safety_refusal_message(locale=locale),
            "rationale": [],
            "safety_notes": ["fitness_safety_boundary"],
        },
    )


def _build_plan_draft(
    *,
    goal: str,
    experience_level: str,
    duration_minutes: int,
    available_equipment: list[str],
    sessions_per_week: int,
) -> dict[str, Any]:
    selected_exercises = _select_exercises(
        goal=goal,
        experience_level=experience_level,
        available_equipment=available_equipment,
        duration_minutes=duration_minutes,
    )
    workouts = [
        _workout_payload(
            day_number=day_number,
            goal=goal,
            experience_level=experience_level,
            duration_minutes=duration_minutes,
            selected_exercises=selected_exercises,
        )
        for day_number in range(1, sessions_per_week + 1)
    ]
    return {
        "title": _plan_title(goal=goal, duration_minutes=duration_minutes),
        "goal": goal,
        "experience_level": experience_level,
        "duration_minutes": duration_minutes,
        "sessions_per_week": sessions_per_week,
        "available_equipment": available_equipment,
        "workouts": workouts,
    }


def _select_exercises(
    *,
    goal: str,
    experience_level: str,
    available_equipment: list[str],
    duration_minutes: int,
) -> list[Exercise]:
    exercise_count = _exercise_count_for_duration(duration_minutes)
    equipment = set(available_equipment)
    candidates = [
        exercise
        for exercise in Exercise.objects.filter(is_active=True).order_by("slug")
        if _exercise_matches(
            exercise,
            goal=goal,
            experience_level=experience_level,
            equipment=equipment,
        )
    ]
    if not candidates:
        raise FitnessPlanCatalogError("fitness_exercise_catalog_empty")

    candidates.sort(
        key=lambda item: _exercise_rank(
            item,
            goal=goal,
            experience_level=experience_level,
        )
    )
    return candidates[:exercise_count]


def _exercise_matches(
    exercise: Exercise,
    *,
    goal: str,
    experience_level: str,
    equipment: set[str],
) -> bool:
    exercise_equipment = set(exercise.equipment or ["bodyweight"])
    if not exercise_equipment.issubset(equipment):
        return False
    if exercise.difficulty == Exercise.Difficulty.ADVANCED and experience_level != "advanced":
        return False
    if exercise.difficulty == Exercise.Difficulty.INTERMEDIATE and experience_level == "beginner":
        return False
    return goal in exercise.training_goals or "general_fitness" in exercise.training_goals


def _exercise_rank(exercise: Exercise, *, goal: str, experience_level: str) -> tuple[int, int, str]:
    goal_match_rank = 0 if goal in exercise.training_goals else 1
    difficulty_rank = (
        0 if exercise.difficulty in {experience_level, Exercise.Difficulty.ALL_LEVELS} else 1
    )
    return (goal_match_rank, difficulty_rank, exercise.slug)


def _exercise_count_for_duration(duration_minutes: int) -> int:
    if duration_minutes <= 30:
        return 3
    if duration_minutes <= 45:
        return 4
    return 5


def _workout_payload(
    *,
    day_number: int,
    goal: str,
    experience_level: str,
    duration_minutes: int,
    selected_exercises: list[Exercise],
) -> dict[str, Any]:
    exercises = [
        _workout_exercise_payload(
            exercise=exercise,
            order=order,
            goal=goal,
            experience_level=experience_level,
        )
        for order, exercise in enumerate(
            _rotate_exercises(selected_exercises, offset=day_number - 1),
            start=1,
        )
    ]
    return {
        "week_number": 1,
        "day_number": day_number,
        "order": day_number,
        "title": f"Workout {day_number}",
        "focus": _focus_for_goal(goal),
        "estimated_duration_minutes": duration_minutes,
        "exercises": exercises,
    }


def _rotate_exercises(exercises: list[Exercise], *, offset: int) -> list[Exercise]:
    if not exercises:
        return exercises
    resolved_offset = offset % len(exercises)
    return [*exercises[resolved_offset:], *exercises[:resolved_offset]]


def _workout_exercise_payload(
    *,
    exercise: Exercise,
    order: int,
    goal: str,
    experience_level: str,
) -> dict[str, Any]:
    sets = {"beginner": 2, "intermediate": 3, "advanced": 4}[experience_level]
    rest_seconds = {"beginner": 60, "intermediate": 75, "advanced": 90}[experience_level]
    intensity = {
        "beginner": WorkoutExercise.Intensity.EASY,
        "intermediate": WorkoutExercise.Intensity.MODERATE,
        "advanced": WorkoutExercise.Intensity.MODERATE,
    }[experience_level]
    payload: dict[str, Any] = {
        "exercise_slug": exercise.slug,
        "order": order,
        "target_sets": sets,
        "target_reps_min": None,
        "target_reps_max": None,
        "target_duration_seconds": None,
        "rest_seconds": rest_seconds,
        "intensity": intensity,
        "coaching_notes": _coaching_note(goal=goal, exercise=exercise),
    }
    if exercise.prescription_type == Exercise.PrescriptionType.TIME:
        payload["target_duration_seconds"] = exercise.default_duration_seconds or _time_target(
            goal=goal
        )
    else:
        reps_min, reps_max = _rep_range(goal=goal, experience_level=experience_level)
        payload["target_reps_min"] = reps_min
        payload["target_reps_max"] = reps_max
    return payload


def _persist_plan_draft(
    *,
    user: User,
    plan_draft: dict[str, Any],
    provider_name: str,
    explanation: dict[str, Any],
) -> WorkoutPlan:
    plan = WorkoutPlan.objects.create(
        user=user,
        title=str(plan_draft["title"]),
        goal=str(plan_draft["goal"]),
        experience_level=str(plan_draft["experience_level"]),
        duration_minutes=int(plan_draft["duration_minutes"]),
        sessions_per_week=int(plan_draft["sessions_per_week"]),
        available_equipment=list(plan_draft["available_equipment"]),
        ai_explanation=explanation,
        safety_warnings=_safety_notes(provider_name=provider_name),
    )
    _create_workouts_from_draft(plan=plan, plan_draft=plan_draft)
    return plan


def _replace_plan_with_draft(
    *,
    plan: WorkoutPlan,
    plan_draft: dict[str, Any],
    provider_name: str,
    explanation: dict[str, Any],
) -> WorkoutPlan:
    plan.title = str(plan_draft["title"])
    plan.goal = str(plan_draft["goal"])
    plan.experience_level = str(plan_draft["experience_level"])
    plan.duration_minutes = int(plan_draft["duration_minutes"])
    plan.sessions_per_week = int(plan_draft["sessions_per_week"])
    plan.available_equipment = list(plan_draft["available_equipment"])
    plan.ai_explanation = explanation
    plan.safety_warnings = _safety_notes(provider_name=provider_name)
    plan.save()
    plan.workouts.all().delete()
    _create_workouts_from_draft(plan=plan, plan_draft=plan_draft)
    return plan


def _create_workouts_from_draft(*, plan: WorkoutPlan, plan_draft: dict[str, Any]) -> None:
    exercise_by_slug = {exercise.slug: exercise for exercise in Exercise.objects.all()}
    for workout_data in plan_draft["workouts"]:
        workout = Workout.objects.create(
            plan=plan,
            week_number=int(workout_data["week_number"]),
            day_number=int(workout_data["day_number"]),
            order=int(workout_data["order"]),
            title=str(workout_data["title"]),
            focus=str(workout_data["focus"]),
            estimated_duration_minutes=int(workout_data["estimated_duration_minutes"]),
        )
        WorkoutExercise.objects.bulk_create(
            [
                WorkoutExercise(
                    workout=workout,
                    exercise=exercise_by_slug[str(exercise_data["exercise_slug"])],
                    order=int(exercise_data["order"]),
                    target_sets=int(exercise_data["target_sets"]),
                    target_reps_min=exercise_data["target_reps_min"],
                    target_reps_max=exercise_data["target_reps_max"],
                    target_duration_seconds=exercise_data["target_duration_seconds"],
                    rest_seconds=int(exercise_data["rest_seconds"]),
                    intensity=str(exercise_data["intensity"]),
                    coaching_notes=str(exercise_data["coaching_notes"]),
                )
                for exercise_data in workout_data["exercises"]
            ]
        )


def _safety_notes(*, provider_name: str) -> list[str]:
    return [
        "general_fitness_guidance_not_medical_advice",
        f"ai_explanation_provider:{provider_name}",
    ]


def _plan_title(*, goal: str, duration_minutes: int) -> str:
    readable_goal = goal.replace("_", " ")
    return f"{readable_goal.title()} Plan, {duration_minutes} min"


def _focus_for_goal(goal: str) -> str:
    focus_by_goal: dict[str, str] = {
        WorkoutPlan.Goal.FAT_LOSS.value: "conditioning and full-body strength",
        WorkoutPlan.Goal.MUSCLE_GAIN.value: "progressive strength volume",
        WorkoutPlan.Goal.STRENGTH.value: "strength skill and compound patterns",
        WorkoutPlan.Goal.ENDURANCE.value: "steady conditioning",
        WorkoutPlan.Goal.MOBILITY.value: "mobility and control",
    }
    return focus_by_goal.get(goal, "balanced full-body fitness")


def _rep_range(*, goal: str, experience_level: str) -> tuple[int, int]:
    if goal == WorkoutPlan.Goal.STRENGTH:
        return (5, 8) if experience_level != "beginner" else (6, 8)
    if goal == WorkoutPlan.Goal.MUSCLE_GAIN:
        return (8, 12)
    if goal in {WorkoutPlan.Goal.ENDURANCE, WorkoutPlan.Goal.FAT_LOSS}:
        return (12, 15)
    return (8, 12)


def _time_target(*, goal: str) -> int:
    if goal == WorkoutPlan.Goal.ENDURANCE:
        return 300
    if goal == WorkoutPlan.Goal.MOBILITY:
        return 45
    return 30


def _coaching_note(*, goal: str, exercise: Exercise) -> str:
    if goal == WorkoutPlan.Goal.STRENGTH:
        return "Keep technique consistent; stop the set before form breaks."
    if goal == WorkoutPlan.Goal.MOBILITY:
        return "Move slowly and keep the range comfortable."
    if exercise.prescription_type == Exercise.PrescriptionType.TIME:
        return "Use a pace that allows controlled breathing."
    return "Use a controlled tempo and leave repetitions in reserve."
