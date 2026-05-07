"""Authentication backends for ForgeCore.

Ported and extended from FileForge's auth model.

Design principles:
  - EmailAuthBackend is the primary login backend (replaces ModelBackend).
  - AuthBackendRegistry allows future OAuth providers and MFA backends
    to register themselves without touching this file.
  - All backends MUST remain free of request/response knowledge.

Future extensibility:
  - OAuth: register an OAuthBackend via AuthBackendRegistry.register()
  - MFA:   register an MFABackend that wraps EmailAuthBackend.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Protocol

from django.contrib.auth.backends import ModelBackend

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Primary email authentication backend
# ---------------------------------------------------------------------------

class EmailAuthBackend(ModelBackend):
    """Authenticate users by email address + password.

    Extends Django's ModelBackend so that permission checks and all
    other ModelBackend behaviour are inherited unchanged.  The only
    override is ``authenticate()``, which looks up the user by email
    rather than by the generic ``username`` kwarg.
    """

    def authenticate(self, request, email: str | None = None, password: str | None = None, **kwargs):
        """Return the matching User on success, None on failure.

        Args:
            request: Django HttpRequest (may be None in tests/tasks).
            email:   User's email address.
            password: Plaintext password to verify.
        """
        if not email or not password:
            return None

        from apps.users.models import User
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Run the password hasher to prevent timing attacks.
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            logger.error("EmailAuthBackend: multiple users for email=%r", email)
            return None

        if not user.check_password(password):
            return None

        if not self.user_can_authenticate(user):
            return None

        return user

    def user_can_authenticate(self, user) -> bool:
        """Active users only (no staff/superuser restriction at backend level)."""
        return getattr(user, "is_active", False)


# ---------------------------------------------------------------------------
# Extensibility registry
# ---------------------------------------------------------------------------

class AuthBackendProtocol(Protocol):
    """Structural protocol that every registered backend must satisfy."""

    def authenticate(self, request, **credentials) -> Any:
        ...


class AuthBackendRegistry:
    """Central registry for pluggable authentication backends.

    Usage (e.g. in an oauth app's AppConfig.ready()):

        from apps.authentication.backends import backend_registry

        class GoogleOAuthBackend:
            name = "google"
            def authenticate(self, request, *, google_token=None, **kw):
                ...

        backend_registry.register("google", GoogleOAuthBackend())

    Then in settings, add the dotted path to AUTHENTICATION_BACKENDS
    *in addition* to EmailAuthBackend.  The registry is a lightweight
    lookup aid — Django's own backend chain drives the actual auth flow.
    """

    def __init__(self) -> None:
        self._backends: dict[str, AuthBackendProtocol] = {}

    def register(self, name: str, backend: AuthBackendProtocol, *, replace: bool = False) -> None:
        if name in self._backends and not replace:
            raise ValueError(f"Auth backend {name!r} is already registered.")
        self._backends[name] = backend
        logger.info("AuthBackendRegistry: registered backend '%s'.", name)

    def unregister(self, name: str) -> None:
        self._backends.pop(name, None)

    def get(self, name: str) -> AuthBackendProtocol:
        try:
            return self._backends[name]
        except KeyError as exc:
            raise KeyError(f"Auth backend {name!r} not registered.") from exc

    def names(self) -> list[str]:
        return list(self._backends)

    def __contains__(self, name: str) -> bool:
        return name in self._backends


backend_registry = AuthBackendRegistry()


# ---------------------------------------------------------------------------
# MFA hook (no-op stub — replace with real impl when MFA is added)
# ---------------------------------------------------------------------------

class MFAHook:
    """Extensibility hook for multi-factor authentication.

    When MFA is implemented, replace this stub with an MFABackend that
    checks the user's second factor before login completes.

    Intended call site: AuthService.login() calls MFAHook.verify() after
    the password check.  If it returns False, login is denied.
    """

    @staticmethod
    def is_required(user) -> bool:
        """Return True if MFA must be completed for this user."""
        return getattr(user, "mfa_enabled", False)

    @staticmethod
    def verify(user, mfa_code: str | None) -> bool:
        """Verify the MFA code for the user.

        Currently always returns True (no MFA implemented).
        Replace this with TOTP / SMS verification when ready.
        """
        if not MFAHook.is_required(user):
            return True
        # TODO: implement TOTP/SMS verification here.
        return False


# ---------------------------------------------------------------------------
# OAuth hook (no-op stub — replace when OAuth is added)
# ---------------------------------------------------------------------------

class OAuthHook:
    """Extensibility hook for OAuth provider authentication.

    Register concrete providers via backend_registry.register().
    AuthService.login_oauth() will call this hook to resolve tokens.
    """

    @staticmethod
    def authenticate(provider: str, token: str, request=None):
        """Delegate to a registered OAuth provider backend.

        Returns a User instance on success, raises ValueError on failure.
        """
        if provider not in backend_registry:
            raise ValueError(f"OAuth provider {provider!r} is not registered.")
        backend = backend_registry.get(provider)
        return backend.authenticate(request, oauth_token=token)
