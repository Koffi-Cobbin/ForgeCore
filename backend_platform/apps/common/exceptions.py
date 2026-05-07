from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status
from .responses import error_response


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, 'default_code', 'error').upper()
        message = str(exc.detail) if hasattr(exc, 'detail') else str(exc)

        if isinstance(exc.detail, dict):
            first_field = next(iter(exc.detail))
            first_error = exc.detail[first_field]
            if isinstance(first_error, list):
                message = f"{first_field}: {first_error[0]}"
            else:
                message = str(first_error)
        elif isinstance(exc.detail, list):
            message = str(exc.detail[0])

        response.data = {
            'success': False,
            'error': {
                'code': error_code,
                'message': message,
            }
        }

    return response


class ServiceException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'service_error'

    def __init__(self, message, code=None, status_code=None):
        self.detail = message
        if code:
            self.default_code = code
        if status_code:
            self.status_code = status_code


class NotFoundError(ServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'not_found'


class PermissionDeniedError(ServiceException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'permission_denied'


class ValidationError(ServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'validation_error'


class ConflictError(ServiceException):
    status_code = status.HTTP_409_CONFLICT
    default_code = 'conflict'
