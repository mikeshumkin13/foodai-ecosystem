from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Protocol

from django.conf import settings
from django.utils.module_loading import import_string

from observability.context import get_correlation_id
from observability.sanitization import sanitize_metadata


@dataclass(frozen=True)
class ErrorReport:
    event_name: str
    error_type: str
    correlation_id: str
    metadata: Mapping[str, Any]


class ErrorMonitoringBackend(Protocol):
    def capture(self, report: ErrorReport) -> None: ...


class NoopErrorMonitoringBackend:
    def capture(self, report: ErrorReport) -> None:
        return None


_error_monitoring_backend: ErrorMonitoringBackend | None = None


def get_error_monitoring_backend() -> ErrorMonitoringBackend:
    global _error_monitoring_backend
    if _error_monitoring_backend is None:
        backend_class = import_string(settings.ERROR_MONITORING_BACKEND)
        _error_monitoring_backend = backend_class()
    return _error_monitoring_backend


def build_error_report(
    *,
    event_name: str,
    error: BaseException,
    metadata: Mapping[str, Any] | None = None,
    correlation_id: str = "",
) -> ErrorReport:
    return ErrorReport(
        event_name=event_name,
        error_type=f"{type(error).__module__}.{type(error).__qualname__}",
        correlation_id=correlation_id or get_correlation_id(),
        metadata=sanitize_metadata(metadata),
    )


@contextmanager
def override_error_monitoring_backend(backend: ErrorMonitoringBackend) -> Iterator[None]:
    global _error_monitoring_backend
    previous_backend = _error_monitoring_backend
    _error_monitoring_backend = backend
    try:
        yield
    finally:
        _error_monitoring_backend = previous_backend
