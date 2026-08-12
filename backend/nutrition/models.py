from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower


class FoodCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    name_ru = models.CharField(max_length=120, blank=True)
    name_en = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slug"]
        verbose_name = "food category"
        verbose_name_plural = "food categories"

    def __str__(self) -> str:
        return self.name


class FoodDataSource(models.Model):
    class SourceType(models.TextChoices):
        DEMO = "demo", "Demo"
        MANUAL = "manual", "Manual"
        EXTERNAL_DATABASE = "external_database", "External database"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    source_type = models.CharField(
        max_length=32,
        choices=SourceType.choices,
        default=SourceType.MANUAL,
    )
    source_reference = models.CharField(max_length=255, blank=True)
    license_name = models.CharField(max_length=120, blank=True)
    license_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name


class Nutrient(models.Model):
    class NutrientType(models.TextChoices):
        ENERGY = "energy", "Energy"
        MACRONUTRIENT = "macronutrient", "Macronutrient"
        MICRONUTRIENT = "micronutrient", "Micronutrient"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    name_ru = models.CharField(max_length=120, blank=True)
    name_en = models.CharField(max_length=120, blank=True)
    unit = models.CharField(max_length=32)
    nutrient_type = models.CharField(
        max_length=32,
        choices=NutrientType.choices,
        default=NutrientType.OTHER,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nutrient_type", "code"]

    def __str__(self) -> str:
        return f"{self.name} ({self.unit})"


class FoodItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canonical_food = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="localized_or_alias_items",
    )
    category = models.ForeignKey(
        FoodCategory,
        on_delete=models.PROTECT,
        related_name="food_items",
    )
    data_source = models.ForeignKey(
        FoodDataSource,
        on_delete=models.PROTECT,
        related_name="food_items",
    )
    name = models.CharField(max_length=160)
    name_ru = models.CharField(max_length=160, blank=True)
    name_en = models.CharField(max_length=160, blank=True)
    synonyms = models.JSONField(default=list, blank=True)
    density_g_per_ml = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    density_metadata = models.JSONField(default=dict, blank=True)
    is_verified = models.BooleanField(default=False)
    source_reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [
            models.Index(Lower("name"), name="nutrition_food_name_lower_idx"),
            models.Index(fields=["is_verified"], name="nutrition_food_verified_idx"),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_canonical(self) -> bool:
        return self.canonical_food_id is None


class FoodNutrient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    food_item = models.ForeignKey(
        FoodItem,
        on_delete=models.CASCADE,
        related_name="nutrient_values",
    )
    nutrient = models.ForeignKey(
        Nutrient,
        on_delete=models.PROTECT,
        related_name="food_values",
    )
    amount_per_100g = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0"))],
    )
    source_reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nutrient__nutrient_type", "nutrient__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["food_item", "nutrient"],
                name="unique_nutrient_per_food_item",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.food_item} - {self.nutrient}: {self.amount_per_100g}/100g"
