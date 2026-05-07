from rest_framework import serializers
from .models import APIKey


class APIKeySerializer(serializers.ModelSerializer):
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'key_prefix', 'organization', 'scopes',
            'is_active', 'is_expired', 'last_used_at', 'expires_at',
            'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'key_prefix', 'is_active', 'last_used_at', 'created_at', 'updated_at']


class APIKeyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    scopes = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    metadata = serializers.DictField(required=False, default=dict)


class APIKeyCreatedSerializer(serializers.ModelSerializer):
    key = serializers.CharField(read_only=True)
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'key', 'key_prefix', 'organization', 'scopes',
            'is_active', 'is_expired', 'expires_at', 'metadata', 'created_at'
        ]
