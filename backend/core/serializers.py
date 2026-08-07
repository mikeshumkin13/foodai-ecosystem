from __future__ import annotations

from rest_framework import serializers


class HealthCheckResponseSerializer(serializers.Serializer):
    status = serializers.CharField()

