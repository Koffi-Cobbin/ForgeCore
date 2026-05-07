from django.urls import path
from apps.authentication.api.views import (
    RegisterView, LoginView, LogoutView, TokenRefreshView,
    EmailVerifyView, PasswordResetRequestView, PasswordResetConfirmView
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('auth/verify-email/', EmailVerifyView.as_view(), name='auth-verify-email'),
    path('auth/password-reset/', PasswordResetRequestView.as_view(), name='auth-password-reset'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),
]
