from __future__ import annotations

from typing import Any, cast

from rest_framework import serializers

from ai_coach.models import AICoachSettings


class AICoachSettingsSerializer(serializers.ModelSerializer[AICoachSettings]):
    chat_history_enabled = serializers.SerializerMethodField()
    chat_history_consent_accepted = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )
    chat_history_consent_revoked = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )

    class Meta:
        model = AICoachSettings
        fields = (
            "id",
            "chat_history_enabled",
            "chat_history_consent_version",
            "chat_history_consent_granted_at",
            "chat_history_consent_revoked_at",
            "chat_history_consent_accepted",
            "chat_history_consent_revoked",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "chat_history_enabled",
            "chat_history_consent_version",
            "chat_history_consent_granted_at",
            "chat_history_consent_revoked_at",
            "created_at",
            "updated_at",
        )

    def get_chat_history_enabled(self, obj: AICoachSettings) -> bool:
        return obj.has_chat_history_consent

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        accepted = bool(attrs.get("chat_history_consent_accepted", False))
        revoked = bool(attrs.get("chat_history_consent_revoked", False))
        if accepted and revoked:
            raise serializers.ValidationError("ai_coach_history_consent_conflict")
        return attrs

    def update(
        self,
        instance: AICoachSettings,
        validated_data: dict[str, Any],
    ) -> AICoachSettings:
        accepted = bool(validated_data.pop("chat_history_consent_accepted", False))
        revoked = bool(validated_data.pop("chat_history_consent_revoked", False))
        if accepted:
            instance.grant_chat_history_consent()
        if revoked:
            instance.revoke_chat_history_consent()
        instance.save()
        return instance


class AICoachAskRequestSerializer(serializers.Serializer[dict[str, Any]]):
    message = serializers.CharField(max_length=2000, trim_whitespace=True)
    date = serializers.DateField(required=False)
    store_response = serializers.BooleanField(required=False, default=False)

    def validate_message(self, value: str) -> str:
        message = value.strip()
        if not message:
            raise serializers.ValidationError("message_required")
        return message


class AICoachSafetySerializer(serializers.Serializer[dict[str, Any]]):
    blocked = serializers.BooleanField()
    code = serializers.CharField()
    categories = serializers.ListField(child=serializers.CharField())
    reason = serializers.CharField(allow_blank=True)


class AICoachNutritionNoteSerializer(serializers.Serializer[dict[str, str]]):
    code = serializers.CharField()
    message = serializers.CharField()


class AICoachAskResponseSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField()
    schema_version = serializers.CharField()
    context_date = serializers.DateField()
    answer = serializers.CharField()
    suggestions = serializers.ListField(child=serializers.CharField())
    nutrition_notes = AICoachNutritionNoteSerializer(many=True)
    warnings = serializers.ListField(child=serializers.CharField())
    safety = AICoachSafetySerializer()
    provider = serializers.CharField()
    stored = serializers.BooleanField()


class AICoachProviderErrorSerializer(serializers.Serializer[dict[str, str]]):
    detail = serializers.CharField()


def serialize_ai_coach_response(payload: dict[str, Any]) -> dict[str, Any]:
    serializer = AICoachAskResponseSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    return cast(dict[str, Any], serializer.data)
