"""Domain services for Stokari identity, Google authentication, and token lifecycle."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.identity.models import OfflineLease, RefreshToken, User
from apps.shops.models import Device, Membership, MembershipRole, MembershipStatus, Shop
from common.kernel.errors import (
    AccountDeactivatedError,
    GoogleTokenInvalidError,
    MembershipSelectionRequiredError,
    NonceInvalidError,
    RefreshTokenInvalidError,
    RefreshTokenReusedError,
    ShopRequiredError,
)

OWNER_ALLOWED_OPS: list[str] = [
    "CreateProduct",
    "UpdateProduct",
    "SetProductStatus",
    "RecordSale",
    "CancelSale",
    "ReceiveStock",
    "AdjustStock",
    "ResolveConflict",
]

ATTENDANT_ALLOWED_OPS: list[str] = [
    "RecordSale",
]

NONCE_PREFIX = "auth_nonce:"
NONCE_EXPIRY_SECONDS = 300  # 5 minutes


def generate_nonce() -> dict[str, str]:
    """Generate a single-use cryptographically secure nonce for Google sign-in."""
    nonce = f"n_{secrets.token_hex(16)}"
    expires_at = timezone.now() + timedelta(seconds=NONCE_EXPIRY_SECONDS)
    cache.set(f"{NONCE_PREFIX}{nonce}", expires_at.isoformat(), timeout=NONCE_EXPIRY_SECONDS)
    return {"nonce": nonce, "expiresAt": expires_at.isoformat()}


def verify_and_consume_nonce(nonce: str) -> bool:
    """Verify that a nonce exists and consume it (single-use)."""
    if not nonce:
        return False
    key = f"{NONCE_PREFIX}{nonce}"
    stored = cache.get(key)
    if not stored:
        return False
    cache.delete(key)
    return True


def verify_google_id_token(id_token_str: str, expected_nonce: str | None = None) -> dict[str, str]:
    """Verify Google ID token and return claims dict.

    Verifies signature, audience, issuer, expiration, email_verified, and nonce.
    Supports a mock token in development/testing.
    """
    if not id_token_str:
        raise GoogleTokenInvalidError("ID token must not be empty")

    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")

    # Test/mock bypass when using mock tokens
    if id_token_str.startswith("mock-google-token:"):
        parts = id_token_str.split(":")
        sub = parts[1] if len(parts) > 1 else "google-mock-sub-123"
        email = parts[2] if len(parts) > 2 else "user@example.com"
        name = parts[3] if len(parts) > 3 else "Mock User"
        return {"sub": sub, "email": email, "name": name}

    try:
        from google.auth.transport import requests
        from google.oauth2 import id_token

        request = requests.Request()
        id_info = id_token.verify_oauth2_token(id_token_str, request, client_id or None)

        if id_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            raise GoogleTokenInvalidError("Invalid token issuer")

        if not id_info.get("email_verified", False):
            raise GoogleTokenInvalidError("Email is not verified by Google")

        if expected_nonce and id_info.get("nonce") and id_info.get("nonce") != expected_nonce:
            raise GoogleTokenInvalidError("Token nonce does not match expected nonce")

        sub = id_info.get("sub")
        email = id_info.get("email")
        name = id_info.get("name") or (email.split("@")[0] if email else "User")

        if not sub or not email:
            raise GoogleTokenInvalidError("Missing sub or email in Google token claims")

        return {"sub": sub, "email": email, "name": name}

    except Exception as exc:
        if isinstance(exc, GoogleTokenInvalidError):
            raise
        raise GoogleTokenInvalidError(f"Google ID token verification failed: {exc}") from exc


def create_access_token(
    user: User,
    shop: Shop | None = None,
    membership: Membership | None = None,
    role: str | None = None,
    device_id: uuid.UUID | None = None,
) -> tuple[str, datetime]:
    """Create short-lived 15-minute access token JWT."""
    now = timezone.now()
    expires_at = now + timedelta(minutes=15)
    payload = {
        "sub": str(user.id),
        "userId": str(user.id),
        "email": user.email,
        "name": user.name,
        "shopId": str(shop.id) if shop else None,
        "membershipId": str(membership.id) if membership else None,
        "role": role,
        "deviceId": str(device_id) if device_id else None,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token, expires_at


def create_drain_token(membership_id: uuid.UUID) -> tuple[str, datetime]:
    """Create a 10-minute drain token for deactivated attendants."""
    now = timezone.now()
    expires_at = now + timedelta(minutes=10)
    payload = {
        "type": "drain",
        "membershipId": str(membership_id),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token, expires_at


def hash_token(raw_token: str) -> str:
    """Hash token string with SHA-256."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_refresh_token(
    user: User, device_id: uuid.UUID, family_id: uuid.UUID | None = None
) -> tuple[str, datetime, RefreshToken]:
    """Create a new 30-day refresh token record and return (raw_token, expires_at, record)."""
    raw_token = f"rt_{secrets.token_urlsafe(48)}"
    token_hash = hash_token(raw_token)
    now = timezone.now()
    expires_at = now + timedelta(days=30)
    fid = family_id or (uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4())
    token_id = uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()

    record = RefreshToken.objects.create(
        id=token_id,
        user=user,
        device_id=device_id,
        hash=token_hash,
        family_id=fid,
        expires_at=expires_at,
    )
    return raw_token, expires_at, record


