from __future__ import annotations

from .base import *  # noqa: F403
from .base import get_env_bool

SESSION_COOKIE_SECURE = get_env_bool("DJANGO_SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = get_env_bool("DJANGO_CSRF_COOKIE_SECURE", default=False)

