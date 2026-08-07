from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from django.contrib.auth.base_user import BaseUserManager

if TYPE_CHECKING:
    from accounts.models import User


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

    def _create_user(
        self,
        email: str,
        password: str | None,
        **extra_fields: Any,
    ) -> User:
        if not email:
            raise ValueError("Email is required.")

        normalized_email = self.normalize_email(email).lower()
        user = cast("User", self.model(email=normalized_email, **extra_fields))
        user.set_password(password)
        user.save(using=self._db)
        if not user.is_superuser:
            from accounts.rbac import Role, assign_role

            assign_role(user, Role.USER, using=self._db or "default")
        return user
