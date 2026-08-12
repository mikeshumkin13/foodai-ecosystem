from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlparse
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from integrations.vision.client import (
    VisionAnalyzeResult,
    VisionClient,
    VisionInvalidResponseError,
    VisionObjectReference,
    VisionTimeoutError,
    VisionUnavailableError,
)
from vision_service.main import app as vision_app


def _reference() -> VisionObjectReference:
    return VisionObjectReference(
        scan_id=UUID("00000000-0000-4000-8000-000000000001"),
        storage_backend="local",
        object_key="food-scans/00/00000000-0000-4000-8000-000000000001.jpg",
        content_type="image/jpeg",
        checksum_sha256="a" * 64,
    )


class _VisionAppBridge:
    def __init__(self) -> None:
        self._client = TestClient(vision_app)
        self.last_timeout: float | None = None
        self.last_payload: dict[str, object] | None = None

    def post(self, url: str, *, json: Mapping[str, object], timeout: float) -> httpx.Response:
        self.last_timeout = timeout
        self.last_payload = dict(json)
        parsed_url = urlparse(url)
        response = self._client.post(parsed_url.path, json=json)
        return httpx.Response(response.status_code, json=response.json())


def test_backend_client_contract_matches_fastapi_vision_service() -> None:
    bridge = _VisionAppBridge()
    client = VisionClient(
        base_url="http://vision.test",
        timeout_seconds=2.5,
        http_client=bridge,
    )

    result = client.analyze_object(_reference())

    assert isinstance(result, VisionAnalyzeResult)
    assert result.items[0].label == "rice"
    assert result.items[0].confidence == 0.92
    assert bridge.last_timeout == 2.5
    assert bridge.last_payload == {
        "object_reference": {
            "scan_id": "00000000-0000-4000-8000-000000000001",
            "storage_backend": "local",
            "object_key": "food-scans/00/00000000-0000-4000-8000-000000000001.jpg",
            "content_type": "image/jpeg",
            "checksum_sha256": "a" * 64,
        }
    }


def test_backend_client_raises_unavailable_for_vision_5xx() -> None:
    client = _client_with_response(httpx.Response(503, json={"detail": "unavailable"}))

    with pytest.raises(VisionUnavailableError):
        client.analyze_object(_reference())


def test_backend_client_raises_timeout_without_retrying() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.TimeoutException("vision timed out")

    client = VisionClient(
        base_url="http://vision.test",
        timeout_seconds=0.1,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(VisionTimeoutError):
        client.analyze_object(_reference())

    assert calls == 1


def test_backend_client_raises_unavailable_for_transport_error_without_retrying() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("connection refused")

    client = VisionClient(
        base_url="http://vision.test",
        timeout_seconds=0.1,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(VisionUnavailableError):
        client.analyze_object(_reference())

    assert calls == 1


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={"items": [{"label": "", "confidence": 0.92}]}),
        httpx.Response(200, json={"items": [{"label": "rice", "confidence": 1.2}]}),
        httpx.Response(200, json={"items": [{"label": "rice", "confidence": "0.92"}]}),
        httpx.Response(200, json={"result": []}),
        httpx.Response(200, content=b"not-json"),
        httpx.Response(422, json={"detail": []}),
    ],
)
def test_backend_client_raises_invalid_response_for_contract_mismatch(
    response: httpx.Response,
) -> None:
    client = _client_with_response(response)

    with pytest.raises(VisionInvalidResponseError):
        client.analyze_object(_reference())


def _client_with_response(response: httpx.Response) -> VisionClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            response.status_code,
            content=response.content,
            headers=response.headers,
            request=request,
        )

    return VisionClient(
        base_url="http://vision.test",
        timeout_seconds=1,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
