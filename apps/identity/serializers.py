"""DRF serializers for identity and authentication contracts."""

from __future__ import annotations

from rest_framework import serializers


class NonceResponseSerializer(serializers.Serializer):
    nonce = serializers.CharField(help_text="One-time nonce for Google sign-in")
    expiresAt = serializers.DateTimeField(help_text="Expiration timestamp (ISO-8601)")


class GoogleSignInRequestSerializer(serializers.Serializer):
    idToken = serializers.CharField(required=True, help_text="Google ID token (JWT)")
    nonce = serializers.CharField(required=True, help_text="Nonce previously returned by E-02")
    deviceId = serializers.UUIDField(required=True, help_text="Client device ID (UUIDv7)")
    membershipId = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optional target membership ID when multiple shops exist",
    )


class RefreshRequestSerializer(serializers.Serializer):
    refreshToken = serializers.CharField(required=True, help_text="Opaque refresh token")
    deviceId = serializers.UUIDField(required=True, help_text="Client device ID")


class LeaseRenewRequestSerializer(serializers.Serializer):
    deviceId = serializers.UUIDField(required=True, help_text="Client device ID")


class LogoutRequestSerializer(serializers.Serializer):
    refreshToken = serializers.CharField(required=True, help_text="Refresh token to revoke")


class SessionInfoSerializer(serializers.Serializer):
    userId = serializers.UUIDField()
    email = serializers.EmailField()
    name = serializers.CharField()
    shopId = serializers.UUIDField(allow_null=True)
    membershipId = serializers.UUIDField(allow_null=True)
    role = serializers.CharField(allow_null=True)


class LeaseInfoSerializer(serializers.Serializer):
    leaseId = serializers.UUIDField()
    token = serializers.CharField()
    issuedAt = serializers.DateTimeField()
    expiresAt = serializers.DateTimeField()
    allowedOps = serializers.ListField(child=serializers.CharField())


class AuthSessionSerializer(serializers.Serializer):
    accessToken = serializers.CharField()
    accessTokenExpiresAt = serializers.DateTimeField()
    refreshToken = serializers.CharField()
    refreshTokenExpiresAt = serializers.DateTimeField()
    session = SessionInfoSerializer()
    lease = LeaseInfoSerializer(allow_null=True)
    serverTime = serializers.DateTimeField()


class LeaseRenewResponseSerializer(serializers.Serializer):
    lease = LeaseInfoSerializer()
    serverTime = serializers.DateTimeField()


class MembershipChoiceSerializer(serializers.Serializer):
    membershipId = serializers.UUIDField()
    shopId = serializers.UUIDField()
    shopName = serializers.CharField()
    role = serializers.CharField()


class ProblemDetailSerializer(serializers.Serializer):
    type = serializers.CharField(help_text="URI identifying the error type")
    title = serializers.CharField(help_text="Short summary of the error")
    status = serializers.IntegerField(help_text="HTTP status code")
    detail = serializers.CharField(help_text="Detailed error description")
    code = serializers.CharField(required=False, help_text="Machine-readable error code")
    drainToken = serializers.CharField(required=False, help_text="Temporary token for drain flow")
    drainTokenExpiresAt = serializers.DateTimeField(required=False)
    memberships = serializers.ListField(
        child=MembershipChoiceSerializer(),
        required=False,
        help_text="List of available memberships",
    )
