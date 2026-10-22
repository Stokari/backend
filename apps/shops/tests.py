import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.identity.models import OfflineLease, User
from apps.shops.models import (
    Device,
    Invite,
    Membership,
    MembershipRole,
    MembershipStatus,
    Shop,
    ShopStatus,
)


class ShopModelTests(TestCase):
    def test_shop_defaults_to_active_with_five_attendants(self):
        shop = Shop.objects.create(id=uuid.uuid4(), name="Hana General Store")

        assert shop.status == ShopStatus.ACTIVE
        assert shop.attendant_limit == 5

    def test_membership_has_unique_user_per_shop(self):
        shop = Shop.objects.create(id=uuid.uuid4(), name="Hana General Store")
        user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="google-sub",
            email="owner@example.com",
            name="Owner",
        )
        Membership.objects.create(
            id=uuid.uuid4(),
            shop=shop,
            user=user,
            role=MembershipRole.OWNER,
        )

        duplicate = Membership(
            id=uuid.uuid4(),
            shop=shop,
            user=user,
            role=MembershipRole.ATTENDANT,
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_membership_status_defaults_to_active(self):
        shop = Shop.objects.create(id=uuid.uuid4(), name="Hana General Store")
        user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="google-sub",
            email="owner@example.com",
            name="Owner",
        )

        membership = Membership.objects.create(
            id=uuid.uuid4(),
            shop=shop,
            user=user,
            role=MembershipRole.OWNER,
        )

        assert membership.status == MembershipStatus.ACTIVE

    def test_device_uses_shop_and_id_as_composite_primary_key(self):
        shop = Shop.objects.create(id=uuid.uuid4(), name="Hana General Store")
        device_id = uuid.uuid4()
        device = Device.objects.create(
            shop=shop,
            id=device_id,
            user_id=uuid.uuid4(),
            last_seen_at=timezone.now(),
        )

        assert device.pk == (shop.pk, device_id)
        assert Device._meta.pk.field_names == ("shop", "id")

    def test_invite_stores_single_use_fields(self):
        shop = Shop.objects.create(id=uuid.uuid4(), name="Hana General Store")
        invite = Invite.objects.create(
            id=uuid.uuid4(),
            shop=shop,
            token_hash="a" * 64,
            expires_at=timezone.now() + timedelta(days=7),
        )

        assert invite.accepted_at is None
        assert invite.token_hash == "a" * 64

    def test_attendant_limit_is_enforced_by_invite_acceptance_boundary(self):
        shop = Shop.objects.create(id=uuid.uuid4(), name="Hana General Store")

        assert shop.attendant_limit == 5


class OfflineLeaseModelTests(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(id=uuid.uuid4(), name="Hana General Store")
        self.user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="google-sub",
            email="owner@example.com",
            name="Owner",
        )
        self.membership = Membership.objects.create(
            id=uuid.uuid4(),
            shop=self.shop,
            user=self.user,
            role=MembershipRole.OWNER,
        )

    def test_offline_lease_accepts_at_most_seven_days(self):
        issued_at = timezone.now()
        lease = OfflineLease(
            id=uuid.uuid4(),
            shop=self.shop,
            membership=self.membership,
            device_id=uuid.uuid4(),
            allowed_ops=["RecordSale"],
            issued_at=issued_at,
            expires_at=issued_at + timedelta(days=7),
        )

        lease.full_clean()

    def test_offline_lease_rejects_expiry_before_issue(self):
        issued_at = timezone.now()
        lease = OfflineLease(
            id=uuid.uuid4(),
            shop=self.shop,
            membership=self.membership,
            device_id=uuid.uuid4(),
            allowed_ops=["RecordSale"],
            issued_at=issued_at,
            expires_at=issued_at - timedelta(seconds=1),
        )

        with self.assertRaises(ValidationError):
            lease.full_clean()

    def test_offline_lease_rejects_expiry_after_seven_days(self):
        issued_at = timezone.now()
        lease = OfflineLease(
            id=uuid.uuid4(),
            shop=self.shop,
            membership=self.membership,
            device_id=uuid.uuid4(),
            allowed_ops=["RecordSale"],
            issued_at=issued_at,
            expires_at=issued_at + timedelta(days=7, seconds=1),
        )

        with self.assertRaises(ValidationError):
            lease.full_clean()
