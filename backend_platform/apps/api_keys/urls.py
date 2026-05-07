from django.urls import path
from apps.api_keys.api.views import APIKeyListCreateView, APIKeyDetailView

urlpatterns = [
    path('organizations/<uuid:org_id>/api-keys/', APIKeyListCreateView.as_view(), name='api-key-list'),
    path('organizations/<uuid:org_id>/api-keys/<uuid:key_id>/', APIKeyDetailView.as_view(), name='api-key-detail'),
]
