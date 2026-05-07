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
    """User management service."""

    @staticmethod
    def get_user_by_id(user_id) -> User:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFoundError("User not found")

    @staticmethod
    def get_user_by_email(email: str) -> User:
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            raise NotFoundError("User not found")

    @staticmethod
    def update_profile(user: User, data: dict) -> User:
        allowed_fields = ["first_name", "last_name", "avatar_url", "phone_number"]
        update_fields = ["updated_at"]
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
                update_fields.append(field)
        user.save(update_fields=update_fields)
        logger.info("UserService.update_profile: updated user %s fields=%s", user.pk, update_fields)
        return user

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str) -> User:
        if not user.check_password(current_password):
            raise ValidationError("Current password is incorrect.", code="invalid_password")
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        logger.info("UserService.change_password: password changed for user %s", user.pk)
        return user

    @staticmethod
    def deactivate_account(user: User) -> User:
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        logger.info("UserService.deactivate_account: deactivated user %s", user.pk)
        return user

    @staticmethod
    def get_organization_memberships(user: User) -> list[dict]:
        try:
            from apps.organizations.models import Membership  # FIX: was OrganizationMembership
            memberships = (
                Membership.objects
                .filter(user=user, is_active=True)
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
        from apps.organizations.models import Membership  # FIX: was OrganizationMembership
        user_ids = Membership.objects.filter(
            organization=org, is_active=True
        ).values_list("user_id", flat=True)
        return User.objects.filter(id__in=user_ids, is_active=True)