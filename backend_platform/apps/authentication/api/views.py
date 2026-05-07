from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.common.responses import success_response, created_response
from apps.authentication.serializers import (
    RegisterSerializer, LoginSerializer, LogoutSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    EmailVerifySerializer, TokenResponseSerializer
)
from apps.authentication.services import AuthService
from apps.users.serializers import UserSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer, summary='Register a new user')
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.register(**serializer.validated_data)
        return created_response(
            data=UserSerializer(user).data,
            message='Registration successful. Please verify your email.'
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses=TokenResponseSerializer, summary='Login')
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthService.login(
            serializer.validated_data['email'],
            serializer.validated_data['password']
        )
        return success_response(data={
            'access': result['access'],
            'refresh': result['refresh'],
            'user': UserSerializer(result['user']).data,
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=LogoutSerializer, summary='Logout (blacklist refresh token)')
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.logout(serializer.validated_data['refresh'])
        return success_response(message='Logged out successfully.')


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request={'application/json': {'type': 'object', 'properties': {'refresh': {'type': 'string'}}}},
        responses=TokenResponseSerializer,
        summary='Refresh access token'
    )
    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            from apps.common.responses import error_response
            return error_response('VALIDATION_ERROR', 'refresh token is required')
        result = AuthService.refresh_token(refresh)
        return success_response(data=result)


class EmailVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=EmailVerifySerializer, summary='Verify email address')
    def post(self, request):
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.verify_email(serializer.validated_data['token'])
        return success_response(
            data=UserSerializer(user).data,
            message='Email verified successfully.'
        )


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=PasswordResetRequestSerializer, summary='Request password reset')
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.request_password_reset(serializer.validated_data['email'])
        return success_response(message='If a user with that email exists, a reset link has been sent.')


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=PasswordResetConfirmSerializer, summary='Confirm password reset')
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.reset_password(
            serializer.validated_data['token'],
            serializer.validated_data['new_password']
        )
        return success_response(message='Password reset successfully.')
