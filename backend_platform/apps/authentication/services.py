import secrets
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import User
from apps.common.exceptions import ValidationError, NotFoundError, ServiceException
from apps.common.tasks import TaskDispatcher


class AuthService:
    @staticmethod
    def register(email, password, first_name='', last_name=''):
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.', code='email_taken')

        token = secrets.token_urlsafe(32)
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_email_verified=False,
            email_verification_token=token,
        )
        TaskDispatcher.dispatch(AuthService._send_verification_email, user.id, token)
        return user

    @staticmethod
    def _send_verification_email(user_id, token):
        try:
            from apps.email_service.services import EmailService
            user = User.objects.get(id=user_id)
            EmailService.send_verification_email(user, token)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'Failed to send verification email: {e}')

    @staticmethod
    def login(email, password):
        user = authenticate(username=email, password=password)
        if not user:
            raise ValidationError('Invalid email or password.', code='invalid_credentials')
        if not user.is_active:
            raise ValidationError('This account has been deactivated.', code='account_inactive')
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user,
        }

    @staticmethod
    def logout(refresh_token):
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            raise ValidationError('Invalid refresh token.', code='invalid_token')

    @staticmethod
    def refresh_token(refresh_token):
        try:
            token = RefreshToken(refresh_token)
            return {
                'access': str(token.access_token),
                'refresh': str(token),
            }
        except Exception:
            raise ValidationError('Invalid or expired refresh token.', code='invalid_token')

    @staticmethod
    def verify_email(token):
        try:
            user = User.objects.get(email_verification_token=token)
        except User.DoesNotExist:
            raise ValidationError('Invalid verification token.', code='invalid_token')
        user.is_email_verified = True
        user.email_verification_token = None
        user.save()
        return user

    @staticmethod
    def request_password_reset(email):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return
        token = secrets.token_urlsafe(32)
        user.password_reset_token = hashlib.sha256(token.encode()).hexdigest()
        user.password_reset_token_expires = timezone.now() + timedelta(hours=1)
        user.save()
        TaskDispatcher.dispatch(AuthService._send_password_reset_email, user.id, token)

    @staticmethod
    def _send_password_reset_email(user_id, token):
        try:
            from apps.email_service.services import EmailService
            user = User.objects.get(id=user_id)
            EmailService.send_password_reset_email(user, token)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'Failed to send password reset email: {e}')

    @staticmethod
    def reset_password(token, new_password):
        hashed = hashlib.sha256(token.encode()).hexdigest()
        try:
            user = User.objects.get(
                password_reset_token=hashed,
                password_reset_token_expires__gt=timezone.now()
            )
        except User.DoesNotExist:
            raise ValidationError('Invalid or expired reset token.', code='invalid_token')
        user.set_password(new_password)
        user.password_reset_token = None
        user.password_reset_token_expires = None
        user.save()
        return user
