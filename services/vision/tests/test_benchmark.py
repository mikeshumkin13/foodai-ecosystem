from __future__ import annotations

from pathlib import Path

from scripts.benchmark_food_model import (
    BenchmarkImageResult,
    _build_report,
    _load_validation_cases,
    _matched_expected_labels,
)
from vision_service.inference import FoodRecognition


def test_validation_report_enforces_multi_region_label_and_confidence_metrics() -> None:
    results: list[BenchmarkImageResult] = [
        {
            "image": "sample-a",
            "latency_ms": 120.0,
            "detected_items": [
                {"label": "fried rice", "confidence": 0.8},
                {"label": "chicken", "confidence": 0.7},
            ],
            "expected_min_items": 2,
            "expected_labels": ["rice", "chicken"],
            "matched_labels": ["rice", "chicken"],
        },
        {
            "image": "sample-b",
            "latency_ms": 80.0,
            "detected_items": [{"label": "salad", "confidence": 0.6}],
            "expected_min_items": 2,
            "expected_labels": ["salad", "bread"],
            "matched_labels": ["salad"],
        },
    ]

    report = _build_report(
        results=results,
        thresholds={
            "multi_region_rate": 0.5,
            "expected_label_recall": 0.75,
            "confidence_coverage": 1.0,
        },
    )

    assert report["summary"] == {
        "image_count": 2,
        "latency_ms_avg": 100.0,
        "latency_ms_p50": 100.0,
        "multi_region_rate": 0.5,
        "expected_label_recall": 0.75,
        "confidence_coverage": 1.0,
    }
    assert report["acceptance"]["passed"] is True


def test_validation_report_fails_unmet_threshold() -> None:
    results: list[BenchmarkImageResult] = [
        {
            "image": "sample",
            "latency_ms": 10.0,
            "detected_items": [{"label": "pizza"}],
            "expected_min_items": 2,
            "expected_labels": ["pizza", "salad"],
            "matched_labels": ["pizza"],
        }
    ]

    report = _build_report(
        results=results,
        thresholds={"multi_region_rate": 1.0, "confidence_coverage": 1.0},
    )

    assert report["acceptance"]["checks"] == {
        "multi_region_rate": False,
        "confidence_coverage": False,
    }
    assert report["acceptance"]["passed"] is False


def test_expected_label_match_accepts_dish_label_containing_ingredient() -> None:
    matched = _matched_expected_labels(
        expected_labels=("rice", "chicken", "pear"),
        predictions=(
            FoodRecognition(label="fried rice", confidence=0.7),
            FoodRecognition(label="chicken curry", confidence=0.6),
        ),
    )

    assert matched == ["rice", "chicken"]


def test_foodseg_validation_manifest_loads_eight_multi_food_crops() -> None:
    fixture_root = Path(__file__).parents[1] / "fixtures" / "validation"

    cases, thresholds = _load_validation_cases(fixture_root / "foodseg103_manifest.json")

    try:
        assert len(cases) == 8
        assert all(case.expected_min_items is not None for case in cases)
        assert all(case.image.width > 0 and case.image.height > 0 for case in cases)
        assert thresholds["multi_region_rate"] == 0.625
    finally:
        for case in cases:
            case.image.close()
