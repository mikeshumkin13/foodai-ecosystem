from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import httpx
from django.conf import settings


class SyncHTTPClient(Protocol):
    def post(self, url: str, *, json: Mapping[str, object], timeout: float) -> httpx.Response:
        ...


@dataclass(frozen=True)
class VisionObjectReference:
    scan_id: UUID
    storage_backend: str
    object_key: str
    content_type: str
    checksum_sha256: str

    def to_payload(self) -> dict[str, object]:
        return {
            "scan_id": str(self.scan_id),
            "storage_backend": self.storage_backend,
            "object_key": self.object_key,
            "content_type": self.content_type,
            "checksum_sha256": self.checksum_sha256,
        }


@dataclass(frozen=True)
class VisionDetectedItem:
    label: str
    confidence: float


@dataclass(frozen=True)
class VisionAnalyzeResult:
    items: tuple[VisionDetectedItem, ...]


class VisionClientError(Exception):
    code = "vision_error"


class VisionUnavailableError(VisionClientError):
    code = "vision_unavailable"


class VisionTimeoutError(VisionClientError):
    code = "vision_timeout"


class VisionInvalidResponseError(VisionClientError):
    code = "vision_invalid_response"


class VisionClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        http_client: SyncHTTPClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client

    def analyze_object(self, object_reference: VisionObjectReference) -> VisionAnalyzeResult:
        payload: dict[str, object] = {
            "object_reference": object_reference.to_payload(),
        }

        if self._http_client is not None:
            response = self._post(self._http_client, payload)
        else:
            with httpx.Client() as http_client:
                response = self._post(http_client, payload)

        if response.status_code >= 500:
            raise VisionUnavailableError
        if response.status_code != 200:
            raise VisionInvalidResponseError

        return _parse_analyze_response(response)

    def _post(self, http_client: SyncHTTPClient, payload: Mapping[str, object]) -> httpx.Response:
        try:
            return http_client.post(
                f"{self._base_url}/v1/analyze",
                json=payload,
                timeout=self._timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise VisionTimeoutError from exc
        except httpx.TransportError as exc:
            raise VisionUnavailableError from exc


def get_vision_client() -> VisionClient:
    return VisionClient(
        base_url=settings.VISION_SERVICE_URL,
        timeout_seconds=settings.VISION_SERVICE_TIMEOUT_SECONDS,
    )


def _parse_analyze_response(response: httpx.Response) -> VisionAnalyzeResult:
    try:
        data = response.json()
    except ValueError as exc:
        raise VisionInvalidResponseError from exc

    if not isinstance(data, dict):
        raise VisionInvalidResponseError

    items = data.get("items")
    if not isinstance(items, list):
        raise VisionInvalidResponseError

    detected_items = tuple(_parse_detected_item(item) for item in items)
    return VisionAnalyzeResult(items=detected_items)


def _parse_detected_item(item: Any) -> VisionDetectedItem:
    if not isinstance(item, dict):
        raise VisionInvalidResponseError

    label = item.get("label")
    confidence = item.get("confidence")
    if not isinstance(label, str) or not label:
        raise VisionInvalidResponseError
    if isinstance(confidence, bool) or not isinstance(confidence, int | float):
        raise VisionInvalidResponseError

    normalized_confidence = float(confidence)
    if normalized_confidence < 0 or normalized_confidence > 1:
        raise VisionInvalidResponseError

    return VisionDetectedItem(label=label, confidence=normalized_confidence)
