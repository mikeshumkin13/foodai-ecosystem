from __future__ import annotations

import uuid
from typing import Any, cast

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from audit.models import AuditLog
from audit.services import record_audit_event
from privacy.permissions import CanUsePrivacyCenter
from privacy.serializers import (
    PrivacyAccountDeletionRequestSerializer,
    PrivacyDataSummarySerializer,
    PrivacyDeletionResponseSerializer,
    PrivacySettingsSerializer,
)
from privacy.services import (
    PrivacyAuthenticationError,
    PrivacyObjectNotFound,
    build_privacy_data_summary,
    build_user_data_export_bytes,
    delete_ai_chat_history,
    delete_food_scan_photo,
    delete_user_account,
    get_privacy_settings,
)


class PrivacyDataSummaryView(APIView):
    permission_classes = [CanUsePrivacyCenter]
    privacy_action = "summary"

    @extend_schema(responses={status.HTTP_200_OK: PrivacyDataSummarySerializer})
    def get(self, request: Request) -> Response:
        payload = build_privacy_data_summary(user=cast(User, request.user))
        serializer = PrivacyDataSummarySerializer(payload)
        return Response(serializer.data)


class PrivacyDataExportView(APIView):
    permission_classes = [CanUsePrivacyCenter]
    privacy_action = "export"

    @extend_schema(responses={status.HTTP_200_OK: OpenApiTypes.BINARY})
    def get(self, request: Request) -> HttpResponse:
        user = cast(User, request.user)
        response = HttpResponse(
            build_user_data_export_bytes(user=user),
            content_type="application/json; charset=utf-8",
        )
        response["Content-Disposition"] = 'attachment; filename="foodai-user-data-export.json"'
        record_audit_event(
            actor=user,
            action=AuditLog.Action.DATA_EXPORTED,
            target_type="accounts.user",
            target_id=user.id,
            metadata={"source": "privacy_center", "export_format": "json"},
            request=request._request,
        )
        return response


class PrivacyConsentView(APIView):
    permission_classes = [CanUsePrivacyCenter]

    @extend_schema(responses={status.HTTP_200_OK: PrivacySettingsSerializer})
    def get(self, request: Request) -> Response:
        self.privacy_action = "consent_read"
        privacy_settings = get_privacy_settings(user=cast(User, request.user))
        return Response(PrivacySettingsSerializer(privacy_settings).data)

    @extend_schema(
        request=PrivacySettingsSerializer,
        responses={status.HTTP_200_OK: PrivacySettingsSerializer},
    )
    def patch(self, request: Request) -> Response:
        self.privacy_action = "consent_update"
        privacy_settings = get_privacy_settings(user=cast(User, request.user))
        serializer = PrivacySettingsSerializer(
            privacy_settings,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_audit_event(
            actor=cast(User, request.user),
            action=AuditLog.Action.PRIVACY_CONSENT_CHANGED,
            target_type="privacy.privacysettings",
            target_id=privacy_settings.id,
            metadata={
                "source": "privacy_center",
                "requested_changes": sorted(serializer.validated_data.keys()),
            },
            request=request._request,
        )
        return Response(serializer.data)


class PrivacyFoodPhotoDeleteView(APIView):
    permission_classes = [CanUsePrivacyCenter]
    privacy_action = "delete_photo"

    @extend_schema(
        request=None,
        responses={
            status.HTTP_200_OK: PrivacyDeletionResponseSerializer,
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
        },
    )
    def delete(self, request: Request, scan_id: uuid.UUID, *args: Any, **kwargs: Any) -> Response:
        try:
            deleted = delete_food_scan_photo(user=cast(User, request.user), food_scan_id=scan_id)
        except PrivacyObjectNotFound as exc:
            raise NotFound(exc.code) from exc
        return Response({"code": "food_photo_deleted", "deleted": deleted})


class PrivacyAIChatHistoryDeleteView(APIView):
    permission_classes = [CanUsePrivacyCenter]
    privacy_action = "delete_ai_history"

    @extend_schema(request=None, responses={status.HTTP_200_OK: PrivacyDeletionResponseSerializer})
    def delete(self, request: Request) -> Response:
        deleted = delete_ai_chat_history(user=cast(User, request.user))
        return Response({"code": "ai_chat_history_deleted", "deleted": deleted})


class PrivacyAccountDeleteView(APIView):
    permission_classes = [CanUsePrivacyCenter]
    privacy_action = "delete_account"

    @extend_schema(
        request=PrivacyAccountDeletionRequestSerializer,
        responses={
            status.HTTP_200_OK: PrivacyDeletionResponseSerializer,
            status.HTTP_403_FORBIDDEN: OpenApiTypes.OBJECT,
        },
    )
    def delete(self, request: Request) -> Response:
        serializer = PrivacyAccountDeletionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = delete_user_account(
                user=cast(User, request.user),
                current_password=serializer.validated_data["current_password"],
                request=request._request,
            )
        except PrivacyAuthenticationError as exc:
            raise PermissionDenied(exc.code) from exc
        return Response({"code": "account_deleted", "deleted": result.deleted_objects})
