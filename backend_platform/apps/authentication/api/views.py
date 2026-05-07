"""Authentication views — thin HTTP adapters only.

Views are responsible for:
  1. Deserializing input via a serializer.
  2. Calling the appropriate AuthService method.
  3. Serializing and returning the response.

Business logic, token handling, and password hashing MUST NOT live here.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.authentication.permissions import IsJWTAuthenticated
from apps.authentication.serializers import (
    EmailVerifySerializer,
    LoginSerializer,
    LogoutSerializer,
    MFAPendingResponseSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    TokenRefreshSerializer,
    TokenResponseSerializer,
)
from apps.authentication.services import AuthService
from apps.common.responses import created_response, error_response, success_response
from apps.users.serializers import UserSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: UserSerializer},
        summary="Register a new user",
        description=(
            "Creates a new user account and dispatches an email verification message. "
            "The account is usable before verification but email-gated endpoints will "
            "require `is_email_verified=true`."
        ),
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.register(**serializer.validated_data)
        return created_response(
            data=UserSerializer(user).data,
            message="Registration successful. Please verify your email.",
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200: TokenResponseSerializer},
        summary="Login",
        description=(
            "Authenticate with email + password. Returns a JWT access/refresh pair "
            "and organization membership context. If MFA is enabled and no `mfa_code` "
            "is provided, returns `mfa_pending=true` with a short-lived MFA token."
        ),
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AuthService.login(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            mfa_code=serializer.validated_data.get("mfa_code"),
            request=request,
        )

        # MFA pending — partial auth, no full session yet.
        if result.get("mfa_pending"):
            return success_response(data={
                "mfa_pending": True,
                "mfa_token": result["mfa_token"],
            })

        return success_response(data={
            "access": result["access"],
            "refresh": result["refresh"],
            "user": UserSerializer(result["user"]).data,
            "organizations": result["organizations"],
            "mfa_pending": False,
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        summary="Logout",
        description="Blacklists the supplied refresh token. The access token expires naturally.",
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.logout(serializer.validated_data["refresh"])
        return success_response(message="Logged out successfully.")


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=TokenRefreshSerializer,
        responses={200: TokenResponseSerializer},
        summary="Refresh access token",
        description=(
            "Rotates the refresh token and issues a new access token. "
            "The old refresh token is blacklisted."
        ),
    )
    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AuthService.refresh_token(serializer.validated_data["refresh"])
        return success_response(data=result)


class EmailVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=EmailVerifySerializer,
        responses={200: UserSerializer},
        summary="Verify email address",
        description="Consume the verification token sent during registration.",
    )
    def post(self, request):
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.verify_email(serializer.validated_data["token"])
        return success_response(
            data=UserSerializer(user).data,
            message="Email verified successfully.",
        )


class ResendVerificationEmailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ResendVerificationSerializer,
        summary="Resend verification email",
        description=(
            "Resends the email verification link. Always returns 200 regardless of "
            "whether the address exists (prevents enumeration)."
        ),
    )
    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.resend_verification_email(serializer.validated_data["email"])
        return success_response(
            message="If an unverified account with that email exists, a new verification link has been sent."
        )


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=PasswordResetRequestSerializer,
        summary="Request password reset",
        description=(
            "Sends a password reset email. Always returns 200 regardless of whether "
            "the email exists (prevents user enumeration)."
        ),
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.request_password_reset(serializer.validated_data["email"])
        return success_response(
            message="If a user with that email exists, a reset link has been sent."
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        summary="Confirm password reset",
        description="Apply a new password using the token from the reset email.",
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.reset_password(
            serializer.validated_data["token"],
            serializer.validated_data["new_password"],
        )
        return success_response(message="Password reset successfully.")
