"""StorageManager — single entry point for all storage operations.

Ported from FileForge and adapted for ForgeCore's organization-aware architecture.
Views and tasks must talk to this module instead of importing providers directly.

The manager is responsible for:
  * Resolving the provider class from the registry.
  * Merging environment-level credentials with per-org credentials stored
    in StorageCredential.
  * Instantiating the provider and routing the call.
"""
from __future__ import annotations

from typing import Any, BinaryIO, Generator, Mapping

from django.conf import settings

from ..providers import (
    BaseStorageProvider,
    DirectUploadTicket,
    ProviderConfigurationError,
    UploadResult,
    registry,
)


def _resolve_credentials(provider: str, organization_id=None) -> dict[str, Any]:
    """Merge env defaults with the organization's stored credentials.

    Org credentials win over env defaults.
    """
    env_defaults = (
        getattr(settings, "FILEFORGE_PROVIDER_ENV_CREDENTIALS", {}) or {}
    ).get(provider, {}) or {}
    merged: dict[str, Any] = {
        k: v for k, v in env_defaults.items() if v not in (None, "")
    }
    if organization_id:
        try:
            from ..models import StorageCredential
            cred = StorageCredential.objects.get(organization_id=organization_id, provider=provider)
            for k, v in (cred.credentials or {}).items():
                if v not in (None, ""):
                    merged[k] = v
        except Exception:
            pass
    return merged


def _build_provider(provider: str, organization_id=None) -> BaseStorageProvider:
    if provider not in registry:
        raise ProviderConfigurationError(
            f"Unknown provider {provider!r}. Available: {registry.names()}"
        )
    creds = _resolve_credentials(provider, organization_id)
    provider_cls = registry.get(provider)
    return provider_cls(credentials=creds)


class StorageManager:
    """Stateless orchestrator that routes calls to the right provider.

    Mirrors FileForge's StorageManager interface.
    """

    @staticmethod
    def list_providers() -> list[dict[str, Any]]:
        return [
            {
                "name": name,
                "supports_direct_upload": cls.supports_direct_upload,
                "supports_streaming": cls.supports_streaming,
            }
            for name, cls in sorted(registry.items())
        ]

    @staticmethod
    def has_provider(name: str) -> bool:
        return name in registry

    @staticmethod
    def upload(
        file: BinaryIO,
        *,
        provider: str,
        path: str,
        organization_id=None,
        content_type: str | None = None,
        size: int | None = None,
        **kwargs: Any,
    ) -> UploadResult:
        return _build_provider(provider, organization_id).upload(
            file, path, content_type=content_type, size=size, **kwargs
        )

    @staticmethod
    def download(
        provider: str,
        file_id: str,
        *,
        organization_id=None,
        **kwargs: Any,
    ) -> bytes:
        return _build_provider(provider, organization_id).download(file_id, **kwargs)

    @staticmethod
    def delete(
        provider: str,
        file_id: str,
        *,
        organization_id=None,
        **kwargs: Any,
    ) -> None:
        _build_provider(provider, organization_id).delete(file_id, **kwargs)

    @staticmethod
    def update(
        provider: str,
        file_id: str,
        *,
        organization_id=None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return _build_provider(provider, organization_id).update(file_id, **kwargs)

    @staticmethod
    def get_url(
        provider: str,
        file_id: str,
        *,
        organization_id=None,
        **kwargs: Any,
    ) -> str:
        return _build_provider(provider, organization_id).get_url(file_id, **kwargs)

    @staticmethod
    def get_signed_url(
        provider: str,
        file_id: str,
        *,
        organization_id=None,
        expires_in: int = 3600,
        **kwargs: Any,
    ) -> str:
        return _build_provider(provider, organization_id).generate_signed_url(
            file_id, expires_in=expires_in, **kwargs
        )

    @staticmethod
    def generate_upload_url(
        provider: str,
        path: str,
        *,
        organization_id=None,
        content_type: str | None = None,
        size: int | None = None,
        **kwargs: Any,
    ) -> DirectUploadTicket:
        return _build_provider(provider, organization_id).generate_upload_url(
            path, content_type=content_type, size=size, **kwargs
        )

    @staticmethod
    def finalize_direct_upload(
        provider: str,
        data: Mapping[str, Any],
        *,
        organization_id=None,
    ) -> UploadResult:
        return _build_provider(provider, organization_id).finalize_direct_upload(data)

    @staticmethod
    def stream(
        provider: str,
        file_id: str,
        *,
        organization_id=None,
        start: int = 0,
        end: int | None = None,
        **kwargs: Any,
    ) -> Generator[bytes, None, None]:
        return _build_provider(provider, organization_id).stream(
            file_id, start=start, end=end, **kwargs
        )
