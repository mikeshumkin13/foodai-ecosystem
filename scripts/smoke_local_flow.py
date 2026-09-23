"""Exercise the local HTTP flow with disposable accounts, real SMTP and real Vision."""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import time
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from local_test import STATE, compose_command, validate_host
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def call(client: httpx.Client, method: str, path: str, expected: int = 200, **kwargs: Any) -> Any:
    response = client.request(method, path, **kwargs)
    if response.status_code != expected:
        # Never dump payloads, cookies, passwords or email tokens to the console.
        raise RuntimeError(f"{method} {path}: expected {expected}, got {response.status_code}")
    return response.json() if response.content else None


def csrf(client: httpx.Client) -> None:
    client.headers["X-CSRFToken"] = call(client, "GET", "auth/csrf/")["csrf_token"]


def register(client: httpx.Client, password: str, frontend: str) -> None:
    email = f"local-qa-{secrets.token_hex(12)}@example.test"
    csrf(client)
    call(client, "POST", "auth/register/", 201, json={"email": email, "password": password})
    with httpx.Client(base_url="http://127.0.0.1:8025", trust_env=False, timeout=10) as mailbox:
        message_id = None
        for _ in range(20):
            response = mailbox.get("/api/v1/messages", params={"limit": 50})
            response.raise_for_status()
            for message in response.json()["messages"]:
                if any(recipient["Address"] == email for recipient in message["To"]):
                    message_id = message["ID"]
                    break
            if message_id is not None:
                break
            time.sleep(0.5)
        if message_id is None:
            raise RuntimeError("Verification email did not reach the local SMTP inbox.")
        message_response = mailbox.get(f"/api/v1/message/{message_id}")
        message_response.raise_for_status()
        text = message_response.json()["Text"]
        link = next(line.strip() for line in text.splitlines() if line.startswith(frontend))
        token = {key: values[0] for key, values in parse_qs(urlparse(link).query).items()}
    call(client, "POST", "auth/email/verify/", json=token)
    call(client, "POST", "auth/login/", json={"email": email, "password": password})
    csrf(client)
    call(client, "GET", "auth/me/")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=validate_host)
    args = parser.parse_args()
    host = validate_host(
        args.host or (STATE.read_text().strip() if STATE.exists() else "localhost")
    )
    frontend = f"http://{host}:3000"
    preflight = subprocess.run(
        compose_command()
        + [
            "exec",
            "-T",
            "backend",
            "python",
            "backend/manage.py",
            "shell",
            "-c",
            "from django.conf import settings; "
            "assert settings.DEBUG and settings.AI_COACH_PROVIDER == 'mock'; "
            "assert settings.EMAIL_HOST == 'mailpit'",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if preflight.returncode != 0:
        raise RuntimeError(
            "Start scripts/local_test.py up first; this test requires mock Coach/Mailpit."
        )
    password = secrets.token_urlsafe(24)
    clients: list[httpx.Client] = []
    try:
        for _ in range(2):
            client = httpx.Client(
                base_url=f"http://{host}:8000/api/v1/",
                headers={"Origin": frontend},
                timeout=90,
                trust_env=False,
            )
            clients.append(client)
            response = client.get("health/")
            assert response.headers["Access-Control-Allow-Origin"] == frontend
            assert response.headers["Access-Control-Allow-Credentials"] == "true"
            register(client, password, frontend)
        client, other = clients
        print(
            "PASS SMTP verification, login, CSRF and credentialed CORS for two accounts", flush=True
        )
        profile = call(client, "GET", "accounts/nutrition-profiles/me/")
        call(
            client,
            "PATCH",
            f"accounts/nutrition-profiles/{profile['id']}/",
            json={
                "goal": "maintain_weight",
                "height_cm": 175,
                "mass_kg": "70.00",
                "consent_accepted": True,
            },
        )
        call(other, "GET", f"accounts/nutrition-profiles/{profile['id']}/", 404)
        foods = call(client, "GET", "foods/search/", params={"q": "rice"})
        rice = next(food for food in foods if food["name"] == "Rice, white, cooked")
        fixture_root = ROOT / "services/vision/fixtures/validation"
        manifest = json.loads((fixture_root / "foodseg103_manifest.json").read_text())
        with Image.open(fixture_root / manifest["source_image"]) as source:
            image = source.crop(manifest["samples"][2]["crop"]).convert("RGB")
            buffer = BytesIO()
            image.save(buffer, format="JPEG")
        uploaded = call(
            client,
            "POST",
            "food-scans/",
            201,
            files={"photo": ("local-qa.jpg", buffer.getvalue(), "image/jpeg")},
        )
        scan = f"food-scans/{uploaded['scan_id']}/"
        started = time.monotonic()
        while time.monotonic() - started < 180:
            result = call(client, "GET", scan + "results/")
            if result["status"] in {"failed", "needs_confirmation"}:
                break
            time.sleep(1)
        assert result["status"] == "needs_confirmation", "Vision did not return proposals."
        items = result["detected_items"]
        assert items
        print(
            f"PASS real photo -> Celery -> Vision: {len(items)} proposals, "
            f"{time.monotonic() - started:.1f}s",
            flush=True,
        )
        item = items[0]
        corrected = call(
            client,
            "PATCH",
            scan + f"items/{item['id']}/",
            json={
                "food_id": rice["id"],
                "mass_g": "200.00",
            },
        )
        assert corrected["portion_estimate"] == item["portion_estimate"]
        assert corrected["manual_mass_g"] == "200.00"
        assert Decimal(corrected["calories"]) == Decimal("260")
        for extra in items[1:]:
            call(client, "DELETE", scan + f"items/{extra['id']}/", 204)
        now = datetime.now(UTC)
        day = now.date().isoformat()
        payload = {"meal_type": "lunch", "logged_at": now.isoformat()}
        assert call(client, "GET", "diary/day/", params={"date": day})["meals"] == []
        confirmed = call(client, "POST", scan + "confirm/", 201, json=payload)
        repeated = call(client, "POST", scan + "confirm/", json=payload)
        assert repeated["meal"]["id"] == confirmed["meal"]["id"]
        call(
            client,
            "POST",
            "meals/",
            201,
            json=payload
            | {
                "items": [{"food_id": rice["id"], "mass_g": "50.00"}],
            },
        )
        diary = call(client, "GET", "diary/day/", params={"date": day})
        assert len(diary["meals"]) == 2 and Decimal(diary["totals"]["calories"]) == Decimal("325")
        call(other, "GET", scan + "results/", 404)
        call(other, "GET", f"meals/{confirmed['meal']['id']}/", 404)
        summary = call(
            client,
            "POST",
            "ai/coach/ask/",
            json={
                "message": "Explain my daily nutrition balance",
                "date": day,
            },
        )
        assert summary["stored"] is False
        exported = call(client, "GET", "privacy/export/")
        assert password not in json.dumps(exported)
        call(client, "DELETE", f"privacy/food-photos/{uploaded['scan_id']}/")
        print(
            "PASS correction -> 260 kcal -> confirm once -> manual 65 kcal -> diary 325 kcal",
            flush=True,
        )
        print("PASS IDOR, mock coach, data export and photo deletion", flush=True)
    finally:
        failures = 0
        for client in clients:
            try:
                response = client.request(
                    "DELETE", "privacy/account/", json={"current_password": password}
                )
                failures += int(response.status_code != 200)
            finally:
                client.close()
        if failures:
            raise RuntimeError("QA cleanup incomplete; inspect only local-qa test accounts.")
        print("PASS disposable QA accounts cleaned; existing users preserved", flush=True)


if __name__ == "__main__":
    main()
