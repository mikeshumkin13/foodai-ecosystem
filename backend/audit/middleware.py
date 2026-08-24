from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponse

CORRELATION_ID_HEADER = "X-Request-ID"
ALTERNATE_CORRELATION_ID_HEADER = "X-Correlation-ID"

_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")


class CorrelationIdMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = resolve_correlation_id(
            request.headers.get(CORRELATION_ID_HEADER)
            or request.headers.get(ALTERNATE_CORRELATION_ID_HEADER)
        )
        request.correlation_id = correlation_id  # type: ignore[attr-defined]
        response = self.get_response(request)
        response[CORRELATION_ID_HEADER] = correlation_id
        return response


def resolve_correlation_id(raw_correlation_id: Any) -> str:
    if isinstance(raw_correlation_id, str):
        candidate = raw_correlation_id.strip()
        if _CORRELATION_ID_PATTERN.fullmatch(candidate):
            return candidate
    return uuid.uuid4().hex
