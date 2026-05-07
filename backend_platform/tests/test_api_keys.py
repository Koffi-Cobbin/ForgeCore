import pytest
from rest_framework.test import APIClient
from apps.users.models import User
from apps.organizations.models import Organization, Membership


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='apikeys@example.com',
        password='Password123',
        is_email_verified=True,
    )


@pytest.fixture
def org(db, user):
    org = Organization.objects.create(name='Test Org', slug='test-org-keys')
    Membership.objects.create(user=user, organization=org, role='owner')
    return org


@pytest.fixture
def auth_client(client, user):
    response = client.post('/api/v1/auth/login/', {
        'email': 'apikeys@example.com',
        'password': 'Password123',
    }, format='json')
    token = response.data['data']['access']
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client


@pytest.mark.django_db
class TestAPIKeys:
    def test_create_api_key(self, auth_client, org):
        response = auth_client.post(
            f'/api/v1/organizations/{org.id}/api-keys/',
            {'name': 'Test Key', 'scopes': ['read', 'write']},
            format='json'
        )
        assert response.status_code == 201
        assert 'key' in response.data['data']
        key = response.data['data']['key']
        assert len(key) > 8

    def test_key_not_shown_after_creation(self, auth_client, org):
        create = auth_client.post(
            f'/api/v1/organizations/{org.id}/api-keys/',
            {'name': 'Ephemeral Key'},
            format='json'
        )
        assert create.status_code == 201
        list_response = auth_client.get(f'/api/v1/organizations/{org.id}/api-keys/')
        for key in list_response.data['data']:
            assert 'key' not in key or key.get('key') is None

    def test_revoke_api_key(self, auth_client, org):
        create = auth_client.post(
            f'/api/v1/organizations/{org.id}/api-keys/',
            {'name': 'Revokable Key'},
            format='json'
        )
        key_id = create.data['data']['id']
        response = auth_client.delete(f'/api/v1/organizations/{org.id}/api-keys/{key_id}/')
        assert response.status_code == 204

    def test_api_key_authentication(self, client, org):
        auth_client = APIClient()
        auth_client.credentials(HTTP_AUTHORIZATION='Bearer ' + APIClient().post(
            '/api/v1/auth/login/',
            {'email': 'apikeys@example.com', 'password': 'Password123'},
            format='json'
        ).data['data']['access'])
        create = auth_client.post(
            f'/api/v1/organizations/{org.id}/api-keys/',
            {'name': 'Auth Test Key'},
            format='json'
        )
        raw_key = create.data['data']['key']
        key_client = APIClient()
        key_client.credentials(HTTP_AUTHORIZATION=f'Api-Key {raw_key}')
        response = key_client.get('/api/v1/users/me/')
        assert response.status_code == 200
