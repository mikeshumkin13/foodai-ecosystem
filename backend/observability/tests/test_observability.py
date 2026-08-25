from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import pytest
from django.http import HttpResponse
from django.test import Client, RequestFactory
from django.urls import reverse

from observability.context import get_correlation_id
from observability.error_monitoring import (
    ErrorReport,
    override_error_monitoring_backend,
)
from observability.events import log_security_event, report_application_error
from observability.logging import SafeJsonFormatter
from observability.metrics import (
    AI_PROVIDER_LATENCY_SECONDS,
    API_LATENCY_SECONDS,
    API_REQUESTS_TOTAL,
    HTTP_ERRORS_TOTAL,
    InMemoryMetricsBackend,
    call_with_ai_provider_metrics,
    increment_metric,
    override_metrics_backend,
)
from observability.middleware import RequestObservabilityMiddleware


@dataclass
class RecordingErrorMonitoringBackend:
    reports: list[ErrorReport] = field(default_factory=list)

    def capture(self, report: ErrorReport) -> None:
        self.reports.append(report)


class FailingMetricsBackend:
    def increment(self, name: str, value: float, tags: Mapping[str, str]) -> None:
        raise RuntimeError("private metrics transport failure")

    def observe(self, name: str, value: float, tags: Mapping[str, str]) -> None:
        raise RuntimeError("private metrics transport failure")


class FailingErrorMonitoringBackend:
    def capture(self, report: ErrorReport) -> None:
        raise RuntimeError("private error transport failure")


def test_safe_json_formatter_redacts_sensitive_fields_and_message_values() -> None:
    formatter = SafeJsonFormatter()
    record = logging.LogRecord(
        name="foodai.application",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="request failed for private@example.com token=plain-token",
        args=(),
        exc_info=None,
    )
    record.__dict__["event_category"] = "application_error"
    record.__dict__["event_name"] = "safe_test_event"
    record.__dict__["safe_metadata"] = {
        "component": "test",
        "food_photo": b"private-image-bytes",
        "health_profile": {"mass_kg": 80},
        "authorization": "Bearer private-token",
    }

    payload = json.loads(formatter.format(record))
    serialized_payload = json.dumps(payload)

    assert payload["category"] == "application_error"
    assert payload["event"] == "safe_test_event"
    assert payload["metadata"]["component"] == "test"
    assert payload["metadata"]["food_photo"] == "[redacted]"
    assert payload["metadata"]["health_profile"] == "[redacted]"
    assert "private@example.com" not in serialized_payload
    assert "plain-token" not in serialized_payload
    assert "private-image-bytes" not in serialized_payload


def test_request_middleware_records_api_latency_and_http_error_rate_without_raw_url() -> None:
    backend = InMemoryMetricsBackend()
    client = Client()

    with override_metrics_backend(backend):
        health_response = client.get(reverse("health"), HTTP_X_REQUEST_ID="request-metrics-1")
        missing_response = client.get("/api/v1/not-found/?email=private@example.com")

    assert health_response.status_code == 200
    assert health_response["X-Request-ID"] == "request-metrics-1"
    assert missing_response.status_code == 404
    metric_names = [measurement.name for measurement in backend.measurements]
    assert metric_names.count(API_REQUESTS_TOTAL) == 2
    assert metric_names.count(API_LATENCY_SECONDS) == 2
    assert metric_names.count(HTTP_ERRORS_TOTAL) == 1
    assert all("private@example.com" not in str(item) for item in backend.measurements)
    assert all("not-found" not in str(item) for item in backend.measurements)
    assert get_correlation_id() == ""


