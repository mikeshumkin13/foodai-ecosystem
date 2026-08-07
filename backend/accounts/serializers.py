from __future__ import annotations

from rest_framework import serializers

from accounts.models import UserProfile


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
