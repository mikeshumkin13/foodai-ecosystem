from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from PIL import Image

from vision_service.inference import (
    FoodRecognition,
    FoodRecognitionModel,
    get_food_recognition_model,
)


class BenchmarkImageResult(TypedDict, total=False):
    image: str
    latency_ms: float
    detected_items: list[dict[str, object]]
    expected_min_items: int
    expected_labels: list[str]
    matched_labels: list[str]


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    image: Image.Image
    expected_min_items: int | None = None
    expected_labels: tuple[str, ...] = ()


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark FoodAI Vision multi-food pipeline.")
    parser.add_argument("images", nargs="*", type=Path, help="Prepared local JPEG/PNG images.")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Run a smoke benchmark against generated synthetic fixtures.",
    )
    parser.add_argument(
        "--validation-manifest",
        type=Path,
        help="Run the licensed validation fixture declared by a JSON manifest.",
    )
    parser.add_argument(
        "--enforce-thresholds",
        action="store_true",
        help="Exit with a failure when manifest acceptance thresholds are not met.",
    )
    args = parser.parse_args()

    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    thresholds: dict[str, float] = {}
    if args.validation_manifest is not None:
        cases, thresholds = _load_validation_cases(args.validation_manifest)
    elif args.synthetic or not args.images:
        temp_dir = tempfile.TemporaryDirectory()
        cases = _create_synthetic_cases(Path(temp_dir.name))
    else:
        cases = [_case_from_path(path) for path in args.images]

    try:
        model = get_food_recognition_model()
        results = [_benchmark_case(model=model, case=case) for case in cases]
    finally:
        for case in cases:
            case.image.close()
        if temp_dir is not None:
            temp_dir.cleanup()

    report = _build_report(results=results, thresholds=thresholds)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.enforce_thresholds and report["acceptance"]["passed"] is not True:
        raise SystemExit(1)


def _benchmark_case(
    *,
    model: FoodRecognitionModel,
    case: BenchmarkCase,
) -> BenchmarkImageResult:
    start = time.perf_counter()
    predictions = model.predict(case.image)
    latency_ms = (time.perf_counter() - start) * 1000

    result: BenchmarkImageResult = {
        "image": case.name,
        "latency_ms": round(latency_ms, 3),
        "detected_items": [_serialize_prediction(prediction) for prediction in predictions],
    }
    if case.expected_min_items is not None:
        result["expected_min_items"] = case.expected_min_items
    if case.expected_labels:
        result["expected_labels"] = list(case.expected_labels)
        result["matched_labels"] = _matched_expected_labels(
            expected_labels=case.expected_labels,
            predictions=predictions,
        )
    return result


def _serialize_prediction(prediction: FoodRecognition) -> dict[str, object]:
    item: dict[str, object] = {
        "label": prediction.label,
        "confidence": round(prediction.confidence, 6),
    }
    if prediction.bounding_box is not None:
        item["bounding_box"] = {
            "left": round(prediction.bounding_box.left, 2),
            "top": round(prediction.bounding_box.top, 2),
            "right": round(prediction.bounding_box.right, 2),
            "bottom": round(prediction.bounding_box.bottom, 2),
        }
    return item


