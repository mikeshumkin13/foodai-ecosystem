from __future__ import annotations

import argparse
import ipaddress
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".cache" / "local-test-host"
PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(value) for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


def validate_host(value: str) -> str:
    if value == "localhost":
        return value
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as exc:
        raise argparse.ArgumentTypeError(
            "Use localhost or the Mac's private IPv4 address."
        ) from exc
    if not any(address in network for network in PRIVATE_NETWORKS):
        raise argparse.ArgumentTypeError("Only a private LAN address is allowed, not a public IP.")
    return str(address)


def compose_command() -> list[str]:
    return [
        "docker",
        "compose",
        "--env-file",
        str(ROOT / ".env"),
        "-f",
        str(ROOT / "docker-compose.yml"),
        "-f",
        str(ROOT / "infra/compose.local-test.yml"),
    ]


def run(arguments: list[str], env: dict[str, str], *, cwd: Path = ROOT) -> None:
    subprocess.run(arguments, cwd=cwd, env=env, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local FoodAI + test mailbox; no external email/LLM."
    )
    parser.add_argument("action", choices=("up", "frontend", "status", "stop"))
    parser.add_argument("--host", type=validate_host)
    parser.add_argument("--build", action="store_true", help="Rebuild images during up.")
    args = parser.parse_args()
    host = args.host or (STATE.read_text().strip() if STATE.exists() else "localhost")
    host = validate_host(host)
    env = dict(os.environ)
    env.update(FOODAI_TEST_HOST=host, FOODAI_TEST_BIND="127.0.0.1" if host == "localhost" else host)
    compose = compose_command()

    if args.action == "up":
        if not (ROOT / ".env").exists():
            shutil.copyfile(ROOT / ".env.example", ROOT / ".env")
            (ROOT / ".env").chmod(0o600)
        STATE.parent.mkdir(exist_ok=True)
        run(compose + ["config", "--quiet"], env)
        run(
            compose
            + ["up", "-d", "--wait", "--wait-timeout", "1800"]
            + (["--build"] if args.build else []),
            env,
        )
        run(
            compose + ["exec", "-T", "backend", "python", "backend/manage.py", "seed_demo_catalog"],
            env,
        )
        STATE.write_text(host + "\n")
        print(f"App: http://{host}:3000 (start frontend in another terminal)")
        print("Test mailbox on Mac: http://localhost:8025; external mail is NOT sent.")
    elif args.action == "frontend":
        runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies"
        pnpm = shutil.which("pnpm")
        if pnpm is None and (runtime / "bin/fallback/pnpm").is_file():
            pnpm = str(runtime / "bin/fallback/pnpm")
        if pnpm is None:
            parser.error("Install Node.js and pnpm first (see docs/GETTING_STARTED.md).")
        if shutil.which("node") is None and (runtime / "node/bin/node").is_file():
            env["PATH"] = str(runtime / "node/bin") + os.pathsep + env.get("PATH", "")
        env["NEXT_PUBLIC_API_BASE_URL"] = f"http://{host}:8000"
        frontend = ROOT / "frontend"
        if not (frontend / "node_modules/.bin/next").is_file():
            run([pnpm, "install", "--frozen-lockfile"], env, cwd=frontend)
        # Refuse occupied ports instead of silently changing the CORS/CSRF origin.
        os.chdir(frontend)
        os.execvpe(
            pnpm, [pnpm, "dev", "--hostname", env["FOODAI_TEST_BIND"], "--port", "3000"], env
        )
    elif args.action == "status":
        run(compose + ["ps"], env)
        print(f"App: http://{host}:3000; test mailbox on Mac: http://localhost:8025")
    else:
        run(compose + ["stop"], env)
        print("Containers stopped; database/photo volumes preserved. Stop frontend with Ctrl+C.")


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, FileNotFoundError, argparse.ArgumentTypeError) as error:
        raise SystemExit(f"Local launch failed: {error}") from error
