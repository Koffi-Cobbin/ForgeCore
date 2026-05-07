import secrets
import hashlib
from django.utils import timezone
from .models import APIKey
from apps.common.exceptions import NotFoundError, PermissionDeniedError


class APIKeyService:
    KEY_PREFIX_LENGTH = 8

    @staticmethod
    def generate_key():
        raw_key = secrets.token_urlsafe(32)
        prefix = raw_key[:APIKeyService.KEY_PREFIX_LENGTH]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return raw_key, prefix, key_hash

    @staticmethod
    def create_api_key(organization, user, name, scopes=None, expires_at=None, metadata=None):
        raw_key, prefix, key_hash = APIKeyService.generate_key()
        api_key = APIKey.objects.create(
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            organization=organization,
            created_by=user,
            scopes=scopes or [],
            expires_at=expires_at,
            metadata=metadata or {},
        )
        return api_key, raw_key

    @staticmethod
    def list_api_keys(organization):
        return APIKey.objects.filter(organization=organization, is_active=True)

    @staticmethod
    def get_api_key(key_id, organization):
        try:
            return APIKey.objects.get(id=key_id, organization=organization, is_active=True)
        except APIKey.DoesNotExist:
            raise NotFoundError('API key not found')

    @staticmethod
    def revoke_api_key(key_id, organization, user):
        key = APIKeyService.get_api_key(key_id, organization)
        key.is_active = False
        key.save()
        return key
