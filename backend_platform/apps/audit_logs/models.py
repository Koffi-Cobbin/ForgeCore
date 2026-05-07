from django.db import models
from django.conf import settings
from apps.common.models import BaseModel


class AuditLog(BaseModel):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='audit_logs',
        db_index=True,
        null=True, blank=True
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        db_index=True
    )
    action = models.CharField(max_length=255, db_index=True)
    resource_type = models.CharField(max_length=100, blank=True, db_index=True)
    resource_id = models.CharField(max_length=255, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(max_length=255, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, default='success')

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'action']),
            models.Index(fields=['actor', 'created_at']),
        ]

    def __str__(self):
        return f"{self.action} by {self.actor} @ {self.created_at}"
