from django.urls import path
from apps.email_service.api.views import SendEmailView, EmailLogListView

urlpatterns = [
    path('organizations/<uuid:org_id>/emails/send/', SendEmailView.as_view(), name='send-email'),
    path('organizations/<uuid:org_id>/emails/logs/', EmailLogListView.as_view(), name='email-logs'),
]
