from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path
from typing import TypedDict

from PIL import Image

from vision_service.inference import FoodRecognitionModel, get_food_recognition_model


class BenchmarkImageResult(TypedDict):
    image: str
    latency_ms: float
    detected_items: list[dict[str, object]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark FoodAI Vision food model v1.")
    parser.add_argument("images", nargs="*", type=Path, help="Prepared local JPEG/PNG images.")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Run benchmark against generated synthetic fixtures instead of repository photos.",
    )
    args = parser.parse_args()

    image_paths = args.images
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    if args.synthetic or not image_paths:
        temp_dir = tempfile.TemporaryDirectory()
        image_paths = _create_synthetic_images(Path(temp_dir.name))

    try:
        model = get_food_recognition_model()
        results = [
            _benchmark_image(model=model, image_path=image_path)
            for image_path in image_paths
        ]
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()

    latencies = [result["latency_ms"] for result in results]
    report = {
        "images": results,
        "summary": {
            "count": len(results),
            "latency_ms_avg": round(statistics.fmean(latencies), 3) if latencies else 0,
            "latency_ms_p50": round(statistics.median(latencies), 3) if latencies else 0,
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _benchmark_image(
    *,
    model: FoodRecognitionModel,
    image_path: Path,
) -> BenchmarkImageResult:
    with Image.open(image_path) as image:
        prepared_image = image.convert("RGB")

    start = time.perf_counter()
    predictions = model.predict(prepared_image)
    latency_ms = (time.perf_counter() - start) * 1000

    return {
        "image": str(image_path),
        "latency_ms": round(latency_ms, 3),
        "detected_items": [
            {"label": prediction.label, "confidence": round(prediction.confidence, 6)}
            for prediction in predictions
        ],
    }


def _create_synthetic_images(directory: Path) -> list[Path]:
    fixtures = [
        ("synthetic_red_plate.jpg", (210, 48, 48)),
        ("synthetic_green_plate.png", (72, 168, 80)),
    ]
    image_paths: list[Path] = []
    for filename, color in fixtures:
        image = Image.new("RGB", (224, 224), color=color)
        image_path = directory / filename
        image.save(image_path)
        image_paths.append(image_path)
    return image_paths


if __name__ == "__main__":
    main()
