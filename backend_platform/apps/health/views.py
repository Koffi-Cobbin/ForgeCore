from django.db import connection
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from apps.common.responses import success_response, error_response


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary='Health check endpoint')
    def get(self, request):
        checks = {
            'status': 'ok',
            'timestamp': timezone.now().isoformat(),
            'database': 'ok',
            'version': '1.0.0',
        }
        try:
            connection.ensure_connection()
        except Exception as e:
            checks['database'] = f'error: {str(e)}'
            checks['status'] = 'degraded'
            return error_response('HEALTH_CHECK_FAILED', 'Database connection failed', status_code=503)
        return success_response(data=checks)
