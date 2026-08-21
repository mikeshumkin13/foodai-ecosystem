from __future__ import annotations

from typing import Any, cast

from rest_framework import serializers

from accounts.models import User
from fitness.models import Exercise, Workout, WorkoutExercise, WorkoutLog, WorkoutPlan
from fitness.services import ALLOWED_EQUIPMENT


class ExerciseReadSerializer(serializers.ModelSerializer[Exercise]):
    class Meta:
        model = Exercise
        fields = (
            "id",
            "slug",
            "name",
            "name_ru",
            "name_en",
            "description",
            "muscle_group",
            "movement_pattern",
            "equipment",
            "difficulty",
            "training_goals",
            "prescription_type",
            "default_duration_seconds",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ExerciseWriteSerializer(serializers.ModelSerializer[Exercise]):
    class Meta:
        model = Exercise
        fields = (
            "id",
            "slug",
            "name",
            "name_ru",
            "name_en",
            "description",
            "muscle_group",
            "movement_pattern",
            "equipment",
            "difficulty",
            "training_goals",
            "prescription_type",
            "default_duration_seconds",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_equipment(self, value: Any) -> list[str]:
        return _validate_equipment(value)

    def validate_training_goals(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            raise serializers.ValidationError("training_goals_must_be_list")
        allowed_goals = {choice[0] for choice in WorkoutPlan.Goal.choices}
        goals: list[str] = []
        for raw_goal in value:
            goal = str(raw_goal).strip().casefold()
            if goal not in allowed_goals:
                raise serializers.ValidationError("unknown_training_goal")
            if goal not in goals:
                goals.append(goal)
        return goals


class WorkoutExerciseReadSerializer(serializers.ModelSerializer[WorkoutExercise]):
    exercise = ExerciseReadSerializer(read_only=True)

    class Meta:
        model = WorkoutExercise
        fields = (
            "id",
            "exercise",
            "order",
            "target_sets",
            "target_reps_min",
            "target_reps_max",
            "target_duration_seconds",
            "rest_seconds",
            "intensity",
            "coaching_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class WorkoutReadSerializer(serializers.ModelSerializer[Workout]):
    exercises = WorkoutExerciseReadSerializer(many=True, read_only=True)

    class Meta:
        model = Workout
        fields = (
            "id",
            "week_number",
            "day_number",
            "order",
            "title",
            "focus",
            "estimated_duration_minutes",
            "exercises",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class WorkoutPlanReadSerializer(serializers.ModelSerializer[WorkoutPlan]):
    user_id = serializers.UUIDField(read_only=True)
    workouts = WorkoutReadSerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutPlan
        fields = (
            "id",
            "user_id",
            "title",
            "goal",
            "experience_level",
            "duration_minutes",
            "sessions_per_week",
            "available_equipment",
            "ai_explanation",
            "safety_warnings",
            "status",
            "workouts",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class WorkoutPlanUpdateSerializer(serializers.ModelSerializer[WorkoutPlan]):
    class Meta:
        model = WorkoutPlan
        fields = ("title", "status")


class FitnessCoachPlanRequestSerializer(serializers.Serializer[dict[str, Any]]):
    goal = serializers.ChoiceField(choices=WorkoutPlan.Goal.choices)
    experience_level = serializers.ChoiceField(choices=WorkoutPlan.ExperienceLevel.choices)
    duration_minutes = serializers.IntegerField(min_value=10, max_value=180)
    sessions_per_week = serializers.IntegerField(min_value=1, max_value=7, default=3)
    available_equipment = serializers.ListField(
        child=serializers.CharField(max_length=40),
        allow_empty=True,
        default=list,
    )
    message = serializers.CharField(max_length=2000, allow_blank=True, required=False, default="")
    locale = serializers.ChoiceField(choices=("ru", "en"), default="ru")

    def validate_available_equipment(self, value: Any) -> list[str]:
        return _validate_equipment(value)


class FitnessCoachPlanAdaptRequestSerializer(serializers.Serializer[dict[str, Any]]):
    goal = serializers.ChoiceField(choices=WorkoutPlan.Goal.choices, required=False)
    experience_level = serializers.ChoiceField(
        choices=WorkoutPlan.ExperienceLevel.choices,
        required=False,
    )
    duration_minutes = serializers.IntegerField(min_value=10, max_value=180, required=False)
    sessions_per_week = serializers.IntegerField(min_value=1, max_value=7, required=False)
    available_equipment = serializers.ListField(
        child=serializers.CharField(max_length=40),
        allow_empty=True,
        required=False,
    )
    message = serializers.CharField(max_length=2000, allow_blank=True, required=False, default="")
    locale = serializers.ChoiceField(choices=("ru", "en"), default="ru")

    def validate_available_equipment(self, value: Any) -> list[str]:
        return _validate_equipment(value)


class FitnessCoachSafetySerializer(serializers.Serializer[dict[str, Any]]):
    blocked = serializers.BooleanField()
    code = serializers.CharField()
    categories = serializers.ListField(child=serializers.CharField())
    reason = serializers.CharField(allow_blank=True)


class FitnessCoachExplanationSerializer(serializers.Serializer[dict[str, Any]]):
    schema_version = serializers.CharField()
    provider = serializers.CharField()
    summary = serializers.CharField()
    rationale = serializers.ListField(child=serializers.CharField())
    safety_notes = serializers.ListField(child=serializers.CharField())


class FitnessCoachPlanResponseSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField()
    schema_version = serializers.CharField()
    plan = serializers.JSONField(allow_null=True)
    safety = FitnessCoachSafetySerializer()
    provider = serializers.CharField()
    explanation = FitnessCoachExplanationSerializer()


class FitnessCoachProviderErrorSerializer(serializers.Serializer[dict[str, str]]):
    detail = serializers.CharField()


class WorkoutLogReadSerializer(serializers.ModelSerializer[WorkoutLog]):
    user_id = serializers.UUIDField(read_only=True)
    workout_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = WorkoutLog
        fields = (
            "id",
            "user_id",
            "workout_id",
            "performed_at",
            "duration_minutes",
            "perceived_exertion",
            "completed",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class WorkoutLogWriteSerializer(serializers.ModelSerializer[WorkoutLog]):
    workout_id = serializers.PrimaryKeyRelatedField(
        queryset=Workout.objects.select_related("plan").all(),
        source="workout",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = WorkoutLog
        fields = (
            "id",
            "workout_id",
            "performed_at",
            "duration_minutes",
            "perceived_exertion",
            "completed",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_workout_id(self, value: Workout | None) -> Workout | None:
        if value is None:
            return value

        request = self.context.get("request")
        user = cast(User | None, getattr(request, "user", None))
        if user is None or not user.is_authenticated:
            raise serializers.ValidationError("invalid_workout")
        if value.plan.user_id != user.id and not user.is_superuser:
            raise serializers.ValidationError("invalid_workout")
        return value


def serialize_fitness_coach_response(payload: dict[str, Any]) -> dict[str, Any]:
    serializer = FitnessCoachPlanResponseSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    return cast(dict[str, Any], serializer.data)


def _validate_equipment(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise serializers.ValidationError("equipment_must_be_list")

    normalized_items: list[str] = []
    seen_items: set[str] = set()
    for raw_item in value:
        item = str(raw_item).strip().casefold()
        if not item:
            continue
        if item not in ALLOWED_EQUIPMENT:
            raise serializers.ValidationError("unknown_equipment")
        if item not in seen_items:
            normalized_items.append(item)
            seen_items.add(item)
    return normalized_items
