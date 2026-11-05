"""Views for authentication endpoints."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.authentication import StokariJWTAuthentication
from apps.identity.exchange import exchange_code_for_session
from apps.identity.serializers import (
    AuthSessionSerializer,
    ExchangeAuthCodeRequestSerializer,
    LeaseRenewRequestSerializer,
    LeaseRenewResponseSerializer,
    LogoutRequestSerializer,
    ProblemDetailSerializer,
    RefreshRequestSerializer,
)
from apps.identity.services import (
    renew_offline_lease,
    revoke_refresh_token,
    rotate_refresh_token,
)


class RefreshTokenView(APIView):
    """E-04: Rotate refresh token and issue a fresh access token."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Rotate refresh token",
        description=(
            "Rotates refresh token. Detects token reuse (revoking entire token family) "
            "and checks for account deactivation (issuing a drain token if deactivated)."
        ),
        request=RefreshRequestSerializer,
        responses={
            200: AuthSessionSerializer,
            401: ProblemDetailSerializer,
            403: ProblemDetailSerializer,
        },
        auth=[],
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = RefreshRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        session_data = rotate_refresh_token(
            raw_refresh_token=validated["refreshToken"],
            device_id=validated["deviceId"],
        )
        return Response(session_data, status=status.HTTP_200_OK)


class LeaseRenewView(APIView):
    """E-05: Renew offline authorization lease for this device."""

    authentication_classes = [StokariJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Renew offline authorization lease",
        description="Issues a renewed 7-day offline lease for the caller's active shop membership.",
        request=LeaseRenewRequestSerializer,
        responses={
            200: LeaseRenewResponseSerializer,
            401: ProblemDetailSerializer,
            403: ProblemDetailSerializer,
        },
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = LeaseRenewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        lease_data = renew_offline_lease(
            user=request.user,
            device_id=validated["deviceId"],
        )
        return Response(lease_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """E-06: Revoke refresh token (idempotent, returns 204)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Logout and revoke refresh token",
        description="Revokes the presented refresh token. Always succeeds with 204.",
        request=LogoutRequestSerializer,
        responses={204: None},
        auth=[],
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:

        serializer = LogoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        revoke_refresh_token(validated["refreshToken"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExchangeAuthCodeView(APIView):
    """Bridge endpoint: Exchange django-auth-headless one-time code for Stokari AuthSession."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Exchange OAuth handoff code for Stokari session",
        description=(
            "Redeems a single-use authorization code from the OAuth callback, "
            "provisions or matches the Stokari user, and returns an AuthSession with "
            "access JWT, refresh token, and offline lease."
        ),
        request=ExchangeAuthCodeRequestSerializer,
        responses={
            200: AuthSessionSerializer,
            400: ProblemDetailSerializer,
            401: ProblemDetailSerializer,
            403: ProblemDetailSerializer,
            409: ProblemDetailSerializer,
        },
        auth=[],
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = ExchangeAuthCodeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        session_data = exchange_code_for_session(
            raw_code=validated["code"],
            device_id=validated["deviceId"],
            membership_id=validated.get("membershipId"),
        )
        return Response(session_data, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    """GET /api/me: Retrieve authenticated current user and tenant session details."""

    authentication_classes = [StokariJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get current user and session",
        description="Returns identity and active tenant context for the authenticated caller.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "user": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "format": "uuid"},
                                    "email": {"type": "string"},
                                    "name": {"type": "string"},
                                },
                            },
                            "session": {
                                "type": "object",
                                "properties": {
                                    "shopId": {"type": "string", "nullable": True},
                                    "membershipId": {"type": "string", "nullable": True},
                                    "role": {"type": "string", "nullable": True},
                                    "deviceId": {"type": "string", "nullable": True},
                                },
                            },
                        },
                    },
                },
            },
            401: ProblemDetailSerializer,
        },
        tags=["auth"],
    )
    def get(self, request: Request) -> Response:
        user = request.user
        return Response(
            {
                "status": 200,
                "data": {
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "name": user.name,
                    },
                    "session": {
                        "shopId": (
                            str(request.shop_id) if getattr(request, "shop_id", None) else None
                        ),
                        "membershipId": (
                            str(request.membership_id)
                            if getattr(request, "membership_id", None)
                            else None
                        ),
                        "role": getattr(request, "role", None),
                        "deviceId": (
                            str(request.device_id) if getattr(request, "device_id", None) else None
                        ),
                    },
                },
            },
            status=status.HTTP_200_OK,
        )
