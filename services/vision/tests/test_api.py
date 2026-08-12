from __future__ import annotations

from fastapi.testclient import TestClient

from vision_service.main import app


def _valid_analyze_payload() -> dict[str, object]:
    return {
        "object_reference": {
            "scan_id": "00000000-0000-4000-8000-000000000001",
            "storage_backend": "local",
            "object_key": "food-scans/00/00000000-0000-4000-8000-000000000001.jpg",
            "content_type": "image/jpeg",
            "checksum_sha256": "a" * 64,
        }
    }


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_returns_mock_food_detection_result() -> None:
    client = TestClient(app)

    response = client.post("/v1/analyze", json=_valid_analyze_payload())

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "label": "rice",
                "confidence": 0.92,
            }
        ]
    }


def test_analyze_rejects_invalid_object_reference_contract() -> None:
    client = TestClient(app)
    payload = _valid_analyze_payload()
    object_reference = payload["object_reference"]
    assert isinstance(object_reference, dict)
    object_reference["checksum_sha256"] = "not-a-sha256"

    response = client.post("/v1/analyze", json=payload)

    assert response.status_code == 422


def test_analyze_rejects_path_traversal_object_key() -> None:
    client = TestClient(app)
    payload = _valid_analyze_payload()
    object_reference = payload["object_reference"]
    assert isinstance(object_reference, dict)
    object_reference["object_key"] = "../private/photo.jpg"

    response = client.post("/v1/analyze", json=payload)

    assert response.status_code == 422
