from __future__ import annotations

from typing import Any

from rest_framework import serializers

from privacy.models import PrivacySettings


class PrivacySettingsSerializer(serializers.ModelSerializer[PrivacySettings]):
    model_improvement_enabled = serializers.SerializerMethodField()
    food_photo_training_enabled = serializers.SerializerMethodField()
    model_improvement_consent_accepted = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )
    model_improvement_consent_revoked = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )
    food_photo_training_consent_accepted = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )
    food_photo_training_consent_revoked = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )

    class Meta:
        model = PrivacySettings
        fields = (
            "id",
            "model_improvement_enabled",
            "model_improvement_consent_version",
            "model_improvement_consent_granted_at",
            "model_improvement_consent_revoked_at",
            "model_improvement_consent_accepted",
            "model_improvement_consent_revoked",
            "food_photo_training_enabled",
            "food_photo_training_consent_version",
            "food_photo_training_consent_granted_at",
            "food_photo_training_consent_revoked_at",
            "food_photo_training_consent_accepted",
            "food_photo_training_consent_revoked",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "model_improvement_enabled",
            "model_improvement_consent_version",
            "model_improvement_consent_granted_at",
            "model_improvement_consent_revoked_at",
            "food_photo_training_enabled",
            "food_photo_training_consent_version",
            "food_photo_training_consent_granted_at",
            "food_photo_training_consent_revoked_at",
            "created_at",
            "updated_at",
        )

    def get_model_improvement_enabled(self, obj: PrivacySettings) -> bool:
        return obj.has_model_improvement_consent

    def get_food_photo_training_enabled(self, obj: PrivacySettings) -> bool:
        return obj.has_food_photo_training_consent

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        model_accepted = bool(attrs.get("model_improvement_consent_accepted", False))
        model_revoked = bool(attrs.get("model_improvement_consent_revoked", False))
        photo_accepted = bool(attrs.get("food_photo_training_consent_accepted", False))
        photo_revoked = bool(attrs.get("food_photo_training_consent_revoked", False))

        if model_accepted and model_revoked:
            raise serializers.ValidationError("model_improvement_consent_conflict")
        if photo_accepted and photo_revoked:
            raise serializers.ValidationError("food_photo_training_consent_conflict")
        if photo_accepted and not (
            model_accepted
            or (
                self.instance is not None
                and self.instance.has_model_improvement_consent
                and not model_revoked
            )
        ):
            raise serializers.ValidationError("model_improvement_consent_required_for_photos")
        return attrs

    def update(
        self,
        instance: PrivacySettings,
        validated_data: dict[str, Any],
    ) -> PrivacySettings:
        model_accepted = bool(validated_data.pop("model_improvement_consent_accepted", False))
        model_revoked = bool(validated_data.pop("model_improvement_consent_revoked", False))
        photo_accepted = bool(validated_data.pop("food_photo_training_consent_accepted", False))
        photo_revoked = bool(validated_data.pop("food_photo_training_consent_revoked", False))

        if model_accepted:
            instance.grant_model_improvement_consent()
        if model_revoked:
            instance.revoke_model_improvement_consent()
            instance.revoke_food_photo_training_consent()
        if photo_accepted:
            instance.grant_food_photo_training_consent()
        if photo_revoked:
            instance.revoke_food_photo_training_consent()
        instance.save()
        return instance


class PrivacyDataCategorySerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField()
    label = serializers.CharField()  # type: ignore[assignment]
    count = serializers.IntegerField(min_value=0)
    contains_sensitive_data = serializers.BooleanField()
    storage = serializers.CharField()
    deletion = serializers.CharField()


class PrivacyDataSummarySerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField()
    categories = PrivacyDataCategorySerializer(many=True)
    privacy_settings = PrivacySettingsSerializer()


class PrivacyDeletionResponseSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField()
    deleted = serializers.DictField(child=serializers.IntegerField(min_value=0))


class PrivacyAccountDeletionRequestSerializer(serializers.Serializer[dict[str, Any]]):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
