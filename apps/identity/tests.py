import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.identity.models import RefreshToken, User


class IdentityModelTests(TestCase):
    def test_user_google_subject_is_unique(self):
        User.objects.create(
            id=uuid.uuid4(),
            google_sub="google-sub",
            email="owner@example.com",
            name="Owner",
        )

        duplicate = User(
            id=uuid.uuid4(),
            google_sub="google-sub",
            email="other@example.com",
            name="Other",
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_refresh_token_stores_hash_and_revocation_fields(self):
        user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="google-sub",
            email="owner@example.com",
            name="Owner",
        )
        token = RefreshToken.objects.create(
            id=uuid.uuid4(),
            user=user,
            device_id=uuid.uuid4(),
            hash="b" * 64,
            family_id=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=30),
        )

        self.assertEqual(token.hash, "b" * 64)
        self.assertIsNone(token.revoked_at)
