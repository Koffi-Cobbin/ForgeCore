from django.urls import path
from apps.users.api.views import MeView, ChangePasswordView

urlpatterns = [
    path('users/me/', MeView.as_view(), name='user-me'),
    path('users/me/change-password/', ChangePasswordView.as_view(), name='change-password'),
]
