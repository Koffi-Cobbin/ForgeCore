import uuid
from django.db import models
from django.conf import settings
from apps.common.models import BaseModel


class Organization(BaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=100)
    description = models.TextField(blank=True)
    logo_url = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'organizations'
        ordering = ['name']

    def __str__(self):
        return self.name


class Membership(BaseModel):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships',
        db_index=True
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='memberships',
        db_index=True
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sent_invitations'
    )

    class Meta:
        db_table = 'memberships'
        unique_together = [['user', 'organization']]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} @ {self.organization.name} ({self.role})"
