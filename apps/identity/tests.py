import uuid
from datetime import timedelta
from unittest import skipUnless

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from apps.identity.models import OfflineLease, RefreshToken, User
from apps.shops.models import Membership, MembershipRole, Shop


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


@skipUnless(connection.vendor == "postgresql", "PostgreSQL is required for integrity tests")
class OfflineLeaseIntegrityTests(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(id=uuid.uuid4(), name="Hana General Store")
        self.other_shop = Shop.objects.create(id=uuid.uuid4(), name="Kebede Market")
        self.user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="google-sub",
            email="owner@example.com",
            name="Owner",
        )
        self.other_user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="other-google-sub",
            email="other@example.com",
            name="Other Owner",
        )
        self.membership = Membership.objects.create(
            id=uuid.uuid4(),
            shop=self.shop,
            user=self.user,
            role=MembershipRole.OWNER,
        )
        self.other_membership = Membership.objects.create(
            id=uuid.uuid4(),
            shop=self.other_shop,
            user=self.other_user,
            role=MembershipRole.OWNER,
        )

    def lease_kwargs(self, shop, membership):
        issued_at = timezone.now()
        return {
            "id": uuid.uuid4(),
            "shop": shop,
            "membership": membership,
            "device_id": uuid.uuid4(),
            "allowed_ops": ["RecordSale"],
            "issued_at": issued_at,
            "expires_at": issued_at + timedelta(days=1),
        }

    def test_same_shop_membership_relationship_is_accepted(self):
        lease = OfflineLease.objects.create(
            **self.lease_kwargs(self.shop, self.membership),
        )

        self.assertEqual(lease.shop_id, self.membership.shop_id)

    def test_cross_shop_membership_relationship_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OfflineLease.objects.create(
                    **self.lease_kwargs(self.shop, self.other_membership),
                )

    def test_membership_deletion_is_rejected_while_lease_exists(self):
        OfflineLease.objects.create(
            **self.lease_kwargs(self.shop, self.membership),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM membership WHERE id = %s",
                        [self.membership.pk],
                    )
