from __future__ import annotations

from typing import cast

from django.contrib.auth import authenticate, password_validation
from django.utils import timezone
from rest_framework import serializers

from accounts.models import (
    NutritionProfile,
    NutritionSensitiveRestriction,
    User,
    UserProfile,
)
from accounts.rbac import role_group_names

DIETARY_PREFERENCE_CHOICES = (
    ("none", "None"),
    ("vegetarian", "Vegetarian"),
    ("vegan", "Vegan"),
    ("pescatarian", "Pescatarian"),
    ("halal", "Halal"),
    ("kosher", "Kosher"),
    ("high_protein", "High protein"),
    ("low_carb", "Low carb"),
)


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


class NutritionProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True)
    dietary_preferences = serializers.ListField(
        child=serializers.ChoiceField(choices=DIETARY_PREFERENCE_CHOICES),
        allow_empty=True,
        required=False,
    )
    consent_accepted = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = NutritionProfile
        fields = (
            "id",
            "user_id",
            "goal",
            "height_cm",
            "mass_kg",
            "age_category",
            "activity_level",
            "preferred_units",
            "dietary_preferences",
            "consent_version",
            "consent_granted_at",
            "consent_revoked_at",
            "consent_accepted",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user_id",
            "consent_version",
            "consent_granted_at",
            "consent_revoked_at",
            "created_at",
            "updated_at",
        )

    def validate_dietary_preferences(self, value: list[str]) -> list[str]:
        unique_preferences = list(dict.fromkeys(value))
        if "none" in unique_preferences and len(unique_preferences) > 1:
            raise serializers.ValidationError("dietary_preferences_none_must_be_alone")
        return unique_preferences

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        consent_accepted = bool(attrs.get("consent_accepted", False))
        profile_fields = set(attrs) - {"consent_accepted"}
        instance = self.instance

        if (
            instance is not None
            and profile_fields
            and instance.consent_granted_at is None
            and not consent_accepted
        ):
            raise serializers.ValidationError("nutrition_profile_consent_required")

        return attrs

    def update(
        self, instance: NutritionProfile, validated_data: dict[str, object]
    ) -> NutritionProfile:
        consent_accepted = bool(validated_data.pop("consent_accepted", False))
        if consent_accepted:
            instance.consent_version = NutritionProfile.CONSENT_VERSION
            instance.consent_granted_at = timezone.now()
            instance.consent_revoked_at = None

        return cast(NutritionProfile, super().update(instance, validated_data))


class NutritionSensitiveRestrictionSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True)
    consent_accepted = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = NutritionSensitiveRestriction
        fields = (
            "id",
            "user_id",
            "restriction_type",
            "label",
            "is_active",
            "consent_version",
            "consent_granted_at",
            "consent_accepted",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user_id",
            "consent_version",
            "consent_granted_at",
            "created_at",
            "updated_at",
        )

    def validate_label(self, value: str) -> str:
        label = value.strip()
        if not label:
            raise serializers.ValidationError("restriction_label_required")
        return label

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if self.instance is None and not bool(attrs.get("consent_accepted", False)):
            raise serializers.ValidationError("sensitive_nutrition_consent_required")
        return attrs

    def create(
        self,
        validated_data: dict[str, object],
    ) -> NutritionSensitiveRestriction:
        validated_data.pop("consent_accepted", None)
        validated_data["consent_version"] = NutritionSensitiveRestriction.CONSENT_VERSION
        validated_data["consent_granted_at"] = timezone.now()
        return cast(NutritionSensitiveRestriction, super().create(validated_data))

    def update(
        self,
        instance: NutritionSensitiveRestriction,
        validated_data: dict[str, object],
    ) -> NutritionSensitiveRestriction:
        validated_data.pop("consent_accepted", None)
        return cast(NutritionSensitiveRestriction, super().update(instance, validated_data))


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
        NutritionProfile.objects.create(user=user)
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
