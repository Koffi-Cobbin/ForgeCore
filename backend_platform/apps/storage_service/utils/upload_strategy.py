"""Upload strategy — ported from FileForge.

Decides whether to use server-side async upload or direct-to-provider upload
based on file size vs a per-provider threshold.
"""
from __future__ import annotations

from django.conf import settings


def get_max_sync_size(provider: str) -> int:
    """Resolve the per-provider sync size threshold (bytes).

    Can be overridden in settings via FILEFORGE_PROVIDER_MAX_SYNC_SIZE dict.
    Defaults to FILEFORGE_DEFAULT_MAX_SYNC_SIZE (default 5 MB).
    """
    overrides = getattr(settings, "FILEFORGE_PROVIDER_MAX_SYNC_SIZE", {}) or {}
    if provider in overrides:
        return int(overrides[provider])
    return int(getattr(settings, "FILEFORGE_DEFAULT_MAX_SYNC_SIZE", 5 * 1024 * 1024))


def should_use_direct_upload(provider: str, size: int) -> bool:
    """Return True when size exceeds the provider's sync threshold.

    If True, callers should direct the client to upload directly to the
    provider using the generate_upload_url flow.
    """
    return int(size) > get_max_sync_size(provider)
