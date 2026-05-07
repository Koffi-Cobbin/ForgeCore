from .models import User
from apps.common.exceptions import NotFoundError, ValidationError


class UserService:
    @staticmethod
    def get_user_by_id(user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFoundError('User not found')

    @staticmethod
    def get_user_by_email(email):
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            raise NotFoundError('User not found')

    @staticmethod
    def update_profile(user, data):
        allowed_fields = ['first_name', 'last_name', 'avatar_url', 'phone_number']
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
        user.save()
        return user

    @staticmethod
    def change_password(user, current_password, new_password):
        if not user.check_password(current_password):
            raise ValidationError('Current password is incorrect', code='invalid_password')
        user.set_password(new_password)
        user.save()
        return user

    @staticmethod
    def deactivate_account(user):
        user.is_active = False
        user.save()
        return user
