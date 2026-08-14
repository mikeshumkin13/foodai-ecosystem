from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from pytest import MonkeyPatch

from vision_service.inference import FoodRecognition, get_food_recognition_model
from vision_service.main import app


class StubFoodRecognitionModel:
    def __init__(self, predictions: tuple[FoodRecognition, ...]) -> None:
        self.predictions = predictions

    def predict(self, image: Image.Image) -> tuple[FoodRecognition, ...]:
        assert image.mode == "RGB"
        return self.predictions


class InvalidFoodRecognitionModel:
    def predict(self, image: Image.Image) -> tuple[FoodRecognition, ...]:
        raise ValueError("invalid_model_prediction")


def _valid_analyze_payload(tmp_path: Path, monkeypatch: MonkeyPatch) -> dict[str, object]:
    image_path = tmp_path / "food-scans" / "00" / "00000000-0000-4000-8000-000000000001.jpg"
    image_path.parent.mkdir(parents=True)
    Image.new("RGB", (224, 224), color=(220, 48, 48)).save(image_path, format="JPEG")
    image_bytes = image_path.read_bytes()
    monkeypatch.setenv("VISION_LOCAL_PRIVATE_MEDIA_ROOT", str(tmp_path))

    return {
        "object_reference": {
            "scan_id": "00000000-0000-4000-8000-000000000001",
            "storage_backend": "local",
            "object_key": "food-scans/00/00000000-0000-4000-8000-000000000001.jpg",
            "content_type": "image/jpeg",
            "checksum_sha256": hashlib.sha256(image_bytes).hexdigest(),
        }
    }


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_uses_food_recognition_model(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    app.dependency_overrides[get_food_recognition_model] = lambda: StubFoodRecognitionModel(
        (FoodRecognition(label="pizza", confidence=0.42),),
    )
    client = TestClient(app)

    try:
        response = client.post("/v1/analyze", json=_valid_analyze_payload(tmp_path, monkeypatch))
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "label": "pizza",
                "confidence": 0.42,
            }
        ]
    }


def test_analyze_rejects_invalid_object_reference_contract(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    client = TestClient(app)
    payload = _valid_analyze_payload(tmp_path, monkeypatch)
    object_reference = payload["object_reference"]
    assert isinstance(object_reference, dict)
    object_reference["checksum_sha256"] = "not-a-sha256"

    response = client.post("/v1/analyze", json=payload)

    assert response.status_code == 422


def test_analyze_rejects_path_traversal_object_key(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    client = TestClient(app)
    payload = _valid_analyze_payload(tmp_path, monkeypatch)
    object_reference = payload["object_reference"]
    assert isinstance(object_reference, dict)
    object_reference["object_key"] = "../private/photo.jpg"

    response = client.post("/v1/analyze", json=payload)

    assert response.status_code == 422


def test_analyze_rejects_checksum_mismatch(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    app.dependency_overrides[get_food_recognition_model] = lambda: StubFoodRecognitionModel(
        (FoodRecognition(label="pizza", confidence=0.42),),
    )
    client = TestClient(app)
    payload = _valid_analyze_payload(tmp_path, monkeypatch)
    object_reference = payload["object_reference"]
    assert isinstance(object_reference, dict)
    object_reference["checksum_sha256"] = "b" * 64

    try:
        response = client.post("/v1/analyze", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"] == {"code": "image_checksum_mismatch"}


def test_analyze_normalizes_invalid_model_response(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    app.dependency_overrides[get_food_recognition_model] = lambda: InvalidFoodRecognitionModel()
    client = TestClient(app)

    try:
        response = client.post("/v1/analyze", json=_valid_analyze_payload(tmp_path, monkeypatch))
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == {"code": "vision_model_invalid_response"}
