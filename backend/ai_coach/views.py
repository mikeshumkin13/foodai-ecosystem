from __future__ import annotations

from typing import Any, cast

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.models import User
from ai_coach.permissions import CanUseAICoach
from ai_coach.providers import AICoachProviderConfigurationError
from ai_coach.serializers import (
    AICoachAskRequestSerializer,
    AICoachAskResponseSerializer,
    AICoachProviderErrorSerializer,
    AICoachSettingsSerializer,
    serialize_ai_coach_response,
)
from ai_coach.services import ask_nutrition_coach, get_ai_coach_settings


class AICoachProviderUnavailable(APIException):
    status_code = 503
    default_detail = "ai_coach_provider_unavailable"
    default_code = "ai_coach_provider_unavailable"


class AICoachSettingsView(APIView):
    permission_classes = [CanUseAICoach]

    @extend_schema(responses={200: AICoachSettingsSerializer})
    def get(self, request: Request) -> Response:
        self.action = "settings_read"
        ai_coach_settings = get_ai_coach_settings(user=cast(User, request.user))
        return Response(AICoachSettingsSerializer(ai_coach_settings).data)

    @extend_schema(request=AICoachSettingsSerializer, responses={200: AICoachSettingsSerializer})
    def patch(self, request: Request) -> Response:
        self.action = "settings_update"
        ai_coach_settings = get_ai_coach_settings(user=cast(User, request.user))
        serializer = AICoachSettingsSerializer(
            ai_coach_settings,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AICoachAskView(APIView):
    permission_classes = [CanUseAICoach]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_coach_ask"

    @extend_schema(
        request=AICoachAskRequestSerializer,
        responses={
            200: AICoachAskResponseSerializer,
            503: AICoachProviderErrorSerializer,
        },
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = AICoachAskRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = ask_nutrition_coach(
                user=cast(User, request.user),
                message=serializer.validated_data["message"],
                context_date=serializer.validated_data.get("date"),
                store_response=serializer.validated_data["store_response"],
            )
        except AICoachProviderConfigurationError as exc:
            raise AICoachProviderUnavailable() from exc

        return Response(serialize_ai_coach_response(result.to_response_payload()))
