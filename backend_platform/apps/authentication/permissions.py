"""Permission classes for ForgeCore.

Adapted from FileForge's two-plane permission model:
  - IsJWTAuthenticated  → JWT (user-facing control plane)
  - IsAPIKeyAuthenticated → API Key (machine-to-machine data plane)

Additional org-aware permissions build on top of these.

All permission logic MUST live here, not in views or services.
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission, IsAuthenticated


class IsJWTAuthenticated(BasePermission):
    """Allow access only to valid JWT-authenticated users.

    Adapted from FileForge's IsAuthenticatedDeveloper, generalised for
    ForgeCore's multi-tenant user model.

    Ensures:
      - request.user is authenticated
      - auth was via JWT (not an API key)
    """

    message = "A valid JWT access token is required."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        # If request.auth is an API key instance, deny — wrong auth plane.
        from apps.api_keys.models import APIKey
        if isinstance(request.auth, APIKey):
            return False
        return True


class IsAPIKeyAuthenticated(BasePermission):
    """Allow access only to valid API-key-authenticated requests.

    Adapted from FileForge's IsAuthenticatedApp.

    Ensures:
      - request.user is authenticated
      - auth was via an API Key (not a JWT)
    """

    message = "A valid API key is required."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        from apps.api_keys.models import APIKey
        return isinstance(request.auth, APIKey)


class IsEmailVerified(BasePermission):
    """Allow access only to users with verified email addresses.

    Combine with IsJWTAuthenticated:
        permission_classes = [IsJWTAuthenticated, IsEmailVerified]
    """

    message = "Email address must be verified to access this resource."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_email_verified", False)
        )


class IsOrganizationMember(BasePermission):
    """Object-level permission: request.user must belong to the organization.

    Usage in views:
        permission_classes = [IsJWTAuthenticated, IsOrganizationMember]

    The view must pass org_id via URL kwargs (key ``org_id``).
    """

    message = "You are not a member of this organization."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        org_id = view.kwargs.get("org_id")
        if not org_id:
            return True  # No org scoping on this view.
        return _is_org_member(request.user, org_id)


class IsOrganizationAdmin(BasePermission):
    """The requesting user must be an admin of the specified organization.

    The view must pass org_id via URL kwargs (key ``org_id``).
    """

    message = "You must be an organization admin to perform this action."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        org_id = view.kwargs.get("org_id")
        if not org_id:
            return False
        return _is_org_admin(request.user, org_id)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _is_org_member(user, org_id) -> bool:
    try:
        from apps.organizations.models import OrganizationMembership
        return OrganizationMembership.objects.filter(
            organization_id=org_id,
            user=user,
        ).exists()
    except Exception:
        return False


def _is_org_admin(user, org_id) -> bool:
    try:
        from apps.organizations.models import OrganizationMembership
        return OrganizationMembership.objects.filter(
            organization_id=org_id,
            user=user,
            role__in=["owner", "admin"],
        ).exists()
    except Exception:
        return False
