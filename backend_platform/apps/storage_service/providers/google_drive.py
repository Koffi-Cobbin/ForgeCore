"""Google Drive storage provider — ported from FileForge.

Authentication modes (in priority order):
  1. OAuth2 refresh token — credentials keys:
       oauth2_client_id, oauth2_client_secret, oauth2_refresh_token
  2. Service account — credentials keys:
       service_account_json  (JSON string or dict)
       OR service_account_file (filesystem path to the JSON key file)

Optional: folder_id — parent Drive folder ID to upload files into.
"""
from __future__ import annotations

import io
import json
import logging
from typing import Any, BinaryIO, Generator, Mapping

from .base import (
    BaseStorageProvider,
    DirectUploadTicket,
    ProviderConfigurationError,
    ProviderError,
    UploadResult,
)

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/drive"]
_CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB


class GoogleDriveProvider(BaseStorageProvider):
    """Upload, download, stream, and manage files in Google Drive.

    Ported from FileForge with full OAuth2 and service account support.
    """

    name = "google_drive"
    supports_direct_upload = True
    supports_streaming = True

    def __init__(self, credentials: Mapping[str, Any] | None = None) -> None:
        super().__init__(credentials)
        self._service = None

    def _build_service(self):
        if self._service is not None:
            return self._service
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise ProviderConfigurationError(
                "google-api-python-client is not installed. "
                "Install with: pip install google-api-python-client google-auth"
            ) from exc
        creds = self._build_oauth2_credentials() or self._build_service_account_credentials()
        if creds is None:
            raise ProviderConfigurationError(
                "Google Drive provider requires OAuth2 credentials "
                "(oauth2_client_id / oauth2_client_secret / oauth2_refresh_token) "
                "or service-account credentials (service_account_json or service_account_file)."
            )
        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def _build_oauth2_credentials(self):
        client_id = self.credentials.get("oauth2_client_id")
        client_secret = self.credentials.get("oauth2_client_secret")
        refresh_token = self.credentials.get("oauth2_refresh_token")
        if not all([client_id, client_secret, refresh_token]):
            return None
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
        except ImportError as exc:
            raise ProviderConfigurationError("google-auth is not installed") from exc
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=_SCOPES,
        )
        if not creds.valid:
            creds.refresh(Request())
        logger.info("Google Drive: authenticated via OAuth2 refresh token")
        return creds

    def _build_service_account_credentials(self):
        sa_json = self.credentials.get("service_account_json")
        sa_file = self.credentials.get("service_account_file")
        if not sa_json and not sa_file:
            return None
        try:
            from google.oauth2 import service_account
        except ImportError as exc:
            raise ProviderConfigurationError("google-auth is not installed") from exc
        if sa_json:
            info = sa_json if isinstance(sa_json, dict) else json.loads(sa_json)
            creds = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
        else:
            creds = service_account.Credentials.from_service_account_file(sa_file, scopes=_SCOPES)
        logger.info("Google Drive: authenticated via service account")
        return creds

    def _refresh_token_if_needed(self, creds) -> None:
        if not creds.valid:
            from google.auth.transport.requests import Request as GAuthRequest
            creds.refresh(GAuthRequest())

    def _folder_id(self) -> str | None:
        return self.credentials.get("folder_id") or None

    def upload(
        self,
        file: BinaryIO,
        path: str,
        *,
        content_type: str | None = None,
        size: int | None = None,
        **kwargs: Any,
    ) -> UploadResult:
        from googleapiclient.http import MediaIoBaseUpload
        service = self._build_service()
        if size is None and hasattr(file, "seek"):
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
        body: dict[str, Any] = {"name": path}
        folder_id = self._folder_id()
        if folder_id:
            body["parents"] = [folder_id]
        media = MediaIoBaseUpload(
            file,
            mimetype=content_type or "application/octet-stream",
            chunksize=_CHUNK_SIZE,
            resumable=True,
        )
        try:
            response = (
                service.files()
                .create(
                    body=body,
                    media_body=media,
                    fields="id, name, size, mimeType, webViewLink, webContentLink",
                    supportsAllDrives=True,
                )
                .execute()
            )
        except Exception as exc:
            raise ProviderError(f"Google Drive upload failed: {exc}") from exc
        logger.info("Google Drive: uploaded '%s' (file_id=%s)", path, response["id"])
        return UploadResult(
            provider_file_id=response["id"],
            url=response.get("webViewLink") or response.get("webContentLink"),
            metadata={
                "mime_type": response.get("mimeType"),
                "size": response.get("size"),
                "name": response.get("name"),
            },
        )

    def download(self, file_id: str, **kwargs: Any) -> bytes:
        buf = io.BytesIO()
        for chunk in self.stream(file_id):
            buf.write(chunk)
        return buf.getvalue()

    def stream(
        self,
        file_id: str,
        *,
        start: int = 0,
        end: int | None = None,
        **kwargs: Any,
    ) -> Generator[bytes, None, None]:
        from googleapiclient.http import MediaIoBaseDownload
        service = self._build_service()
        try:
            meta = (
                service.files()
                .get(fileId=file_id, fields="size, mimeType", supportsAllDrives=True)
                .execute()
            )
        except Exception as exc:
            raise ProviderError(f"Google Drive metadata fetch failed: {exc}") from exc
        total_size = int(meta.get("size", 0))
        if end is None or end >= total_size:
            end = total_size - 1
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request, chunksize=_CHUNK_SIZE)
        bytes_yielded = 0
        done = False
        while not done:
            try:
                _status, done = downloader.next_chunk()
            except Exception as exc:
                raise ProviderError(f"Google Drive stream failed: {exc}") from exc
            buffer.seek(0)
            chunk = buffer.read()
            buffer.seek(0)
            buffer.truncate(0)
            chunk_start = bytes_yielded
            chunk_end = bytes_yielded + len(chunk) - 1
            if chunk_end < start:
                bytes_yielded += len(chunk)
                continue
            if chunk_start > end:
                return
            slice_start = max(0, start - chunk_start)
            slice_end = min(len(chunk), end - chunk_start + 1)
            yield chunk[slice_start:slice_end]
            bytes_yielded += len(chunk)

    def delete(self, file_id: str, **kwargs: Any) -> None:
        service = self._build_service()
        try:
            service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        except Exception as exc:
            raise ProviderError(f"Google Drive delete failed: {exc}") from exc
        logger.info("Google Drive: deleted file_id=%s", file_id)

    def update(self, file_id: str, **kwargs: Any) -> dict[str, Any]:
        service = self._build_service()
        body: dict[str, Any] = {}
        if "name" in kwargs:
            body["name"] = kwargs["name"]
        try:
            response = (
                service.files()
                .update(
                    fileId=file_id,
                    body=body,
                    fields="id, name, mimeType, webViewLink, webContentLink",
                    supportsAllDrives=True,
                )
                .execute()
            )
        except Exception as exc:
            raise ProviderError(f"Google Drive update failed: {exc}") from exc
        logger.info("Google Drive: updated file_id=%s", file_id)
        return response

    def get_url(self, file_id: str, **kwargs: Any) -> str:
        service = self._build_service()
        try:
            response = (
                service.files()
                .get(fileId=file_id, fields="id, webViewLink, webContentLink", supportsAllDrives=True)
                .execute()
            )
        except Exception as exc:
            raise ProviderError(f"Google Drive get_url failed: {exc}") from exc
        return response.get("webViewLink") or response.get("webContentLink") or ""

    def generate_upload_url(
        self,
        path: str,
        *,
        content_type: str | None = None,
        size: int | None = None,
        **kwargs: Any,
    ) -> DirectUploadTicket:
        import requests as req_lib
        service = self._build_service()
        creds = service._http.credentials
        self._refresh_token_if_needed(creds)
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": content_type or "application/octet-stream",
        }
        if size is not None:
            headers["X-Upload-Content-Length"] = str(size)
        body: dict[str, Any] = {"name": path}
        folder_id = self._folder_id()
        if folder_id:
            body["parents"] = [folder_id]
        resp = req_lib.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true",
            headers=headers,
            data=json.dumps(body),
            timeout=30,
        )
        if resp.status_code >= 300:
            raise ProviderError(f"Failed to start Drive resumable upload: {resp.status_code} {resp.text}")
        session_url = resp.headers.get("Location")
        if not session_url:
            raise ProviderError("Drive did not return a resumable upload Location header.")
        return DirectUploadTicket(
            upload_url=session_url,
            method="PUT",
            headers={"Content-Type": content_type or "application/octet-stream"},
            provider_ref={"path": path},
        )

    def finalize_direct_upload(self, data: Mapping[str, Any]) -> UploadResult:
        provider_file_id = data.get("provider_file_id")
        if not provider_file_id:
            raise ProviderError("Google Drive finalize requires `provider_file_id`.")
        service = self._build_service()
        try:
            response = (
                service.files()
                .get(fileId=provider_file_id, fields="id, name, size, mimeType, webViewLink, webContentLink", supportsAllDrives=True)
                .execute()
            )
        except Exception as exc:
            raise ProviderError(f"Google Drive finalize lookup failed: {exc}") from exc
        return UploadResult(
            provider_file_id=response["id"],
            url=response.get("webViewLink") or response.get("webContentLink"),
            metadata={"mime_type": response.get("mimeType"), "size": response.get("size"), "name": response.get("name")},
        )

    def get_provider_name(self) -> str:
        return "google_drive"
