from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/v1/', include('apps.health.urls')),
    path('api/v1/', include('apps.authentication.urls')),
    path('api/v1/', include('apps.users.urls')),
    path('api/v1/', include('apps.organizations.urls')),
    path('api/v1/', include('apps.api_keys.urls')),
    path('api/v1/', include('apps.storage_service.urls')),
    path('api/v1/', include('apps.email_service.urls')),
    path('api/v1/', include('apps.audit_logs.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
