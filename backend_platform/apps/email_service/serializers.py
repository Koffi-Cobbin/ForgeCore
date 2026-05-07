from rest_framework import serializers
from .models import EmailLog


class EmailLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailLog
        fields = [
            'id', 'organization', 'to_email', 'subject', 'template',
            'status', 'provider', 'error_message', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class SendEmailSerializer(serializers.Serializer):
    to_email = serializers.EmailField()
    subject = serializers.CharField(max_length=512)
    body_html = serializers.CharField()
    body_text = serializers.CharField(required=False, allow_blank=True)
    template = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.DictField(required=False, default=dict)
