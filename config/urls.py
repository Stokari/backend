from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.identity.views import CurrentUserView, ExchangeAuthCodeView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Stokari custom auth bridge & current user
    path("api/auth/exchange", ExchangeAuthCodeView.as_view(), name="exchange_code"),
    path("api/me", CurrentUserView.as_view(), name="current_user"),
    # django-auth-headless (allauth headless, social callback, /api/me fallback)
    path("", include("django_auth_headless.urls")),
    # Authentication & Identity
    path("v1/auth/", include("apps.identity.urls")),
    # OpenAPI 3 Schema & Interactive Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
