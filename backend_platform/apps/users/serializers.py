from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'is_active', 'is_email_verified', 'avatar_url',
            'phone_number', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'is_active', 'is_email_verified', 'created_at', 'updated_at']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'avatar_url', 'phone_number']
