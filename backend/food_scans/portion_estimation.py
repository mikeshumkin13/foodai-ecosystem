from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from integrations.vision.client import VisionPortionReference
from nutrition.models import FoodItem

DECIMAL_PI = Decimal("3.1416")
MASS_QUANT = Decimal("0.01")
VOLUME_QUANT = Decimal("0.01")
CONFIDENCE_QUANT = Decimal("0.0001")


@dataclass(frozen=True)
class FoodTypeAssumption:
    code: str
    keywords: tuple[str, ...]
    density_g_per_ml: Decimal
    typical_volume_ml: Decimal
    assumed_depth_cm: Decimal


@dataclass(frozen=True)
class PortionEstimate:
    estimated_volume_ml: Decimal
    estimated_mass_g: Decimal
    confidence: Decimal
    min_estimate_g: Decimal
    max_estimate_g: Decimal
    method: str
    metadata: dict[str, str]


FOOD_TYPE_ASSUMPTIONS = (
    FoodTypeAssumption(
        code="grains",
        keywords=("grain", "grains", "rice", "pasta", "noodle", "греч", "рис", "круп"),
        density_g_per_ml=Decimal("0.8000"),
        typical_volume_ml=Decimal("180.00"),
        assumed_depth_cm=Decimal("2.20"),
    ),
    FoodTypeAssumption(
        code="protein_foods",
        keywords=("protein", "chicken", "beef", "pork", "fish", "meat", "кур", "мяс", "рыб"),
        density_g_per_ml=Decimal("0.9500"),
        typical_volume_ml=Decimal("120.00"),
        assumed_depth_cm=Decimal("1.60"),
    ),
    FoodTypeAssumption(
        code="fruits",
        keywords=("fruit", "apple", "banana", "berry", "яблок", "банан", "фрукт"),
        density_g_per_ml=Decimal("0.6500"),
        typical_volume_ml=Decimal("170.00"),
        assumed_depth_cm=Decimal("2.40"),
    ),
    FoodTypeAssumption(
        code="vegetables",
        keywords=("vegetable", "salad", "lettuce", "tomato", "овощ", "салат", "томат"),
        density_g_per_ml=Decimal("0.4500"),
        typical_volume_ml=Decimal("250.00"),
        assumed_depth_cm=Decimal("2.50"),
    ),
    FoodTypeAssumption(
        code="bread_flat",
        keywords=("bread", "pizza", "toast", "sandwich", "хлеб", "пицц", "тост"),
        density_g_per_ml=Decimal("0.3500"),
        typical_volume_ml=Decimal("140.00"),
        assumed_depth_cm=Decimal("1.20"),
    ),
    FoodTypeAssumption(
        code="liquid",
        keywords=("soup", "drink", "juice", "milk", "суп", "напит", "сок", "молок"),
        density_g_per_ml=Decimal("1.0000"),
        typical_volume_ml=Decimal("240.00"),
        assumed_depth_cm=Decimal("3.00"),
    ),
)

GENERIC_ASSUMPTION = FoodTypeAssumption(
    code="generic_mixed_food",
    keywords=(),
    density_g_per_ml=Decimal("0.8000"),
    typical_volume_ml=Decimal("150.00"),
    assumed_depth_cm=Decimal("2.00"),
)


def estimate_food_portion(
    *,
    food: FoodItem | None,
    label: str,
    recognition_confidence: Decimal | None,
    segment_area_px: Decimal | None,
    portion_reference: VisionPortionReference | None,
) -> PortionEstimate:
    """Estimate portion size as an uncertain MVP estimate, not a precise measurement."""

    assumption = _resolve_food_type_assumption(food=food, label=label)
    density, density_source = _resolve_density(food=food, assumption=assumption)

    if _has_usable_reference(segment_area_px=segment_area_px, reference=portion_reference):
        assert segment_area_px is not None
        assert portion_reference is not None
        assert portion_reference.area_px is not None
        assert portion_reference.diameter_cm is not None
        estimate = _estimate_from_plate_reference(
            segment_area_px=segment_area_px,
            reference=portion_reference,
            assumption=assumption,
            density_g_per_ml=density,
            density_source=density_source,
            recognition_confidence=recognition_confidence,
        )
    else:
        estimate = _estimate_from_typical_volume(
            assumption=assumption,
            density_g_per_ml=density,
            density_source=density_source,
            recognition_confidence=recognition_confidence,
        )

    return estimate


def _estimate_from_plate_reference(
    *,
    segment_area_px: Decimal,
    reference: VisionPortionReference,
    assumption: FoodTypeAssumption,
    density_g_per_ml: Decimal,
    density_source: str,
    recognition_confidence: Decimal | None,
) -> PortionEstimate:
    reference_diameter_cm = _to_decimal(reference.diameter_cm)
    reference_area_px = _to_decimal(reference.area_px)
    if reference_diameter_cm is None or reference_area_px is None:
        raise ValueError("reference_must_be_validated_before_estimation")

    reference_area_cm2 = DECIMAL_PI * (reference_diameter_cm / Decimal("2")) ** 2
    segment_area_cm2 = reference_area_cm2 * (segment_area_px / reference_area_px)
    estimated_volume_ml = segment_area_cm2 * assumption.assumed_depth_cm
    estimated_mass_g = estimated_volume_ml * density_g_per_ml
    base_confidence = (
        Decimal("0.6200")
        if density_source == "food_item_density"
        else Decimal("0.5600")
    )
    confidence = _combine_confidence(
        base_confidence=base_confidence,
        recognition_confidence=recognition_confidence,
    )

    return _build_estimate(
        estimated_volume_ml=estimated_volume_ml,
        estimated_mass_g=estimated_mass_g,
        confidence=confidence,
        lower_multiplier=Decimal("0.6500"),
        upper_multiplier=Decimal("1.4500"),
        method="segment_area_plate_reference_geometry_v1",
        metadata={
            "food_type": assumption.code,
            "density_source": density_source,
            "density_g_per_ml": str(density_g_per_ml),
            "assumed_depth_cm": str(assumption.assumed_depth_cm),
            "reference_type": reference.reference_type,
            "reference_diameter_cm": str(reference_diameter_cm),
            "reference_area_px": str(reference_area_px),
            "segment_area_px": str(segment_area_px),
        },
    )


