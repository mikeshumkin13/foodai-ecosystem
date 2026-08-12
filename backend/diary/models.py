from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Meal(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", "Breakfast"
        LUNCH = "lunch", "Lunch"
        DINNER = "dinner", "Dinner"
        SNACK = "snack", "Snack"
        CUSTOM = "custom", "Custom"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meals",
    )
    meal_type = models.CharField(
        max_length=32,
        choices=MealType.choices,
        default=MealType.CUSTOM,
    )
    logged_at = models.DateTimeField()
    name = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-logged_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "logged_at"], name="diary_meal_user_logged_idx"),
        ]
        permissions = [
            ("view_own_meal", "Can view own meal"),
            ("change_own_meal", "Can change own meal"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.meal_type} {self.logged_at.isoformat()}"


class MealItem(models.Model):
    class Source(models.TextChoices):
        FOOD_CATALOG = "food_catalog", "Food catalog"
        MANUAL = "manual", "Manual"
        VISION = "vision", "Vision"
        IMPORT = "import", "Import"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name="items")
    food = models.ForeignKey(
        "nutrition.FoodItem",
        on_delete=models.PROTECT,
        related_name="meal_items",
    )
    food_name_snapshot = models.CharField(max_length=160)
    food_source_reference_snapshot = models.CharField(max_length=255, blank=True)
    mass_g = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    calories_kcal = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0"))],
    )
    protein_g = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0"))],
    )
    fat_g = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0"))],
    )
    carbs_g = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0"))],
    )
    micronutrient_snapshot = models.JSONField(default=dict, blank=True)
    nutrient_snapshot = models.JSONField(default=dict, blank=True)
    source = models.CharField(
        max_length=32,
        choices=Source.choices,
        default=Source.FOOD_CATALOG,
    )
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("1"))],
    )
    manually_corrected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["meal", "food"], name="diary_item_meal_food_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.food_name_snapshot} {self.mass_g}g"