def _build_report(
    *,
    results: list[BenchmarkImageResult],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    latencies = [result["latency_ms"] for result in results]
    evaluated_multi_item = [
        result
        for result in results
        if isinstance(result.get("expected_min_items"), int)
        and result["expected_min_items"] >= 2
    ]
    multi_region_hits = sum(
        len(result["detected_items"]) >= result["expected_min_items"]
        for result in evaluated_multi_item
    )
    expected_label_count = sum(len(result.get("expected_labels", [])) for result in results)
    matched_label_count = sum(len(result.get("matched_labels", [])) for result in results)
    prediction_count = sum(len(result["detected_items"]) for result in results)
    predictions_with_confidence = sum(
        "confidence" in item for result in results for item in result["detected_items"]
    )
    metrics = {
        "image_count": len(results),
        "latency_ms_avg": round(statistics.fmean(latencies), 3) if latencies else 0.0,
        "latency_ms_p50": round(statistics.median(latencies), 3) if latencies else 0.0,
        "multi_region_rate": _ratio(multi_region_hits, len(evaluated_multi_item)),
        "expected_label_recall": _ratio(matched_label_count, expected_label_count),
        "confidence_coverage": _ratio(predictions_with_confidence, prediction_count),
    }
    checks = {
        metric: isinstance(metrics.get(metric), int | float)
        and float(metrics[metric]) >= threshold
        for metric, threshold in thresholds.items()
    }
    return {
        "images": results,
        "summary": metrics,
        "acceptance": {
            "thresholds": thresholds,
            "checks": checks,
            "passed": all(checks.values()) if checks else None,
        },
    }


def _load_validation_cases(manifest_path: Path) -> tuple[list[BenchmarkCase], dict[str, float]]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("invalid_validation_manifest")
    source_name = data.get("source_image")
    samples = data.get("samples")
    acceptance = data.get("acceptance", {})
    if not isinstance(source_name, str) or not isinstance(samples, list):
        raise ValueError("invalid_validation_manifest")
    if not isinstance(acceptance, dict):
        raise ValueError("invalid_validation_manifest")

    source_path = manifest_path.parent / source_name
    with Image.open(source_path) as source:
        prepared_source = source.convert("RGB")
    cases = [_parse_validation_sample(sample, source=prepared_source) for sample in samples]
    prepared_source.close()
    thresholds = {
        str(name): float(value)
        for name, value in acceptance.items()
        if isinstance(value, int | float) and not isinstance(value, bool)
    }
    return cases, thresholds


def _parse_validation_sample(sample: Any, *, source: Image.Image) -> BenchmarkCase:
    if not isinstance(sample, dict):
        raise ValueError("invalid_validation_manifest")
    name = sample.get("name")
    crop = sample.get("crop")
    expected_min_items = sample.get("expected_min_items")
    expected_labels = sample.get("expected_labels")
    if (
        not isinstance(name, str)
        or not isinstance(crop, list)
        or len(crop) != 4
        or not all(isinstance(value, int) and not isinstance(value, bool) for value in crop)
        or not isinstance(expected_min_items, int)
        or isinstance(expected_min_items, bool)
        or not isinstance(expected_labels, list)
        or not all(isinstance(label, str) for label in expected_labels)
    ):
        raise ValueError("invalid_validation_manifest")
    return BenchmarkCase(
        name=name,
        image=source.crop(tuple(crop)),
        expected_min_items=expected_min_items,
        expected_labels=tuple(expected_labels),
    )


def _matched_expected_labels(
    *,
    expected_labels: tuple[str, ...],
    predictions: tuple[FoodRecognition, ...],
) -> list[str]:
    predicted_labels = [_normalize_label(prediction.label) for prediction in predictions]
    return [
        expected
        for expected in expected_labels
        if any(
            _normalize_label(expected) in predicted or predicted in _normalize_label(expected)
            for predicted in predicted_labels
        )
    ]


def _normalize_label(label: str) -> str:
    return " ".join(label.casefold().replace("_", " ").split())


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _case_from_path(path: Path) -> BenchmarkCase:
    with Image.open(path) as image:
        prepared = image.convert("RGB")
    return BenchmarkCase(name=str(path), image=prepared)


def _create_synthetic_cases(directory: Path) -> list[BenchmarkCase]:
    fixtures = [
        ("synthetic_red_plate.jpg", (210, 48, 48)),
        ("synthetic_green_plate.png", (72, 168, 80)),
    ]
    cases: list[BenchmarkCase] = []
    for filename, color in fixtures:
        image = Image.new("RGB", (224, 224), color=color)
        image_path = directory / filename
        image.save(image_path)
        cases.append(BenchmarkCase(name=filename, image=image))
    return cases


if __name__ == "__main__":
    main()
