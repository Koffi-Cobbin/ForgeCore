from django.urls import path
from apps.storage_service.api.views import (
    ProviderListView,
    FileListUploadView,
    FileDetailView,
    FileStreamView,
    DirectUploadInitView,
    DirectUploadCompleteView,
    StorageCredentialListCreateView,
    StorageCredentialDetailView,
)

urlpatterns = [
    path("storage/providers/", ProviderListView.as_view(), name="storage-providers"),
    path("organizations/<uuid:org_id>/files/", FileListUploadView.as_view(), name="file-list"),
    path("organizations/<uuid:org_id>/files/<uuid:file_id>/", FileDetailView.as_view(), name="file-detail"),
    path("organizations/<uuid:org_id>/files/<uuid:file_id>/stream/", FileStreamView.as_view(), name="file-stream"),
    path("organizations/<uuid:org_id>/files/direct-upload/", DirectUploadInitView.as_view(), name="file-direct-upload-init"),
    path("organizations/<uuid:org_id>/files/direct-upload/complete/", DirectUploadCompleteView.as_view(), name="file-direct-upload-complete"),
    path("organizations/<uuid:org_id>/storage-credentials/", StorageCredentialListCreateView.as_view(), name="storage-credentials-list"),
    path("organizations/<uuid:org_id>/storage-credentials/<str:provider>/", StorageCredentialDetailView.as_view(), name="storage-credentials-detail"),
]
