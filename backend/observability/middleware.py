from __future__ import annotations

import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from observability.events import report_application_error
from observability.metrics import (
    API_LATENCY_SECONDS,
    API_REQUESTS_TOTAL,
    HTTP_ERRORS_TOTAL,
    increment_metric,
    observe_metric,
)


class RequestObservabilityMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        started_at = time.monotonic()
        response = self.get_response(request)
        if request.path_info.startswith("/api/"):
            method = request.method or "UNKNOWN"
            tags = {
                "method": method,
                "route": _route_name(request),
                "status_class": f"{response.status_code // 100}xx",
            }
            increment_metric(API_REQUESTS_TOTAL, tags=tags)
            observe_metric(API_LATENCY_SECONDS, time.monotonic() - started_at, tags=tags)
            if response.status_code >= 400:
                increment_metric(
                    HTTP_ERRORS_TOTAL,
                    tags={
                        "method": method,
                        "route": tags["route"],
                        "status_code": str(response.status_code),
                    },
                )
        return response

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        if request.path_info.startswith("/api/"):
            report_application_error(
                event_name="unhandled_api_exception",
                error=exception,
                metadata={
                    "method": request.method or "UNKNOWN",
                    "route": _route_name(request),
                },
                correlation_id=str(getattr(request, "correlation_id", "")),
            )
        return None


def _route_name(request: HttpRequest) -> str:
    resolver_match = request.resolver_match
    if resolver_match is None:
        return "unmatched"
    route_name = resolver_match.view_name or resolver_match.url_name or "unnamed"
    return str(route_name)[:80]
