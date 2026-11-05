import uuid
from datetime import timedelta

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django_auth_headless.models import OAuthHandoffCode
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.models import User as IdentityUser
from apps.shops.models import Membership, MembershipRole, MembershipStatus, Shop

DjangoUser = get_user_model()


class AuthBridgeTests(TestCase):
    def setUp(self):
        self.client = APIClient(HTTP_HOST="localhost")
        self.device_id = uuid.uuid4()

    def test_exchange_valid_code_provisions_user_and_issues_session(self):
        django_user = DjangoUser.objects.create_user(
            username="google_user",
            email="google_user@example.com",
            first_name="Google",
            last_name="Tester",
        )
        SocialAccount.objects.create(
            user=django_user,
            provider="google",
            uid="google-sub-12345",
            extra_data={"email": "google_user@example.com", "name": "Google Tester"},
        )
        _, raw_code = OAuthHandoffCode.issue(django_user, timedelta(minutes=5))

        res = self.client.post(
            "/api/auth/exchange",
            {
                "code": raw_code,
                "deviceId": str(self.device_id),
            },
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data

        # Verify Stokari AuthSession payload
        self.assertIn("accessToken", data)
        self.assertIn("refreshToken", data)
        self.assertIn("session", data)
        self.assertIn("serverTime", data)

        # Verify persistent domain user
        identity_user = IdentityUser.objects.get(google_sub="google-sub-12345")
        self.assertEqual(identity_user.email, "google_user@example.com")
        self.assertEqual(identity_user.name, "Google Tester")
        self.assertEqual(data["session"]["userId"], str(identity_user.id))

    def test_exchange_code_is_single_use(self):
        django_user = DjangoUser.objects.create_user(username="single_use_user")
        _, raw_code = OAuthHandoffCode.issue(django_user, timedelta(minutes=5))

        first_res = self.client.post(
            "/api/auth/exchange",
            {
                "code": raw_code,
                "deviceId": str(self.device_id),
            },
            format="json",
        )
        self.assertEqual(first_res.status_code, status.HTTP_200_OK)

        # Second redemption with same code must fail
        second_res = self.client.post(
            "/api/auth/exchange",
            {
                "code": raw_code,
                "deviceId": str(self.device_id),
            },
            format="json",
        )
        self.assertEqual(second_res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_exchange_missing_device_id_fails_validation(self):
        django_user = DjangoUser.objects.create_user(username="no_device_user")
        _, raw_code = OAuthHandoffCode.issue(django_user, timedelta(minutes=5))

        res = self.client.post(
            "/api/auth/exchange",
            {"code": raw_code},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_exchange_existing_identity_user_reuses_record(self):
        existing_user = IdentityUser.objects.create(
            id=uuid.uuid4(),
            google_sub="google-sub-existing",
            email="existing@example.com",
            name="Existing Merchant",
        )
        django_user = DjangoUser.objects.create_user(
            username="existing_django",
            email="existing@example.com",
        )
        SocialAccount.objects.create(
            user=django_user,
            provider="google",
            uid="google-sub-existing",
            extra_data={"email": "existing@example.com", "name": "Existing Merchant"},
        )
        _, raw_code = OAuthHandoffCode.issue(django_user, timedelta(minutes=5))

        res = self.client.post(
            "/api/auth/exchange",
            {
                "code": raw_code,
                "deviceId": str(self.device_id),
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["session"]["userId"], str(existing_user.id))

    def test_exchange_active_owner_gets_offline_lease_and_shop_claims(self):
        django_user = DjangoUser.objects.create_user(
            username="shop_owner",
            email="owner@example.com",
        )
        SocialAccount.objects.create(
            user=django_user,
            provider="google",
            uid="google-sub-owner",
            extra_data={"email": "owner@example.com", "name": "Owner Name"},
        )
        identity_user = IdentityUser.objects.create(
            id=uuid.uuid4(),
            google_sub="google-sub-owner",
            email="owner@example.com",
            name="Owner Name",
        )
        shop = Shop.objects.create(id=uuid.uuid4(), name="Central Depot")
        membership = Membership.objects.create(
            id=uuid.uuid4(),
            shop=shop,
            user=identity_user,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )

        _, raw_code = OAuthHandoffCode.issue(django_user, timedelta(minutes=5))

        res = self.client.post(
            "/api/auth/exchange",
            {
                "code": raw_code,
                "deviceId": str(self.device_id),
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data

        self.assertEqual(data["session"]["shopId"], str(shop.id))
        self.assertEqual(data["session"]["membershipId"], str(membership.id))
        self.assertEqual(data["session"]["role"], "OWNER")
        self.assertIsNotNone(data["lease"])
        self.assertIn("CreateProduct", data["lease"]["allowedOps"])
        self.assertIn("RecordSale", data["lease"]["allowedOps"])

    def test_exchange_multiple_memberships_without_selection_returns_409(self):
        django_user = DjangoUser.objects.create_user(
            username="multi_user",
            email="multi@example.com",
        )
        SocialAccount.objects.create(
            user=django_user,
            provider="google",
            uid="google-sub-multi",
            extra_data={"email": "multi@example.com", "name": "Multi User"},
        )
        identity_user = IdentityUser.objects.create(
            id=uuid.uuid4(),
            google_sub="google-sub-multi",
            email="multi@example.com",
            name="Multi User",
        )
        shop1 = Shop.objects.create(id=uuid.uuid4(), name="Store 1")
        shop2 = Shop.objects.create(id=uuid.uuid4(), name="Store 2")
        m1 = Membership.objects.create(
            id=uuid.uuid4(),
            shop=shop1,
            user=identity_user,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        Membership.objects.create(
            id=uuid.uuid4(),
            shop=shop2,
            user=identity_user,
            role=MembershipRole.ATTENDANT,
            status=MembershipStatus.ACTIVE,
        )

        _, raw_code = OAuthHandoffCode.issue(django_user, timedelta(minutes=5))

        # 1. Exchange without membershipId returns 409
        res = self.client.post(
            "/api/auth/exchange",
            {
                "code": raw_code,
                "deviceId": str(self.device_id),
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(res.data["code"], "MEMBERSHIP_SELECTION_REQUIRED")

        # 2. Exchange with chosen membership succeeds
        _, raw_code_2 = OAuthHandoffCode.issue(django_user, timedelta(minutes=5))
        res2 = self.client.post(
            "/api/auth/exchange",
            {
                "code": raw_code_2,
                "deviceId": str(self.device_id),
                "membershipId": str(m1.id),
            },
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["session"]["shopId"], str(shop1.id))

    def test_exchange_deactivated_attendant_returns_403_drain_token(self):
        django_user = DjangoUser.objects.create_user(
            username="deact_user",
            email="deact@example.com",
        )
        SocialAccount.objects.create(
            user=django_user,
            provider="google",
            uid="google-sub-deact",
            extra_data={"email": "deact@example.com", "name": "Deact User"},
        )
        identity_user = IdentityUser.objects.create(
            id=uuid.uuid4(),
            google_sub="google-sub-deact",
            email="deact@example.com",
            name="Deact User",
        )
        shop = Shop.objects.create(id=uuid.uuid4(), name="Store")
        Membership.objects.create(
            id=uuid.uuid4(),
            shop=shop,
            user=identity_user,
            role=MembershipRole.ATTENDANT,
            status=MembershipStatus.DEACTIVATED,
            deactivated_at=timezone.now(),
        )

        _, raw_code = OAuthHandoffCode.issue(django_user, timedelta(minutes=5))

        res = self.client.post(
            "/api/auth/exchange",
            {
                "code": raw_code,
                "deviceId": str(self.device_id),
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data["code"], "ACCOUNT_DEACTIVATED")
        self.assertIn("drainToken", res.data)

    def test_current_user_endpoint_with_stokari_jwt(self):
        django_user = DjangoUser.objects.create_user(
            username="current_tester",
            email="current@example.com",
        )
        SocialAccount.objects.create(
            user=django_user,
            provider="google",
            uid="google-sub-current",
            extra_data={"email": "current@example.com", "name": "Current Tester"},
        )
        _, raw_code = OAuthHandoffCode.issue(django_user, timedelta(minutes=5))

        exchange_res = self.client.post(
            "/api/auth/exchange",
            {
                "code": raw_code,
                "deviceId": str(self.device_id),
            },
            format="json",
        )
        access_token = exchange_res.data["accessToken"]

        # Call GET /api/me with Stokari JWT Bearer token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        me_res = self.client.get("/api/me")
        self.assertEqual(me_res.status_code, status.HTTP_200_OK)
        self.assertEqual(me_res.data["status"], 200)
        self.assertEqual(me_res.data["data"]["user"]["email"], "current@example.com")
        self.assertEqual(me_res.data["data"]["user"]["name"], "Current Tester")
        self.assertEqual(me_res.data["data"]["session"]["deviceId"], str(self.device_id))
