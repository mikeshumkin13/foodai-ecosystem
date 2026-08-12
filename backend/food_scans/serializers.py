from __future__ import annotations

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from food_scans.image_processing import FoodPhotoValidationError
from food_scans.models import FoodScan
from food_scans.services import create_food_scan


class FoodScanReadSerializer(serializers.ModelSerializer[FoodScan]):
    user_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = FoodScan
        fields = (
            "id",
            "user_id",
            "status",
            "image_format",
            "content_type",
            "uploaded_byte_size",
            "stored_byte_size",
            "width",
            "height",
            "exif_stripped",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class FoodScanUploadSerializer(serializers.Serializer[FoodScan]):
    photo = serializers.FileField(write_only=True)

    def create(self, validated_data: dict[str, UploadedFile]) -> FoodScan:
        request = self.context["request"]
        try:
            return create_food_scan(user=request.user, uploaded_file=validated_data["photo"])
        except FoodPhotoValidationError as exc:
            raise serializers.ValidationError({"photo": [exc.code]}) from exc

    def update(self, instance: FoodScan, validated_data: dict[str, UploadedFile]) -> FoodScan:
        raise NotImplementedError
