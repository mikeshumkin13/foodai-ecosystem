from __future__ import annotations

from django.contrib import admin

from nutrition.models import FoodCategory, FoodDataSource, FoodItem, FoodNutrient, Nutrient


@admin.register(FoodCategory)
class FoodCategoryAdmin(admin.ModelAdmin):
    actions = None
    ordering = ("slug",)
    list_display = ("slug", "name", "name_ru", "name_en", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("slug", "name", "name_ru", "name_en")
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "slug", "name", "name_ru", "name_en", "description", "created_at", "updated_at")


@admin.register(FoodDataSource)
class FoodDataSourceAdmin(admin.ModelAdmin):
    actions = None
    ordering = ("code",)
    list_display = ("code", "name", "source_type", "source_reference", "created_at", "updated_at")
    list_filter = ("source_type", "created_at", "updated_at")
    search_fields = ("code", "name", "source_reference", "license_name")
    readonly_fields = ("id", "created_at", "updated_at")
    fields = (
        "id",
        "code",
        "name",
        "source_type",
        "source_reference",
        "license_name",
        "license_url",
        "created_at",
        "updated_at",
    )


@admin.register(Nutrient)
class NutrientAdmin(admin.ModelAdmin):
    actions = None
    ordering = ("nutrient_type", "code")
    list_display = ("code", "name", "unit", "nutrient_type", "created_at", "updated_at")
    list_filter = ("nutrient_type", "unit", "created_at", "updated_at")
    search_fields = ("code", "name", "name_ru", "name_en")
    readonly_fields = ("id", "created_at", "updated_at")
    fields = (
        "id",
        "code",
        "name",
        "name_ru",
        "name_en",
        "unit",
        "nutrient_type",
        "created_at",
        "updated_at",
    )


class FoodNutrientInline(admin.TabularInline):
    model = FoodNutrient
    extra = 0
    autocomplete_fields = ("nutrient",)
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "nutrient", "amount_per_100g", "source_reference", "created_at", "updated_at")


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    actions = None
    ordering = ("name",)
    date_hierarchy = "created_at"
    list_select_related = ("category", "data_source", "canonical_food")
    list_display = (
        "name",
        "category",
        "data_source",
        "is_verified",
        "density_g_per_ml",
        "created_at",
        "updated_at",
    )
    list_filter = ("category", "data_source", "is_verified", "created_at", "updated_at")
    search_fields = ("name", "name_ru", "name_en", "synonyms", "source_reference")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("canonical_food", "category", "data_source")
    fields = (
        "id",
        "canonical_food",
        "name",
        "name_ru",
        "name_en",
        "synonyms",
        "category",
        "data_source",
        "density_g_per_ml",
        "density_metadata",
        "is_verified",
        "source_reference",
        "created_at",
        "updated_at",
    )
    inlines = (FoodNutrientInline,)


@admin.register(FoodNutrient)
class FoodNutrientAdmin(admin.ModelAdmin):
    actions = None
    ordering = ("food_item__name", "nutrient__code")
    list_select_related = ("food_item", "nutrient")
    list_display = ("food_item", "nutrient", "amount_per_100g", "unit", "created_at", "updated_at")
    list_filter = ("nutrient__nutrient_type", "nutrient__unit", "created_at", "updated_at")
    search_fields = ("food_item__name", "food_item__synonyms", "nutrient__code", "nutrient__name")
    readonly_fields = ("id", "unit", "created_at", "updated_at")
    autocomplete_fields = ("food_item", "nutrient")
    fields = (
        "id",
        "food_item",
        "nutrient",
        "amount_per_100g",
        "unit",
        "source_reference",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Unit")
    def unit(self, obj: FoodNutrient) -> str:
        return obj.nutrient.unit
