"""User serializers — pure I/O contracts.

No business logic here. Profile mutations go through UserService.
"""
from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User


class OrganizationMembershipSerializer(serializers.Serializer):
    """Lightweight org membership summary embedded in UserSerializer."""
    id = serializers.UUIDField()
    name = serializers.CharField()
    role = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    """Full read-only representation of the authenticated user.

    Includes a lightweight list of organization memberships so the
    client can bootstrap without an extra round-trip.
    """

    full_name = serializers.ReadOnlyField()
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_active",
            "is_email_verified",
            "mfa_enabled",
            "avatar_url",
            "phone_number",
            "organizations",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "email", "is_active", "is_email_verified",
            "mfa_enabled", "created_at", "updated_at",
        ]

    def get_organizations(self, user) -> list[dict]:
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
        except Exception:
            return []


class UserUpdateSerializer(serializers.Serializer):
    """Writable fields for PATCH /users/me/."""
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    avatar_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Input for POST /users/me/change-password/."""
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate_new_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value
