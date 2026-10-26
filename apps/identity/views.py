"""Views for authentication endpoints."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.authentication import StokariJWTAuthentication
from apps.identity.serializers import (
    AuthSessionSerializer,
    GoogleSignInRequestSerializer,
    LeaseRenewRequestSerializer,
    LeaseRenewResponseSerializer,
    LogoutRequestSerializer,
    NonceResponseSerializer,
    ProblemDetailSerializer,
    RefreshRequestSerializer,
)
from apps.identity.services import (
    authenticate_google,
    generate_nonce,
    renew_offline_lease,
    revoke_refresh_token,
    rotate_refresh_token,
)


class NonceView(APIView):
    """E-02: Issue a one-time single-use nonce for Google sign-in."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get one-time sign-in nonce",
        description="Returns a cryptographically random single-use nonce valid for 5 minutes.",
        responses={200: NonceResponseSerializer},
        auth=[],
        tags=["auth"],
    )
    def get(self, request: Request) -> Response:
        data = generate_nonce()
        serializer = NonceResponseSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GoogleSignInView(APIView):
    """E-03: Exchange Google ID token and verified nonce for a Stokari session."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Exchange Google ID token for Stokari session",
        description=(
            "Validates Google ID token and nonce, retrieves or provisions User, "
            "and returns an AuthSession with access token, refresh token, and offline lease."
        ),
        request=GoogleSignInRequestSerializer,
        responses={
            200: AuthSessionSerializer,
            401: ProblemDetailSerializer,
            403: ProblemDetailSerializer,
            409: ProblemDetailSerializer,
        },
        auth=[],
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = GoogleSignInRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        session_data = authenticate_google(
            id_token=validated["idToken"],
            nonce=validated["nonce"],
            device_id=validated["deviceId"],
            membership_id=validated.get("membershipId"),
        )
        return Response(session_data, status=status.HTTP_200_OK)


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
