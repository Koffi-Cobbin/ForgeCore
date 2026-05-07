import logging
from .models import AuditLog

logger = logging.getLogger(__name__)


class AuditLogService:
    @staticmethod
    def log(action, actor=None, organization=None, resource_type='', resource_id='',
            ip_address=None, user_agent='', request_id='', metadata=None, status='success'):
        try:
            return AuditLog.objects.create(
                action=action,
                actor=actor,
                organization=organization,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else '',
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                metadata=metadata or {},
                status=status,
            )
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            return None

    @staticmethod
    def log_from_request(request, action, resource_type='', resource_id='',
                          organization=None, metadata=None, status='success'):
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or \
                     request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        actor = request.user if request.user.is_authenticated else None
        return AuditLogService.log(
            action=action,
            actor=actor,
            organization=organization,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
            status=status,
        )

    @staticmethod
    def get_logs(organization=None, actor=None, action=None, limit=100):
        qs = AuditLog.objects.all()
        if organization:
            qs = qs.filter(organization=organization)
        if actor:
            qs = qs.filter(actor=actor)
        if action:
            qs = qs.filter(action=action)
        return qs[:limit]
