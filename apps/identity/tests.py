import uuid
from datetime import timedelta

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.models import OfflineLease, RefreshToken, User
from apps.identity.services import (
    create_access_token,
    generate_nonce,
    verify_and_consume_nonce,
)
from apps.shops.models import Membership, MembershipRole, MembershipStatus, Shop


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
        cache.clear()
        self.client = APIClient()
        self.device_id = uuid.uuid4()

    def test_nonce_issuance_and_single_use(self):
        # 1. Fetch nonce
        response = self.client.get("/v1/auth/nonce")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        nonce = response.data["nonce"]
        self.assertTrue(nonce.startswith("n_"))
        self.assertIn("expiresAt", response.data)

        # 2. Verify and consume
        self.assertTrue(verify_and_consume_nonce(nonce))
        # 3. Re-consuming fails
        self.assertFalse(verify_and_consume_nonce(nonce))

    def test_google_sign_in_new_user_onboarding_session(self):
        nonce_data = generate_nonce()
        nonce = nonce_data["nonce"]

        response = self.client.post(
            "/v1/auth/google",
            {
                "idToken": "mock-google-token:sub-new:new@example.com:New User",
                "nonce": nonce,
                "deviceId": str(self.device_id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn("accessToken", data)
        self.assertIn("refreshToken", data)
        self.assertIsNone(data["lease"])
        self.assertIsNone(data["session"]["shopId"])
        self.assertIsNone(data["session"]["membershipId"])
        self.assertIsNone(data["session"]["role"])
        self.assertEqual(data["session"]["email"], "new@example.com")
        self.assertEqual(data["session"]["name"], "New User")

        # User record was created in database
        user = User.objects.get(google_sub="sub-new")
        self.assertEqual(user.email, "new@example.com")

    def test_google_sign_in_active_owner_receives_lease_and_session(self):
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

        nonce = generate_nonce()["nonce"]
        response = self.client.post(
            "/v1/auth/google",
            {
                "idToken": "mock-google-token:sub-owner:owner@example.com:Shop Owner",
                "nonce": nonce,
                "deviceId": str(self.device_id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
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

    def test_google_sign_in_active_attendant_allowed_ops(self):
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

        nonce = generate_nonce()["nonce"]
        response = self.client.post(
            "/v1/auth/google",
            {
                "idToken": "mock-google-token:sub-attendant:attendant@example.com:Attendant",
                "nonce": nonce,
                "deviceId": str(self.device_id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lease = response.data["lease"]
        self.assertEqual(lease["allowedOps"], ["RecordSale"])

    def test_google_sign_in_multiple_memberships_requires_selection(self):
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

        # 1. Calling without membershipId gives 409 MEMBERSHIP_SELECTION_REQUIRED
        nonce1 = generate_nonce()["nonce"]
        response = self.client.post(
            "/v1/auth/google",
            {
                "idToken": "mock-google-token:sub-multi:multi@example.com:Multi Member",
                "nonce": nonce1,
                "deviceId": str(self.device_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "MEMBERSHIP_SELECTION_REQUIRED")
        self.assertEqual(len(response.data["memberships"]), 2)

        # 2. Calling with membershipId selects that specific shop
        nonce2 = generate_nonce()["nonce"]
        response2 = self.client.post(
            "/v1/auth/google",
            {
                "idToken": "mock-google-token:sub-multi:multi@example.com:Multi Member",
                "nonce": nonce2,
                "deviceId": str(self.device_id),
                "membershipId": str(m1.id),
            },
            format="json",
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data["session"]["shopId"], str(shop1.id))
        self.assertEqual(response2.data["session"]["role"], "OWNER")

    def test_google_sign_in_deactivated_attendant_gives_403_and_drain_token(self):
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

        nonce = generate_nonce()["nonce"]
        response = self.client.post(
            "/v1/auth/google",
            {
                "idToken": "mock-google-token:sub-deact:deact@example.com:Deactivated",
                "nonce": nonce,
                "deviceId": str(self.device_id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "ACCOUNT_DEACTIVATED")
        self.assertIn("drainToken", response.data)
        self.assertIn("drainTokenExpiresAt", response.data)

    def test_google_sign_in_invalid_nonce_rejected(self):
        response = self.client.post(
            "/v1/auth/google",
            {
                "idToken": "mock-google-token:sub:test@example.com:Test",
                "nonce": "n_invalid_nonce_123",
                "deviceId": str(self.device_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["code"], "NONCE_INVALID")

    def test_refresh_token_rotation_and_family_reuse_detection(self):
        # 1. Sign in to obtain initial tokens
        nonce = generate_nonce()["nonce"]
        login_res = self.client.post(
            "/v1/auth/google",
            {
                "idToken": "mock-google-token:sub-rot:rot@example.com:Rotator",
                "nonce": nonce,
                "deviceId": str(self.device_id),
            },
            format="json",
        )
        refresh_token_1 = login_res.data["refreshToken"]

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
        nonce = generate_nonce()["nonce"]
        login_res = self.client.post(
            "/v1/auth/google",
            {
                "idToken": "mock-google-token:sub-logout:logout@example.com:Logout User",
                "nonce": nonce,
                "deviceId": str(self.device_id),
            },
            format="json",
        )
        refresh_token = login_res.data["refreshToken"]

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
