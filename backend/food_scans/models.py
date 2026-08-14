from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class FoodScan(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        NEEDS_CONFIRMATION = "needs_confirmation", "Needs confirmation"
        CONFIRMED = "confirmed", "Confirmed"
        FAILED = "failed", "Failed"

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
    failure_code = models.CharField(max_length=64, blank=True)
    analysis_run_id = models.UUIDField(null=True, blank=True)
    analysis_task_id = models.CharField(max_length=255, blank=True)
    analysis_attempt_count = models.PositiveIntegerField(default=0)
    confirmed_meal = models.OneToOneField(
        "diary.Meal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_food_scan",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "created_at"], name="food_scan_user_created_idx"),
            models.Index(fields=["status"], name="food_scan_status_idx"),
            models.Index(fields=["analysis_run_id"], name="food_scan_analysis_run_idx"),
        ]
        permissions = [
            ("view_own_foodscan", "Can view own food scan"),
            ("change_own_foodscan", "Can change own food scan"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.status} {self.created_at.isoformat()}"


class FoodScanDetectedItem(models.Model):
    class Source(models.TextChoices):
        VISION = "vision", "Vision"
        MANUAL = "manual", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    food_scan = models.ForeignKey(
        FoodScan,
        on_delete=models.CASCADE,
        related_name="detected_items",
    )
    matched_food = models.ForeignKey(
        "nutrition.FoodItem",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="scan_detected_items",
    )
    label = models.CharField(max_length=160)
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("1"))],
    )
    estimated_mass_g = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    portion_estimated_volume_ml = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    portion_estimated_mass_g = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    portion_min_mass_g = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    portion_max_mass_g = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    portion_confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("1"))],
    )
    portion_estimation_method = models.CharField(max_length=80, blank=True)
    portion_estimation_metadata = models.JSONField(default=dict, blank=True)
    manual_mass_g = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    food_name_snapshot = models.CharField(max_length=160, blank=True)
    food_source_reference_snapshot = models.CharField(max_length=255, blank=True)
    calories_kcal = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0.0000"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    protein_g = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0.0000"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    fat_g = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0.0000"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    carbs_g = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0.0000"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    micronutrient_snapshot = models.JSONField(default=dict, blank=True)
    nutrient_snapshot = models.JSONField(default=dict, blank=True)
    source = models.CharField(
        max_length=32,
        choices=Source.choices,
        default=Source.VISION,
    )
    position = models.PositiveIntegerField(default=0)
    is_removed = models.BooleanField(default=False)
    manually_corrected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "created_at", "id"]
        indexes = [
            models.Index(fields=["food_scan", "is_removed"], name="scan_item_scan_removed_idx"),
            models.Index(fields=["matched_food"], name="scan_item_food_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.food_scan_id} {self.label} {self.estimated_mass_g}g"
