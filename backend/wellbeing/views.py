from __future__ import annotations

from typing import Any, cast

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.models import User
from wellbeing.permissions import CanUseWellbeingAssistant
from wellbeing.providers import WellbeingAssistantProviderConfigurationError
from wellbeing.serializers import (
    WellbeingAskRequestSerializer,
    WellbeingAskResponseSerializer,
    WellbeingAssistantSettingsSerializer,
    WellbeingProviderErrorSerializer,
    serialize_wellbeing_response,
)
from wellbeing.services import ask_wellbeing_assistant, get_wellbeing_assistant_settings


class WellbeingProviderUnavailable(APIException):
    status_code = 503
    default_detail = "wellbeing_assistant_provider_unavailable"
    default_code = "wellbeing_assistant_provider_unavailable"


class WellbeingAssistantSettingsView(APIView):
    permission_classes = [CanUseWellbeingAssistant]

    @extend_schema(responses={200: WellbeingAssistantSettingsSerializer})
    def get(self, request: Request) -> Response:
        self.action = "settings_read"
        assistant_settings = get_wellbeing_assistant_settings(user=cast(User, request.user))
        return Response(WellbeingAssistantSettingsSerializer(assistant_settings).data)

    @extend_schema(
        request=WellbeingAssistantSettingsSerializer,
        responses={200: WellbeingAssistantSettingsSerializer},
    )
    def patch(self, request: Request) -> Response:
        self.action = "settings_update"
        assistant_settings = get_wellbeing_assistant_settings(user=cast(User, request.user))
        serializer = WellbeingAssistantSettingsSerializer(
            assistant_settings,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class WellbeingAskView(APIView):
    permission_classes = [CanUseWellbeingAssistant]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "wellbeing_assistant"

    @extend_schema(
        request=WellbeingAskRequestSerializer,
        responses={
            200: WellbeingAskResponseSerializer,
            503: WellbeingProviderErrorSerializer,
        },
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = WellbeingAskRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = ask_wellbeing_assistant(
                user=cast(User, request.user),
                message=serializer.validated_data["message"],
                context_date=serializer.validated_data.get("date"),
                store_response=serializer.validated_data["store_response"],
            )
        except WellbeingAssistantProviderConfigurationError as exc:
            raise WellbeingProviderUnavailable() from exc

        return Response(serialize_wellbeing_response(result.to_response_payload()))
