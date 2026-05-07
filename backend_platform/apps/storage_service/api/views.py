"""Storage API views — adapted from FileForge for organization-aware architecture."""
from __future__ import annotations

import uuid as uuid_lib

from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.common.responses import success_response, created_response, no_content_response, error_response
from apps.common.tasks import TaskDispatcher
from apps.organizations.services import OrganizationService

from ..models import StoredFile, StorageCredential, FileStatus
from ..providers import (
    ProviderConfigurationError,
    ProviderError,
    ProviderUnsupportedOperation,
    registry,
)
from ..serializers import (
    StoredFileSerializer,
    FileUploadSerializer,
    DirectUploadInitSerializer,
    DirectUploadCompleteSerializer,
    StorageCredentialSerializer,
    ProviderListSerializer,
)
from ..services import StorageManager
from ..utils import save_to_temp, delete_temp_file, should_use_direct_upload


def _provider_error_response(exc: Exception):
    if isinstance(exc, ProviderConfigurationError):
        return error_response("PROVIDER_CONFIG_ERROR", str(exc), status_code=400)
    elif isinstance(exc, ProviderUnsupportedOperation):
        return error_response("PROVIDER_UNSUPPORTED", str(exc), status_code=400)
    elif isinstance(exc, ProviderError):
        return error_response("PROVIDER_ERROR", str(exc), status_code=502)
    return error_response("STORAGE_ERROR", str(exc), status_code=500)


class ProviderListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=ProviderListSerializer(many=True), summary="List available storage providers")
    def get(self, request):
        providers = StorageManager.list_providers()
        return success_response(data=providers)


class FileListUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(responses=StoredFileSerializer(many=True), summary="List files for an organization")
    def get(self, request, org_id):
        org = OrganizationService.get_organization(org_id)
        provider_filter = request.query_params.get("provider")
        status_filter = request.query_params.get("status")
        qs = StoredFile.objects.filter(organization=org)
        if provider_filter:
            qs = qs.filter(provider=provider_filter)
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = StoredFileSerializer(qs, many=True)
        return success_response(data=serializer.data)

    @extend_schema(
        request=FileUploadSerializer,
        responses=StoredFileSerializer,
        summary="Upload a file (sync or async)",
    )
    def post(self, request, org_id):
        org = OrganizationService.get_organization(org_id)
        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        upload = serializer.validated_data["file"]
        provider = serializer.validated_data["provider"]
        mode = serializer.validated_data.get("mode", "sync")
        is_public = serializer.validated_data.get("is_public", False)
        original_name = getattr(upload, "name", "upload")
        size = getattr(upload, "size", 0) or 0

        if size and should_use_direct_upload(provider, size):
            return error_response(
                "FILE_TOO_LARGE",
                f"File exceeds the sync upload threshold for provider '{provider}'. "
                "Use the direct-upload flow instead.",
                status_code=413,
            )

        import os
        file_key = f"{org.id}/{uuid_lib.uuid4()}{os.path.splitext(original_name)[1]}"
        temp_path, real_size = save_to_temp(upload, original_name=original_name)

        stored = StoredFile.objects.create(
            organization=org,
            uploaded_by=request.user,
            provider=provider,
            file_key=file_key,
            original_name=original_name,
            mime_type=getattr(upload, "content_type", "") or "",
            size=real_size,
            is_public=is_public,
            status=FileStatus.PENDING,
            upload_strategy=mode,
            temp_path=str(temp_path),
        )

        if mode == "sync":
            return _upload_sync(stored)
        else:
            return _upload_async(stored)


def _upload_sync(stored: StoredFile):
    from ..tasks import process_file_upload
    process_file_upload(stored.id)
    stored.refresh_from_db()
    if stored.status == FileStatus.FAILED:
        return error_response("UPLOAD_FAILED", stored.error_message or "Upload failed.", status_code=502)
    return created_response(data=StoredFileSerializer(stored).data)


def _upload_async(stored: StoredFile):
    from ..tasks import process_file_upload
    TaskDispatcher.dispatch(process_file_upload, stored.id)
    stored.refresh_from_db()
    return created_response(
        data=StoredFileSerializer(stored).data,
        message="Upload queued. Poll GET /files/{id}/ for status.",
    )


class FileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_file(self, org_id, file_id):
        org = OrganizationService.get_organization(org_id)
        return get_object_or_404(StoredFile, id=file_id, organization=org)

    @extend_schema(responses=StoredFileSerializer, summary="Get file details")
    def get(self, request, org_id, file_id):
        stored = self._get_file(org_id, file_id)
        return success_response(data=StoredFileSerializer(stored).data)

    @extend_schema(summary="Delete a file")
    def delete(self, request, org_id, file_id):
        stored = self._get_file(org_id, file_id)
        if stored.provider_file_id:
            try:
                StorageManager.delete(
                    stored.provider,
                    stored.provider_file_id,
                    organization_id=stored.organization_id,
                )
            except (ProviderError, ProviderConfigurationError, ProviderUnsupportedOperation) as exc:
                return _provider_error_response(exc)
        delete_temp_file(stored.temp_path)
        stored.delete()
        return no_content_response()


