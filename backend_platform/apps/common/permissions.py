from rest_framework.permissions import BasePermission
from apps.organizations.models import Membership


class IsOrganizationMember(BasePermission):
    def has_permission(self, request, view):
        org_id = view.kwargs.get('org_id') or request.data.get('organization')
        if not org_id:
            return False
        return Membership.objects.filter(
            user=request.user,
            organization_id=org_id,
            is_active=True
        ).exists()


class IsOrganizationAdmin(BasePermission):
    def has_permission(self, request, view):
        org_id = view.kwargs.get('org_id') or request.data.get('organization')
        if not org_id:
            return False
        return Membership.objects.filter(
            user=request.user,
            organization_id=org_id,
            role__in=['owner', 'admin'],
            is_active=True
        ).exists()


class IsOrganizationOwner(BasePermission):
    def has_permission(self, request, view):
        org_id = view.kwargs.get('org_id') or request.data.get('organization')
        if not org_id:
            return False
        return Membership.objects.filter(
            user=request.user,
            organization_id=org_id,
            role='owner',
            is_active=True
        ).exists()
