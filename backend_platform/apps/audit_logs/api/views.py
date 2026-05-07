from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.common.responses import success_response
from apps.audit_logs.serializers import AuditLogSerializer
from apps.audit_logs.services import AuditLogService
from apps.organizations.services import OrganizationService


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=AuditLogSerializer(many=True), summary='List audit logs for an organization')
    def get(self, request, org_id):
        org = OrganizationService.get_organization(org_id)
        action_filter = request.query_params.get('action')
        logs = AuditLogService.get_logs(organization=org, action=action_filter)
        serializer = AuditLogSerializer(logs, many=True)
        return success_response(data=serializer.data)
