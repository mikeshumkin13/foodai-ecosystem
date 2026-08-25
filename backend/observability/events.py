from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from observability.context import get_correlation_id
from observability.error_monitoring import build_error_report, get_error_monitoring_backend
from observability.sanitization import sanitize_metadata

application_logger = logging.getLogger("foodai.application")
security_logger = logging.getLogger("foodai.security")


def report_application_error(
    *,
    event_name: str,
    error: BaseException,
    metadata: Mapping[str, Any] | None = None,
    correlation_id: str = "",
) -> None:
    report = build_error_report(
        event_name=event_name,
        error=error,
        metadata=metadata,
        correlation_id=correlation_id,
    )
    try:
        get_error_monitoring_backend().capture(report)
    except Exception as monitoring_error:
        application_logger.error(
            "error_monitoring_backend_failed",
            extra={
                "event_category": "application_error",
                "event_name": "error_monitoring_backend_failed",
                "correlation_id": report.correlation_id,
                "safe_metadata": {
                    "error_type": (
                        f"{type(monitoring_error).__module__}."
                        f"{type(monitoring_error).__qualname__}"
                    ),
                },
            },
        )
    application_logger.error(
        event_name,
        extra={
            "event_category": "application_error",
            "event_name": event_name,
            "correlation_id": report.correlation_id,
            "safe_metadata": {
                **dict(report.metadata),
                "error_type": report.error_type,
            },
        },
    )


def log_security_event(
    *,
    event_name: str,
    metadata: Mapping[str, Any] | None = None,
    correlation_id: str = "",
) -> None:
    security_logger.info(
        event_name,
        extra={
            "event_category": "security_event",
            "event_name": event_name,
            "correlation_id": correlation_id or get_correlation_id(),
            "safe_metadata": sanitize_metadata(metadata),
        },
    )
