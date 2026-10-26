"""Stokari JWT Authentication class for Django REST Framework."""

import jwt
from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request

from apps.identity.models import User


class StokariJWTAuthentication(BaseAuthentication):
    """Authenticates Bearer tokens issued by Stokari identity service."""

    keyword = "Bearer"

    def authenticate_header(self, request: Request) -> str:
        return self.keyword

    def authenticate(self, request: Request) -> tuple[User, dict] | None:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != self.keyword.lower():
            return None

        raw_token = parts[1]

        try:
            payload = jwt.decode(raw_token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as exc:
            raise exceptions.AuthenticationFailed("Access token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed("Invalid access token") from exc

        if payload.get("type") != "access":
            raise exceptions.AuthenticationFailed("Token is not an access token")

        user_id = payload.get("sub") or payload.get("userId")
        if not user_id:
            raise exceptions.AuthenticationFailed("Missing user identity in token claims")

        user = User.objects.filter(id=user_id).first()
        if not user:
            raise exceptions.AuthenticationFailed("User not found")

        # Set session context on request for downstream view/permission handlers
        setattr(request, "shop_id", payload.get("shopId"))
        setattr(request, "membership_id", payload.get("membershipId"))
        setattr(request, "role", payload.get("role"))
        setattr(request, "device_id", payload.get("deviceId"))

        return user, payload


try:
    from drf_spectacular.extensions import OpenApiAuthenticationExtension

    class StokariJWTAuthenticationExtension(OpenApiAuthenticationExtension):
        target_class = "apps.identity.authentication.StokariJWTAuthentication"
        name = "bearerAuth"

        def get_security_definition(self, auto_schema: object) -> dict[str, str]:
            return {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
except ImportError:
    pass
