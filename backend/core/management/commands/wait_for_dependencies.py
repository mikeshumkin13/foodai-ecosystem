from __future__ import annotations

import socket
from argparse import ArgumentParser
from time import monotonic, sleep
from typing import Any
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connections


class Command(BaseCommand):
    help = "Wait until database and Redis dependencies are ready."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--timeout", type=float, default=60.0)
        parser.add_argument("--interval", type=float, default=1.0)

    def handle(self, *args: Any, **options: Any) -> None:
        timeout = float(options["timeout"])
        interval = float(options["interval"])
        deadline = monotonic() + timeout
        last_error = "dependencies are not ready"

        while monotonic() < deadline:
            database_ready, database_error = self._database_ready()
            redis_ready, redis_error = self._redis_ready()

            if database_ready and redis_ready:
                self.stdout.write(self.style.SUCCESS("Dependencies are ready."))
                return None

            last_error = "; ".join(error for error in (database_error, redis_error) if error)
            sleep(interval)

        raise CommandError(f"Timed out waiting for dependencies: {last_error}")

    def _database_ready(self) -> tuple[bool, str]:
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
        except DatabaseError as exc:
            return False, f"database: {exc}"
        return True, ""

    def _redis_ready(self) -> tuple[bool, str]:
        redis_url = str(getattr(settings, "REDIS_URL", ""))
        if not redis_url:
            return True, ""

        parsed_url = urlparse(redis_url)
        host = parsed_url.hostname
        if host is None:
            return False, "redis: REDIS_URL host is missing"

        port = parsed_url.port or 6379
        password = unquote(parsed_url.password or "")

        try:
            with socket.create_connection((host, port), timeout=1.0) as redis_socket:
                if password:
                    auth_response = self._send_redis_command(redis_socket, "AUTH", password)
                    if not auth_response.startswith(b"+OK"):
                        return False, "redis: AUTH failed"

                ping_response = self._send_redis_command(redis_socket, "PING")
        except OSError as exc:
            return False, f"redis: {exc}"

        if not ping_response.startswith(b"+PONG"):
            return False, "redis: PING failed"

        return True, ""

    def _send_redis_command(self, redis_socket: socket.socket, *parts: str) -> bytes:
        encoded_parts = [part.encode("utf-8") for part in parts]
        command = f"*{len(encoded_parts)}\r\n".encode("ascii")
        for part in encoded_parts:
            command += f"${len(part)}\r\n".encode("ascii") + part + b"\r\n"

        redis_socket.sendall(command)
        return redis_socket.recv(1024)
