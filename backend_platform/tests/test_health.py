import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestHealth:
    def test_health_check(self, client):
        response = client.get('/api/v1/health/')
        assert response.status_code == 200
        assert response.data['data']['status'] == 'ok'
        assert response.data['data']['database'] == 'ok'
