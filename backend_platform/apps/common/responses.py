from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message=None, status_code=status.HTTP_200_OK):
    payload = {'success': True}
    if data is not None:
        payload['data'] = data
    if message:
        payload['message'] = message
    return Response(payload, status=status_code)


def created_response(data=None, message=None):
    return success_response(data=data, message=message, status_code=status.HTTP_201_CREATED)


def no_content_response():
    return Response(status=status.HTTP_204_NO_CONTENT)


def error_response(code, message, status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {
            'success': False,
            'error': {
                'code': code,
                'message': message,
            }
        },
        status=status_code
    )
