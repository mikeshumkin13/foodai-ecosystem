from __future__ import annotations

from typing import Any, cast

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle, ScopedRateThrottle

from accounts.models import User
from accounts.rbac import (
    CHANGE_OWN_WORKOUT_LOG_PERMISSION,
    CHANGE_OWN_WORKOUT_PLAN_PERMISSION,
    VIEW_OWN_WORKOUT_LOG_PERMISSION,
    VIEW_OWN_WORKOUT_PLAN_PERMISSION,
)
from fitness.models import Exercise, WorkoutLog, WorkoutPlan
from fitness.permissions import (
    CanAccessWorkoutLog,
    CanAccessWorkoutPlan,
    CanReadOrManageExerciseCatalog,
)
from fitness.providers import FitnessCoachProviderConfigurationError
from fitness.serializers import (
    ExerciseReadSerializer,
    ExerciseWriteSerializer,
    FitnessCoachPlanAdaptRequestSerializer,
    FitnessCoachPlanRequestSerializer,
    FitnessCoachPlanResponseSerializer,
    FitnessCoachProviderErrorSerializer,
    WorkoutLogReadSerializer,
    WorkoutLogWriteSerializer,
    WorkoutPlanReadSerializer,
    WorkoutPlanUpdateSerializer,
    serialize_fitness_coach_response,
)
from fitness.services import (
    FitnessCoachPlanResult,
    FitnessPlanCatalogError,
    adapt_workout_plan,
    generate_workout_plan,
)


class FitnessCoachProviderUnavailable(APIException):
    status_code = 503
    default_detail = "fitness_coach_provider_unavailable"
    default_code = "fitness_coach_provider_unavailable"


class FitnessPlanCatalogUnavailable(APIException):
    status_code = 503
    default_detail = "fitness_exercise_catalog_unavailable"
    default_code = "fitness_exercise_catalog_unavailable"


class ExerciseViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [CanReadOrManageExerciseCatalog]
    lookup_field = "id"

    def get_queryset(self) -> QuerySet[Exercise]:
        queryset = Exercise.objects.order_by("name", "id")
        query = self.request.query_params.get("q", "").strip().casefold()
        if query:
            return queryset.filter(name__icontains=query)
        return queryset

    def get_serializer_class(
        self,
    ) -> type[ExerciseReadSerializer] | type[ExerciseWriteSerializer]:
        if self.action in {"create", "update", "partial_update"}:
            return ExerciseWriteSerializer
        return ExerciseReadSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exercise = serializer.save()
        return Response(
            ExerciseReadSerializer(exercise, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        partial = kwargs.pop("partial", False)
        exercise = self.get_object()
        serializer = self.get_serializer(exercise, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_exercise = serializer.save()
        return Response(
            ExerciseReadSerializer(updated_exercise, context=self.get_serializer_context()).data,
        )


class WorkoutPlanViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [CanAccessWorkoutPlan]
    lookup_field = "id"

    def get_queryset(self) -> QuerySet[WorkoutPlan]:
        request_user = self.request.user
        queryset = WorkoutPlan.objects.select_related("user").prefetch_related(
            "workouts__exercises__exercise",
        )
        if not request_user or not request_user.is_authenticated:
            return queryset.none()

        user = cast(User, request_user)
        if user.is_superuser:
            return queryset
        if user.has_perm(VIEW_OWN_WORKOUT_PLAN_PERMISSION) or user.has_perm(
            CHANGE_OWN_WORKOUT_PLAN_PERMISSION
        ):
            return queryset.filter(user=user)
        return queryset.none()

    def get_serializer_class(
        self,
    ) -> type[WorkoutPlanReadSerializer] | type[WorkoutPlanUpdateSerializer]:
        if self.action in {"update", "partial_update"}:
            return WorkoutPlanUpdateSerializer
        return WorkoutPlanReadSerializer

    def get_throttles(self) -> list[BaseThrottle]:
        if self.action in {"generate", "adapt"}:
            self.throttle_scope = "fitness_coach"
            return [ScopedRateThrottle()]
        return []

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        partial = kwargs.pop("partial", False)
        plan = self.get_object()
        serializer = self.get_serializer(plan, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_plan = serializer.save()
        return Response(
            WorkoutPlanReadSerializer(updated_plan, context=self.get_serializer_context()).data,
        )

    @extend_schema(
        request=FitnessCoachPlanRequestSerializer,
        responses={
            201: FitnessCoachPlanResponseSerializer,
            200: FitnessCoachPlanResponseSerializer,
            503: FitnessCoachProviderErrorSerializer,
        },
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="generate",
    )
    def generate(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = FitnessCoachPlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = generate_workout_plan(
                user=cast(User, request.user),
                goal=serializer.validated_data["goal"],
                experience_level=serializer.validated_data["experience_level"],
                duration_minutes=serializer.validated_data["duration_minutes"],
                available_equipment=serializer.validated_data["available_equipment"],
                sessions_per_week=serializer.validated_data["sessions_per_week"],
                message=serializer.validated_data["message"],
                locale=serializer.validated_data["locale"],
            )
        except FitnessCoachProviderConfigurationError as exc:
            raise FitnessCoachProviderUnavailable() from exc
        except FitnessPlanCatalogError as exc:
            raise FitnessPlanCatalogUnavailable() from exc

        return _coach_response(result, context=self.get_serializer_context())

    @extend_schema(
        request=FitnessCoachPlanAdaptRequestSerializer,
        responses={
            200: FitnessCoachPlanResponseSerializer,
            503: FitnessCoachProviderErrorSerializer,
        },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="adapt",
    )
    def adapt(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        plan = self.get_object()
        serializer = FitnessCoachPlanAdaptRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = adapt_workout_plan(
                plan=plan,
                goal=serializer.validated_data.get("goal"),
                experience_level=serializer.validated_data.get("experience_level"),
                duration_minutes=serializer.validated_data.get("duration_minutes"),
                available_equipment=serializer.validated_data.get("available_equipment"),
                sessions_per_week=serializer.validated_data.get("sessions_per_week"),
                message=serializer.validated_data["message"],
                locale=serializer.validated_data["locale"],
            )
        except FitnessCoachProviderConfigurationError as exc:
            raise FitnessCoachProviderUnavailable() from exc
        except FitnessPlanCatalogError as exc:
            raise FitnessPlanCatalogUnavailable() from exc

        return _coach_response(result, context=self.get_serializer_context())


class WorkoutLogViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [CanAccessWorkoutLog]
    lookup_field = "id"

    def get_queryset(self) -> QuerySet[WorkoutLog]:
        request_user = self.request.user
        queryset = WorkoutLog.objects.select_related("user", "workout", "workout__plan")
        if not request_user or not request_user.is_authenticated:
            return queryset.none()

        user = cast(User, request_user)
        if user.is_superuser:
            return queryset
        if user.has_perm(VIEW_OWN_WORKOUT_LOG_PERMISSION) or user.has_perm(
            CHANGE_OWN_WORKOUT_LOG_PERMISSION
        ):
            return queryset.filter(user=user)
        return queryset.none()

    def get_serializer_class(
        self,
    ) -> type[WorkoutLogReadSerializer] | type[WorkoutLogWriteSerializer]:
        if self.action in {"create", "update", "partial_update"}:
            return WorkoutLogWriteSerializer
        return WorkoutLogReadSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workout_log = serializer.save(user=cast(User, request.user))
        return Response(
            WorkoutLogReadSerializer(workout_log, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        partial = kwargs.pop("partial", False)
        workout_log = self.get_object()
        serializer = self.get_serializer(workout_log, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_log = serializer.save()
        return Response(
            WorkoutLogReadSerializer(updated_log, context=self.get_serializer_context()).data,
        )


def _coach_response(result: FitnessCoachPlanResult, *, context: dict[str, Any]) -> Response:
    plan_payload = None
    status_code: int = status.HTTP_200_OK
    if result.plan is not None:
        plan_payload = cast(
            dict[str, Any],
            WorkoutPlanReadSerializer(result.plan, context=context).data,
        )
        if result.code == "fitness_coach_plan_created":
            status_code = status.HTTP_201_CREATED

    payload = result.to_response_payload(plan_payload=plan_payload)
    return Response(serialize_fitness_coach_response(payload), status=status_code)
