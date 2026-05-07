"""Migration: Add FileForge-style fields to StoredFile and create StorageCredential.

Adds to stored_files:
  - provider_file_id
  - url
  - status
  - error_message
  - upload_strategy
  - temp_path
  - new indexes

Creates:
  - storage_credentials table
"""
from __future__ import annotations

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("storage_service", "0001_initial"),
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------
        # Add new fields to stored_files
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name="storedfile",
            name="provider_file_id",
            field=models.CharField(blank=True, db_index=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name="storedfile",
            name="url",
            field=models.URLField(blank=True, max_length=2048, null=True),
        ),
        migrations.AddField(
            model_name="storedfile",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("uploading", "Uploading"),
                    ("completed", "Completed"),
                    ("failed", "Failed"),
                ],
                db_index=True,
                default="completed",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="storedfile",
            name="error_message",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="storedfile",
            name="upload_strategy",
            field=models.CharField(blank=True, default="sync", max_length=16),
        ),
        migrations.AddField(
            model_name="storedfile",
            name="temp_path",
            field=models.CharField(blank=True, default="", max_length=1024),
        ),
        # ------------------------------------------------------------------
        # Add composite indexes to stored_files
        # ------------------------------------------------------------------
        migrations.AddIndex(
            model_name="storedfile",
            index=models.Index(fields=["organization", "provider"], name="sf_org_prov_idx"),
        ),
        migrations.AddIndex(
            model_name="storedfile",
            index=models.Index(fields=["status"], name="sf_status_idx"),
        ),
        # ------------------------------------------------------------------
        # Create storage_credentials table
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="StorageCredential",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("provider", models.CharField(max_length=64)),
                ("credentials", models.JSONField(default=dict)),
                ("is_default", models.BooleanField(default=True)),
                (
                    "organization",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="storage_credentials",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={
                "db_table": "storage_credentials",
                "ordering": ["organization", "provider"],
            },
        ),
        migrations.AddConstraint(
            model_name="storagecredential",
            constraint=models.UniqueConstraint(
                fields=["organization", "provider"],
                name="uniq_org_provider_credential",
            ),
        ),
        # ------------------------------------------------------------------
        # Update db_table meta for stored_files (already named correctly)
        # ------------------------------------------------------------------
        migrations.AlterModelOptions(
            name="storedfile",
            options={"ordering": ["-created_at"]},
        ),
    ]
