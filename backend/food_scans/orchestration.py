from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from diary.models import Meal, MealItem
from food_scans.matching import match_food_label
from food_scans.models import FoodScan, FoodScanDetectedItem
from food_scans.vision import VisionAnalyzer, analyze_food_scan
from integrations.vision.client import VisionClientError, VisionDetectedItem
from nutrition.models import FoodItem

DEFAULT_ESTIMATED_MASS_G = Decimal("100.00")
NUTRIENT_QUANT = Decimal("0.0001")


class FoodScanWorkflowError(ValueError):
    def __init__(self, code: str, *, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.details = details or {}
        super().__init__(code)


def start_scan_analysis(
    food_scan: FoodScan,
    *,
    vision_client: VisionAnalyzer | None = None,
) -> FoodScan:
    if food_scan.status == FoodScan.Status.CONFIRMED:
        return food_scan

    _mark_scan_processing(food_scan)
    try:
        analysis_result = analyze_food_scan(food_scan, vision_client=vision_client)
    except VisionClientError as exc:
        return _mark_scan_failed(food_scan, failure_code=exc.code)

    with transaction.atomic():
        locked_scan = FoodScan.objects.select_for_update().get(id=food_scan.id)
        if locked_scan.status == FoodScan.Status.CONFIRMED:
            return locked_scan

        locked_scan.detected_items.all().delete()
        FoodScanDetectedItem.objects.bulk_create(
            [
                _build_detected_item(
                    food_scan=locked_scan,
                    detected_item=detected_item,
                    position=position,
                )
                for position, detected_item in enumerate(analysis_result.items)
            ],
        )
        locked_scan.status = FoodScan.Status.NEEDS_CONFIRMATION
        locked_scan.failure_code = ""
        locked_scan.save(update_fields=["status", "failure_code", "updated_at"])

    food_scan.refresh_from_db()
    return food_scan


def update_scan_detected_item(
    *,
    food_scan: FoodScan,
    detected_item: FoodScanDetectedItem,
    matched_food: FoodItem,
    mass_g: Decimal,
) -> FoodScanDetectedItem:
    _ensure_scan_can_be_edited(food_scan)
    _ensure_item_belongs_to_scan(food_scan=food_scan, detected_item=detected_item)
    if detected_item.is_removed:
        raise FoodScanWorkflowError("detected_item_removed")

    snapshot_fields = _snapshot_fields(food=matched_food, mass_g=mass_g)
    detected_item.matched_food = matched_food
    detected_item.estimated_mass_g = mass_g
    detected_item.manually_corrected = True
    for field_name, value in snapshot_fields.items():
        setattr(detected_item, field_name, value)
    detected_item.save(
        update_fields=[
            "matched_food",
            "estimated_mass_g",
            "food_name_snapshot",
            "food_source_reference_snapshot",
            "calories_kcal",
            "protein_g",
            "fat_g",
            "carbs_g",
            "micronutrient_snapshot",
            "nutrient_snapshot",
            "manually_corrected",
            "updated_at",
        ],
    )
    return detected_item


def add_manual_detected_item(
    *,
    food_scan: FoodScan,
    matched_food: FoodItem,
    mass_g: Decimal,
    label: str,
) -> FoodScanDetectedItem:
    _ensure_scan_can_be_edited(food_scan)
    resolved_label = label.strip() or matched_food.name
    snapshot_fields = _snapshot_fields(food=matched_food, mass_g=mass_g)
    return FoodScanDetectedItem.objects.create(
        food_scan=food_scan,
        matched_food=matched_food,
        label=resolved_label,
        confidence=None,
        estimated_mass_g=mass_g,
        source=FoodScanDetectedItem.Source.MANUAL,
        position=_next_detected_item_position(food_scan),
        is_removed=False,
        manually_corrected=True,
        **snapshot_fields,
    )


def remove_scan_detected_item(
    *,
    food_scan: FoodScan,
    detected_item: FoodScanDetectedItem,
) -> FoodScanDetectedItem:
    _ensure_scan_can_be_edited(food_scan)
    _ensure_item_belongs_to_scan(food_scan=food_scan, detected_item=detected_item)
    if not detected_item.is_removed:
        detected_item.is_removed = True
        detected_item.manually_corrected = True
        detected_item.save(update_fields=["is_removed", "manually_corrected", "updated_at"])
    return detected_item


def confirm_food_scan(
    *,
    food_scan: FoodScan,
    meal_type: str,
    logged_at: datetime,
    name: str,
) -> Meal:
    with transaction.atomic():
        locked_scan = (
            FoodScan.objects.select_for_update()
            .select_related("user", "confirmed_meal")
            .get(id=food_scan.id)
        )
        if locked_scan.status == FoodScan.Status.CONFIRMED:
            confirmed_meal = locked_scan.confirmed_meal
            if confirmed_meal is not None:
                return confirmed_meal
            raise FoodScanWorkflowError("confirmed_meal_missing")

        _ensure_scan_can_be_edited(locked_scan)
        detected_items = list(
            locked_scan.detected_items.select_related("matched_food")
            .filter(is_removed=False)
            .order_by("position", "created_at", "id")
        )
        if not detected_items:
            raise FoodScanWorkflowError("no_detected_items_to_confirm")

        unmatched_item_ids = [
            str(detected_item.id)
            for detected_item in detected_items
            if detected_item.matched_food_id is None
        ]
        if unmatched_item_ids:
            raise FoodScanWorkflowError(
                "detected_items_require_food_match",
                details={"item_ids": unmatched_item_ids},
            )

        meal = Meal.objects.create(
            user=locked_scan.user,
            meal_type=meal_type,
            logged_at=logged_at,
            name=name,
        )
        MealItem.objects.bulk_create(
            [
                _build_meal_item_from_detected_item(meal, detected_item)
                for detected_item in detected_items
            ],
        )
        locked_scan.status = FoodScan.Status.CONFIRMED
        locked_scan.failure_code = ""
        locked_scan.confirmed_meal = meal
        locked_scan.save(
            update_fields=["status", "failure_code", "confirmed_meal", "updated_at"],
        )

    return (
        Meal.objects.select_related("user").prefetch_related("items", "items__food").get(id=meal.id)
    )


def _mark_scan_processing(food_scan: FoodScan) -> None:
    FoodScan.objects.filter(id=food_scan.id).update(
        status=FoodScan.Status.PROCESSING,
        failure_code="",
        updated_at=timezone.now(),
    )
    food_scan.status = FoodScan.Status.PROCESSING
    food_scan.failure_code = ""


def _mark_scan_failed(food_scan: FoodScan, *, failure_code: str) -> FoodScan:
    FoodScan.objects.filter(id=food_scan.id).update(
        status=FoodScan.Status.FAILED,
        failure_code=failure_code,
        updated_at=timezone.now(),
    )
    food_scan.refresh_from_db()
    return food_scan


def _build_detected_item(
    *,
    food_scan: FoodScan,
    detected_item: VisionDetectedItem,
    position: int,
) -> FoodScanDetectedItem:
    matched_food = match_food_label(detected_item.label)
    snapshot_fields = (
        _snapshot_fields(food=matched_food, mass_g=DEFAULT_ESTIMATED_MASS_G)
        if matched_food is not None
        else _empty_snapshot_fields()
    )
    return FoodScanDetectedItem(
        food_scan=food_scan,
        matched_food=matched_food,
        label=detected_item.label,
        confidence=_confidence_decimal(detected_item.confidence),
        estimated_mass_g=DEFAULT_ESTIMATED_MASS_G,
        source=FoodScanDetectedItem.Source.VISION,
        position=position,
        is_removed=False,
        manually_corrected=False,
        **snapshot_fields,
    )


def _build_meal_item_from_detected_item(
    meal: Meal,
    detected_item: FoodScanDetectedItem,
) -> MealItem:
    matched_food = detected_item.matched_food
    if matched_food is None:
        raise FoodScanWorkflowError("detected_items_require_food_match")

    return MealItem(
        meal=meal,
        food=matched_food,
        food_name_snapshot=detected_item.food_name_snapshot,
        food_source_reference_snapshot=detected_item.food_source_reference_snapshot,
        mass_g=detected_item.estimated_mass_g,
        calories_kcal=detected_item.calories_kcal,
        protein_g=detected_item.protein_g,
        fat_g=detected_item.fat_g,
        carbs_g=detected_item.carbs_g,
        micronutrient_snapshot=detected_item.micronutrient_snapshot,
        nutrient_snapshot=detected_item.nutrient_snapshot,
        source=_meal_item_source(detected_item),
        confidence=detected_item.confidence,
        manually_corrected=detected_item.manually_corrected,
    )


def _snapshot_fields(*, food: FoodItem, mass_g: Decimal) -> dict[str, Any]:
    from diary.snapshots import build_food_snapshot

    snapshot = build_food_snapshot(food, mass_g)
    return {
        "food_name_snapshot": snapshot["food_name_snapshot"],
        "food_source_reference_snapshot": snapshot["food_source_reference_snapshot"],
        "calories_kcal": snapshot["calories_kcal"],
        "protein_g": snapshot["protein_g"],
        "fat_g": snapshot["fat_g"],
        "carbs_g": snapshot["carbs_g"],
        "micronutrient_snapshot": snapshot["micronutrient_snapshot"],
        "nutrient_snapshot": snapshot["nutrient_snapshot"],
    }


def _empty_snapshot_fields() -> dict[str, Any]:
    return {
        "food_name_snapshot": "",
        "food_source_reference_snapshot": "",
        "calories_kcal": Decimal("0.0000"),
        "protein_g": Decimal("0.0000"),
        "fat_g": Decimal("0.0000"),
        "carbs_g": Decimal("0.0000"),
        "micronutrient_snapshot": {},
        "nutrient_snapshot": {},
    }


def _confidence_decimal(confidence: float) -> Decimal:
    return Decimal(str(confidence)).quantize(NUTRIENT_QUANT, rounding=ROUND_HALF_UP)


def _meal_item_source(detected_item: FoodScanDetectedItem) -> str:
    if detected_item.source == FoodScanDetectedItem.Source.MANUAL:
        return MealItem.Source.MANUAL
    return MealItem.Source.VISION


def _next_detected_item_position(food_scan: FoodScan) -> int:
    max_position = food_scan.detected_items.aggregate(Max("position"))["position__max"]
    if max_position is None:
        return 0
    return int(max_position) + 1


def _ensure_scan_can_be_edited(food_scan: FoodScan) -> None:
    if food_scan.status != FoodScan.Status.NEEDS_CONFIRMATION:
        raise FoodScanWorkflowError(
            "scan_not_ready_for_confirmation",
            details={"status": food_scan.status},
        )


def _ensure_item_belongs_to_scan(
    *,
    food_scan: FoodScan,
    detected_item: FoodScanDetectedItem,
) -> None:
    if detected_item.food_scan_id != food_scan.id:
        raise FoodScanWorkflowError("detected_item_not_found")
