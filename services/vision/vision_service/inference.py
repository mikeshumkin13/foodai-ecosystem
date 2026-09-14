from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

from PIL import Image

from vision_service.config import (
    VISION_FOOD_DETECTOR_LABELS,
    VISION_FOOD_DETECTOR_MAX_REGIONS,
    VISION_FOOD_DETECTOR_MODEL_ID,
    VISION_FOOD_DETECTOR_MODEL_REVISION,
    VISION_FOOD_DETECTOR_NMS_THRESHOLD,
    VISION_FOOD_DETECTOR_TEXT_THRESHOLD,
    VISION_FOOD_DETECTOR_THRESHOLD,
    VISION_FOOD_MODEL_ID,
    VISION_FOOD_MODEL_REVISION,
    VISION_FOOD_MODEL_TOP_K,
)


@dataclass(frozen=True)
class BoundingBox:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def area(self) -> float:
        return (self.right - self.left) * (self.bottom - self.top)


@dataclass(frozen=True)
class FoodRecognition:
    label: str
    confidence: float
    bounding_box: BoundingBox | None = None


@dataclass(frozen=True)
class FoodRegion:
    confidence: float
    bounding_box: BoundingBox
    label: str | None = None


class FoodRecognitionModel(Protocol):
    def predict(self, image: Image.Image) -> tuple[FoodRecognition, ...]:
        ...


class FoodRegionDetector(Protocol):
    def detect(self, image: Image.Image) -> tuple[FoodRegion, ...]:
        ...


class HuggingFaceFoodRecognitionModel:
    def __init__(
        self,
        *,
        model_id: str,
        revision: str,
        top_k: int,
    ) -> None:
        self._model_id = model_id
        self._revision = revision
        self._top_k = top_k
        self._pipeline: Any | None = None

    def predict(self, image: Image.Image) -> tuple[FoodRecognition, ...]:
        predictions = self._load_pipeline()(image)
        return tuple(
            _parse_pipeline_prediction(item)
            for item in _normalize_predictions(predictions, top_k=self._top_k)
        )

    def _load_pipeline(self) -> Any:
        if self._pipeline is None:
            from transformers import pipeline

            self._pipeline = pipeline(
                task="image-classification",
                model=self._model_id,
                revision=self._revision,
                model_kwargs={"use_safetensors": True},
                top_k=self._top_k,
            )
        return self._pipeline


class HuggingFaceFoodRegionDetector:
    def __init__(
        self,
        *,
        model_id: str,
        revision: str,
        candidate_labels: tuple[str, ...],
        threshold: float,
        text_threshold: float,
    ) -> None:
        self._model_id = model_id
        self._revision = revision
        self._candidate_labels = candidate_labels
        self._threshold = threshold
        self._text_threshold = text_threshold
        self._runtime: tuple[Any, Any, Any] | None = None

    def detect(self, image: Image.Image) -> tuple[FoodRegion, ...]:
        predictions = self._run_inference(image)
        if not isinstance(predictions, list):
            raise ValueError("invalid_detector_prediction")
        return tuple(_parse_detector_prediction(item, image=image) for item in predictions)

    def _run_inference(self, image: Image.Image) -> list[dict[str, object]]:
        processor, model, torch = self._load_runtime()
        inputs = processor(
            images=image,
            text=[list(self._candidate_labels)],
            return_tensors="pt",
        )
        with torch.no_grad():
            outputs = model(**inputs)
        results = processor.post_process_grounded_object_detection(
            outputs,
            inputs["input_ids"],
            threshold=self._threshold,
            text_threshold=self._text_threshold,
            target_sizes=[(image.height, image.width)],
        )
        if not isinstance(results, list) or not results:
            raise ValueError("invalid_detector_prediction")
        result = results[0]
        if not isinstance(result, dict):
            raise ValueError("invalid_detector_prediction")
        scores = _to_list(result.get("scores"))
        boxes = _to_list(result.get("boxes"))
        labels = result.get("text_labels", result.get("labels"))
        if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
            raise ValueError("invalid_detector_prediction")
        if len(scores) != len(boxes) or len(scores) != len(labels):
            raise ValueError("invalid_detector_prediction")
        return [
            {
                "score": score,
                "label": _resolve_candidate_label(label, self._candidate_labels),
                "box": {"xmin": box[0], "ymin": box[1], "xmax": box[2], "ymax": box[3]},
            }
            for score, box, label in zip(scores, boxes, labels, strict=True)
            if isinstance(box, list) and len(box) == 4
        ]

    def _load_runtime(self) -> tuple[Any, Any, Any]:
        if self._runtime is None:
            import torch
            from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

            processor = AutoProcessor.from_pretrained(
                self._model_id,
                revision=self._revision,
            )
            model = AutoModelForZeroShotObjectDetection.from_pretrained(
                self._model_id,
                revision=self._revision,
                use_safetensors=True,
            )
            model.eval()
            self._runtime = (processor, model, torch)
        return self._runtime


