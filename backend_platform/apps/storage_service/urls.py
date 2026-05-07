from django.urls import path
from apps.storage_service.api.views import FileListUploadView, FileDetailView

urlpatterns = [
    path('organizations/<uuid:org_id>/files/', FileListUploadView.as_view(), name='file-list'),
    path('organizations/<uuid:org_id>/files/<uuid:file_id>/', FileDetailView.as_view(), name='file-detail'),
]
