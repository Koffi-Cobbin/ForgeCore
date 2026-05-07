from django.db import transaction
from .models import Organization, Membership
from apps.users.models import User
from apps.common.exceptions import NotFoundError, PermissionDeniedError, ConflictError


class OrganizationService:
    @staticmethod
    @transaction.atomic
    def create_organization(user, data):
        org = Organization.objects.create(**data)
        Membership.objects.create(
            user=user,
            organization=org,
            role='owner',
            is_active=True
        )
        return org

    @staticmethod
    def get_organization(org_id):
        try:
            return Organization.objects.get(id=org_id, is_active=True)
        except Organization.DoesNotExist:
            raise NotFoundError('Organization not found')

    @staticmethod
    def get_user_organizations(user):
        return Organization.objects.filter(
            memberships__user=user,
            memberships__is_active=True,
            is_active=True
        ).distinct()

    @staticmethod
    def update_organization(org, data):
        allowed_fields = ['name', 'description', 'logo_url', 'website', 'metadata']
        for field in allowed_fields:
            if field in data:
                setattr(org, field, data[field])
        org.save()
        return org

    @staticmethod
    def invite_member(org, invited_by, email, role='member'):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise NotFoundError(f'No user found with email {email}')

        if Membership.objects.filter(user=user, organization=org, is_active=True).exists():
            raise ConflictError('User is already a member of this organization')

        membership = Membership.objects.create(
            user=user,
            organization=org,
            role=role,
            invited_by=invited_by,
            is_active=True
        )
        return membership

    @staticmethod
    def remove_member(org, user_id, requesting_user):
        try:
            membership = Membership.objects.get(
                organization=org,
                user_id=user_id,
                is_active=True
            )
        except Membership.DoesNotExist:
            raise NotFoundError('Membership not found')

        if membership.role == 'owner':
            raise PermissionDeniedError('Cannot remove the organization owner')

        membership.is_active = False
        membership.save()
        return membership

    @staticmethod
    def update_member_role(org, user_id, new_role, requesting_user):
        try:
            membership = Membership.objects.get(
                organization=org,
                user_id=user_id,
                is_active=True
            )
        except Membership.DoesNotExist:
            raise NotFoundError('Membership not found')

        if membership.role == 'owner' and new_role != 'owner':
            raise PermissionDeniedError('Cannot change the owner role directly')

        membership.role = new_role
        membership.save()
        return membership
