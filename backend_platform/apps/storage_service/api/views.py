from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema
from apps.common.responses import success_response, created_response, no_content_response
from apps.storage_service.serializers import StoredFileSerializer
from apps.storage_service.services import StorageService
from apps.organizations.services import OrganizationService


class FileListUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(responses=StoredFileSerializer(many=True), summary='List files for an organization')
    def get(self, request, org_id):
        org = OrganizationService.get_organization(org_id)
        files = StorageService.list_files(org)
        serializer = StoredFileSerializer(files, many=True)
        return success_response(data=serializer.data)

    @extend_schema(
        request={'multipart/form-data': {'type': 'object', 'properties': {
            'file': {'type': 'string', 'format': 'binary'},
            'is_public': {'type': 'boolean'},
        }}},
        responses=StoredFileSerializer,
        summary='Upload a file'
    )
    def post(self, request, org_id):
        org = OrganizationService.get_organization(org_id)
        file_obj = request.FILES.get('file')
        if not file_obj:
            from apps.common.responses import error_response
            return error_response('VALIDATION_ERROR', 'No file provided.')
        is_public = request.data.get('is_public', 'false').lower() == 'true'
        stored = StorageService.upload_file(
            file_obj=file_obj,
            organization=org,
            uploaded_by=request.user,
            is_public=is_public,
        )
        return created_response(data=StoredFileSerializer(stored).data)


class FileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=StoredFileSerializer, summary='Get file details')
    def get(self, request, org_id, file_id):
        org = OrganizationService.get_organization(org_id)
        stored = StorageService.get_file(file_id, org)
        return success_response(data=StoredFileSerializer(stored).data)

    @extend_schema(summary='Delete a file')
    def delete(self, request, org_id, file_id):
        org = OrganizationService.get_organization(org_id)
        StorageService.delete_file(file_id, org)
        return no_content_response()