class MultiRegionFoodRecognitionModel:
    def __init__(
        self,
        *,
        detector: FoodRegionDetector,
        classifier: FoodRecognitionModel,
        max_regions: int,
        nms_threshold: float,
    ) -> None:
        self._detector = detector
        self._classifier = classifier
        self._max_regions = max_regions
        self._nms_threshold = nms_threshold

    def predict(self, image: Image.Image) -> tuple[FoodRecognition, ...]:
        regions = _select_regions(
            self._detector.detect(image),
            max_regions=self._max_regions,
            nms_threshold=self._nms_threshold,
        )
        if not regions:
            return self._classifier.predict(image)

        predictions: list[FoodRecognition] = []
        for region in regions:
            if region.label is not None and not _is_generic_region_label(region.label):
                predictions.append(
                    FoodRecognition(
                        label=_normalize_label(region.label),
                        confidence=region.confidence,
                        bounding_box=region.bounding_box,
                    )
                )
                continue
            crop = image.crop(_pil_crop_box(region.bounding_box))
            classified = self._classifier.predict(crop)
            if not classified:
                continue
            top_prediction = classified[0]
            predictions.append(
                FoodRecognition(
                    label=top_prediction.label,
                    confidence=min(region.confidence, top_prediction.confidence),
                    bounding_box=region.bounding_box,
                )
            )
        return tuple(predictions) if predictions else self._classifier.predict(image)


@lru_cache(maxsize=1)
def get_food_recognition_model() -> FoodRecognitionModel:
    classifier = HuggingFaceFoodRecognitionModel(
        model_id=VISION_FOOD_MODEL_ID,
        revision=VISION_FOOD_MODEL_REVISION,
        top_k=VISION_FOOD_MODEL_TOP_K,
    )
    detector = HuggingFaceFoodRegionDetector(
        model_id=VISION_FOOD_DETECTOR_MODEL_ID,
        revision=VISION_FOOD_DETECTOR_MODEL_REVISION,
        candidate_labels=VISION_FOOD_DETECTOR_LABELS,
        threshold=VISION_FOOD_DETECTOR_THRESHOLD,
        text_threshold=VISION_FOOD_DETECTOR_TEXT_THRESHOLD,
    )
    return MultiRegionFoodRecognitionModel(
        detector=detector,
        classifier=classifier,
        max_regions=VISION_FOOD_DETECTOR_MAX_REGIONS,
        nms_threshold=VISION_FOOD_DETECTOR_NMS_THRESHOLD,
    )


def _normalize_predictions(predictions: Any, *, top_k: int) -> Sequence[dict[str, Any]]:
    if isinstance(predictions, list) and predictions and isinstance(predictions[0], list):
        predictions = predictions[0]
    if not isinstance(predictions, list):
        raise ValueError("invalid_model_prediction")
    if not all(isinstance(item, dict) for item in predictions):
        raise ValueError("invalid_model_prediction")
    return predictions[:top_k]


