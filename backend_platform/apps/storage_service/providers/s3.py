"""AWS S3 storage provider."""
from __future__ import annotations

from typing import Any, BinaryIO, Mapping

from django.conf import settings

from .base import BaseStorageProvider, DirectUploadTicket, ProviderConfigurationError, ProviderError, UploadResult


class S3StorageProvider(BaseStorageProvider):
    """Upload, download, and manage files in AWS S3."""

    name = "s3"
    supports_direct_upload = True
    supports_streaming = False

    def __init__(self, credentials: Mapping[str, Any] | None = None) -> None:
        super().__init__(credentials)
        self._s3 = None
        self._bucket: str = ""

    def _build_client(self):
        if self._s3 is not None:
            return self._s3, self._bucket
        try:
            import boto3
        except ImportError as exc:
            raise ProviderConfigurationError(
                "boto3 is required for S3 storage. Install with: pip install boto3"
            ) from exc
        key = self.credentials.get("aws_access_key_id") or settings.AWS_ACCESS_KEY_ID
        secret = self.credentials.get("aws_secret_access_key") or settings.AWS_SECRET_ACCESS_KEY
        region = self.credentials.get("aws_s3_region_name") or settings.AWS_S3_REGION_NAME
        bucket = self.credentials.get("aws_storage_bucket_name") or settings.AWS_STORAGE_BUCKET_NAME
        if not all([key, secret, bucket]):
            raise ProviderConfigurationError(
                "S3 provider requires aws_access_key_id, aws_secret_access_key, and aws_storage_bucket_name."
            )
        self._s3 = boto3.client("s3", aws_access_key_id=key, aws_secret_access_key=secret, region_name=region)
        self._bucket = bucket
        return self._s3, self._bucket

    def upload(
        self,
        file: BinaryIO,
        path: str,
        *,
        content_type: str | None = None,
        size: int | None = None,
        **kwargs: Any,
    ) -> UploadResult:
        s3, bucket = self._build_client()
        extra = {}
        if content_type:
            extra["ContentType"] = content_type
        try:
            s3.upload_fileobj(file, bucket, path, ExtraArgs=extra)
        except Exception as exc:
            raise ProviderError(f"S3 upload failed: {exc}") from exc
        url = self.get_url(path)
        return UploadResult(provider_file_id=path, url=url, metadata={})

    def download(self, file_id: str, **kwargs: Any) -> bytes:
        s3, bucket = self._build_client()
        try:
            response = s3.get_object(Bucket=bucket, Key=file_id)
            return response["Body"].read()
        except Exception as exc:
            raise ProviderError(f"S3 download failed: {exc}") from exc

    def delete(self, file_id: str, **kwargs: Any) -> None:
        s3, bucket = self._build_client()
        try:
            s3.delete_object(Bucket=bucket, Key=file_id)
        except Exception as exc:
            raise ProviderError(f"S3 delete failed: {exc}") from exc

    def update(self, file_id: str, **kwargs: Any) -> dict[str, Any]:
        new_name = kwargs.get("name") or kwargs.get("new_public_id")
        if new_name:
            s3, bucket = self._build_client()
            try:
                s3.copy_object(Bucket=bucket, CopySource={"Bucket": bucket, "Key": file_id}, Key=new_name)
                s3.delete_object(Bucket=bucket, Key=file_id)
            except Exception as exc:
                raise ProviderError(f"S3 rename failed: {exc}") from exc
            return {"file_id": new_name}
        return {"file_id": file_id}

    def get_url(self, file_id: str, **kwargs: Any) -> str:
        _, bucket = self._build_client()
        return f"https://{bucket}.s3.amazonaws.com/{file_id}"

    def generate_signed_url(self, file_id: str, expires_in: int = 3600, **kwargs: Any) -> str:
        s3, bucket = self._build_client()
        try:
            return s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": file_id},
                ExpiresIn=expires_in,
            )
        except Exception as exc:
            raise ProviderError(f"S3 presigned URL generation failed: {exc}") from exc

    def generate_upload_url(
        self,
        path: str,
        *,
        content_type: str | None = None,
        size: int | None = None,
        **kwargs: Any,
    ) -> DirectUploadTicket:
        s3, bucket = self._build_client()
        params: dict[str, Any] = {"Bucket": bucket, "Key": path}
        if content_type:
            params["ContentType"] = content_type
        try:
            url = s3.generate_presigned_url("put_object", Params=params, ExpiresIn=3600)
        except Exception as exc:
            raise ProviderError(f"S3 direct upload URL failed: {exc}") from exc
        return DirectUploadTicket(
            upload_url=url,
            method="PUT",
            headers={"Content-Type": content_type or "application/octet-stream"},
            provider_ref={"path": path},
            expires_in=3600,
        )

    def finalize_direct_upload(self, data: Mapping[str, Any]) -> UploadResult:
        path = data.get("provider_file_id") or data.get("path") or (data.get("provider_ref") or {}).get("path")
        if not path:
            raise ProviderError("S3 finalize requires provider_file_id or path.")
        return UploadResult(
            provider_file_id=path,
            url=self.get_url(path),
            metadata={},
        )

    def get_provider_name(self) -> str:
        return "s3"