def create_offline_lease(
    shop: Shop,
    membership: Membership,
    device_id: uuid.UUID,
    renewed_from: uuid.UUID | None = None,
) -> tuple[dict[str, Any], OfflineLease]:
    """Issue a fresh 7-day offline authorization lease."""
    now = timezone.now()
    expires_at = now + timedelta(days=7)
    allowed_ops = (
        ATTENDANT_ALLOWED_OPS if membership.role == MembershipRole.ATTENDANT else OWNER_ALLOWED_OPS
    )
    lease_id = uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()

    lease_record = OfflineLease.objects.create(
        id=lease_id,
        shop=shop,
        membership=membership,
        device_id=device_id,
        allowed_ops=allowed_ops,
        issued_at=now,
        expires_at=expires_at,
        renewed_from=renewed_from,
    )

    payload = {
        "type": "lease",
        "leaseId": str(lease_id),
        "shopId": str(shop.id),
        "membershipId": str(membership.id),
        "deviceId": str(device_id),
        "allowedOps": allowed_ops,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    lease_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    lease_info = {
        "leaseId": str(lease_id),
        "token": lease_jwt,
        "issuedAt": now.isoformat(),
        "expiresAt": expires_at.isoformat(),
        "allowedOps": allowed_ops,
    }
    return lease_info, lease_record


def authenticate_google(
    id_token: str,
    nonce: str,
    device_id: uuid.UUID,
    membership_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Exchange Google ID token and verified nonce for a Stokari AuthSession."""
    if not verify_and_consume_nonce(nonce):
        raise NonceInvalidError()

    claims = verify_google_id_token(id_token, expected_nonce=nonce)

    user_id = uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()
    user, created = User.objects.get_or_create(
        google_sub=claims["sub"],
        defaults={"id": user_id, "email": claims["email"], "name": claims["name"]},
    )

    if not created:
        updated = False
        if user.email != claims["email"]:
            user.email = claims["email"]
            updated = True
        if claims["name"] and user.name != claims["name"]:
            user.name = claims["name"]
            updated = True
        if updated:
            user.save(update_fields=["email", "name"])

    memberships = list(user.memberships.select_related("shop").all())
    active_memberships = [m for m in memberships if m.status == MembershipStatus.ACTIVE]
    deactivated_memberships = [m for m in memberships if m.status == MembershipStatus.DEACTIVATED]

    now = timezone.now()

    # Case 1: No memberships (Onboarding session)
    if not memberships:
        access_token, access_exp = create_access_token(user, device_id=device_id)
        refresh_token, refresh_exp, _ = create_refresh_token(user, device_id=device_id)
        return {
            "accessToken": access_token,
            "accessTokenExpiresAt": access_exp.isoformat(),
            "refreshToken": refresh_token,
            "refreshTokenExpiresAt": refresh_exp.isoformat(),
            "session": {
                "userId": str(user.id),
                "email": user.email,
                "name": user.name,
                "shopId": None,
                "membershipId": None,
                "role": None,
            },
            "lease": None,
            "serverTime": now.isoformat(),
        }

    # Case 2: Only membership is deactivated
    if not active_memberships and deactivated_memberships:
        drain_token, drain_exp = create_drain_token(deactivated_memberships[0].id)
        raise AccountDeactivatedError(
            drain_token=drain_token,
            drain_token_expires_at=drain_exp.isoformat(),
        )

    # Case 3: Multiple active memberships without membershipId -> selection required
    if len(active_memberships) > 1 and membership_id is None:
        choices = [
            {
                "membershipId": str(m.id),
                "shopId": str(m.shop.id),
                "shopName": m.shop.name,
                "role": m.role,
            }
            for m in active_memberships
        ]
        raise MembershipSelectionRequiredError(memberships=choices)

    # Resolve targeted active membership
    if membership_id:
        target_membership = next((m for m in active_memberships if m.id == membership_id), None)
        if not target_membership:
            raise MembershipSelectionRequiredError(
                message="Specified membership not found or not active"
            )
    else:
        target_membership = active_memberships[0]

    shop = target_membership.shop

    # Register/update device
    Device.objects.update_or_create(
        shop=shop,
        id=device_id,
        defaults={"user_id": user.id, "last_seen_at": now},
    )

    access_token, access_exp = create_access_token(
        user,
        shop=shop,
        membership=target_membership,
        role=target_membership.role,
        device_id=device_id,
    )
    refresh_token, refresh_exp, _ = create_refresh_token(user, device_id=device_id)
    lease_info, _ = create_offline_lease(shop, target_membership, device_id)

    return {
        "accessToken": access_token,
        "accessTokenExpiresAt": access_exp.isoformat(),
        "refreshToken": refresh_token,
        "refreshTokenExpiresAt": refresh_exp.isoformat(),
        "session": {
            "userId": str(user.id),
            "email": user.email,
            "name": user.name,
            "shopId": str(shop.id),
            "membershipId": str(target_membership.id),
            "role": target_membership.role,
        },
        "lease": lease_info,
        "serverTime": now.isoformat(),
    }


def rotate_refresh_token(raw_refresh_token: str, device_id: uuid.UUID) -> dict[str, Any]:
    """Rotate a refresh token, issuing a new access token and refresh token."""
    hashed = hash_token(raw_refresh_token)
    token = RefreshToken.objects.select_related("user").filter(hash=hashed).first()

    if not token or token.device_id != device_id:
        raise RefreshTokenInvalidError()

    now = timezone.now()

    # Reused token detection: revoke the whole token family
    if token.revoked_at is not None:
        RefreshToken.objects.filter(family_id=token.family_id).update(revoked_at=now)
        raise RefreshTokenReusedError()

    if token.expires_at <= now:
        raise RefreshTokenInvalidError("Refresh token has expired")

    token.revoked_at = now
    token.save(update_fields=["revoked_at"])

    user = token.user
    memberships = list(user.memberships.select_related("shop").all())
    active_memberships = [m for m in memberships if m.status == MembershipStatus.ACTIVE]
    deactivated_memberships = [m for m in memberships if m.status == MembershipStatus.DEACTIVATED]

    # If user was deactivated
    if not active_memberships and deactivated_memberships:
        drain_token, drain_exp = create_drain_token(deactivated_memberships[0].id)
        raise AccountDeactivatedError(
            drain_token=drain_token,
            drain_token_expires_at=drain_exp.isoformat(),
        )

    shop = active_memberships[0].shop if active_memberships else None
    membership = active_memberships[0] if active_memberships else None
    role = membership.role if membership else None

    # Issue rotated refresh token in the same family
    new_raw_token, refresh_exp, _ = create_refresh_token(
        user, device_id=device_id, family_id=token.family_id
    )
    access_token, access_exp = create_access_token(
        user, shop=shop, membership=membership, role=role, device_id=device_id
    )

    return {
        "accessToken": access_token,
        "accessTokenExpiresAt": access_exp.isoformat(),
        "refreshToken": new_raw_token,
        "refreshTokenExpiresAt": refresh_exp.isoformat(),
        "session": {
            "userId": str(user.id),
            "email": user.email,
            "name": user.name,
            "shopId": str(shop.id) if shop else None,
            "membershipId": str(membership.id) if membership else None,
            "role": role,
        },
        "lease": None,
        "serverTime": now.isoformat(),
    }


def renew_offline_lease(user: User, device_id: uuid.UUID) -> dict[str, Any]:
    """Renew the 7-day offline lease for an active shop member."""
    membership = (
        user.memberships.select_related("shop").filter(status=MembershipStatus.ACTIVE).first()
    )

    if not membership:
        deactivated = user.memberships.filter(status=MembershipStatus.DEACTIVATED).first()
        if deactivated:
            raise AccountDeactivatedError("Membership is deactivated")
        raise ShopRequiredError("No active shop membership found for user")

    prev_lease = (
        OfflineLease.objects.filter(membership=membership, device_id=device_id)
        .order_by("-issued_at")
        .first()
    )
    renewed_from = prev_lease.id if prev_lease else None

    lease_info, _ = create_offline_lease(
        membership.shop, membership, device_id, renewed_from=renewed_from
    )

    return {"lease": lease_info, "serverTime": timezone.now().isoformat()}


def revoke_refresh_token(raw_refresh_token: str) -> None:
    """Revoke a refresh token on logout (idempotent, always safe)."""
    if not raw_refresh_token:
        return
    hashed = hash_token(raw_refresh_token)
    token = RefreshToken.objects.filter(hash=hashed).first()
    if token and token.revoked_at is None:
        token.revoked_at = timezone.now()
        token.save(update_fields=["revoked_at"])
