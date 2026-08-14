from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

from PIL import Image

from vision_service.config import (
    VISION_FOOD_MODEL_ID,
    VISION_FOOD_MODEL_REVISION,
    VISION_FOOD_MODEL_TOP_K,
)


@dataclass(frozen=True)
class FoodRecognition:
    label: str
    confidence: float


class FoodRecognitionModel(Protocol):
    def predict(self, image: Image.Image) -> tuple[FoodRecognition, ...]:
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


@lru_cache(maxsize=1)
def get_food_recognition_model() -> FoodRecognitionModel:
    return HuggingFaceFoodRecognitionModel(
        model_id=VISION_FOOD_MODEL_ID,
        revision=VISION_FOOD_MODEL_REVISION,
        top_k=VISION_FOOD_MODEL_TOP_K,
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


def _normalize_label(label: str) -> str:
    return " ".join(label.strip().replace("_", " ").split()).casefold()
