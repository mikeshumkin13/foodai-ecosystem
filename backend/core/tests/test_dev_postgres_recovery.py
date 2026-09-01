from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RECOVERY_SCRIPT = PROJECT_ROOT / "scripts" / "postgres-volume-recovery.sh"


def test_compose_uses_versioned_postgres_volume_by_default() -> None:
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))

    assert compose["volumes"]["postgres_data"]["name"] == (
        "${POSTGRES_VOLUME_NAME:-foodai-ecosystem_postgres_data_v2}"
    )

    recovery_compose = yaml.safe_load(
        (PROJECT_ROOT / "infra" / "postgres-recovery.compose.yml").read_text(encoding="utf-8")
    )
    assert recovery_compose["volumes"]["postgres_data"] == {
        "external": True,
        "name": "${POSTGRES_VOLUME_NAME:?Set POSTGRES_VOLUME_NAME for recovery}",
    }


def test_recovery_script_help_does_not_require_docker() -> None:
    result = subprocess.run(
        [str(RECOVERY_SCRIPT), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "не удаляет данные" in result.stdout


def test_recovery_inspection_uses_isolated_project_without_destructive_commands(
    tmp_path: Path,
) -> None:
    invocation_log = tmp_path / "docker-invocations.log"
    fake_docker = tmp_path / "docker"
    fake_docker.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> {invocation_log}\n"
        "case \"$*\" in\n"
        "  *to_regclass*) printf 'django_migrations\\n' ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)
    env_file = tmp_path / ".env"
    env_file.write_text("POSTGRES_DB=foodai\nPOSTGRES_USER=foodai\n", encoding="utf-8")
    environment = os.environ | {
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "FOODAI_ENV_FILE": str(env_file),
    }

    result = subprocess.run(
        [str(RECOVERY_SCRIPT), "inspect", "foodai-ecosystem_postgres_data"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0
    invocations = invocation_log.read_text(encoding="utf-8")
    assert "-p foodai-postgres-recovery" in invocations
    assert "--pull never" in invocations
    assert "down --remove-orphans" in invocations
    assert "volume rm" not in invocations
    assert "down -v" not in invocations
