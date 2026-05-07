"""Storage models — evolved from FileForge's File and StorageCredential models,
adapted for ForgeCore's organization-aware architecture.
"""
from __future__ import annotations

from django.db import models
from django.conf import settings
from apps.common.models import BaseModel


class FileStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    UPLOADING = "uploading", "Uploading"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class StoredFile(BaseModel):
    """A file tracked by ForgeCore's storage service.

    Maps to exactly ONE storage provider. Tracks status through the upload
    lifecycle: pending → uploading → completed | failed.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="stored_files",
        db_index=True,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_files",
    )
    provider = models.CharField(max_length=64, db_index=True)
    provider_file_id = models.CharField(max_length=512, null=True, blank=True, db_index=True)
    file_key = models.CharField(max_length=512, db_index=True, blank=True)
    original_name = models.CharField(max_length=512)
    mime_type = models.CharField(max_length=255, blank=True)
    size = models.BigIntegerField(default=0)
    url = models.URLField(max_length=2048, null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=FileStatus.choices,
        default=FileStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True, default="")
    is_public = models.BooleanField(default=False)
    upload_strategy = models.CharField(max_length=16, blank=True, default="sync")
    temp_path = models.CharField(max_length=1024, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "stored_files"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "provider"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"StoredFile(name={self.original_name!r}, provider={self.provider}, status={self.status})"

    @property
    def is_ready(self) -> bool:
        return self.status == FileStatus.COMPLETED


class StorageCredential(BaseModel):
    """Per-organization credentials for a single storage provider.

    Credentials is a JSON blob whose shape is provider-specific. The
    StorageManager merges these with environment-level defaults before
    instantiating the provider. Sensitive values should never be returned
    directly to clients — mask them first.

    Ported from FileForge's StorageCredential (owner → organization FK).
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="storage_credentials",
        db_index=True,
    )
    provider = models.CharField(max_length=64)
    credentials = models.JSONField(default=dict)
    is_default = models.BooleanField(default=True)

    class Meta:
        db_table = "storage_credentials"
        ordering = ["organization", "provider"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "provider"],
                name="uniq_org_provider_credential",
            )
        ]

    def __str__(self) -> str:
        return f"StorageCredential(org={self.organization_id}, provider={self.provider})"
