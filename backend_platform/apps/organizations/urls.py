from django.urls import path
from apps.organizations.api.views import (
    OrganizationListCreateView,
    OrganizationDetailView,
    OrganizationMemberView,
    OrganizationMemberDetailView,
)

urlpatterns = [
    path('organizations/', OrganizationListCreateView.as_view(), name='organization-list'),
    path('organizations/<uuid:org_id>/', OrganizationDetailView.as_view(), name='organization-detail'),
    path('organizations/<uuid:org_id>/members/', OrganizationMemberView.as_view(), name='organization-members'),
    path('organizations/<uuid:org_id>/members/<uuid:user_id>/', OrganizationMemberDetailView.as_view(), name='organization-member-detail'),
]
