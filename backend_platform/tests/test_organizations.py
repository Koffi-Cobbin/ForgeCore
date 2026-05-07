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
        email='orgtest@example.com',
        password='Password123',
        is_email_verified=True,
    )


@pytest.fixture
def auth_client(client, user):
    response = client.post('/api/v1/auth/login/', {
        'email': 'orgtest@example.com',
        'password': 'Password123',
    }, format='json')
    token = response.data['data']['access']
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client


@pytest.mark.django_db
class TestOrganizations:
    def test_create_organization(self, auth_client, user):
        response = auth_client.post('/api/v1/organizations/', {
            'name': 'Acme Corp',
            'slug': 'acme-corp',
        }, format='json')
        assert response.status_code == 201
        assert response.data['data']['name'] == 'Acme Corp'
        assert Membership.objects.filter(user=user, role='owner').exists()

    def test_list_organizations(self, auth_client, user):
        auth_client.post('/api/v1/organizations/', {'name': 'Org 1', 'slug': 'org-1'}, format='json')
        response = auth_client.get('/api/v1/organizations/')
        assert response.status_code == 200
        assert len(response.data['data']) >= 1

    def test_get_organization(self, auth_client, user):
        create = auth_client.post('/api/v1/organizations/', {
            'name': 'Test Org', 'slug': 'test-org'
        }, format='json')
        org_id = create.data['data']['id']
        response = auth_client.get(f'/api/v1/organizations/{org_id}/')
        assert response.status_code == 200
        assert response.data['data']['id'] == org_id

    def test_duplicate_slug(self, auth_client):
        auth_client.post('/api/v1/organizations/', {'name': 'Org', 'slug': 'my-org'}, format='json')
        response = auth_client.post('/api/v1/organizations/', {'name': 'Other', 'slug': 'my-org'}, format='json')
        assert response.status_code == 400
