import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.users.models import User


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user_data():
    return {
        'email': 'test@example.com',
        'password': 'StrongPassword123',
        'first_name': 'Test',
        'last_name': 'User',
    }


@pytest.fixture
def registered_user(db, user_data):
    return User.objects.create_user(
        email=user_data['email'],
        password=user_data['password'],
        first_name=user_data['first_name'],
        last_name=user_data['last_name'],
        is_email_verified=True,
    )


@pytest.mark.django_db
class TestRegistration:
    def test_register_success(self, client, user_data):
        response = client.post('/api/v1/auth/register/', user_data, format='json')
        assert response.status_code == 201
        assert response.data['success'] is True
        assert User.objects.filter(email=user_data['email']).exists()

    def test_register_duplicate_email(self, client, user_data, registered_user):
        response = client.post('/api/v1/auth/register/', user_data, format='json')
        assert response.status_code == 400
        assert response.data['success'] is False

    def test_register_invalid_email(self, client):
        response = client.post('/api/v1/auth/register/', {
            'email': 'not-an-email',
            'password': 'StrongPassword123',
        }, format='json')
        assert response.status_code == 400


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, client, registered_user, user_data):
        response = client.post('/api/v1/auth/login/', {
            'email': user_data['email'],
            'password': user_data['password'],
        }, format='json')
        assert response.status_code == 200
        assert 'access' in response.data['data']
        assert 'refresh' in response.data['data']

    def test_login_wrong_password(self, client, registered_user, user_data):
        response = client.post('/api/v1/auth/login/', {
            'email': user_data['email'],
            'password': 'wrongpassword',
        }, format='json')
        assert response.status_code == 400
        assert response.data['success'] is False

    def test_login_nonexistent_user(self, client):
        response = client.post('/api/v1/auth/login/', {
            'email': 'nobody@example.com',
            'password': 'password123',
        }, format='json')
        assert response.status_code == 400


@pytest.mark.django_db
class TestTokenRefresh:
    def test_refresh_token(self, client, registered_user, user_data):
        login = client.post('/api/v1/auth/login/', {
            'email': user_data['email'],
            'password': user_data['password'],
        }, format='json')
        refresh = login.data['data']['refresh']
        response = client.post('/api/v1/auth/token/refresh/', {'refresh': refresh}, format='json')
        assert response.status_code == 200
        assert 'access' in response.data['data']
