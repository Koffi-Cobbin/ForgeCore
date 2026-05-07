from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.common.responses import success_response, created_response, no_content_response
from apps.api_keys.serializers import APIKeySerializer, APIKeyCreateSerializer, APIKeyCreatedSerializer
from apps.api_keys.services import APIKeyService
from apps.organizations.services import OrganizationService


class APIKeyListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=APIKeySerializer(many=True), summary='List API keys for an organization')
    def get(self, request, org_id):
        org = OrganizationService.get_organization(org_id)
        keys = APIKeyService.list_api_keys(org)
        serializer = APIKeySerializer(keys, many=True)
        return success_response(data=serializer.data)

    @extend_schema(request=APIKeyCreateSerializer, responses=APIKeyCreatedSerializer, summary='Create API key')
    def post(self, request, org_id):
        org = OrganizationService.get_organization(org_id)
        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        api_key, raw_key = APIKeyService.create_api_key(
            organization=org,
            user=request.user,
            **serializer.validated_data
        )
        response_data = APIKeySerializer(api_key).data
        response_data['key'] = raw_key
        return created_response(
            data=response_data,
            message='API key created. Store the key securely — it will not be shown again.'
        )


class APIKeyDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Revoke an API key')
    def delete(self, request, org_id, key_id):
        org = OrganizationService.get_organization(org_id)
        APIKeyService.revoke_api_key(key_id, org, request.user)
        return no_content_response()
