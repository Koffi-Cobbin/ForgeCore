from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.common.responses import success_response
from apps.users.serializers import UserSerializer, UserUpdateSerializer
from apps.users.services import UserService


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer, summary='Get current user profile')
    def get(self, request):
        serializer = UserSerializer(request.user)
        return success_response(data=serializer.data)

    @extend_schema(request=UserUpdateSerializer, responses=UserSerializer, summary='Update current user profile')
    def patch(self, request):
        serializer = UserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = UserService.update_profile(request.user, serializer.validated_data)
        return success_response(data=UserSerializer(user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={'application/json': {'type': 'object', 'properties': {
            'current_password': {'type': 'string'},
            'new_password': {'type': 'string'},
        }}},
        summary='Change password'
    )
    def post(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        if not current_password or not new_password:
            from apps.common.responses import error_response
            return error_response('VALIDATION_ERROR', 'current_password and new_password are required')
        UserService.change_password(request.user, current_password, new_password)
        return success_response(message='Password changed successfully')
