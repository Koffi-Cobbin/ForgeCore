import uuid
from django.db import models
from django.conf import settings
from apps.common.models import BaseModel


class APIKey(BaseModel):
    name = models.CharField(max_length=255)
    key_prefix = models.CharField(max_length=10, db_index=True)
    key_hash = models.CharField(max_length=256, unique=True, db_index=True)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='api_keys',
        db_index=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='api_keys'
    )
    scopes = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'api_keys'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        from django.utils import timezone
        return self.expires_at < timezone.now()