class FileStreamView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Stream file content (byte-range aware)")
    def get(self, request, org_id, file_id):
        from django.http import StreamingHttpResponse
        stored = get_object_or_404(
            StoredFile, id=file_id,
            organization=OrganizationService.get_organization(org_id)
        )
        if stored.status != FileStatus.COMPLETED:
            return error_response("FILE_NOT_READY", f"File is not ready (status: {stored.status})")

        provider_fid = stored.provider_file_id or stored.file_key
        range_header = request.META.get("HTTP_RANGE", "")
        start, end = 0, None
        if range_header.startswith("bytes="):
            parts = range_header[6:].split("-")
            try:
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if len(parts) > 1 and parts[1] else None
            except ValueError:
                pass

        try:
            stream = StorageManager.stream(
                stored.provider, provider_fid,
                organization_id=stored.organization_id,
                start=start, end=end,
            )
        except (ProviderError, ProviderConfigurationError) as exc:
            return _provider_error_response(exc)

        response = StreamingHttpResponse(stream, content_type=stored.mime_type or "application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{stored.original_name}"'
        return response


class DirectUploadInitView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=DirectUploadInitSerializer, summary="Initiate a direct upload to provider")
    def post(self, request, org_id):
        org = OrganizationService.get_organization(org_id)
        serializer = DirectUploadInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data["provider"]
        name = serializer.validated_data["name"]
        size = serializer.validated_data["size"]
        content_type = serializer.validated_data.get("content_type", "")

        try:
            ticket = StorageManager.generate_upload_url(
                provider, name,
                organization_id=org.id,
                content_type=content_type or None,
                size=size,
            )
        except (ProviderError, ProviderConfigurationError, ProviderUnsupportedOperation) as exc:
            return _provider_error_response(exc)

        stored = StoredFile.objects.create(
            organization=org,
            uploaded_by=request.user,
            provider=provider,
            file_key=name,
            original_name=name,
            mime_type=content_type or "",
            size=size,
            status=FileStatus.PENDING,
            upload_strategy="direct",
            metadata={"provider_ref": ticket.provider_ref},
        )

        return created_response(data={
            "file_id": str(stored.id),
            "upload_url": ticket.upload_url,
            "method": ticket.method,
            "fields": ticket.fields,
            "headers": ticket.headers,
            "expires_in": ticket.expires_in,
            "provider_ref": ticket.provider_ref,
        })


class DirectUploadCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=DirectUploadCompleteSerializer, summary="Complete a direct upload")
    def post(self, request, org_id):
        org = OrganizationService.get_organization(org_id)
        serializer = DirectUploadCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_id = serializer.validated_data["file_id"]
        stored = get_object_or_404(StoredFile, id=file_id, organization=org)

        payload = dict(serializer.validated_data.get("provider_response") or {})
        if serializer.validated_data.get("provider_file_id"):
            payload["provider_file_id"] = serializer.validated_data["provider_file_id"]
        if serializer.validated_data.get("url"):
            payload["url"] = serializer.validated_data["url"]
        provider_ref = (stored.metadata or {}).get("provider_ref") or {}
        for k, v in provider_ref.items():
            payload.setdefault(k, v)

        try:
            result = StorageManager.finalize_direct_upload(
                stored.provider, payload, organization_id=org.id
            )
        except (ProviderError, ProviderConfigurationError, ProviderUnsupportedOperation) as exc:
            stored.status = FileStatus.FAILED
            stored.error_message = str(exc)[:2000]
            stored.save(update_fields=["status", "error_message", "updated_at"])
            return _provider_error_response(exc)

        stored.provider_file_id = result.provider_file_id
        stored.url = result.url or ""
        merged_meta = dict(stored.metadata or {})
        merged_meta.update(result.metadata or {})
        stored.metadata = merged_meta
        stored.status = FileStatus.COMPLETED
        stored.error_message = ""
        stored.save(update_fields=[
            "provider_file_id", "url", "metadata",
            "status", "error_message", "updated_at",
        ])
        return success_response(data=StoredFileSerializer(stored).data)


class StorageCredentialListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=StorageCredentialSerializer(many=True), summary="List storage credentials for org")
    def get(self, request, org_id):
        org = OrganizationService.get_organization(org_id)
        creds = StorageCredential.objects.filter(organization=org)
        return success_response(data=StorageCredentialSerializer(creds, many=True).data)

    @extend_schema(request=StorageCredentialSerializer, responses=StorageCredentialSerializer, summary="Create/update storage credentials")
    def post(self, request, org_id):
        org = OrganizationService.get_organization(org_id)
        provider = request.data.get("provider")
        existing = StorageCredential.objects.filter(organization=org, provider=provider).first()
        if existing:
            serializer = StorageCredentialSerializer(existing, data=request.data, partial=True)
        else:
            serializer = StorageCredentialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cred = serializer.save(organization=org)
        return created_response(data=StorageCredentialSerializer(cred).data)


class StorageCredentialDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Delete storage credentials for a provider")
    def delete(self, request, org_id, provider):
        org = OrganizationService.get_organization(org_id)
        cred = get_object_or_404(StorageCredential, organization=org, provider=provider)
        cred.delete()
        return no_content_response()
