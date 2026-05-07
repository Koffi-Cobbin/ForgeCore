"""Common permissions for ForgeCore.

NOTE: The primary permission classes (IsJWTAuthenticated, IsOrganizationMember,
IsOrganizationAdmin, etc.) live in apps.authentication.permissions.
This module re-exports them for backwards compatibility and adds
IsOrganizationOwner which is not in the auth module.
"""
from apps.authentication.permissions import (  # noqa: F401 — re-export
    IsJWTAuthenticated,
    IsAPIKeyAuthenticated,
    IsEmailVerified,
    IsOrganizationMember,
    IsOrganizationAdmin,
)
from rest_framework.permissions import BasePermission


class IsOrganizationOwner(BasePermission):
    """The requesting user must be the owner of the organization."""

    message = "You must be the organization owner to perform this action."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        org_id = view.kwargs.get("org_id") or request.data.get("organization")
        if not org_id:
            return False
        try:
            from apps.organizations.models import Membership
            return Membership.objects.filter(
                user=request.user,
                organization_id=org_id,
                role='owner',
                is_active=True,
            ).exists()
        except Exception:
            return False