from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_local_private_storage_is_shared_with_read_only_vision() -> None:
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text())
    services = compose["services"]
    private_mount = (
        "${FOOD_SCAN_LOCAL_STORAGE_PATH:-./local_uploads/private}:"
        "${FOOD_SCAN_PRIVATE_MEDIA_ROOT:-/app/local_uploads/private}"
    )
    for service in ("backend", "celery_worker"):
        assert private_mount in services[service]["volumes"]
    vision = services["vision"]
    assert private_mount + ":ro" in vision["volumes"]
    assert ".:/app" not in vision["volumes"]
    assert "ports" not in vision
    assert vision["environment"]["VISION_LOCAL_PRIVATE_MEDIA_ROOT"] == (
        "${FOOD_SCAN_PRIVATE_MEDIA_ROOT:-/app/local_uploads/private}"
    )


def test_vision_warms_model_before_serving_and_keeps_cache_between_restarts() -> None:
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text())
    vision = compose["services"]["vision"]
    command = vision["command"][-1]
    assert command.index("get_food_recognition_model().predict") < command.index("uvicorn.run")
    assert vision["command"][:2] == ["python", "-c"]
    assert "${VISION_MODEL_CACHE_PATH:-./.cache/huggingface}:/tmp/huggingface" in vision["volumes"]
    assert vision["environment"]["HF_HOME"] == "/tmp/huggingface"


def test_documented_timeouts_allow_inference_to_fail_before_celery_kills_task() -> None:
    values = dict(
        line.split("=", 1)
        for line in (PROJECT_ROOT / ".env.example").read_text().splitlines()
        if "=" in line and not line.startswith("#")
    )
    timeout = float(values["VISION_SERVICE_TIMEOUT_SECONDS"])
    soft_limit = float(values["CELERY_TASK_SOFT_TIME_LIMIT_SECONDS"])
    hard_limit = float(values["CELERY_TASK_TIME_LIMIT_SECONDS"])
    assert 30 <= timeout < soft_limit < hard_limit