def test_application_error_monitor_receives_safe_report_without_exception_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = RequestFactory().get("/api/v1/private/?token=raw-token")
    request.correlation_id = "request-error-1"  # type: ignore[attr-defined]
    error_backend = RecordingErrorMonitoringBackend()
    logged_events: list[dict[str, Any]] = []

    def capture_log(*args: Any, **kwargs: Any) -> None:
        logged_events.append(kwargs["extra"])

    monkeypatch.setattr("observability.events.application_logger.error", capture_log)
    middleware = RequestObservabilityMiddleware(lambda _request: HttpResponse())

    with override_error_monitoring_backend(error_backend):
        middleware.process_exception(
            request,
            RuntimeError("private@example.com password=unsafe-value"),
        )

    assert len(error_backend.reports) == 1
    report = error_backend.reports[0]
    assert report.event_name == "unhandled_api_exception"
    assert report.error_type == "builtins.RuntimeError"
    assert report.correlation_id == "request-error-1"
    assert report.metadata == {"method": "GET", "route": "unmatched"}
    assert "private@example.com" not in str(report)
    assert "unsafe-value" not in str(report)
    assert logged_events[0]["event_category"] == "application_error"


def test_security_events_are_separate_and_sensitive_metadata_is_redacted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logged_events: list[dict[str, Any]] = []

    def capture_log(*args: Any, **kwargs: Any) -> None:
        logged_events.append(kwargs["extra"])

    monkeypatch.setattr("observability.events.security_logger.info", capture_log)

    log_security_event(
        event_name="support_access",
        metadata={"target_type": "accounts.user", "food_photo": "private-photo"},
        correlation_id="security-event-1",
    )

    assert logged_events == [
        {
            "event_category": "security_event",
            "event_name": "support_access",
            "correlation_id": "security-event-1",
            "safe_metadata": {
                "target_type": "accounts.user",
                "food_photo": "[redacted]",
            },
        }
    ]


def test_business_metrics_reject_unknown_or_sensitive_tags() -> None:
    backend = InMemoryMetricsBackend()

    with override_metrics_backend(backend):
        with pytest.raises(ValueError, match="unsupported_metric_tag"):
            increment_metric(
                API_REQUESTS_TOTAL,
                tags={
                    "method": "GET",
                    "route": "health",
                    "status_class": "2xx",
                    "photo": "private-image",
                },
            )

    assert backend.measurements == []


def test_ai_provider_latency_records_success_and_error_without_provider_payload() -> None:
    backend = InMemoryMetricsBackend()

    with override_metrics_backend(backend):
        result = call_with_ai_provider_metrics(
            assistant="nutrition",
            provider="mock",
            operation=lambda: "provider-response",
        )
        with pytest.raises(RuntimeError, match="private provider payload"):
            call_with_ai_provider_metrics(
                assistant="wellbeing",
                provider="mock",
                operation=lambda: _raise_provider_error(),
            )

    assert result == "provider-response"
    measurements = [
        measurement
        for measurement in backend.measurements
        if measurement.name == AI_PROVIDER_LATENCY_SECONDS
    ]
    assert [measurement.tags["outcome"] for measurement in measurements] == [
        "success",
        "error",
    ]
    assert "provider-response" not in str(measurements)
    assert "private provider payload" not in str(measurements)


def test_telemetry_backend_failures_do_not_change_business_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logged_events: list[dict[str, Any]] = []

    def capture_log(*args: Any, **kwargs: Any) -> None:
        logged_events.append(kwargs["extra"])

    monkeypatch.setattr("observability.events.application_logger.error", capture_log)
    monkeypatch.setattr("observability.metrics._metrics_error_logger.error", capture_log)

    with override_metrics_backend(FailingMetricsBackend()):
        increment_metric(
            API_REQUESTS_TOTAL,
            tags={"method": "GET", "route": "health", "status_class": "2xx"},
        )
    with override_error_monitoring_backend(FailingErrorMonitoringBackend()):
        report_application_error(
            event_name="test_application_error",
            error=RuntimeError("private original error"),
            metadata={"component": "test"},
        )

    assert [event["event_name"] for event in logged_events] == [
        "metrics_backend_failed",
        "error_monitoring_backend_failed",
        "test_application_error",
    ]
    assert "private metrics transport failure" not in str(logged_events)
    assert "private error transport failure" not in str(logged_events)
    assert "private original error" not in str(logged_events)


def _raise_provider_error() -> None:
    raise RuntimeError("private provider payload")
