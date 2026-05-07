from .base import *
from decouple import config

DEBUG = False

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

CORS_ALLOW_ALL_ORIGINS = False

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

TASK_MODE = config('TASK_MODE', default='django_q')
