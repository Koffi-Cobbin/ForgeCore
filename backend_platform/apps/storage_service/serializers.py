"""Storage serializers — adapted from FileForge for organization-aware architecture."""
from __future__ import annotations

from rest_framework import serializers

from .models import StoredFile, StorageCredential
from .providers import registry

MASKED_SENTINEL = "***"


def mask_credentials(credentials: dict) -> dict:
    """Mask sensitive credential values for API responses."""
    sensitive_keys = {
        "api_secret", "api_key", "aws_secret_access_key", "service_account_json",
        "oauth2_client_secret", "oauth2_refresh_token", "password", "secret",
    }
    masked = {}
    for key, value in credentials.items():
        if any(s in key.lower() for s in ("secret", "password", "token", "key")):
            masked[key] = MASKED_SENTINEL
        else:
            masked[key] = value
    return masked


def merge_credentials(existing: dict, incoming: dict) -> dict:
    """Merge incoming into existing, skipping masked sentinel values.

    When the frontend sends '***' for a field it did not change, that
    field is left untouched so the stored secret is preserved.
    """
    merged = dict(existing or {})
    for key, value in (incoming or {}).items():
        if value != MASKED_SENTINEL:
            merged[key] = value
    return merged


class StoredFileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    is_ready = serializers.ReadOnlyField()

    class Meta:
        model = StoredFile
        fields = [
            "id", "organization", "uploaded_by", "provider",
            "provider_file_id", "file_key", "original_name",
            "mime_type", "size", "url", "status", "error_message",
            "is_public", "upload_strategy", "metadata",
            "is_ready", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "provider_file_id", "url", "status", "error_message",
            "upload_strategy", "created_at", "updated_at",
        ]

    def get_url(self, obj: StoredFile) -> str | None:
        if obj.status != "completed":
            return obj.url or None
        try:
            if obj.is_public:
                return StorageManager_get_url(obj)
            return StorageManager_get_signed_url(obj)
        except Exception:
            return obj.url or None


def StorageManager_get_url(obj: StoredFile) -> str:
    from .services import StorageManager
    file_id = obj.provider_file_id or obj.file_key
    return StorageManager.get_url(obj.provider, file_id, organization_id=obj.organization_id)


def StorageManager_get_signed_url(obj: StoredFile) -> str:
    from .services import StorageManager
    file_id = obj.provider_file_id or obj.file_key
    return StorageManager.get_signed_url(obj.provider, file_id, organization_id=obj.organization_id)


class FileUploadSerializer(serializers.Serializer):
    """Body for POST /organizations/{org_id}/files/ (multipart).

    mode controls execution:
      sync  — upload performed within the request cycle (default for small files)
      async — file queued for background upload, returns immediately with status: pending
    """
    file = serializers.FileField()
    provider = serializers.CharField(default="local")
    mode = serializers.ChoiceField(choices=["async", "sync"], default="sync", required=False)
    is_public = serializers.BooleanField(default=False, required=False)

    def validate_provider(self, value: str) -> str:
        if value not in registry:
            raise serializers.ValidationError(
                f"Unknown provider {value!r}. Available: {registry.names()}"
            )
        return value


class DirectUploadInitSerializer(serializers.Serializer):
    """Body for POST /organizations/{org_id}/files/direct-upload/"""
    name = serializers.CharField()
    provider = serializers.CharField()
    size = serializers.IntegerField(min_value=0)
    content_type = serializers.CharField(required=False, allow_blank=True)

    def validate_provider(self, value: str) -> str:
        if value not in registry:
            raise serializers.ValidationError(
                f"Unknown provider {value!r}. Available: {registry.names()}"
            )
        return value


class DirectUploadCompleteSerializer(serializers.Serializer):
    """Body for POST /organizations/{org_id}/files/direct-upload/complete/"""
    file_id = serializers.UUIDField()
    provider_file_id = serializers.CharField(required=False, allow_blank=True)
    url = serializers.URLField(required=False, allow_blank=True)
    provider_response = serializers.JSONField(required=False)


class StorageCredentialSerializer(serializers.ModelSerializer):
    """Credentials serializer — masks sensitive values in responses."""

    class Meta:
        model = StorageCredential
        fields = [
            "id", "organization", "provider", "credentials",
            "is_default", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]

    def validate_provider(self, value: str) -> str:
        if value not in registry:
            raise serializers.ValidationError(
                f"Unknown provider {value!r}. Available: {registry.names()}"
            )
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["credentials"] = mask_credentials(instance.credentials or {})
        return data

    def update(self, instance, validated_data):
        incoming_creds = validated_data.pop("credentials", {})
        instance.credentials = merge_credentials(instance.credentials or {}, incoming_creds)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ProviderListSerializer(serializers.Serializer):
    name = serializers.CharField()
    supports_direct_upload = serializers.BooleanField()
    supports_streaming = serializers.BooleanField()
