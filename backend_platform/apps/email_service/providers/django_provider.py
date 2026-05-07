from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from .base import BaseEmailProvider


class DjangoEmailProvider(BaseEmailProvider):
    def send(self, to_email, subject, body_html, body_text=None, from_email=None, **kwargs):
        from_addr = from_email or settings.DEFAULT_FROM_EMAIL
        msg = EmailMultiAlternatives(
            subject=subject,
            body=body_text or '',
            from_email=from_addr,
            to=[to_email],
        )
        if body_html:
            msg.attach_alternative(body_html, 'text/html')
        msg.send()

    def get_provider_name(self):
        return 'django'
