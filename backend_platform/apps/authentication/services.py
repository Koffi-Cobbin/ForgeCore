"""Authentication service layer for ForgeCore.

All authentication logic lives here. Views and serializers must never
touch tokens, password hashing, or authentication backends directly.

This service is organisation-aware: login returns a summary of the
user's organization memberships so clients can bootstrap their session
without extra API calls.

Extensibility points:
  - MFAHook.is_required() / MFAHook.verify(): pluggable MFA verification.
  - OAuthHook.authenticate():                  pluggable OAuth provider auth.
  - TokenService / ClaimsRegistry:             pluggable JWT claim embedding.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta

from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError

from apps.common.exceptions import ValidationError
from apps.common.tasks import TaskDispatcher

from .backends import MFAHook, OAuthHook
from .tokens import TokenService

logger = logging.getLogger(__name__)


class AuthService:
    """Central authentication service.

    Responsibilities:
      - User registration and email verification dispatch
      - Email+password login with optional MFA check
      - JWT token issuance via TokenService (never directly)
      - Token refresh and logout (blacklisting)
      - Password reset flow (request + confirm)
      - OAuth authentication hook delegation

    NOT responsible for:
      - Serialization / deserialization
      - HTTP responses
      - Organization management (see OrganizationService)
    """

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @staticmethod
    def register(email: str, password: str, first_name: str = "", last_name: str = ""):
        """Create a new user account and dispatch a verification email.

        Raises:
            ValidationError: if the email is already registered.
        """
        from apps.users.models import User

        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.", code="email_taken")

        verification_token = secrets.token_urlsafe(32)
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_email_verified=False,
            email_verification_token=verification_token,
        )

        TaskDispatcher.dispatch(AuthService._send_verification_email, str(user.id), verification_token)
        logger.info("AuthService.register: user %s registered", user.pk)
        return user

    @staticmethod
    def _send_verification_email(user_id: str, token: str) -> None:
        try:
            from apps.email_service.services import EmailService
            from apps.users.models import User
            user = User.objects.get(id=user_id)
            EmailService.send_verification_email(user, token)
        except Exception as exc:
            logger.error(
                "AuthService: failed to send verification email to user %s: %s",
                user_id, exc,
            )

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    @staticmethod
    def login(email: str, password: str, mfa_code: str | None = None, request=None) -> dict:
        """Authenticate a user and return a JWT pair + session context.

        Raises:
            ValidationError: for invalid credentials, inactive account,
                             or incomplete MFA.

        Returns:
            {
                "access":        str,
                "refresh":       str,
                "user":          User instance,
                "organizations": list[{id, name, role}],
                "mfa_pending":   bool
            }

            When MFA is required but no valid code is provided:
            {
                "mfa_pending": True,
                "mfa_token":   str  (short-lived partial-auth token)
            }
        """
        user = authenticate(request=request, email=email, password=password)

        if user is None:
            raise ValidationError("Invalid email or password.", code="invalid_credentials")

        if not user.is_active:
            raise ValidationError("This account has been deactivated.", code="account_inactive")

        # MFA gate — if enabled and code not yet provided, return a
        # partial-auth token instead of a full session.
        if MFAHook.is_required(user):
            if not mfa_code or not MFAHook.verify(user, mfa_code):
                return {
                    "mfa_pending": True,
                    "mfa_token": TokenService.mfa_pending_token(user),
                }

        tokens = TokenService.for_user(user)
        logger.info("AuthService.login: user %s authenticated", user.pk)
        return {
            **tokens,
            "user": user,
            "organizations": AuthService._get_org_context(user),
            "mfa_pending": False,
        }

    @staticmethod
    def _get_org_context(user) -> list[dict]:
        """Return a lightweight org membership summary for the login response."""
        try:
            from apps.organizations.models import OrganizationMembership
            memberships = (
                OrganizationMembership.objects
                .filter(user=user)
                .select_related("organization")
            )
            return [
                {
                    "id": str(m.organization.id),
                    "name": m.organization.name,
                    "role": m.role,
                }
                for m in memberships
            ]
        except Exception as exc:
            logger.warning(
                "AuthService: could not fetch org context for user %s: %s",
                user.pk, exc,
            )
            return []

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    @staticmethod
    def refresh_token(refresh_token_str: str) -> dict[str, str]:
        """Rotate a refresh token and return a new pair.

        Raises:
            ValidationError: if the token is invalid or blacklisted.
        """
        try:
            return TokenService.refresh(refresh_token_str)
        except TokenError as exc:
            raise ValidationError(
                "Invalid or expired refresh token.", code="invalid_token"
            ) from exc

    @staticmethod
    def logout(refresh_token_str: str) -> None:
        """Blacklist a refresh token to complete logout.

        Raises:
            ValidationError: if the token is invalid.
        """
        try:
            TokenService.blacklist(refresh_token_str)
            logger.info("AuthService.logout: refresh token blacklisted")
        except TokenError as exc:
            raise ValidationError(
                "Invalid refresh token.", code="invalid_token"
            ) from exc

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------

    @staticmethod
    def verify_email(token: str):
        """Mark the user's email as verified.

        Raises:
            ValidationError: if the token is not found.
        """
        from apps.users.models import User

        try:
            user = User.objects.get(email_verification_token=token)
        except User.DoesNotExist:
            raise ValidationError("Invalid verification token.", code="invalid_token")

        user.is_email_verified = True
        user.email_verification_token = None
        user.save(update_fields=["is_email_verified", "email_verification_token", "updated_at"])
        logger.info("AuthService.verify_email: user %s verified email", user.pk)
        return user

    @staticmethod
    def resend_verification_email(email: str) -> None:
        """Resend the verification email for an unverified account.

        Silently does nothing if the account is already verified or not found
        (prevents email enumeration).
        """
        from apps.users.models import User

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return

        if user.is_email_verified:
            return

        token = secrets.token_urlsafe(32)
        user.email_verification_token = token
        user.save(update_fields=["email_verification_token", "updated_at"])
        TaskDispatcher.dispatch(AuthService._send_verification_email, str(user.id), token)

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    @staticmethod
    def request_password_reset(email: str) -> None:
        """Generate a reset token and dispatch a reset email.

        Always succeeds regardless of whether the email exists
        (prevents user enumeration via timing attacks).
        """
        from apps.users.models import User

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return

        raw_token = secrets.token_urlsafe(32)
        user.password_reset_token = hashlib.sha256(raw_token.encode()).hexdigest()
        user.password_reset_token_expires = timezone.now() + timedelta(hours=1)
        user.save(update_fields=[
            "password_reset_token", "password_reset_token_expires", "updated_at"
        ])
        TaskDispatcher.dispatch(
            AuthService._send_password_reset_email, str(user.id), raw_token
        )
        logger.info(
            "AuthService.request_password_reset: reset dispatched for user %s", user.pk
        )

    @staticmethod
    def _send_password_reset_email(user_id: str, token: str) -> None:
        try:
            from apps.email_service.services import EmailService
            from apps.users.models import User
            user = User.objects.get(id=user_id)
            EmailService.send_password_reset_email(user, token)
        except Exception as exc:
            logger.error(
                "AuthService: failed to send password reset email to user %s: %s",
                user_id, exc,
            )

    @staticmethod
    def reset_password(token: str, new_password: str):
        """Apply a new password using a valid reset token.

        Raises:
            ValidationError: if the token is invalid/expired or the
                             password fails Django's validators.
        """
        from apps.users.models import User
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError

        hashed = hashlib.sha256(token.encode()).hexdigest()
        try:
            user = User.objects.get(
                password_reset_token=hashed,
                password_reset_token_expires__gt=timezone.now(),
            )
        except User.DoesNotExist:
            raise ValidationError("Invalid or expired reset token.", code="invalid_token")

        try:
            validate_password(new_password, user)
        except DjangoValidationError as exc:
            raise ValidationError(" ".join(exc.messages), code="password_invalid")

        user.set_password(new_password)
        user.password_reset_token = None
        user.password_reset_token_expires = None
        user.save(update_fields=[
            "password", "password_reset_token", "password_reset_token_expires", "updated_at"
        ])
        logger.info("AuthService.reset_password: password reset for user %s", user.pk)
        return user

    # ------------------------------------------------------------------
    # OAuth (future extensibility hook)
    # ------------------------------------------------------------------

    @staticmethod
    def login_oauth(provider: str, token: str, request=None) -> dict:
        """Authenticate via an OAuth provider and return a JWT pair.

        Delegates to OAuthHook which routes to the registered provider backend.

        Raises:
            ValueError:      if the provider is not registered.
            ValidationError: if the OAuth token is invalid.
        """
        try:
            user = OAuthHook.authenticate(provider, token, request=request)
        except ValueError as exc:
            raise ValidationError(str(exc), code="oauth_provider_unknown")
        except Exception as exc:
            raise ValidationError(
                f"OAuth authentication failed: {exc}", code="oauth_failed"
            )

        if not user or not user.is_active:
            raise ValidationError(
                "OAuth authentication returned no valid user.", code="oauth_no_user"
            )

        tokens = TokenService.for_user(user)
        logger.info(
            "AuthService.login_oauth: user %s authenticated via %s", user.pk, provider
        )
        return {
            **tokens,
            "user": user,
            "organizations": AuthService._get_org_context(user),
            "mfa_pending": False,
        }
