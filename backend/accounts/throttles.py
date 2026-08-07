from __future__ import annotations

import hashlib

from rest_framework.request import Request
from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView


class DynamicRateThrottle(SimpleRateThrottle):
    def get_rate(self) -> str | None:
        if self.scope is None:
            return None

        rate = api_settings.DEFAULT_THROTTLE_RATES.get(self.scope)
        if rate is None:
            return None
        return str(rate)


class EmailAndIPThrottle(DynamicRateThrottle):
    email_field = "email"

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        if request.method == "GET":
            return None

        raw_email = request.data.get(self.email_field, "")
        email = str(raw_email).strip().lower()
        ident = self.get_ident(request)
        email_hash = hashlib.sha256(email.encode("utf-8")).hexdigest()
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{ident}:{email_hash}",
        }


class RegisterRateThrottle(EmailAndIPThrottle):
    scope = "auth_register"


class LoginRateThrottle(EmailAndIPThrottle):
    scope = "auth_login"


class EmailVerificationRateThrottle(DynamicRateThrottle):
    scope = "auth_email_verification"

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        if request.method == "GET":
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class PasswordResetRateThrottle(EmailAndIPThrottle):
    scope = "auth_password_reset"


class UserScopedRateThrottle(DynamicRateThrottle):
    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        user = request.user
        if not user or not user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": getattr(user, "pk", self.get_ident(request)),
        }


class LogoutRateThrottle(UserScopedRateThrottle):
    scope = "auth_logout"


class RefreshRateThrottle(UserScopedRateThrottle):
    scope = "auth_refresh"


class PasswordChangeRateThrottle(UserScopedRateThrottle):
    scope = "auth_password_change"
