from __future__ import annotations

import argparse
import os
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = ROOT / "scripts/local_test.py"


@pytest.mark.parametrize("host", ["localhost", "192.168.0.148", "10.0.0.2", "172.16.1.2"])
def test_local_launcher_accepts_only_explicit_local_destinations(host: str) -> None:
    assert runpy.run_path(str(LAUNCHER))["validate_host"](host) == host


@pytest.mark.parametrize("host", ["0.0.0.0", "8.8.8.8", "::", "example.com", "localhost,evil"])
def test_local_launcher_refuses_public_or_wildcard_hosts(host: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        runpy.run_path(str(LAUNCHER))["validate_host"](host)


def test_local_compose_keeps_mail_private_and_auth_protected() -> None:
    class ComposeLoader(yaml.SafeLoader):
        pass

    def override(loader: ComposeLoader, node: yaml.SequenceNode) -> list[Any]:
        return loader.construct_sequence(node)

    ComposeLoader.add_constructor("!override", override)
    compose = yaml.load((ROOT / "infra/compose.local-test.yml").read_text(), Loader=ComposeLoader)
    mail = compose["services"]["mailpit"]
    assert mail["ports"] == ["127.0.0.1:8025:8025"]
    assert mail["tmpfs"] == ["/tmp"]
    assert "env_file" not in mail
    env = compose["services"]["backend"]["environment"]
    assert env["DJANGO_EMAIL_BACKEND"] == "django.core.mail.backends.smtp.EmailBackend"
    assert env["DJANGO_EMAIL_HOST"] == "mailpit"
    assert env["DJANGO_EMAIL_HOST_PASSWORD"] == ""
    assert env["DJANGO_CORS_ALLOW_CREDENTIALS"] == "true"
    assert "*" not in env["DJANGO_ALLOWED_HOSTS"]
    assert env["DJANGO_CSRF_TRUSTED_ORIGINS"] == "http://${FOODAI_TEST_HOST:-localhost}:3000"
    assert env["AI_COACH_PROVIDER"] == "mock"


def test_local_launcher_stop_does_not_delete_volumes(monkeypatch: pytest.MonkeyPatch) -> None:
    launcher = runpy.run_path(str(LAUNCHER))
    invocations: list[Any] = []
    monkeypatch.setattr(sys, "argv", [str(LAUNCHER), "stop", "--host", "localhost"])
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: invocations.append(args[0]))
    launcher["main"]()
    assert invocations[0][-1] == "stop"
    assert "down" not in invocations[0] and "-v" not in invocations[0]


def settings_process(extra: dict[str, str], code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        env=os.environ | {"PYTHONPATH": str(ROOT / "backend")} | extra,
        capture_output=True,
        text=True,
        check=False,
    )


def test_smtp_environment_is_connected_to_django_settings() -> None:
    result = settings_process(
        {
            "DJANGO_EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "DJANGO_EMAIL_HOST": "smtp.example.test",
            "DJANGO_EMAIL_PORT": "587",
            "DJANGO_EMAIL_HOST_USER": "test-smtp-user",
            "DJANGO_EMAIL_HOST_PASSWORD": "test-only-password",
            "DJANGO_EMAIL_USE_TLS": "true",
            "DJANGO_EMAIL_USE_SSL": "false",
            "DJANGO_EMAIL_TIMEOUT_SECONDS": "5",
        },
        "from config.settings import base as s; "
        "assert s.EMAIL_HOST == 'smtp.example.test'; "
        "assert s.EMAIL_PORT == 587; assert s.EMAIL_USE_TLS and not s.EMAIL_USE_SSL; "
        "assert s.EMAIL_HOST_USER == 'test-smtp-user'; "
        "assert s.EMAIL_HOST_PASSWORD == 'test-only-password'; assert s.EMAIL_TIMEOUT == 5",
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "invalid",
    [
        {"DJANGO_EMAIL_USE_TLS": "true", "DJANGO_EMAIL_USE_SSL": "true"},
        {"DJANGO_EMAIL_TIMEOUT_SECONDS": "0"},
    ],
)
def test_smtp_configuration_rejects_ambiguous_tls_or_no_timeout(invalid: dict[str, str]) -> None:
    result = settings_process(invalid, "from config.settings import base")
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
