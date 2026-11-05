"""URL routing for identity and authentication endpoints."""

from django.urls import path

from apps.identity.views import (
    LeaseRenewView,
    LogoutView,
    RefreshTokenView,
)

urlpatterns = [
    path("refresh", RefreshTokenView.as_view(), name="auth-refresh"),
    path("lease", LeaseRenewView.as_view(), name="auth-lease"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
]
