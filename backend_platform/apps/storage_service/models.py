from django.db import models
from django.conf import settings
from apps.common.models import BaseModel


class StoredFile(BaseModel):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='stored_files',
        db_index=True
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_files'
    )
    provider = models.CharField(max_length=50, default='local')
    file_key = models.CharField(max_length=512, db_index=True)
    original_name = models.CharField(max_length=512)
    mime_type = models.CharField(max_length=255, blank=True)
    size = models.BigIntegerField(default=0)
    is_public = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'stored_files'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_name} ({self.provider})"
