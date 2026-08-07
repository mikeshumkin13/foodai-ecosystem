from __future__ import annotations

import socket
from collections.abc import Iterator
from typing import Any

import pytest
from django.core.management import call_command
from django.test import override_settings

pytestmark = pytest.mark.django_db


class FakeRedisSocket:
    def __init__(self, responses: list[bytes]) -> None:
        self.responses = responses
        self.sent_commands: list[bytes] = []

    def __enter__(self) -> FakeRedisSocket:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def sendall(self, command: bytes) -> None:
        self.sent_commands.append(command)

    def recv(self, buffer_size: int) -> bytes:
        if not self.responses:
            return b""
        return self.responses.pop(0)


def test_wait_for_dependencies_passes_with_database_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    call_command("wait_for_dependencies", timeout=1, interval=0)

    assert "Dependencies are ready." in capsys.readouterr().out


def test_wait_for_dependencies_checks_redis(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_socket = FakeRedisSocket([b"+OK\r\n", b"+PONG\r\n"])

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float,
        *_args: Any,
        **_kwargs: Any,
    ) -> FakeRedisSocket:
        assert address == ("redis", 6379)
        assert timeout == 1.0
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    with override_settings(REDIS_URL="redis://:redis-password@redis:6379/0"):
        call_command("wait_for_dependencies", timeout=1, interval=0)

    assert "Dependencies are ready." in capsys.readouterr().out
    assert fake_socket.sent_commands == [
        b"*2\r\n$4\r\nAUTH\r\n$14\r\nredis-password\r\n",
        b"*1\r\n$4\r\nPING\r\n",
    ]


@pytest.fixture(autouse=True)
def _disable_sleep(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr("core.management.commands.wait_for_dependencies.sleep", lambda _: None)
    yield
