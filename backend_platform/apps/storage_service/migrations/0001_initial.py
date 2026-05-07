"""Original initial migration — reconstructed as a stub.

The stored_files table was created by the original migration.
This stub keeps the migration graph consistent so that 0002 can depend on it.
"""
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StoredFile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("provider", models.CharField(default="local", max_length=50)),
                ("file_key", models.CharField(db_index=True, max_length=512)),
                ("original_name", models.CharField(max_length=512)),
                ("mime_type", models.CharField(blank=True, max_length=255)),
                ("size", models.BigIntegerField(default=0)),
                ("is_public", models.BooleanField(default=False)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stored_files",
                        to="organizations.organization",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="uploaded_files",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "stored_files",
                "ordering": ["-created_at"],
            },
        ),
    ]
