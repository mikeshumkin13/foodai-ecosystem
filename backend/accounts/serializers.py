from __future__ import annotations

from django.contrib.auth import authenticate, password_validation
from rest_framework import serializers

from accounts.models import User, UserProfile
from accounts.rbac import role_group_names


class UserProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            "id",
            "user_id",
            "display_name",
            "preferred_language",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user_id", "created_at", "updated_at")


class UserSummarySerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "is_active",
            "roles",
            "profile",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_roles(self, user: User) -> list[str]:
        return list(user.groups.filter(name__in=role_group_names()).values_list("name", flat=True))


class CodeResponseSerializer(serializers.Serializer):
    code = serializers.CharField()


class CSRFTokenResponseSerializer(CodeResponseSerializer):
    csrf_token = serializers.CharField()


class AuthUserResponseSerializer(CodeResponseSerializer):
    user = UserSummarySerializer()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    preferred_language = serializers.ChoiceField(
        choices=(("ru", "Russian"), ("en", "English")),
        required=False,
        default="ru",
    )

    def validate_email(self, value: str) -> str:
        email = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("email_already_registered")
        return email

    def validate_password(self, value: str) -> str:
        password_validation.validate_password(value)
        return value

    def create(self, validated_data: dict[str, object]) -> User:
        display_name = str(validated_data.pop("display_name", ""))
        preferred_language = str(validated_data.pop("preferred_language", "ru"))
        user = User.objects.create_user(
            email=str(validated_data["email"]),
            password=str(validated_data["password"]),
            is_active=False,
        )
        UserProfile.objects.create(
            user=user,
            display_name=display_name,
            preferred_language=preferred_language,
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        request = self.context.get("request")
        email = User.objects.normalize_email(str(attrs["email"])).lower()
        user = authenticate(
            request=request,
            username=email,
            password=str(attrs["password"]),
        )
        if user is None:
            raise serializers.ValidationError("invalid_credentials")

        attrs["user"] = user
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    token_id = serializers.UUIDField()
    token = serializers.CharField(trim_whitespace=False)


class EmailResendSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return User.objects.normalize_email(value).lower()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return User.objects.normalize_email(value).lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token_id = serializers.UUIDField()
    token = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        password_validation.validate_password(value)
        return value


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        password_validation.validate_password(value, self.context.get("user"))
        return value
