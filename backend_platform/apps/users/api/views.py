"""User profile views — thin HTTP adapters only.

Views are responsible for:
  1. Deserializing input via a serializer.
  2. Calling the appropriate UserService method.
  3. Serializing and returning the response.

Business logic MUST NOT live here.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.authentication.permissions import IsJWTAuthenticated
from apps.common.responses import success_response
from apps.users.serializers import (
    ChangePasswordSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.users.services import UserService


class MeView(APIView):
    permission_classes = [IsJWTAuthenticated]

    @extend_schema(
        responses={200: UserSerializer},
        summary="Get current user profile",
        description="Returns the authenticated user's profile including organization memberships.",
    )
    def get(self, request):
        return success_response(data=UserSerializer(request.user).data)

    @extend_schema(
        request=UserUpdateSerializer,
        responses={200: UserSerializer},
        summary="Update current user profile",
        description="Partial update — only supplied fields are written.",
    )
    def patch(self, request):
        serializer = UserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = UserService.update_profile(request.user, serializer.validated_data)
        return success_response(data=UserSerializer(user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsJWTAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        summary="Change password",
        description="Verifies the current password then applies the new one.",
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        UserService.change_password(
            request.user,
            serializer.validated_data["current_password"],
            serializer.validated_data["new_password"],
        )
        return success_response(message="Password changed successfully.")


class UserOrganizationsView(APIView):
    """GET /users/me/organizations/ — list the authenticated user's org memberships."""

    permission_classes = [IsJWTAuthenticated]

    @extend_schema(
        summary="List current user's organizations",
        description="Returns all organizations the authenticated user belongs to, with their role.",
    )
    def get(self, request):
        memberships = UserService.get_organization_memberships(request.user)
        return success_response(data=memberships)
