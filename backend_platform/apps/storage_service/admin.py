"""Admin registrations for storage service models."""
from django.contrib import admin
from .models import StoredFile, StorageCredential


@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = ("id", "original_name", "provider", "organization", "size", "status", "created_at")
    list_filter = ("provider", "status", "is_public", "created_at")
    search_fields = ("original_name", "provider_file_id", "file_key")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(StorageCredential)
class StorageCredentialAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "provider", "is_default", "created_at")
    list_filter = ("provider", "is_default")
    search_fields = ("organization__name",)
    readonly_fields = ("id", "created_at", "updated_at")
