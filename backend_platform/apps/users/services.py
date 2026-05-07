"""User service layer for ForgeCore.

All user-related business logic lives here.
Views must not perform data mutations or validation directly.
"""
from __future__ import annotations

import logging

from apps.common.exceptions import NotFoundError, ValidationError

from .models import User

logger = logging.getLogger(__name__)


class UserService:
    """User management service.

    Responsibilities:
      - Profile reads and updates
      - Password change (current password verification → set new)
      - Account deactivation
      - Organization membership queries

    NOT responsible for:
      - Authentication / token issuance (see AuthService)
      - Registration (see AuthService)
    """

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    @staticmethod
    def get_user_by_id(user_id) -> User:
        """Raise NotFoundError if the user does not exist."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFoundError("User not found")

    @staticmethod
    def get_user_by_email(email: str) -> User:
        """Raise NotFoundError if the user does not exist."""
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            raise NotFoundError("User not found")

    # ------------------------------------------------------------------
    # Profile management
    # ------------------------------------------------------------------

    @staticmethod
    def update_profile(user: User, data: dict) -> User:
        """Apply allowed profile field updates.

        Only the fields present in ``data`` are written.
        """
        allowed_fields = ["first_name", "last_name", "avatar_url", "phone_number"]
        update_fields = ["updated_at"]
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
                update_fields.append(field)
        user.save(update_fields=update_fields)
        logger.info("UserService.update_profile: updated user %s fields=%s", user.pk, update_fields)
        return user

    # ------------------------------------------------------------------
    # Password
    # ------------------------------------------------------------------

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str) -> User:
        """Verify the current password then apply the new one.

        Raises:
            ValidationError: if current_password is incorrect.
        """
        if not user.check_password(current_password):
            raise ValidationError("Current password is incorrect.", code="invalid_password")

        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        logger.info("UserService.change_password: password changed for user %s", user.pk)
        return user

    # ------------------------------------------------------------------
    # Account lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    def deactivate_account(user: User) -> User:
        """Soft-delete: mark the account inactive."""
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        logger.info("UserService.deactivate_account: deactivated user %s", user.pk)
        return user

    # ------------------------------------------------------------------
    # Organization context
    # ------------------------------------------------------------------

    @staticmethod
    def get_organization_memberships(user: User) -> list[dict]:
        """Return all organization memberships for the user.

        Returns:
            list of {id, name, slug, role, joined_at}
        """
        try:
            from apps.organizations.models import OrganizationMembership
            memberships = (
                OrganizationMembership.objects
                .filter(user=user)
                .select_related("organization")
                .order_by("organization__name")
            )
            return [
                {
                    "id": str(m.organization.id),
                    "name": m.organization.name,
                    "role": m.role,
                    "joined_at": m.created_at.isoformat() if hasattr(m, "created_at") else None,
                }
                for m in memberships
            ]
        except Exception as exc:
            logger.warning(
                "UserService.get_organization_memberships: failed for user %s: %s",
                user.pk, exc,
            )
            return []

    @staticmethod
    def get_users_for_organization(org) -> "QuerySet":
        """Return all active users belonging to an organization.

        Used by org admin views.
        """
        from apps.organizations.models import OrganizationMembership
        user_ids = OrganizationMembership.objects.filter(
            organization=org
        ).values_list("user_id", flat=True)
        return User.objects.filter(id__in=user_ids, is_active=True)
