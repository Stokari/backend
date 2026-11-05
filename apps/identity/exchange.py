"""Bridge logic for redeeming django-auth-headless handoff codes into Stokari AuthSessions."""

import uuid
from typing import Any

from allauth.socialaccount.models import SocialAccount
from django_auth_headless.models import OAuthHandoffCode

from apps.identity.models import User
from apps.identity.services import create_user_session
from common.core.errors import ValidationError


def exchange_code_for_session(
    raw_code: str,
    device_id: uuid.UUID,
    membership_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Redeem a one-time OAuthHandoffCode and produce a Stokari AuthSession."""
    user = OAuthHandoffCode.redeem(raw_code)
    if user is None:
        raise ValidationError("The authorization code is invalid or expired.")

    # Extract identity attributes from allauth SocialAccount if available
    social_account = SocialAccount.objects.filter(user=user, provider="google").first()
    if social_account:
        google_sub = str(social_account.uid)
        email = user.email or social_account.extra_data.get("email", "")
        name = (
            user.get_full_name() or social_account.extra_data.get("name") or user.username
        ).strip()
    else:
        google_sub = f"django-{user.pk}"
        email = user.email or ""
        name = (user.get_full_name() or user.username).strip()

    # Resolve or provision Stokari's domain user
    identity_user, created = User.objects.get_or_create(
        google_sub=google_sub,
        defaults={
            "id": uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            "email": email,
            "name": name or "User",
        },
    )

    if not created:
        update_fields = []
        if email and identity_user.email != email:
            identity_user.email = email
            update_fields.append("email")
        if name and identity_user.name != name:
            identity_user.name = name
            update_fields.append("name")
        if update_fields:
            identity_user.save(update_fields=update_fields)

    # Issue full Stokari session (JWT access token, refresh token, offline lease)
    return create_user_session(
        user=identity_user,
        device_id=device_id,
        membership_id=membership_id,
    )
