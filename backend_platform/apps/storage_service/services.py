import uuid
import os
from django.conf import settings
from .models import StoredFile
from apps.common.exceptions import NotFoundError


def _get_provider():
    provider_name = getattr(settings, 'STORAGE_PROVIDER', 'local')
    if provider_name == 's3':
        from .providers.s3 import S3StorageProvider
        return S3StorageProvider()
    from .providers.local import LocalStorageProvider
    return LocalStorageProvider()


class StorageService:
    @staticmethod
    def upload_file(file_obj, organization, uploaded_by, is_public=False, metadata=None):
        ext = os.path.splitext(file_obj.name)[1]
        file_key = f"{organization.id}/{uuid.uuid4()}{ext}"
        provider = _get_provider()
        provider.upload(file_obj, file_key, content_type=file_obj.content_type)
        stored = StoredFile.objects.create(
            organization=organization,
            uploaded_by=uploaded_by,
            provider=provider.get_provider_name(),
            file_key=file_key,
            original_name=file_obj.name,
            mime_type=file_obj.content_type or '',
            size=file_obj.size,
            is_public=is_public,
            metadata=metadata or {},
        )
        return stored

    @staticmethod
    def get_file(file_id, organization):
        try:
            return StoredFile.objects.get(id=file_id, organization=organization)
        except StoredFile.DoesNotExist:
            raise NotFoundError('File not found')

    @staticmethod
    def list_files(organization):
        return StoredFile.objects.filter(organization=organization)

    @staticmethod
    def delete_file(file_id, organization):
        stored = StorageService.get_file(file_id, organization)
        provider = _get_provider()
        try:
            provider.delete(stored.file_key)
        except Exception:
            pass
        stored.delete()

    @staticmethod
    def get_file_url(stored_file):
        provider = _get_provider()
        if stored_file.is_public:
            return provider.get_url(stored_file.file_key)
        return provider.generate_signed_url(stored_file.file_key)
