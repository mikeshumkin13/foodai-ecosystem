from __future__ import annotations

from contextvars import ContextVar, Token

_correlation_id: ContextVar[str] = ContextVar("foodai_correlation_id", default="")


def bind_correlation_id(correlation_id: str) -> Token[str]:
    return _correlation_id.set(correlation_id)


def reset_correlation_id(token: Token[str]) -> None:
    _correlation_id.reset(token)


def get_correlation_id() -> str:
    return _correlation_id.get()
