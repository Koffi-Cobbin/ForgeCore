from rest_framework import serializers
from .models import StoredFile


class StoredFileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = StoredFile
        fields = [
            'id', 'organization', 'uploaded_by', 'provider', 'file_key',
            'original_name', 'mime_type', 'size', 'is_public',
            'metadata', 'url', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_url(self, obj):
        from .services import StorageService
        try:
            return StorageService.get_file_url(obj)
        except Exception:
            return None
