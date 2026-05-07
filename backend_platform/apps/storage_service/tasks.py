"""Async file upload tasks — ported from FileForge, using ForgeCore's TaskDispatcher.

Tasks must be dispatched via TaskDispatcher, never called via async_task directly.
"""
from __future__ import annotations

import logging
from pathlib import Path

from django.utils import timezone

from .models import StoredFile, FileStatus
from .services import StorageManager
from .utils import delete_temp_file

logger = logging.getLogger(__name__)


def process_file_upload(file_id: str) -> dict:
    """Upload the temp file backing StoredFile(id=file_id) to its provider.

    Status transitions: pending → uploading → completed | failed.
    The temp file is deleted regardless of outcome.
    """
    try:
        file_obj = StoredFile.objects.get(pk=file_id)
    except StoredFile.DoesNotExist:
        logger.warning("process_file_upload: StoredFile %s no longer exists", file_id)
        return {"ok": False, "reason": "file_missing"}

    temp_path = file_obj.temp_path
    if not temp_path or not Path(temp_path).exists():
        file_obj.status = FileStatus.FAILED
        file_obj.error_message = "Temp file missing before upload."
        file_obj.save(update_fields=["status", "error_message", "updated_at"])
        return {"ok": False, "reason": "temp_missing"}

    file_obj.status = FileStatus.UPLOADING
    file_obj.save(update_fields=["status", "updated_at"])

    try:
        with open(temp_path, "rb") as fh:
            result = StorageManager.upload(
                fh,
                provider=file_obj.provider,
                path=file_obj.file_key or file_obj.original_name,
                organization_id=file_obj.organization_id,
                content_type=file_obj.mime_type or None,
                size=file_obj.size or None,
            )

        file_obj.provider_file_id = result.provider_file_id
        file_obj.url = result.url or ""
        merged_meta = dict(file_obj.metadata or {})
        merged_meta.update(result.metadata or {})
        file_obj.metadata = merged_meta
        file_obj.status = FileStatus.COMPLETED
        file_obj.error_message = ""
        file_obj.save(update_fields=[
            "provider_file_id", "url", "metadata",
            "status", "error_message", "updated_at",
        ])
        logger.info("process_file_upload: completed file %s via %s", file_id, file_obj.provider)
        return {"ok": True, "file_id": str(file_id)}

    except Exception as exc:
        logger.exception("process_file_upload: upload failed for file %s", file_id)
        file_obj.status = FileStatus.FAILED
        file_obj.error_message = str(exc)[:2000]
        file_obj.save(update_fields=["status", "error_message", "updated_at"])
        return {"ok": False, "file_id": str(file_id), "error": str(exc)}

    finally:
        delete_temp_file(temp_path)
        StoredFile.objects.filter(pk=file_id).update(
            temp_path="", updated_at=timezone.now()
        )


def cleanup_temp_files() -> dict:
    """Periodic cleanup target — removes stale temp files."""
    from .utils import cleanup_orphaned_temp_files
    removed = cleanup_orphaned_temp_files()
    return {"ok": True, "removed": removed}
