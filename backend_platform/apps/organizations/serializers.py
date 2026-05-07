from rest_framework import serializers
from .models import Organization, Membership
from apps.users.serializers import UserSerializer


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'description', 'logo_url',
            'website', 'is_active', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrganizationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['name', 'slug', 'description', 'logo_url', 'website']

    def validate_slug(self, value):
        # FIX: exclude the current instance when checking uniqueness (supports partial PATCH)
        qs = Organization.objects.filter(slug=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('An organization with this slug already exists.')
        return value


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = Membership
        fields = [
            'id', 'user', 'organization', 'organization_name',
            'role', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=['admin', 'member', 'viewer'], default='member')