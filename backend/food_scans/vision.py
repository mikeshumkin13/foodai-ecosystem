from __future__ import annotations

from typing import Protocol

from food_scans.models import FoodScan
from integrations.vision.client import (
    VisionAnalyzeResult,
    VisionObjectReference,
    get_vision_client,
)


class VisionAnalyzer(Protocol):
    def analyze_object(self, object_reference: VisionObjectReference) -> VisionAnalyzeResult:
        ...


def build_food_scan_vision_reference(food_scan: FoodScan) -> VisionObjectReference:
    return VisionObjectReference(
        scan_id=food_scan.id,
        storage_backend=food_scan.storage_backend,
        object_key=food_scan.object_key,
        content_type=food_scan.content_type,
        checksum_sha256=food_scan.checksum_sha256,
    )


def analyze_food_scan(
    food_scan: FoodScan,
    *,
    vision_client: VisionAnalyzer | None = None,
) -> VisionAnalyzeResult:
    client = vision_client or get_vision_client()
    return client.analyze_object(build_food_scan_vision_reference(food_scan))
