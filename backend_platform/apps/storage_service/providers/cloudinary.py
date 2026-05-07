"""Cloudinary storage provider — ported from FileForge.

Credentials expected:
  cloud_name, api_key, api_secret  — preferred
  OR url — a cloudinary://api_key:api_secret@cloud_name URL

Optional:
  folder        — folder prefix prepended to uploads
  resource_type — "auto" (default), "image", "video", or "raw"
  api_proxy     — HTTP proxy URL
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, BinaryIO, Mapping

import certifi
from urllib3 import PoolManager, ProxyManager

from .base import (
    BaseStorageProvider,
    DirectUploadTicket,
    ProviderConfigurationError,
    ProviderError,
    UploadResult,
)

logger = logging.getLogger(__name__)


class CloudinaryProvider(BaseStorageProvider):
    """Upload, download, and delete files in Cloudinary.

    Ported from FileForge with per-instance urllib3 connectors for
    proper multi-tenant credential isolation.
    """

    name = "cloudinary"
    supports_direct_upload = True

    def __init__(self, credentials: Mapping[str, Any] | None = None) -> None:
        super().__init__(credentials)
        self._cloud_name: str = ""
        self._api_key: str = ""
        self._api_secret: str = ""
        self._http: PoolManager | ProxyManager | None = None

    def _parse_cloudinary_url(self, url: str) -> tuple[str, str, str]:
        without_scheme = url.replace("cloudinary://", "")
        auth, cloud = without_scheme.rsplit("@", 1)
        key, secret = auth.split(":", 1)
        return cloud.strip(), key.strip(), secret.strip()

    def _ensure_credentials(self) -> None:
        if self._cloud_name:
            return
        url = self.credentials.get("url")
        if url:
            self._cloud_name, self._api_key, self._api_secret = self._parse_cloudinary_url(url)
            return
        cloud = self.credentials.get("cloud_name", "").strip()
        key = self.credentials.get("api_key", "").strip()
        secret = self.credentials.get("api_secret", "").strip()
        if not (cloud and key and secret):
            raise ProviderConfigurationError(
                "Cloudinary provider requires either `url` or "
                "`cloud_name` + `api_key` + `api_secret` in credentials."
            )
        self._cloud_name = cloud
        self._api_key = key
        self._api_secret = secret

    def _get_http(self) -> PoolManager | ProxyManager:
        if self._http is not None:
            return self._http
        kwargs = {"cert_reqs": "CERT_REQUIRED", "ca_certs": certifi.where()}
        proxy = (self.credentials.get("api_proxy") or "").strip()
        if proxy:
            logger.info("Cloudinary: using proxy %r", proxy)
            self._http = ProxyManager(proxy, **kwargs)
        else:
            self._http = PoolManager(**kwargs)
        return self._http

    def _resource_type(self, override: str | None = None) -> str:
        return override or self.credentials.get("resource_type") or "auto"

    def _folder(self) -> str | None:
        return self.credentials.get("folder") or None

    def _sign(self, params: dict[str, Any]) -> str:
        to_sign = "&".join(
            f"{k}={v}"
            for k, v in sorted(params.items())
            if v not in (None, "")
        ) + self._api_secret
        return hashlib.sha1(to_sign.encode()).hexdigest()

    def _upload_url(self, resource_type: str) -> str:
        return f"https://api.cloudinary.com/v1_1/{self._cloud_name}/{resource_type}/upload"

    def upload(
        self,
        file: BinaryIO,
        path: str,
        *,
        content_type: str | None = None,
        size: int | None = None,
        **kwargs: Any,
    ) -> UploadResult:
        self._ensure_credentials()
        resource_type = self._resource_type(kwargs.get("resource_type"))
        timestamp = int(time.time())
        params: dict[str, Any] = {
            "public_id": path,
            "timestamp": timestamp,
            "overwrite": "true",
            "unique_filename": "false",
            "use_filename": "false",
        }
        folder = self._folder()
        if folder:
            params["folder"] = folder
        signature = self._sign(params)
        fields = {
            **{k: str(v) for k, v in params.items()},
            "api_key": self._api_key,
            "signature": signature,
        }
        file_bytes = file.read() if hasattr(file, "read") else b""
        fields["file"] = (path, file_bytes, content_type or "application/octet-stream")
        http = self._get_http()
        try:
            response = http.request("POST", self._upload_url(resource_type), fields=fields)
        except Exception as exc:
            raise ProviderError(f"Cloudinary upload failed: {exc}") from exc
        if response.status >= 400:
            raise ProviderError(
                f"Cloudinary upload returned {response.status}: {response.data.decode(errors='replace')}"
            )
        data = json.loads(response.data)
        return UploadResult(
            provider_file_id=data["public_id"],
            url=data.get("secure_url") or data.get("url"),
            metadata={
                "resource_type": data.get("resource_type"),
                "format": data.get("format"),
                "bytes": data.get("bytes"),
                "version": data.get("version"),
            },
        )

    def download(self, file_id: str, **kwargs: Any) -> bytes:
        url = self.get_url(file_id, **kwargs)
        http = self._get_http()
        try:
            response = http.request("GET", url)
        except Exception as exc:
            raise ProviderError(f"Cloudinary download failed: {exc}") from exc
        if response.status >= 300:
            raise ProviderError(f"Cloudinary download returned {response.status}")
        return response.data

    def delete(self, file_id: str, **kwargs: Any) -> None:
        self._ensure_credentials()
        resource_type = self._resource_type(kwargs.get("resource_type"))
        if resource_type == "auto":
            resource_type = "image"
        timestamp = int(time.time())
        params = {"public_id": file_id, "timestamp": timestamp}
        signature = self._sign(params)
        fields = {
            "public_id": file_id,
            "timestamp": str(timestamp),
            "api_key": self._api_key,
            "signature": signature,
        }
        url = f"https://api.cloudinary.com/v1_1/{self._cloud_name}/{resource_type}/destroy"
        http = self._get_http()
        try:
            response = http.request("POST", url, fields=fields)
        except Exception as exc:
            raise ProviderError(f"Cloudinary delete failed: {exc}") from exc
        data = json.loads(response.data)
        if data.get("result") not in {"ok", "not found"}:
            raise ProviderError(f"Cloudinary delete returned: {data!r}")

    def update(self, file_id: str, **kwargs: Any) -> dict[str, Any]:
        self._ensure_credentials()
        resource_type = self._resource_type(kwargs.get("resource_type"))
        if resource_type == "auto":
            resource_type = "image"
        new_id = kwargs.get("new_public_id") or kwargs.get("name")
        if not new_id:
            raise ProviderError("Cloudinary update requires `new_public_id` or `name`.")
        timestamp = int(time.time())
        params = {"from_public_id": file_id, "to_public_id": new_id, "timestamp": timestamp, "overwrite": "true"}
        signature = self._sign(params)
        fields = {**{k: str(v) for k, v in params.items()}, "api_key": self._api_key, "signature": signature}
        url = f"https://api.cloudinary.com/v1_1/{self._cloud_name}/{resource_type}/rename"
        http = self._get_http()
        try:
            response = http.request("POST", url, fields=fields)
        except Exception as exc:
            raise ProviderError(f"Cloudinary update failed: {exc}") from exc
        return json.loads(response.data)

    def get_url(self, file_id: str, **kwargs: Any) -> str:
        self._ensure_credentials()
        resource_type = self._resource_type(kwargs.get("resource_type"))
        if resource_type == "auto":
            resource_type = "image"
        return f"https://res.cloudinary.com/{self._cloud_name}/{resource_type}/upload/{file_id}"

    def generate_upload_url(
        self,
        path: str,
        *,
        content_type: str | None = None,
        size: int | None = None,
        **kwargs: Any,
    ) -> DirectUploadTicket:
        self._ensure_credentials()
        resource_type = self._resource_type(kwargs.get("resource_type"))
        timestamp = int(time.time())
        params: dict[str, Any] = {
            "public_id": path,
            "timestamp": timestamp,
            "overwrite": "true",
            "unique_filename": "false",
            "use_filename": "false",
        }
        folder = self._folder()
        if folder:
            params["folder"] = folder
        signature = self._sign(params)
        fields = {**{k: str(v) for k, v in params.items()}, "api_key": self._api_key, "signature": signature}
        return DirectUploadTicket(
            upload_url=self._upload_url(resource_type),
            method="POST",
            fields=fields,
            provider_ref={"public_id": path, "resource_type": resource_type, "folder": folder},
        )

    def finalize_direct_upload(self, data: Mapping[str, Any]) -> UploadResult:
        public_id = data.get("public_id") or data.get("provider_file_id")
        if not public_id:
            raise ProviderError("Cloudinary finalize requires `public_id`.")
        secure_url = data.get("secure_url") or data.get("url") or self.get_url(public_id, resource_type=data.get("resource_type"))
        return UploadResult(
            provider_file_id=public_id,
            url=secure_url,
            metadata={
                "resource_type": data.get("resource_type"),
                "format": data.get("format"),
                "bytes": data.get("bytes"),
                "version": data.get("version"),
            },
        )

    def get_provider_name(self) -> str:
        return "cloudinary"
