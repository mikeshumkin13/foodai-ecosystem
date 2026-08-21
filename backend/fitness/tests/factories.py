from __future__ import annotations

from typing import Any

from django.utils import timezone

from accounts.models import User
from accounts.tests.factories import make_user
from fitness.models import Exercise, Workout, WorkoutExercise, WorkoutLog, WorkoutPlan


def make_exercise(**extra_fields: Any) -> Exercise:
    extra_fields.setdefault("slug", "test_exercise")
    extra_fields.setdefault("name", "Test exercise")
    extra_fields.setdefault("equipment", ["bodyweight"])
    extra_fields.setdefault("training_goals", [WorkoutPlan.Goal.GENERAL_FITNESS])
    return Exercise.objects.create(**extra_fields)


def make_workout_plan(*, user: User | None = None, **extra_fields: Any) -> WorkoutPlan:
    resolved_user = user or make_user()
    extra_fields.setdefault("title", "Test plan")
    extra_fields.setdefault("goal", WorkoutPlan.Goal.GENERAL_FITNESS)
    extra_fields.setdefault("experience_level", WorkoutPlan.ExperienceLevel.BEGINNER)
    extra_fields.setdefault("duration_minutes", 30)
    extra_fields.setdefault("sessions_per_week", 3)
    extra_fields.setdefault("available_equipment", ["bodyweight"])
    return WorkoutPlan.objects.create(user=resolved_user, **extra_fields)


def make_workout(*, plan: WorkoutPlan | None = None, **extra_fields: Any) -> Workout:
    resolved_plan = plan or make_workout_plan()
    extra_fields.setdefault("week_number", 1)
    extra_fields.setdefault("day_number", 1)
    extra_fields.setdefault("order", 1)
    extra_fields.setdefault("title", "Workout 1")
    extra_fields.setdefault("estimated_duration_minutes", 30)
    return Workout.objects.create(plan=resolved_plan, **extra_fields)


def make_workout_exercise(
    *,
    workout: Workout | None = None,
    exercise: Exercise | None = None,
    **extra_fields: Any,
) -> WorkoutExercise:
    resolved_workout = workout or make_workout()
    resolved_exercise = exercise or Exercise.objects.order_by("slug").first() or make_exercise()
    extra_fields.setdefault("order", 1)
    extra_fields.setdefault("target_sets", 2)
    extra_fields.setdefault("target_reps_min", 8)
    extra_fields.setdefault("target_reps_max", 12)
    return WorkoutExercise.objects.create(
        workout=resolved_workout,
        exercise=resolved_exercise,
        **extra_fields,
    )


def make_workout_log(
    *,
    user: User | None = None,
    workout: Workout | None = None,
    **extra_fields: Any,
) -> WorkoutLog:
    resolved_user = user or make_user()
    extra_fields.setdefault("performed_at", timezone.now())
    extra_fields.setdefault("duration_minutes", 30)
    return WorkoutLog.objects.create(user=resolved_user, workout=workout, **extra_fields)
