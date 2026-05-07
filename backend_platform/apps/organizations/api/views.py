from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.common.responses import success_response, created_response, no_content_response
from apps.organizations.serializers import (
    OrganizationSerializer, OrganizationCreateSerializer,
    MembershipSerializer, InviteMemberSerializer
)
from apps.organizations.services import OrganizationService


class OrganizationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OrganizationSerializer(many=True), summary='List user organizations')
    def get(self, request):
        orgs = OrganizationService.get_user_organizations(request.user)
        serializer = OrganizationSerializer(orgs, many=True)
        return success_response(data=serializer.data)

    @extend_schema(request=OrganizationCreateSerializer, responses=OrganizationSerializer, summary='Create organization')
    def post(self, request):
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = OrganizationService.create_organization(request.user, serializer.validated_data)
        return created_response(data=OrganizationSerializer(org).data)


class OrganizationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_org(self, org_id):
        return OrganizationService.get_organization(org_id)

    @extend_schema(responses=OrganizationSerializer, summary='Get organization details')
    def get(self, request, org_id):
        org = self.get_org(org_id)
        return success_response(data=OrganizationSerializer(org).data)

    @extend_schema(request=OrganizationCreateSerializer, responses=OrganizationSerializer, summary='Update organization')
    def patch(self, request, org_id):
        org = self.get_org(org_id)
        serializer = OrganizationCreateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        org = OrganizationService.update_organization(org, serializer.validated_data)
        return success_response(data=OrganizationSerializer(org).data)


class OrganizationMemberView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MembershipSerializer(many=True), summary='List organization members')
    def get(self, request, org_id):
        from apps.organizations.models import Membership
        members = Membership.objects.filter(organization_id=org_id, is_active=True).select_related('user')
        serializer = MembershipSerializer(members, many=True)
        return success_response(data=serializer.data)

    @extend_schema(request=InviteMemberSerializer, responses=MembershipSerializer, summary='Invite member')
    def post(self, request, org_id):
        org = OrganizationService.get_organization(org_id)
        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = OrganizationService.invite_member(
            org, request.user,
            serializer.validated_data['email'],
            serializer.validated_data['role']
        )
        return created_response(data=MembershipSerializer(membership).data)


class OrganizationMemberDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Remove member from organization')
    def delete(self, request, org_id, user_id):
        org = OrganizationService.get_organization(org_id)
        OrganizationService.remove_member(org, user_id, request.user)
        return no_content_response()
