from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "AGENTS.md",
    "README.md",
    ".env.example",
    ".gitignore",
    "docker-compose.yml",
    "docs/PROJECT_CONTEXT.md",
    "docs/ARCHITECTURE.md",
    "docs/ROADMAP.md",
    "docs/STATUS.md",
    "docs/DECISIONS.md",
    "docs/SECURITY.md",
    "docs/API.md",
)

REQUIRED_DIRECTORIES = (
    "backend",
    "frontend",
    "services/vision",
    "infra",
    "docs",
    "scripts",
    ".github/workflows",
)


def main() -> int:
    missing_files = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    missing_dirs = [path for path in REQUIRED_DIRECTORIES if not (ROOT / path).is_dir()]

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    env_is_ignored = ".env\n" in gitignore or ".env\r\n" in gitignore

    errors = []
    if missing_files:
        errors.append("Missing files: " + ", ".join(missing_files))
    if missing_dirs:
        errors.append("Missing directories: " + ", ".join(missing_dirs))
    if not env_is_ignored:
        errors.append(".gitignore must ignore .env")

    if errors:
        for error in errors:
            print(error)
        return 1

    print("Project memory structure is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

