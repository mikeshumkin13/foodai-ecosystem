from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from observability.context import get_correlation_id
from observability.sanitization import sanitize_metadata, sanitize_text


class SafeJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        correlation_id = getattr(record, "correlation_id", "") or get_correlation_id()
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "category": getattr(record, "event_category", "application"),
            "event": getattr(record, "event_name", record.name),
            "correlation_id": sanitize_text(str(correlation_id)) if correlation_id else "",
            "message": sanitize_text(record.getMessage()),
            "metadata": sanitize_metadata(getattr(record, "safe_metadata", None)),
        }
        if record.exc_info and record.exc_info[0] is not None:
            payload["error_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
