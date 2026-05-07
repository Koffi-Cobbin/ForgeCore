"""Permission classes for ForgeCore."""
from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsJWTAuthenticated(BasePermission):
    """Allow access only to valid JWT-authenticated users."""

    message = "A valid JWT access token is required."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        from apps.api_keys.models import APIKey
        if isinstance(request.auth, APIKey):
            return False
        return True


class IsAPIKeyAuthenticated(BasePermission):
    """Allow access only to valid API-key-authenticated requests."""

    message = "A valid API key is required."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        from apps.api_keys.models import APIKey
        return isinstance(request.auth, APIKey)


class IsEmailVerified(BasePermission):
    """Allow access only to users with verified email addresses."""

    message = "Email address must be verified to access this resource."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_email_verified", False)
        )


class IsOrganizationMember(BasePermission):
    """Request user must belong to the organization (org_id from URL kwargs)."""

    message = "You are not a member of this organization."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        org_id = view.kwargs.get("org_id")
        if not org_id:
            return True
        return _is_org_member(request.user, org_id)


class IsOrganizationAdmin(BasePermission):
    """The requesting user must be an owner or admin of the organization."""

    message = "You must be an organization admin to perform this action."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        org_id = view.kwargs.get("org_id")
        if not org_id:
            return False
        return _is_org_admin(request.user, org_id)


# ---------------------------------------------------------------------------
# Private helpers — use Membership (the actual model)
# ---------------------------------------------------------------------------

def _is_org_member(user, org_id) -> bool:
    try:
        from apps.organizations.models import Membership  # FIX: was OrganizationMembership
        return Membership.objects.filter(
            organization_id=org_id,
            user=user,
            is_active=True,
        ).exists()
    except Exception:
        return False


def _is_org_admin(user, org_id) -> bool:
    try:
        from apps.organizations.models import Membership  # FIX: was OrganizationMembership
        return Membership.objects.filter(
            organization_id=org_id,
            user=user,
            role__in=["owner", "admin"],
            is_active=True,
        ).exists()
    except Exception:
        return False