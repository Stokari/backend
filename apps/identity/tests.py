import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.models import OfflineLease, RefreshToken, User
from apps.identity.services import (
    create_access_token,
    create_user_session,
)
from apps.shops.models import Membership, MembershipRole, MembershipStatus, Shop
from common.core.errors import AccountDeactivatedError, MembershipSelectionRequiredError


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


class AuthEndpointsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.device_id = uuid.uuid4()

    def test_session_creation_onboarding_session(self):
        user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="sub-new",
            email="new@example.com",
            name="New User",
        )
        data = create_user_session(user, device_id=self.device_id)

        self.assertIn("accessToken", data)
        self.assertIn("refreshToken", data)
        self.assertIsNone(data["lease"])
        self.assertIsNone(data["session"]["shopId"])
        self.assertIsNone(data["session"]["membershipId"])
        self.assertIsNone(data["session"]["role"])
        self.assertEqual(data["session"]["email"], "new@example.com")
        self.assertEqual(data["session"]["name"], "New User")

    def test_session_creation_active_owner_receives_lease_and_session(self):
        user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="sub-owner",
            email="owner@example.com",
            name="Shop Owner",
        )
        shop = Shop.objects.create(id=uuid.uuid4(), name="Central Depot")
        membership = Membership.objects.create(
            id=uuid.uuid4(),
            shop=shop,
            user=user,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )

        data = create_user_session(user, device_id=self.device_id)

        self.assertEqual(data["session"]["shopId"], str(shop.id))
        self.assertEqual(data["session"]["membershipId"], str(membership.id))
        self.assertEqual(data["session"]["role"], "OWNER")

        # Lease is issued with owner permissions
        lease = data["lease"]
        self.assertIsNotNone(lease)
        self.assertIn("CreateProduct", lease["allowedOps"])
        self.assertIn("RecordSale", lease["allowedOps"])

        # OfflineLease record exists in DB
        db_lease = OfflineLease.objects.get(id=lease["leaseId"])
        self.assertEqual(db_lease.shop, shop)
        self.assertEqual(db_lease.membership, membership)
        self.assertEqual(db_lease.device_id, self.device_id)

    def test_session_creation_active_attendant_allowed_ops(self):
        user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="sub-attendant",
            email="attendant@example.com",
            name="Attendant",
        )
        shop = Shop.objects.create(id=uuid.uuid4(), name="Store #1")
        Membership.objects.create(
            id=uuid.uuid4(),
            shop=shop,
            user=user,
            role=MembershipRole.ATTENDANT,
            status=MembershipStatus.ACTIVE,
        )

        data = create_user_session(user, device_id=self.device_id)
        lease = data["lease"]
        self.assertEqual(lease["allowedOps"], ["RecordSale"])

    def test_session_creation_multiple_memberships_requires_selection(self):
        user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="sub-multi",
            email="multi@example.com",
            name="Multi Member",
        )
        shop1 = Shop.objects.create(id=uuid.uuid4(), name="Shop One")
        shop2 = Shop.objects.create(id=uuid.uuid4(), name="Shop Two")
        m1 = Membership.objects.create(
            id=uuid.uuid4(),
            shop=shop1,
            user=user,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        Membership.objects.create(
            id=uuid.uuid4(),
            shop=shop2,
            user=user,
            role=MembershipRole.ATTENDANT,
            status=MembershipStatus.ACTIVE,
        )

        # 1. Calling without membershipId raises MembershipSelectionRequiredError
        with self.assertRaises(MembershipSelectionRequiredError) as ctx:
            create_user_session(user, device_id=self.device_id)
        self.assertEqual(ctx.exception.code, "MEMBERSHIP_SELECTION_REQUIRED")

        # 2. Calling with membershipId selects that specific shop
        data = create_user_session(user, device_id=self.device_id, membership_id=m1.id)
        self.assertEqual(data["session"]["shopId"], str(shop1.id))
        self.assertEqual(data["session"]["role"], "OWNER")

    def test_session_creation_deactivated_attendant_gives_drain_token(self):
        user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="sub-deact",
            email="deact@example.com",
            name="Deactivated Staff",
        )
        shop = Shop.objects.create(id=uuid.uuid4(), name="Shop")
        Membership.objects.create(
            id=uuid.uuid4(),
            shop=shop,
            user=user,
            role=MembershipRole.ATTENDANT,
            status=MembershipStatus.DEACTIVATED,
            deactivated_at=timezone.now(),
        )

        with self.assertRaises(AccountDeactivatedError) as ctx:
            create_user_session(user, device_id=self.device_id)
        self.assertEqual(ctx.exception.code, "ACCOUNT_DEACTIVATED")
        self.assertTrue(ctx.exception.details["drainToken"])

    def test_refresh_token_rotation_and_family_reuse_detection(self):
        user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="sub-rot",
            email="rot@example.com",
            name="Rotator",
        )
        session = create_user_session(user, device_id=self.device_id)
        refresh_token_1 = session["refreshToken"]

        # 2. Rotate token
        rotate_res = self.client.post(
            "/v1/auth/refresh",
            {"refreshToken": refresh_token_1, "deviceId": str(self.device_id)},
            format="json",
        )
        self.assertEqual(rotate_res.status_code, status.HTTP_200_OK)
        refresh_token_2 = rotate_res.data["refreshToken"]
        self.assertNotEqual(refresh_token_1, refresh_token_2)

        # 3. Presenting the old (already rotated) token triggers reuse detection
        reuse_res = self.client.post(
            "/v1/auth/refresh",
            {"refreshToken": refresh_token_1, "deviceId": str(self.device_id)},
            format="json",
        )
        self.assertEqual(reuse_res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(reuse_res.data["code"], "REFRESH_TOKEN_REUSED")

        # 4. Whole family is revoked; even refresh_token_2 cannot be used anymore
        cascade_res = self.client.post(
            "/v1/auth/refresh",
            {"refreshToken": refresh_token_2, "deviceId": str(self.device_id)},
            format="json",
        )
        self.assertEqual(cascade_res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(cascade_res.data["code"], "REFRESH_TOKEN_REUSED")

    def test_lease_renewal_flow(self):
        user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="sub-lease",
            email="lease@example.com",
            name="Lease User",
        )
        shop = Shop.objects.create(id=uuid.uuid4(), name="Lease Shop")
        membership = Membership.objects.create(
            id=uuid.uuid4(),
            shop=shop,
            user=user,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )

        access_token, _ = create_access_token(
            user, shop=shop, membership=membership, role=membership.role, device_id=self.device_id
        )

        # 1. Unauthenticated request rejected
        unauth_res = self.client.post(
            "/v1/auth/lease",
            {"deviceId": str(self.device_id)},
            format="json",
        )
        self.assertEqual(unauth_res.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Authenticated request succeeds
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        renew_res = self.client.post(
            "/v1/auth/lease",
            {"deviceId": str(self.device_id)},
            format="json",
        )
        self.assertEqual(renew_res.status_code, status.HTTP_200_OK)

        self.assertIn("lease", renew_res.data)
        self.assertIn("token", renew_res.data["lease"])
        self.assertIn("serverTime", renew_res.data)

    def test_logout_revokes_refresh_token(self):
        user = User.objects.create(
            id=uuid.uuid4(),
            google_sub="sub-logout",
            email="logout@example.com",
            name="Logout User",
        )
        session = create_user_session(user, device_id=self.device_id)
        refresh_token = session["refreshToken"]

        # Logout with 204
        logout_res = self.client.post(
            "/v1/auth/logout",
            {"refreshToken": refresh_token},
            format="json",
        )
        self.assertEqual(logout_res.status_code, status.HTTP_204_NO_CONTENT)

        # Attempting to refresh with the revoked token fails
        refresh_res = self.client.post(
            "/v1/auth/refresh",
            {"refreshToken": refresh_token, "deviceId": str(self.device_id)},
            format="json",
        )
        self.assertEqual(refresh_res.status_code, status.HTTP_401_UNAUTHORIZED)
