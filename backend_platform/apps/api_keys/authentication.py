import hashlib
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import APIKey


class APIKeyAuthentication(BaseAuthentication):
    keyword = 'Api-Key'

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith(f'{self.keyword} '):
            return None

        raw_key = auth_header[len(f'{self.keyword} '):]
        return self._authenticate_key(raw_key)

    def authenticate_header(self, request):
        return self.keyword

    def _authenticate_key(self, raw_key):
        if len(raw_key) < 10:
            raise AuthenticationFailed('Invalid API key format.')

        prefix = raw_key[:8]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        try:
            api_key = APIKey.objects.select_related('created_by').get(
                key_prefix=prefix,
                key_hash=key_hash,
                is_active=True
            )
        except APIKey.DoesNotExist:
            raise AuthenticationFailed('Invalid or revoked API key.')

        if api_key.is_expired:
            raise AuthenticationFailed('API key has expired.')

        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=['last_used_at'])

        return (api_key.created_by, api_key)
