import logging
from django.conf import settings
from .models import EmailLog
from .providers.django_provider import DjangoEmailProvider
from apps.common.tasks import TaskDispatcher

logger = logging.getLogger(__name__)


def _get_provider():
    provider_name = getattr(settings, 'EMAIL_SERVICE_PROVIDER', 'django')
    providers = {
        'django': DjangoEmailProvider,
    }
    provider_class = providers.get(provider_name, DjangoEmailProvider)
    return provider_class()


class EmailService:
    @staticmethod
    def send_email(to_email, subject, body_html, body_text=None, from_email=None,
                   organization=None, sent_by=None, template=None, metadata=None):
        log = EmailLog.objects.create(
            to_email=to_email,
            subject=subject,
            template=template or '',
            organization=organization,
            sent_by=sent_by,
            status='pending',
            metadata=metadata or {},
        )
        TaskDispatcher.dispatch(
            EmailService._send_email_task,
            log.id, to_email, subject, body_html, body_text, from_email
        )
        return log

    @staticmethod
    def _send_email_task(log_id, to_email, subject, body_html, body_text, from_email):
        try:
            log = EmailLog.objects.get(id=log_id)
            provider = _get_provider()
            provider.send(
                to_email=to_email,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                from_email=from_email
            )
            log.status = 'sent'
            log.provider = provider.get_provider_name()
            log.save()
            logger.info(f"Email sent to {to_email}: {subject}")
        except Exception as e:
            logger.error(f"Email failed to {to_email}: {e}")
            try:
                log = EmailLog.objects.get(id=log_id)
                log.status = 'failed'
                log.error_message = str(e)
                log.save()
            except Exception:
                pass

    @staticmethod
    def send_verification_email(user, token):
        subject = 'Verify your email address'
        body_html = f"""
        <h2>Email Verification</h2>
        <p>Hi {user.first_name or user.email},</p>
        <p>Please verify your email address using the token below:</p>
        <p><strong>{token}</strong></p>
        <p>This token will expire in 24 hours.</p>
        """
        body_text = f"Your email verification token: {token}"
        EmailService._send_email_task(
            None, user.email, subject, body_html, body_text, None
        ) if True else None
        provider = _get_provider()
        try:
            provider.send(
                to_email=user.email,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
            )
            logger.info(f"Verification email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")

    @staticmethod
    def send_password_reset_email(user, token):
        subject = 'Password Reset Request'
        body_html = f"""
        <h2>Password Reset</h2>
        <p>Hi {user.first_name or user.email},</p>
        <p>Use the token below to reset your password:</p>
        <p><strong>{token}</strong></p>
        <p>This token expires in 1 hour. If you did not request this, ignore this email.</p>
        """
        body_text = f"Your password reset token: {token}"
        provider = _get_provider()
        try:
            provider.send(
                to_email=user.email,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
            )
            logger.info(f"Password reset email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
