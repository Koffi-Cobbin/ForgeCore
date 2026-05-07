import os
from pathlib import Path
from django.conf import settings
from .base import BaseStorageProvider


class LocalStorageProvider(BaseStorageProvider):
    def __init__(self):
        self.root = Path(getattr(settings, 'STORAGE_LOCAL_ROOT', settings.MEDIA_ROOT / 'uploads'))
        self.root.mkdir(parents=True, exist_ok=True)

    def upload(self, file_obj, file_key, content_type=None, **kwargs):
        file_path = self.root / file_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'wb') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
        return file_key

    def delete(self, file_key, **kwargs):
        file_path = self.root / file_key
        if file_path.exists():
            os.remove(file_path)

    def generate_signed_url(self, file_key, expires_in=3600, **kwargs):
        return self.get_url(file_key)

    def get_url(self, file_key, **kwargs):
        return f"{settings.MEDIA_URL}uploads/{file_key}"

    def get_provider_name(self):
        return 'local'
