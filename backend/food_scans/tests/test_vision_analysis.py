from __future__ import annotations

import pytest

from accounts.tests.factories import make_user
from food_scans.models import FoodScan
from food_scans.vision import analyze_food_scan, build_food_scan_vision_reference
from integrations.vision.client import (
    VisionAnalyzeResult,
    VisionDetectedItem,
    VisionObjectReference,
)

pytestmark = pytest.mark.django_db


class _FakeVisionClient:
    def __init__(self) -> None:
        self.reference: VisionObjectReference | None = None

    def analyze_object(self, object_reference: VisionObjectReference) -> VisionAnalyzeResult:
        self.reference = object_reference
        return VisionAnalyzeResult(items=(VisionDetectedItem(label="rice", confidence=0.92),))


def test_food_scan_builds_minimal_internal_vision_reference() -> None:
    food_scan = _make_food_scan()

    reference = build_food_scan_vision_reference(food_scan)

    assert reference.scan_id == food_scan.id
    assert reference.storage_backend == "local"
    assert reference.object_key == "food-scans/test/photo.jpg"
    assert reference.content_type == "image/jpeg"
    assert reference.checksum_sha256 == "b" * 64


def test_food_scan_analysis_uses_vision_client_abstraction() -> None:
    food_scan = _make_food_scan()
    fake_client = _FakeVisionClient()

    result = analyze_food_scan(food_scan, vision_client=fake_client)

    assert result.items[0].label == "rice"
    assert fake_client.reference == build_food_scan_vision_reference(food_scan)


def _make_food_scan() -> FoodScan:
    return FoodScan.objects.create(
        user=make_user(),
        storage_backend="local",
        object_key="food-scans/test/photo.jpg",
        image_format=FoodScan.ImageFormat.JPEG,
        content_type="image/jpeg",
        uploaded_byte_size=128,
        stored_byte_size=120,
        width=12,
        height=10,
        checksum_sha256="b" * 64,
    )
