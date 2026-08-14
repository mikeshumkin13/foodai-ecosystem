from __future__ import annotations

from typing import Any

import pytest
from PIL import Image

from vision_service.inference import HuggingFaceFoodRecognitionModel


class FakePipelineFoodRecognitionModel(HuggingFaceFoodRecognitionModel):
    def __init__(self, predictions: Any) -> None:
        super().__init__(model_id="test-model", revision="test-revision", top_k=2)
        self._predictions = predictions

    def _load_pipeline(self) -> Any:
        return lambda image: self._predictions


def test_hugging_face_food_model_normalizes_pipeline_predictions() -> None:
    model = FakePipelineFoodRecognitionModel(
        [
            {"label": "Fried_Rice", "score": 0.81234},
            {"label": "pizza", "score": 0.102},
        ],
    )

    predictions = model.predict(_synthetic_image())

    assert [prediction.label for prediction in predictions] == ["fried rice", "pizza"]
    assert [prediction.confidence for prediction in predictions] == [0.81234, 0.102]


def test_hugging_face_food_model_supports_nested_pipeline_predictions() -> None:
    model = FakePipelineFoodRecognitionModel([[{"label": "Ice_Cream", "score": 1.2}]])

    predictions = model.predict(_synthetic_image())

    assert predictions[0].label == "ice cream"
    assert predictions[0].confidence == 1.0


@pytest.mark.parametrize(
    "prediction",
    [
        {"label": "", "score": 0.9},
        {"label": "rice", "score": "0.9"},
        {"result": "rice"},
        "not-a-dict",
    ],
)
def test_hugging_face_food_model_rejects_invalid_prediction(prediction: object) -> None:
    model = FakePipelineFoodRecognitionModel([prediction])

    with pytest.raises(ValueError, match="invalid_model_prediction"):
        model.predict(_synthetic_image())


def _synthetic_image() -> Image.Image:
    return Image.new("RGB", (224, 224), color=(210, 48, 48))
