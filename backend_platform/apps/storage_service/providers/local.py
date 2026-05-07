"""Local filesystem storage provider."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, BinaryIO, Generator, Mapping

from django.conf import settings

from .base import BaseStorageProvider, UploadResult


class LocalStorageProvider(BaseStorageProvider):
    """Store files on the local filesystem under STORAGE_LOCAL_ROOT."""

    name = "local"
    supports_direct_upload = False
    supports_streaming = True

    def __init__(self, credentials: Mapping[str, Any] | None = None) -> None:
        super().__init__(credentials)
        self.root = Path(
            credentials.get("root") if credentials else None
            or getattr(settings, "STORAGE_LOCAL_ROOT", None)
            or (Path(settings.MEDIA_ROOT) / "uploads")
        )
        self.root.mkdir(parents=True, exist_ok=True)

    def upload(
        self,
        file: BinaryIO,
        path: str,
        *,
        content_type: str | None = None,
        size: int | None = None,
        **kwargs: Any,
    ) -> UploadResult:
        file_path = self.root / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(file, "chunks"):
            with open(file_path, "wb") as f:
                for chunk in file.chunks():
                    f.write(chunk)
        else:
            with open(file_path, "wb") as f:
                while True:
                    chunk = file.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
        url = self.get_url(path)
        return UploadResult(provider_file_id=path, url=url, metadata={})

    def download(self, file_id: str, **kwargs: Any) -> bytes:
        file_path = self.root / file_id
        with open(file_path, "rb") as f:
            return f.read()

    def stream(
        self,
        file_id: str,
        *,
        start: int = 0,
        end: int | None = None,
        **kwargs: Any,
    ) -> Generator[bytes, None, None]:
        file_path = self.root / file_id
        chunk_size = 1024 * 1024
        with open(file_path, "rb") as f:
            f.seek(start)
            bytes_left = (end - start + 1) if end is not None else None
            while True:
                to_read = chunk_size if bytes_left is None else min(chunk_size, bytes_left)
                chunk = f.read(to_read)
                if not chunk:
                    break
                yield chunk
                if bytes_left is not None:
                    bytes_left -= len(chunk)
                    if bytes_left <= 0:
                        break

    def delete(self, file_id: str, **kwargs: Any) -> None:
        file_path = self.root / file_id
        if file_path.exists():
            os.remove(file_path)

    def update(self, file_id: str, **kwargs: Any) -> dict[str, Any]:
        new_name = kwargs.get("name") or kwargs.get("new_public_id")
        if new_name:
            old_path = self.root / file_id
            new_path = self.root / new_name
            new_path.parent.mkdir(parents=True, exist_ok=True)
            old_path.rename(new_path)
            return {"file_id": new_name}
        return {"file_id": file_id}

    def get_url(self, file_id: str, **kwargs: Any) -> str:
        return f"{settings.MEDIA_URL}uploads/{file_id}"

    def generate_signed_url(self, file_id: str, expires_in: int = 3600, **kwargs: Any) -> str:
        return self.get_url(file_id)

    def get_provider_name(self) -> str:
        return "local"
