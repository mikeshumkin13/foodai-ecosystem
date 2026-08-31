from __future__ import annotations

from typing import Any

import pytest
from PIL import Image

from vision_service.inference import (
    BoundingBox,
    FoodRecognition,
    FoodRegion,
    HuggingFaceFoodRecognitionModel,
    HuggingFaceFoodRegionDetector,
    MultiRegionFoodRecognitionModel,
)


class FakePipelineFoodRecognitionModel(HuggingFaceFoodRecognitionModel):
    def __init__(self, predictions: Any) -> None:
        super().__init__(model_id="test-model", revision="test-revision", top_k=2)
        self._predictions = predictions

    def _load_pipeline(self) -> Any:
        return lambda image: self._predictions


class FakePipelineFoodRegionDetector(HuggingFaceFoodRegionDetector):
    def __init__(self, predictions: Any) -> None:
        super().__init__(
            model_id="test-detector",
            revision="test-revision",
            candidate_labels=("food",),
            threshold=0.25,
            text_threshold=0.20,
        )
        self._predictions = predictions

    def _run_inference(self, image: Image.Image) -> Any:
        return self._predictions


class FakeTensor:
    def __init__(self, value: list[object]) -> None:
        self._value = value

    def tolist(self) -> list[object]:
        return self._value


class FakeGroundingDinoProcessor:
    def __init__(self, *, text_label: str = "rice") -> None:
        self.text: object = None
        self.target_sizes: object = None
        self.text_label = text_label

    def __call__(
        self,
        *,
        images: Image.Image,
        text: object,
        return_tensors: str,
    ) -> dict[str, object]:
        assert images.mode == "RGB"
        assert return_tensors == "pt"
        self.text = text
        return {"input_ids": [[1, 2, 3]], "pixel_values": "prepared"}

    def post_process_grounded_object_detection(
        self,
        outputs: object,
        input_ids: object,
        *,
        threshold: float,
        text_threshold: float,
        target_sizes: object,
    ) -> list[dict[str, object]]:
        assert outputs == {"predictions": "raw"}
        assert input_ids == [[1, 2, 3]]
        assert threshold == 0.25
        assert text_threshold == 0.20
        self.target_sizes = target_sizes
        return [
            {
                "scores": FakeTensor([0.77]),
                "boxes": FakeTensor([[10.0, 20.0, 110.0, 120.0]]),
                "text_labels": [self.text_label],
            }
        ]


class FakeGroundingDinoModel:
    def __call__(self, **inputs: object) -> dict[str, str]:
        assert inputs == {"input_ids": [[1, 2, 3]], "pixel_values": "prepared"}
        return {"predictions": "raw"}


class FakeNoGrad:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *args: object) -> None:
        return None


class FakeTorch:
    @staticmethod
    def no_grad() -> FakeNoGrad:
        return FakeNoGrad()


class RuntimeFoodRegionDetector(HuggingFaceFoodRegionDetector):
    def __init__(
        self,
        *,
        processor: FakeGroundingDinoProcessor,
        model: FakeGroundingDinoModel,
    ) -> None:
        super().__init__(
            model_id="test-detector",
            revision="test-revision",
            candidate_labels=("food", "rice", "chicken"),
            threshold=0.25,
            text_threshold=0.20,
        )
        self._fake_runtime = (processor, model, FakeTorch())

    def _load_runtime(self) -> tuple[Any, Any, Any]:
        return self._fake_runtime


class StubDetector:
    def __init__(self, regions: tuple[FoodRegion, ...]) -> None:
        self.regions = regions

    def detect(self, image: Image.Image) -> tuple[FoodRegion, ...]:
        return self.regions


class RecordingClassifier:
    def __init__(self, predictions: tuple[FoodRecognition, ...]) -> None:
        self.predictions = predictions
        self.image_sizes: list[tuple[int, int]] = []

    def predict(self, image: Image.Image) -> tuple[FoodRecognition, ...]:
        self.image_sizes.append(image.size)
        return self.predictions


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


def test_hugging_face_detector_normalizes_and_clamps_regions() -> None:
    detector = FakePipelineFoodRegionDetector(
        [
            {
                "label": "food",
                "score": 1.2,
                "box": {"xmin": -5, "ymin": 10, "xmax": 250, "ymax": 100},
            },
        ]
    )

    regions = detector.detect(_synthetic_image())

    assert regions == (
        FoodRegion(
            confidence=1.0,
            bounding_box=BoundingBox(left=0.0, top=10.0, right=224.0, bottom=100.0),
            label="food",
        ),
    )


