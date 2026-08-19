from __future__ import annotations

from typing import Any, cast

from django.contrib.auth import login, logout, update_session_auth_hash
from django.db.models import QuerySet
from django.http import HttpResponse
from django.middleware.csrf import get_token, rotate_token
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.authentication import CSRFCheck
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from accounts.auth_tokens import (
    consume_email_verification_token,
    consume_password_reset_token,
    issue_email_verification_token,
    issue_password_reset_token,
    revoke_password_reset_tokens,
)
from accounts.email_delivery import send_email_verification, send_password_reset
from accounts.models import NutritionProfile, NutritionSensitiveRestriction, User, UserProfile
from accounts.permissions import (
    CanAccessNutritionProfile,
    CanAccessNutritionSensitiveRestriction,
    CanAccessUserProfile,
)
from accounts.rbac import (
    ADMINISTER_ACCOUNTS_PERMISSION,
    CHANGE_OWN_NUTRITION_PROFILE_PERMISSION,
    CHANGE_OWN_NUTRITION_RESTRICTION_PERMISSION,
    CHANGE_OWN_PROFILE_PERMISSION,
    VIEW_OWN_NUTRITION_PROFILE_PERMISSION,
    VIEW_OWN_NUTRITION_RESTRICTION_PERMISSION,
    VIEW_OWN_PROFILE_PERMISSION,
)
from accounts.serializers import (
    AuthUserResponseSerializer,
    CodeResponseSerializer,
    CSRFTokenResponseSerializer,
    EmailResendSerializer,
    EmailVerificationSerializer,
    LoginSerializer,
    NutritionProfileSerializer,
    NutritionSensitiveRestrictionSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    UserSummarySerializer,
)
from accounts.throttles import (
    EmailVerificationRateThrottle,
    LoginRateThrottle,
    LogoutRateThrottle,
    PasswordChangeRateThrottle,
    PasswordResetRateThrottle,
    RefreshRateThrottle,
    RegisterRateThrottle,
)


def _enforce_csrf(request: Request) -> None:
    check = CSRFCheck(lambda csrf_request: HttpResponse())
    check.process_request(request._request)
    reason = check.process_view(request._request, lambda csrf_request: HttpResponse(), (), {})
    if reason:
        raise PermissionDenied("csrf_failed")


class PublicCsrfProtectedAPIView(APIView):
    permission_classes = [AllowAny]

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)
        _enforce_csrf(request)


def _refresh_session(request: Request) -> None:
    request.session.set_expiry(None)
    request.session.cycle_key()
    rotate_token(request)
    get_token(request)


def _auth_response(user: User, *, code: str) -> Response:
    return Response(
        {
            "code": code,
            "user": UserSummarySerializer(user).data,
        }
    )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFTokenView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: CSRFTokenResponseSerializer})
    def get(self, request: Request) -> Response:
        return Response({"code": "csrf_cookie_set", "csrf_token": get_token(request)})


