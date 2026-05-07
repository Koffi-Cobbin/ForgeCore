from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.common.responses import success_response, created_response
from apps.email_service.serializers import EmailLogSerializer, SendEmailSerializer
from apps.email_service.services import EmailService
from apps.email_service.models import EmailLog
from apps.organizations.services import OrganizationService


class SendEmailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=SendEmailSerializer, responses=EmailLogSerializer, summary='Send an email')
    def post(self, request, org_id):
        org = OrganizationService.get_organization(org_id)
        serializer = SendEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        log = EmailService.send_email(
            to_email=d['to_email'],
            subject=d['subject'],
            body_html=d['body_html'],
            body_text=d.get('body_text'),
            organization=org,
            sent_by=request.user,
            template=d.get('template'),
            metadata=d.get('metadata', {}),
        )
        return created_response(data=EmailLogSerializer(log).data)


class EmailLogListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=EmailLogSerializer(many=True), summary='List email logs for an organization')
    def get(self, request, org_id):
        logs = EmailLog.objects.filter(organization_id=org_id).order_by('-created_at')[:100]
        serializer = EmailLogSerializer(logs, many=True)
        return success_response(data=serializer.data)
