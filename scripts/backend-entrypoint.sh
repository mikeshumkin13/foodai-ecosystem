set -eu

python backend/manage.py wait_for_dependencies --settings="${DJANGO_SETTINGS_MODULE:-config.settings.local}"

if [ "${DJANGO_RUN_MIGRATIONS:-true}" = "true" ]; then
  python backend/manage.py migrate --noinput --settings="${DJANGO_SETTINGS_MODULE:-config.settings.local}"
fi

exec "$@"

