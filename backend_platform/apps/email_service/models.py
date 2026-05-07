from django.db import models
from django.conf import settings
from apps.common.models import BaseModel


class EmailLog(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='email_logs',
        db_index=True
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sent_emails'
    )
    to_email = models.EmailField(db_index=True)
    subject = models.CharField(max_length=512)
    template = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    provider = models.CharField(max_length=50, default='django')
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'email_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} → {self.to_email} ({self.status})"
