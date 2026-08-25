from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.utils.module_loading import import_string

from observability.context import get_correlation_id

API_REQUESTS_TOTAL = "api_requests_total"
API_LATENCY_SECONDS = "api_latency_seconds"
HTTP_ERRORS_TOTAL = "http_errors_total"
SCAN_PROCESSING_SECONDS = "scan_processing_seconds"
VISION_REQUESTS_TOTAL = "vision_requests_total"
VISION_FAILURES_TOTAL = "vision_failures_total"
AI_PROVIDER_LATENCY_SECONDS = "ai_provider_latency_seconds"
CELERY_QUEUE_LATENCY_SECONDS = "celery_queue_latency_seconds"
CELERY_ENQUEUED_AT_HEADER = "foodai_enqueued_at"

_ALLOWED_TAGS = {
    API_REQUESTS_TOTAL: frozenset({"method", "route", "status_class"}),
    API_LATENCY_SECONDS: frozenset({"method", "route", "status_class"}),
    HTTP_ERRORS_TOTAL: frozenset({"method", "route", "status_code"}),
    SCAN_PROCESSING_SECONDS: frozenset({"outcome"}),
    VISION_REQUESTS_TOTAL: frozenset({"outcome"}),
    VISION_FAILURES_TOTAL: frozenset({"failure_code"}),
    AI_PROVIDER_LATENCY_SECONDS: frozenset({"assistant", "provider", "outcome"}),
    CELERY_QUEUE_LATENCY_SECONDS: frozenset({"task", "outcome"}),
}
_TAG_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")


class MetricsBackend(Protocol):
    def increment(self, name: str, value: float, tags: Mapping[str, str]) -> None: ...

    def observe(self, name: str, value: float, tags: Mapping[str, str]) -> None: ...


class NoopMetricsBackend:
    def increment(self, name: str, value: float, tags: Mapping[str, str]) -> None:
        return None

    def observe(self, name: str, value: float, tags: Mapping[str, str]) -> None:
        return None


@dataclass(frozen=True)
class MetricMeasurement:
    operation: str
    name: str
    value: float
    tags: Mapping[str, str]


class InMemoryMetricsBackend:
    def __init__(self) -> None:
        self.measurements: list[MetricMeasurement] = []

    def increment(self, name: str, value: float, tags: Mapping[str, str]) -> None:
        self.measurements.append(MetricMeasurement("increment", name, value, dict(tags)))

    def observe(self, name: str, value: float, tags: Mapping[str, str]) -> None:
        self.measurements.append(MetricMeasurement("observe", name, value, dict(tags)))


class StructuredLogMetricsBackend:
    def __init__(self) -> None:
        self._logger = logging.getLogger("foodai.business_metrics")

    def increment(self, name: str, value: float, tags: Mapping[str, str]) -> None:
        self._emit(name=name, metric_type="counter", value=value, tags=tags)

    def observe(self, name: str, value: float, tags: Mapping[str, str]) -> None:
        self._emit(name=name, metric_type="histogram", value=value, tags=tags)

    def _emit(
        self,
        *,
        name: str,
        metric_type: str,
        value: float,
        tags: Mapping[str, str],
    ) -> None:
        self._logger.info(
            name,
            extra={
                "event_category": "business_metric",
                "event_name": name,
                "correlation_id": get_correlation_id(),
                "safe_metadata": {
                    "metric_type": metric_type,
                    "value": value,
                    "tags": dict(tags),
                },
            },
        )


_metrics_backend: MetricsBackend | None = None
_metrics_error_logger = logging.getLogger("foodai.application")


def get_metrics_backend() -> MetricsBackend:
    global _metrics_backend
    if _metrics_backend is None:
        backend_class = import_string(settings.OBSERVABILITY_METRICS_BACKEND)
        _metrics_backend = backend_class()
    return _metrics_backend


def increment_metric(name: str, *, tags: Mapping[str, str], value: float = 1.0) -> None:
    validated_tags = _validate_tags(name=name, tags=tags)
    try:
        get_metrics_backend().increment(name, float(value), validated_tags)
    except Exception as exc:
        _log_metrics_backend_failure(metric_name=name, operation="increment", error=exc)


def observe_metric(name: str, value: float, *, tags: Mapping[str, str]) -> None:
    validated_tags = _validate_tags(name=name, tags=tags)
    try:
        get_metrics_backend().observe(name, max(0.0, float(value)), validated_tags)
    except Exception as exc:
        _log_metrics_backend_failure(metric_name=name, operation="observe", error=exc)


def call_with_ai_provider_metrics[T](
    *,
    assistant: str,
    provider: str,
    operation: Callable[[], T],
) -> T:
    started_at = time.monotonic()
    outcome = "success"
    try:
        return operation()
    except Exception:
        outcome = "error"
        raise
    finally:
        observe_metric(
            AI_PROVIDER_LATENCY_SECONDS,
            time.monotonic() - started_at,
            tags={"assistant": assistant, "provider": provider, "outcome": outcome},
        )


@contextmanager
def override_metrics_backend(backend: MetricsBackend) -> Iterator[None]:
    global _metrics_backend
    previous_backend = _metrics_backend
    _metrics_backend = backend
    try:
        yield
    finally:
        _metrics_backend = previous_backend


def _validate_tags(*, name: str, tags: Mapping[str, str]) -> dict[str, str]:
    allowed_tags = _ALLOWED_TAGS.get(name)
    if allowed_tags is None:
        raise ValueError("unsupported_metric")
    if not set(tags).issubset(allowed_tags):
        raise ValueError("unsupported_metric_tag")

    normalized: dict[str, str] = {}
    for key, raw_value in sorted(tags.items()):
        value = str(raw_value).strip()
        normalized[key] = value if _TAG_VALUE_PATTERN.fullmatch(value) else "invalid"
    return normalized


def _log_metrics_backend_failure(
    *,
    metric_name: str,
    operation: str,
    error: BaseException,
) -> None:
    _metrics_error_logger.error(
        "metrics_backend_failed",
        extra={
            "event_category": "application_error",
            "event_name": "metrics_backend_failed",
            "correlation_id": get_correlation_id(),
            "safe_metadata": {
                "metric_name": metric_name,
                "operation": operation,
                "error_type": f"{type(error).__module__}.{type(error).__qualname__}",
            },
        },
    )
