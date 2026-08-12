from __future__ import annotations

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class FoodScan(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        FAILED = "failed", "Failed"
        COMPLETED = "completed", "Completed"

    class ImageFormat(models.TextChoices):
        JPEG = "JPEG", "JPEG"
        PNG = "PNG", "PNG"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="food_scans",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.UPLOADED,
    )
    storage_backend = models.CharField(max_length=32)
    object_key = models.CharField(max_length=512, unique=True)
    image_format = models.CharField(max_length=8, choices=ImageFormat.choices)
    content_type = models.CharField(max_length=64)
    uploaded_byte_size = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    stored_byte_size = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    width = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    height = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    checksum_sha256 = models.CharField(max_length=64)
    exif_stripped = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "created_at"], name="food_scan_user_created_idx"),
            models.Index(fields=["status"], name="food_scan_status_idx"),
        ]
        permissions = [
            ("view_own_foodscan", "Can view own food scan"),
            ("change_own_foodscan", "Can change own food scan"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.status} {self.created_at.isoformat()}"
