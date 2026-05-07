"""JWT token utilities for ForgeCore.

Inspired by FileForge's EmailTokenObtainPairSerializer, refactored into a
proper service layer so views and serializers never touch tokens directly.

All JWT logic MUST live here, not in views or serializers.

Extensibility:
  - ClaimsProvider protocol + claims_registry: register custom claim
    contributors (e.g. MFA status, OAuth provider, org context).
  - TokenService.for_user() calls each registered ClaimsProvider so
    tokens automatically include any registered extra claims.
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom claims extension point
# ---------------------------------------------------------------------------

class ClaimsProvider(Protocol):
    """Structural protocol for custom JWT claim contributors."""

    def get_claims(self, user) -> dict[str, Any]:
        """Return a dict of additional claims to embed in the token."""
        ...


class ClaimsRegistry:
    """Registry for pluggable JWT claim contributors.

    Usage (e.g. in an org app's AppConfig.ready()):

        from apps.authentication.tokens import claims_registry

        class OrgClaimsProvider:
            def get_claims(self, user):
                return {"org_ids": [...]}

        claims_registry.register("orgs", OrgClaimsProvider())

    Claims are merged (later registrations win on key conflicts).
    """

    def __init__(self) -> None:
        self._providers: dict[str, ClaimsProvider] = {}

    def register(self, name: str, provider: ClaimsProvider, *, replace: bool = False) -> None:
        if name in self._providers and not replace:
            raise ValueError(f"Claims provider {name!r} already registered.")
        self._providers[name] = provider
        logger.debug("ClaimsRegistry: registered provider '%s'.", name)

    def unregister(self, name: str) -> None:
        self._providers.pop(name, None)

    def collect(self, user) -> dict[str, Any]:
        """Collect and merge claims from all registered providers."""
        merged: dict[str, Any] = {}
        for name, provider in self._providers.items():
            try:
                merged.update(provider.get_claims(user))
            except Exception as exc:
                logger.warning("ClaimsProvider %r failed for user %s: %s", name, user.pk, exc)
        return merged


claims_registry = ClaimsRegistry()


# ---------------------------------------------------------------------------
# Built-in claims provider — user identity (always registered)
# ---------------------------------------------------------------------------

class _UserIdentityClaims:
    """Embed stable user identity fields in every JWT (FileForge pattern)."""

    def get_claims(self, user) -> dict[str, Any]:
        return {
            "email": user.email,
            "full_name": getattr(user, "full_name", ""),
            "is_email_verified": getattr(user, "is_email_verified", False),
            "mfa_enabled": getattr(user, "mfa_enabled", False),
        }


claims_registry.register("user_identity", _UserIdentityClaims())


# ---------------------------------------------------------------------------
# TokenService — single entry point for all JWT operations
# ---------------------------------------------------------------------------

class TokenService:
    """Stateless JWT token service.

    Views and AuthService MUST use this class; they must never import
    RefreshToken or AccessToken directly.
    """

    @staticmethod
    def _embed_claims(token, user) -> None:
        """Write all registered claims into the token payload."""
        extra = claims_registry.collect(user)
        for key, value in extra.items():
            token[key] = value

    @classmethod
    def for_user(cls, user) -> dict[str, str]:
        """Create a JWT pair for user, including all registered claims.

        Returns:
            {"access": "<access_token>", "refresh": "<refresh_token>"}
        """
        refresh = RefreshToken.for_user(user)
        cls._embed_claims(refresh, user)
        cls._embed_claims(refresh.access_token, user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @staticmethod
    def refresh(refresh_token_str: str) -> dict[str, str]:
        """Rotate a refresh token and return a new pair.

        Raises:
            TokenError: if the token is invalid or blacklisted.
        """
        try:
            token = RefreshToken(refresh_token_str)
            return {
                "access": str(token.access_token),
                "refresh": str(token),
            }
        except TokenError as exc:
            raise TokenError(str(exc)) from exc

    @staticmethod
    def blacklist(refresh_token_str: str) -> None:
        """Blacklist a refresh token (logout).

        Raises:
            TokenError: if the token is invalid.
        """
        try:
            token = RefreshToken(refresh_token_str)
            token.blacklist()
        except TokenError as exc:
            raise TokenError(str(exc)) from exc

    @staticmethod
    def decode_access(access_token_str: str) -> dict[str, Any]:
        """Decode and return the payload of an access token.

        Raises:
            TokenError: if the token is invalid or expired.
        """
        try:
            token = AccessToken(access_token_str)
            return dict(token.payload)
        except TokenError as exc:
            raise TokenError(str(exc)) from exc

    @staticmethod
    def mfa_pending_token(user) -> str:
        """Return a short-lived partial-auth token for MFA flows.

        This token signals that password auth passed but MFA is still
        required. Stub — implement when MFA is added.
        """
        refresh = RefreshToken.for_user(user)
        refresh["mfa_pending"] = True
        refresh["mfa_enabled"] = True
        # Short expiry for MFA window — 5 minutes.
        from datetime import timedelta
        from django.utils import timezone
        refresh.set_exp(lifetime=timedelta(minutes=5))
        return str(refresh)
