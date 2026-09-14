#!/bin/sh
set -eu

usage() {
    cat <<'EOF'
Использование:
  scripts/postgres-volume-recovery.sh inspect VOLUME_NAME
  scripts/postgres-volume-recovery.sh backup VOLUME_NAME [OUTPUT.dump]

Команда только инспектирует или архивирует существующий local PostgreSQL volume.
Она не применяет migrations, не восстанавливает dump и не удаляет данные.
EOF
}

action="${1:-}"
volume_name="${2:-}"
if [ "$action" = "--help" ] || [ "$action" = "-h" ]; then
    usage
    exit 0
fi
if [ "$action" != "inspect" ] && [ "$action" != "backup" ]; then
    usage >&2
    exit 2
fi
if [ -z "$volume_name" ]; then
    usage >&2
    exit 2
fi
case "$volume_name" in
    *[!A-Za-z0-9_.-]*)
        echo "Недопустимое имя Docker volume." >&2
        exit 2
        ;;
esac

script_directory="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
project_root="$(dirname "$script_directory")"
env_file="${FOODAI_ENV_FILE:-$project_root/.env}"
project_name="${POSTGRES_RECOVERY_PROJECT:-foodai-postgres-recovery}"
if [ ! -f "$env_file" ]; then
    echo "Файл окружения не найден: $env_file" >&2
    exit 2
fi
if ! command -v docker >/dev/null 2>&1; then
    echo "Docker CLI не найден." >&2
    exit 2
fi
if ! docker volume inspect "$volume_name" >/dev/null 2>&1; then
    echo "Docker volume не найден: $volume_name" >&2
    exit 2
fi

compose() {
    POSTGRES_VOLUME_NAME="$volume_name" docker compose \
        -f "$project_root/docker-compose.yml" \
        -f "$project_root/infra/postgres-recovery.compose.yml" \
        -p "$project_name" --env-file "$env_file" "$@"
}

cleanup() {
    compose down --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT HUP INT TERM

compose up -d --no-deps --pull never postgres >/dev/null
compose exec -T postgres sh -c \
    'until pg_isready -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do sleep 1; done'

if [ "$action" = "backup" ]; then
    output_path="${3:-$project_root/.local-backups/${volume_name}-$(date -u +%Y%m%dT%H%M%SZ).dump}"
    if [ -e "$output_path" ]; then
        echo "Backup уже существует, перезапись запрещена: $output_path" >&2
        exit 2
    fi
    umask 077
    mkdir -p "$(dirname "$output_path")"
    compose exec -T postgres sh -c \
        'exec pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --format=custom --no-owner --no-acl' \
        >"$output_path"
    compose exec -T postgres pg_restore --list <"$output_path" >/dev/null
    echo "Backup создан и проверен: $output_path"
    exit 0
fi

echo "Volume: $volume_name"
echo "Migration history accounts/admin:"
migration_table="$(
    compose exec -T postgres sh -c \
        'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only --no-align --command "SELECT to_regclass('"'"'public.django_migrations'"'"');"'
)"
if [ "$migration_table" = "django_migrations" ]; then
    compose exec -T postgres sh -c \
        'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --no-psqlrc --command "SELECT app, name, applied FROM django_migrations WHERE app IN ('"'"'accounts'"'"', '"'"'admin'"'"') ORDER BY applied;"'
else
    echo "django_migrations отсутствует"
fi

echo "Domain table row counts (без содержимого строк):"
compose exec -T postgres sh -c \
    'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --no-psqlrc' <<'SQL'
SELECT format(
    'SELECT %L AS table_name, count(*) AS row_count FROM %I.%I;',
    table_name,
    table_schema,
    table_name
)
FROM information_schema.tables
WHERE table_schema = 'public'
  AND (
      table_name = 'auth_user'
      OR table_name LIKE 'accounts\_%' ESCAPE '\'
      OR table_name LIKE 'ai_coach\_%' ESCAPE '\'
      OR table_name LIKE 'diary\_%' ESCAPE '\'
      OR table_name LIKE 'fitness\_%' ESCAPE '\'
      OR table_name LIKE 'food_scans\_%' ESCAPE '\'
      OR table_name LIKE 'nutrition\_%' ESCAPE '\'
      OR table_name LIKE 'privacy\_%' ESCAPE '\'
      OR table_name LIKE 'wellbeing\_%' ESCAPE '\'
  )
ORDER BY table_name
\gexec
SQL