def _parse_pipeline_prediction(item: dict[str, Any]) -> FoodRecognition:
    label = item.get("label")
    score = item.get("score")
    if not isinstance(label, str) or not label.strip():
        raise ValueError("invalid_model_prediction")
    if isinstance(score, bool) or not isinstance(score, int | float):
        raise ValueError("invalid_model_prediction")

    confidence = max(0.0, min(1.0, float(score)))
    return FoodRecognition(label=_normalize_label(label), confidence=confidence)


def _parse_detector_prediction(item: Any, *, image: Image.Image) -> FoodRegion:
    if not isinstance(item, dict):
        raise ValueError("invalid_detector_prediction")
    score = item.get("score")
    label = item.get("label")
    box = item.get("box")
    if isinstance(score, bool) or not isinstance(score, int | float):
        raise ValueError("invalid_detector_prediction")
    if not isinstance(box, dict):
        raise ValueError("invalid_detector_prediction")
    if label is not None and (not isinstance(label, str) or not label.strip()):
        raise ValueError("invalid_detector_prediction")

    left, top, right, bottom = (
        _parse_detector_coordinate(box.get(name)) for name in ("xmin", "ymin", "xmax", "ymax")
    )
    bounding_box = BoundingBox(
        left=max(0.0, min(float(image.width), left)),
        top=max(0.0, min(float(image.height), top)),
        right=max(0.0, min(float(image.width), right)),
        bottom=max(0.0, min(float(image.height), bottom)),
    )
    if bounding_box.area <= 0:
        raise ValueError("invalid_detector_prediction")
    return FoodRegion(
        confidence=max(0.0, min(1.0, float(score))),
        bounding_box=bounding_box,
        label=label.strip() if isinstance(label, str) else None,
    )


def _parse_detector_coordinate(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("invalid_detector_prediction")
    return float(value)


def _to_list(value: Any) -> list[Any]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, list):
        raise ValueError("invalid_detector_prediction")
    return value


def _select_regions(
    regions: Sequence[FoodRegion],
    *,
    max_regions: int,
    nms_threshold: float,
) -> tuple[FoodRegion, ...]:
    selected: list[FoodRegion] = []
    for candidate in sorted(regions, key=lambda item: item.confidence, reverse=True):
        if all(
            _intersection_over_union(candidate.bounding_box, item.bounding_box) < nms_threshold
            for item in selected
        ):
            selected.append(candidate)
        if len(selected) >= max_regions:
            break
    return tuple(selected)


def _intersection_over_union(first: BoundingBox, second: BoundingBox) -> float:
    intersection_width = max(0.0, min(first.right, second.right) - max(first.left, second.left))
    intersection_height = max(0.0, min(first.bottom, second.bottom) - max(first.top, second.top))
    intersection = intersection_width * intersection_height
    union = first.area + second.area - intersection
    return intersection / union if union > 0 else 0.0


def _pil_crop_box(bounding_box: BoundingBox) -> tuple[int, int, int, int]:
    return (
        int(bounding_box.left),
        int(bounding_box.top),
        max(int(bounding_box.right), int(bounding_box.left) + 1),
        max(int(bounding_box.bottom), int(bounding_box.top) + 1),
    )


def _normalize_label(label: str) -> str:
    return " ".join(label.strip().replace("_", " ").split()).casefold()


def _resolve_candidate_label(label: str, candidate_labels: tuple[str, ...]) -> str:
    normalized_label = _normalize_label(label)
    padded_label = f" {normalized_label} "
    matches: list[tuple[int, int, str]] = []
    for candidate in candidate_labels:
        normalized_candidate = _normalize_label(candidate)
        position = padded_label.find(f" {normalized_candidate} ")
        if position >= 0:
            matches.append((position, -len(normalized_candidate), normalized_candidate))
    if not matches:
        return normalized_label
    return min(matches)[2]


def _is_generic_region_label(label: str) -> bool:
    return _normalize_label(label) in {"food", "dish", "meal", "ingredient"}
