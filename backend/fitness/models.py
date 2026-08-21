from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower


class Exercise(models.Model):
    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        ALL_LEVELS = "all_levels", "All levels"

    class MuscleGroup(models.TextChoices):
        FULL_BODY = "full_body", "Full body"
        LEGS = "legs", "Legs"
        CHEST = "chest", "Chest"
        BACK = "back", "Back"
        SHOULDERS = "shoulders", "Shoulders"
        ARMS = "arms", "Arms"
        CORE = "core", "Core"
        CARDIO = "cardio", "Cardio"
        MOBILITY = "mobility", "Mobility"

    class MovementPattern(models.TextChoices):
        SQUAT = "squat", "Squat"
        HINGE = "hinge", "Hinge"
        PUSH = "push", "Push"
        PULL = "pull", "Pull"
        LUNGE = "lunge", "Lunge"
        CORE = "core", "Core"
        CARRY = "carry", "Carry"
        CARDIO = "cardio", "Cardio"
        MOBILITY = "mobility", "Mobility"

    class PrescriptionType(models.TextChoices):
        REPS = "reps", "Reps"
        TIME = "time", "Time"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=160)
    name_ru = models.CharField(max_length=160, blank=True)
    name_en = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    muscle_group = models.CharField(
        max_length=32,
        choices=MuscleGroup.choices,
        default=MuscleGroup.FULL_BODY,
    )
    movement_pattern = models.CharField(
        max_length=32,
        choices=MovementPattern.choices,
        default=MovementPattern.CORE,
    )
    equipment = models.JSONField(default=list, blank=True)
    difficulty = models.CharField(
        max_length=32,
        choices=Difficulty.choices,
        default=Difficulty.ALL_LEVELS,
    )
    training_goals = models.JSONField(default=list, blank=True)
    prescription_type = models.CharField(
        max_length=16,
        choices=PrescriptionType.choices,
        default=PrescriptionType.REPS,
    )
    default_duration_seconds = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [
            models.Index(Lower("name"), name="fit_ex_name_lower_idx"),
            models.Index(fields=["is_active"], name="fitness_exercise_active_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class WorkoutPlan(models.Model):
    class Goal(models.TextChoices):
        GENERAL_FITNESS = "general_fitness", "General fitness"
        FAT_LOSS = "fat_loss", "Fat loss"
        MUSCLE_GAIN = "muscle_gain", "Muscle gain"
        STRENGTH = "strength", "Strength"
        ENDURANCE = "endurance", "Endurance"
        MOBILITY = "mobility", "Mobility"

    class ExperienceLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workout_plans",
    )
    title = models.CharField(max_length=160)
    goal = models.CharField(max_length=32, choices=Goal.choices)
    experience_level = models.CharField(max_length=32, choices=ExperienceLevel.choices)
    duration_minutes = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(180)],
    )
    sessions_per_week = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
    )
    available_equipment = models.JSONField(default=list, blank=True)
    ai_explanation = models.JSONField(default=dict, blank=True)
    safety_warnings = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "id"]
        indexes = [
            models.Index(fields=["user", "status"], name="fitness_plan_user_status_idx"),
        ]
        permissions = [
            ("use_ai_fitness_coach", "Can use AI fitness coach"),
            ("view_own_workoutplan", "Can view own workout plan"),
            ("change_own_workoutplan", "Can change own workout plan"),
        ]

    def __str__(self) -> str:
        return f"{self.title} for user {self.user_id}"


class Workout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE, related_name="workouts")
    week_number = models.PositiveSmallIntegerField(default=1)
    day_number = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    order = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=160)
    focus = models.CharField(max_length=120, blank=True)
    estimated_duration_minutes = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(5), MaxValueValidator(180)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["week_number", "day_number", "order", "id"]
        indexes = [
            models.Index(
                fields=["plan", "week_number", "day_number"],
                name="fitness_workout_plan_day_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "week_number", "day_number", "order"],
                name="unique_workout_order_per_plan_day",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.plan_id})"


class WorkoutExercise(models.Model):
    class Intensity(models.TextChoices):
        EASY = "easy", "Easy"
        MODERATE = "moderate", "Moderate"
        HARD = "hard", "Hard"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name="exercises")
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.PROTECT,
        related_name="workout_prescriptions",
    )
    order = models.PositiveSmallIntegerField(default=1)
    target_sets = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    target_reps_min = models.PositiveSmallIntegerField(null=True, blank=True)
    target_reps_max = models.PositiveSmallIntegerField(null=True, blank=True)
    target_duration_seconds = models.PositiveSmallIntegerField(null=True, blank=True)
    rest_seconds = models.PositiveSmallIntegerField(default=60)
    intensity = models.CharField(
        max_length=16,
        choices=Intensity.choices,
        default=Intensity.MODERATE,
    )
    coaching_notes = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        indexes = [
            models.Index(fields=["workout", "exercise"], name="fitness_wex_workout_ex_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workout", "order"],
                name="unique_exercise_order_per_workout",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.exercise} in {self.workout}"


class WorkoutLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workout_logs",
    )
    workout = models.ForeignKey(
        Workout,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
    )
    performed_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(300)],
    )
    perceived_exertion = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("1")), MaxValueValidator(Decimal("10"))],
    )
    completed = models.BooleanField(default=True)
    notes = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-performed_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "performed_at"], name="fitness_log_user_time_idx"),
        ]
        permissions = [
            ("view_own_workoutlog", "Can view own workout log"),
            ("change_own_workoutlog", "Can change own workout log"),
        ]

    def __str__(self) -> str:
        return f"Workout log {self.id} for user {self.user_id}"
