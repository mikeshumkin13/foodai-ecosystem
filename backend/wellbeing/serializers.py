from __future__ import annotations

from typing import Any, cast

from rest_framework import serializers

from wellbeing.models import WellbeingAssistantSettings


class WellbeingAssistantSettingsSerializer(serializers.ModelSerializer[WellbeingAssistantSettings]):
    history_enabled = serializers.SerializerMethodField()
    history_consent_accepted = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )
    history_consent_revoked = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )

    class Meta:
        model = WellbeingAssistantSettings
        fields = (
            "id",
            "history_enabled",
            "history_consent_version",
            "history_consent_granted_at",
            "history_consent_revoked_at",
            "history_consent_accepted",
            "history_consent_revoked",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "history_enabled",
            "history_consent_version",
            "history_consent_granted_at",
            "history_consent_revoked_at",
            "created_at",
            "updated_at",
        )

    def get_history_enabled(self, obj: WellbeingAssistantSettings) -> bool:
        return obj.has_history_consent

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        accepted = bool(attrs.get("history_consent_accepted", False))
        revoked = bool(attrs.get("history_consent_revoked", False))
        if accepted and revoked:
            raise serializers.ValidationError("wellbeing_history_consent_conflict")
        return attrs

    def update(
        self,
        instance: WellbeingAssistantSettings,
        validated_data: dict[str, Any],
    ) -> WellbeingAssistantSettings:
        accepted = bool(validated_data.pop("history_consent_accepted", False))
        revoked = bool(validated_data.pop("history_consent_revoked", False))
        if accepted:
            instance.grant_history_consent()
        if revoked:
            instance.revoke_history_consent()
        instance.save()
        return instance


class WellbeingAskRequestSerializer(serializers.Serializer[dict[str, Any]]):
    message = serializers.CharField(max_length=2000, trim_whitespace=True)
    date = serializers.DateField(required=False)
    store_response = serializers.BooleanField(required=False, default=False)

    def validate_message(self, value: str) -> str:
        message = value.strip()
        if not message:
            raise serializers.ValidationError("message_required")
        return message


class WellbeingSafetySerializer(serializers.Serializer[dict[str, Any]]):
    blocked = serializers.BooleanField()
    code = serializers.CharField()
    categories = serializers.ListField(child=serializers.CharField())
    reason = serializers.CharField(allow_blank=True)
    urgent_support_recommended = serializers.BooleanField()


class WellbeingSmallActionSerializer(serializers.Serializer[dict[str, str]]):
    title = serializers.CharField()
    description = serializers.CharField()
    timeframe = serializers.CharField()


class WellbeingAskResponseSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField()
    schema_version = serializers.CharField()
    context_date = serializers.DateField()
    answer = serializers.CharField()
    focus_area = serializers.CharField()
    small_actions = WellbeingSmallActionSerializer(many=True)
    reflection_prompts = serializers.ListField(child=serializers.CharField())
    adherence_strategy = serializers.CharField(allow_blank=True)
    warnings = serializers.ListField(child=serializers.CharField())
    safety = WellbeingSafetySerializer()
    provider = serializers.CharField()
    stored = serializers.BooleanField()
    storage_reason = serializers.CharField()


class WellbeingProviderErrorSerializer(serializers.Serializer[dict[str, str]]):
    detail = serializers.CharField()


def serialize_wellbeing_response(payload: dict[str, Any]) -> dict[str, Any]:
    serializer = WellbeingAskResponseSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    return cast(dict[str, Any], serializer.data)