def test_hugging_face_detector_runs_one_combined_prompt() -> None:
    processor = FakeGroundingDinoProcessor()
    detector = RuntimeFoodRegionDetector(
        processor=processor,
        model=FakeGroundingDinoModel(),
    )

    regions = detector.detect(_synthetic_image())

    assert processor.text == [["food", "rice", "chicken"]]
    assert processor.target_sizes == [(224, 224)]
    assert regions == (
        FoodRegion(
            confidence=0.77,
            bounding_box=BoundingBox(left=10, top=20, right=110, bottom=120),
            label="rice",
        ),
    )


def test_hugging_face_detector_resolves_combined_text_label_to_candidate() -> None:
    detector = RuntimeFoodRegionDetector(
        processor=FakeGroundingDinoProcessor(text_label="rice chicken"),
        model=FakeGroundingDinoModel(),
    )

    regions = detector.detect(_synthetic_image())

    assert regions[0].label == "rice"


@pytest.mark.parametrize(
    "prediction",
    [
        {"score": "0.9", "box": {"xmin": 0, "ymin": 0, "xmax": 10, "ymax": 10}},
        {"score": 0.9, "box": {"xmin": 0, "ymin": 0, "xmax": 0, "ymax": 10}},
        {"score": 0.9, "box": None},
        "not-a-dict",
    ],
)
def test_hugging_face_detector_rejects_invalid_regions(prediction: object) -> None:
    detector = FakePipelineFoodRegionDetector([prediction])

    with pytest.raises(ValueError, match="invalid_detector_prediction"):
        detector.detect(_synthetic_image())


def test_multi_region_model_classifies_distinct_crops_and_combines_confidence() -> None:
    classifier = RecordingClassifier((FoodRecognition(label="fried rice", confidence=0.81),))
    model = MultiRegionFoodRecognitionModel(
        detector=StubDetector(
            (
                _region(0, 0, 100, 100, confidence=0.72),
                _region(120, 20, 220, 180, confidence=0.64),
            )
        ),
        classifier=classifier,
        max_regions=8,
        nms_threshold=0.6,
    )

    predictions = model.predict(_synthetic_image())

    assert classifier.image_sizes == [(100, 100), (100, 160)]
    assert [prediction.confidence for prediction in predictions] == [0.72, 0.64]
    assert [prediction.bounding_box for prediction in predictions] == [
        BoundingBox(left=0, top=0, right=100, bottom=100),
        BoundingBox(left=120, top=20, right=220, bottom=180),
    ]


def test_multi_region_model_uses_specific_detector_label_without_classifier() -> None:
    classifier = RecordingClassifier((FoodRecognition(label="wrong dish", confidence=0.99),))
    model = MultiRegionFoodRecognitionModel(
        detector=StubDetector(
            (
                FoodRegion(
                    confidence=0.68,
                    bounding_box=BoundingBox(left=0, top=0, right=100, bottom=100),
                    label="Fried Rice",
                ),
            )
        ),
        classifier=classifier,
        max_regions=8,
        nms_threshold=0.6,
    )

    predictions = model.predict(_synthetic_image())

    assert predictions == (
        FoodRecognition(
            label="fried rice",
            confidence=0.68,
            bounding_box=BoundingBox(left=0, top=0, right=100, bottom=100),
        ),
    )
    assert classifier.image_sizes == []


def test_multi_region_model_suppresses_overlapping_regions_and_honors_limit() -> None:
    classifier = RecordingClassifier((FoodRecognition(label="pizza", confidence=0.9),))
    model = MultiRegionFoodRecognitionModel(
        detector=StubDetector(
            (
                _region(0, 0, 100, 100, confidence=0.9),
                _region(5, 5, 100, 100, confidence=0.8),
                _region(120, 0, 220, 100, confidence=0.7),
                _region(0, 120, 100, 220, confidence=0.6),
            )
        ),
        classifier=classifier,
        max_regions=2,
        nms_threshold=0.6,
    )

    predictions = model.predict(_synthetic_image())

    assert len(predictions) == 2
    assert classifier.image_sizes == [(100, 100), (100, 100)]


def test_multi_region_model_falls_back_to_full_image_without_regions() -> None:
    classifier = RecordingClassifier((FoodRecognition(label="salad", confidence=0.51),))
    model = MultiRegionFoodRecognitionModel(
        detector=StubDetector(()),
        classifier=classifier,
        max_regions=8,
        nms_threshold=0.6,
    )

    predictions = model.predict(_synthetic_image())

    assert predictions == (FoodRecognition(label="salad", confidence=0.51),)
    assert classifier.image_sizes == [(224, 224)]


def _synthetic_image() -> Image.Image:
    return Image.new("RGB", (224, 224), color=(210, 48, 48))


def _region(
    left: float,
    top: float,
    right: float,
    bottom: float,
    *,
    confidence: float,
) -> FoodRegion:
    return FoodRegion(
        confidence=confidence,
        bounding_box=BoundingBox(left=left, top=top, right=right, bottom=bottom),
    )
