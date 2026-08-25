from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

REDACTED_VALUE = "[redacted]"

_SENSITIVE_KEY_PARTS = (
    "authorization",
    "conversation",
    "cookie",
    "csrf",
    "email",
    "health",
    "image",
    "medical",
    "message",
    "object_key",
    "password",
    "photo",
    "prompt",
    "request_body",
    "response_body",
    "session",
    "token",
    "user_id",
    "actor_id",
    "target_id",
    "uuid",
)
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_BEARER_PATTERN = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(password|token|secret|api[_-]?key)=([^\s&]+)",
)
_MAX_DEPTH = 4
_MAX_MAPPING_KEYS = 30
_MAX_SEQUENCE_ITEMS = 20
_MAX_STRING_LENGTH = 256


def sanitize_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    if metadata is None:
        return {}
    return _sanitize_mapping(metadata, depth=0)


def sanitize_text(value: str) -> str:
    sanitized = _EMAIL_PATTERN.sub(REDACTED_VALUE, value)
    sanitized = _BEARER_PATTERN.sub(f"Bearer {REDACTED_VALUE}", sanitized)
    sanitized = _SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}={REDACTED_VALUE}",
        sanitized,
    )
    return _truncate(sanitized)


def _sanitize_mapping(metadata: Mapping[str, Any], *, depth: int) -> dict[str, Any]:
    if depth >= _MAX_DEPTH:
        return {"truncated": True}

    sanitized: dict[str, Any] = {}
    for index, (raw_key, value) in enumerate(metadata.items()):
        if index >= _MAX_MAPPING_KEYS:
            sanitized["truncated"] = True
            break
        key = _normalize_key(raw_key)
        sanitized[key] = (
            REDACTED_VALUE if _is_sensitive_key(key) else _sanitize_value(value, depth=depth + 1)
        )
    return sanitized


def _sanitize_value(value: Any, *, depth: int) -> Any:
    if isinstance(value, Mapping):
        return _sanitize_mapping(value, depth=depth)
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, Decimal):
        return str(value)
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, bytes | bytearray | memoryview):
        return REDACTED_VALUE
    if isinstance(value, Sequence):
        return [
            _sanitize_value(item, depth=depth + 1)
            for item in list(value)[:_MAX_SEQUENCE_ITEMS]
        ]
    return sanitize_text(str(value))


def _normalize_key(value: Any) -> str:
    normalized = str(value).strip().lower().replace(" ", "_")
    return (normalized or "unknown")[:120]


def _is_sensitive_key(key: str) -> bool:
    return any(part in key for part in _SENSITIVE_KEY_PARTS)


def _truncate(value: str) -> str:
    if len(value) <= _MAX_STRING_LENGTH:
        return value
    return f"{value[: _MAX_STRING_LENGTH - 3]}..."
