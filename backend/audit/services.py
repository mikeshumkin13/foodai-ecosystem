from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.http import HttpRequest

from accounts.models import User
from audit.middleware import resolve_correlation_id
from audit.models import AuditLog

REDACTED_VALUE = "[redacted]"

_SENSITIVE_KEY_PARTS = (
    "authorization",
    "conversation",
    "cookie",
    "csrf",
    "health",
    "image",
    "medical",
    "message",
    "object_key",
    "password",
    "photo",
    "secret",
    "session",
    "token",
)
_MAX_METADATA_DEPTH = 4
_MAX_MAPPING_KEYS = 50
_MAX_SEQUENCE_ITEMS = 50
_MAX_STRING_LENGTH = 256


@dataclass(frozen=True)
class AuditTarget:
    target_type: str
    target_id: str = ""


def record_audit_event(
    *,
    actor: User | None,
    action: AuditLog.Action | str,
    target_type: str,
    target_id: object = "",
    metadata: Mapping[str, Any] | None = None,
    request: HttpRequest | None = None,
    request_correlation_id: str | None = None,
) -> AuditLog:
    actor_id_snapshot = str(actor.pk) if actor is not None and actor.pk is not None else ""
    correlation_id = request_correlation_id or get_request_correlation_id(request)

    return AuditLog.objects.create(
        actor=actor,
        actor_id_snapshot=actor_id_snapshot[:255],
        action=str(action),
        target_type=str(target_type)[:120],
        target_id=str(target_id or "")[:255],
        metadata=sanitize_audit_metadata(metadata),
        request_correlation_id=correlation_id[:64],
    )


def record_support_access(
    *,
    actor: User | None,
    target_user_id: object,
    reason_code: str,
    request: HttpRequest | None = None,
) -> AuditLog:
    return record_audit_event(
        actor=actor,
        action=AuditLog.Action.SUPPORT_ACCESS,
        target_type="accounts.user",
        target_id=target_user_id,
        metadata={"reason_code": reason_code, "source": "support_tool"},
        request=request,
    )


def get_request_correlation_id(request: HttpRequest | None) -> str:
    if request is None:
        return ""

    candidate = getattr(request, "correlation_id", "")
    if isinstance(candidate, str) and candidate:
        return resolve_correlation_id(candidate)

    return resolve_correlation_id(
        request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
    )


def sanitize_audit_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    if metadata is None:
        return {}
    sanitized = _sanitize_mapping(metadata, depth=0)
    return sanitized if isinstance(sanitized, dict) else {}


def _sanitize_mapping(metadata: Mapping[str, Any], *, depth: int) -> dict[str, Any]:
    if depth >= _MAX_METADATA_DEPTH:
        return {"truncated": True}

    sanitized: dict[str, Any] = {}
    for key_index, (key, value) in enumerate(metadata.items()):
        if key_index >= _MAX_MAPPING_KEYS:
            sanitized["truncated"] = True
            break

        normalized_key = _normalize_key(key)
        if _is_sensitive_key(normalized_key):
            sanitized[normalized_key] = REDACTED_VALUE
            continue

        sanitized[normalized_key] = _sanitize_value(value, depth=depth + 1)

    return sanitized


def _sanitize_value(value: Any, *, depth: int) -> Any:
    if isinstance(value, Mapping):
        return _sanitize_mapping(value, depth=depth)
    if isinstance(value, str):
        return _truncate_string(value)
    if isinstance(value, uuid.UUID):
        return str(value)
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
    return _truncate_string(str(value))


def _normalize_key(key: Any) -> str:
    normalized = str(key).strip().lower().replace(" ", "_")
    if not normalized:
        return "unknown"
    return normalized[:120]


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def _truncate_string(value: str) -> str:
    if len(value) <= _MAX_STRING_LENGTH:
        return value
    return f"{value[: _MAX_STRING_LENGTH - 3]}..."