class RegisterView(PublicCsrfProtectedAPIView):
    throttle_classes = [RegisterRateThrottle]

    @extend_schema(request=RegisterSerializer, responses={201: AuthUserResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        issued_token = issue_email_verification_token(user)
        send_email_verification(user, issued_token)

        response = _auth_response(user, code="registration_created")
        response.status_code = 201
        return response


class LoginView(PublicCsrfProtectedAPIView):
    throttle_classes = [LoginRateThrottle]

    @extend_schema(request=LoginSerializer, responses={200: AuthUserResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = cast(User, serializer.validated_data["user"])

        login(request, user)
        _refresh_session(request)
        return _auth_response(user, code="login_success")


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [LogoutRateThrottle]

    @extend_schema(request=None, responses={200: CodeResponseSerializer})
    def post(self, request: Request) -> Response:
        logout(request)
        rotate_token(request)
        get_token(request)
        return Response({"code": "logout_success"})


class RefreshView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [RefreshRateThrottle]

    @extend_schema(request=None, responses={200: AuthUserResponseSerializer})
    def post(self, request: Request) -> Response:
        user = cast(User, request.user)
        _refresh_session(request)
        return _auth_response(user, code="session_refreshed")


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSummarySerializer})
    def get(self, request: Request) -> Response:
        return Response(UserSummarySerializer(cast(User, request.user)).data)


class EmailVerificationView(PublicCsrfProtectedAPIView):
    throttle_classes = [EmailVerificationRateThrottle]

    @extend_schema(request=EmailVerificationSerializer, responses={200: CodeResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = consume_email_verification_token(
            serializer.validated_data["token_id"],
            serializer.validated_data["token"],
        )
        if user is None:
            raise PermissionDenied("invalid_or_expired_token")
        return Response({"code": "email_verified"})


class EmailVerificationResendView(PublicCsrfProtectedAPIView):
    throttle_classes = [EmailVerificationRateThrottle]

    @extend_schema(request=EmailResendSerializer, responses={200: CodeResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = EmailResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email=serializer.validated_data["email"], is_active=False
        ).first()
        if user is not None:
            issued_token = issue_email_verification_token(user)
            send_email_verification(user, issued_token)
        return Response({"code": "verification_email_if_account_exists"})


class PasswordResetRequestView(PublicCsrfProtectedAPIView):
    throttle_classes = [PasswordResetRateThrottle]

    @extend_schema(request=PasswordResetRequestSerializer, responses={200: CodeResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"], is_active=True).first()
        if user is not None:
            issued_token = issue_password_reset_token(user)
            send_password_reset(user, issued_token)
        return Response({"code": "password_reset_if_account_exists"})


class PasswordResetConfirmView(PublicCsrfProtectedAPIView):
    throttle_classes = [PasswordResetRateThrottle]

    @extend_schema(request=PasswordResetConfirmSerializer, responses={200: CodeResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = consume_password_reset_token(
            serializer.validated_data["token_id"],
            serializer.validated_data["token"],
        )
        if user is None:
            raise PermissionDenied("invalid_or_expired_token")

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        revoke_password_reset_tokens(user)
        return Response({"code": "password_reset_complete"})


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [PasswordChangeRateThrottle]

    @extend_schema(request=PasswordChangeSerializer, responses={200: CodeResponseSerializer})
    def post(self, request: Request) -> Response:
        user = cast(User, request.user)
        serializer = PasswordChangeSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)

        if not user.check_password(serializer.validated_data["current_password"]):
            raise PermissionDenied("invalid_current_password")

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        update_session_auth_hash(request, user)
        rotate_token(request)
        get_token(request)
        return Response({"code": "password_changed"})


class UserProfileViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = UserProfileSerializer
    permission_classes = [CanAccessUserProfile]
    lookup_field = "id"

    def get_queryset(self) -> QuerySet[UserProfile]:
        request_user = self.request.user
        base_queryset = UserProfile.objects.select_related("user")

        if not request_user or not request_user.is_authenticated:
            return base_queryset.none()

        user = cast(User, request_user)
        if user.is_superuser or user.has_perm(ADMINISTER_ACCOUNTS_PERMISSION):
            return base_queryset

        if user.has_perm(VIEW_OWN_PROFILE_PERMISSION) or user.has_perm(
            CHANGE_OWN_PROFILE_PERMISSION
        ):
            return base_queryset.filter(user=user)

        return base_queryset.none()


class NutritionProfileViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = NutritionProfileSerializer
    permission_classes = [CanAccessNutritionProfile]
    lookup_field = "id"

    def get_queryset(self) -> QuerySet[NutritionProfile]:
        request_user = self.request.user
        base_queryset = NutritionProfile.objects.select_related("user")

        if not request_user or not request_user.is_authenticated:
            return base_queryset.none()

        user = cast(User, request_user)
        if user.is_superuser:
            return base_queryset

        if user.has_perm(VIEW_OWN_NUTRITION_PROFILE_PERMISSION) or user.has_perm(
            CHANGE_OWN_NUTRITION_PROFILE_PERMISSION
        ):
            return base_queryset.filter(user=user)

        return base_queryset.none()

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request: Request) -> Response:
        user = cast(User, request.user)
        nutrition_profile = get_object_or_404(self.get_queryset(), user=user)
        serializer = self.get_serializer(nutrition_profile)
        return Response(serializer.data)


class NutritionSensitiveRestrictionViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = NutritionSensitiveRestrictionSerializer
    permission_classes = [CanAccessNutritionSensitiveRestriction]
    lookup_field = "id"

    def get_queryset(self) -> QuerySet[NutritionSensitiveRestriction]:
        request_user = self.request.user
        base_queryset = NutritionSensitiveRestriction.objects.select_related("user")

        if not request_user or not request_user.is_authenticated:
            return base_queryset.none()

        user = cast(User, request_user)
        if user.is_superuser:
            return base_queryset

        if user.has_perm(VIEW_OWN_NUTRITION_RESTRICTION_PERMISSION) or user.has_perm(
            CHANGE_OWN_NUTRITION_RESTRICTION_PERMISSION
        ):
            return base_queryset.filter(user=user)

        return base_queryset.none()

    def perform_create(self, serializer: BaseSerializer[Any]) -> None:
        serializer.save(user=cast(User, self.request.user))
