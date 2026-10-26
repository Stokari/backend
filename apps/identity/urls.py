"""URL routing for identity and authentication endpoints."""

from django.urls import path

from apps.identity.views import (
    GoogleSignInView,
    LeaseRenewView,
    LogoutView,
    NonceView,
    RefreshTokenView,
)

urlpatterns = [
    path("nonce", NonceView.as_view(), name="auth-nonce"),
    path("google", GoogleSignInView.as_view(), name="auth-google"),
    path("refresh", RefreshTokenView.as_view(), name="auth-refresh"),
    path("lease", LeaseRenewView.as_view(), name="auth-lease"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
]