def _estimate_from_typical_volume(
    *,
    assumption: FoodTypeAssumption,
    density_g_per_ml: Decimal,
    density_source: str,
    recognition_confidence: Decimal | None,
) -> PortionEstimate:
    estimated_volume_ml = assumption.typical_volume_ml
    estimated_mass_g = estimated_volume_ml * density_g_per_ml
    base_confidence = (
        Decimal("0.4200")
        if density_source == "food_item_density"
        else Decimal("0.3400")
    )
    confidence = _combine_confidence(
        base_confidence=base_confidence,
        recognition_confidence=recognition_confidence,
    )

    return _build_estimate(
        estimated_volume_ml=estimated_volume_ml,
        estimated_mass_g=estimated_mass_g,
        confidence=confidence,
        lower_multiplier=Decimal("0.5000"),
        upper_multiplier=Decimal("1.8000"),
        method="food_type_typical_volume_density_table_v1",
        metadata={
            "food_type": assumption.code,
            "density_source": density_source,
            "density_g_per_ml": str(density_g_per_ml),
            "typical_volume_ml": str(assumption.typical_volume_ml),
            "geometric_assumption": "no reliable physical reference supplied",
        },
    )


def _build_estimate(
    *,
    estimated_volume_ml: Decimal,
    estimated_mass_g: Decimal,
    confidence: Decimal,
    lower_multiplier: Decimal,
    upper_multiplier: Decimal,
    method: str,
    metadata: dict[str, str],
) -> PortionEstimate:
    rounded_mass = _quantize(estimated_mass_g, MASS_QUANT)
    return PortionEstimate(
        estimated_volume_ml=_quantize(estimated_volume_ml, VOLUME_QUANT),
        estimated_mass_g=rounded_mass,
        confidence=_quantize(confidence, CONFIDENCE_QUANT),
        min_estimate_g=_quantize(rounded_mass * lower_multiplier, MASS_QUANT),
        max_estimate_g=_quantize(rounded_mass * upper_multiplier, MASS_QUANT),
        method=method,
        metadata=metadata,
    )


def _resolve_density(
    *,
    food: FoodItem | None,
    assumption: FoodTypeAssumption,
) -> tuple[Decimal, str]:
    if food is not None:
        if food.density_g_per_ml is not None and food.density_g_per_ml > 0:
            return food.density_g_per_ml, "food_item_density"
        metadata_density = _parse_density_metadata(food.density_metadata)
        if metadata_density is not None:
            return metadata_density, "food_density_metadata"
    return assumption.density_g_per_ml, f"density_table:{assumption.code}"


def _parse_density_metadata(metadata: Any) -> Decimal | None:
    if not isinstance(metadata, dict):
        return None
    value = metadata.get("density_g_per_ml") or metadata.get("density")
    density = _to_decimal(value)
    if density is None or density <= 0:
        return None
    return density


def _resolve_food_type_assumption(
    *,
    food: FoodItem | None,
    label: str,
) -> FoodTypeAssumption:
    searchable_text = _food_searchable_text(food=food, label=label)
    for assumption in FOOD_TYPE_ASSUMPTIONS:
        if any(keyword in searchable_text for keyword in assumption.keywords):
            return assumption
    return GENERIC_ASSUMPTION


def _food_searchable_text(*, food: FoodItem | None, label: str) -> str:
    parts = [label]
    if food is not None:
        parts.extend([food.name, food.name_ru, food.name_en])
        category = food.category
        parts.extend([category.slug, category.name, category.name_ru, category.name_en])
        if isinstance(food.synonyms, list):
            parts.extend(str(item) for item in food.synonyms)
    return " ".join(parts).casefold()


def _has_usable_reference(
    *,
    segment_area_px: Decimal | None,
    reference: VisionPortionReference | None,
) -> bool:
    if segment_area_px is None or segment_area_px <= 0 or reference is None:
        return False
    return (
        _to_decimal(reference.area_px) is not None
        and _to_decimal(reference.diameter_cm) is not None
    )


def _combine_confidence(
    *,
    base_confidence: Decimal,
    recognition_confidence: Decimal | None,
) -> Decimal:
    if recognition_confidence is None:
        return base_confidence
    bounded_recognition_confidence = max(Decimal("0"), min(Decimal("1"), recognition_confidence))
    multiplier = Decimal("0.5000") + bounded_recognition_confidence * Decimal("0.5000")
    return min(Decimal("0.8500"), base_confidence * multiplier)


def _to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if decimal_value <= 0:
        return None
    return decimal_value


def _quantize(value: Decimal, quant: Decimal) -> Decimal:
    return value.quantize(quant, rounding=ROUND_HALF_UP)
