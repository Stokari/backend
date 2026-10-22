import uuid
from datetime import timedelta

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import F


class User(models.Model):
    id = models.UUIDField(primary_key=True)
    google_sub = models.TextField(unique=True)
    email = models.TextField()
    name = models.TextField()

    class Meta:
        db_table = "app_user"


class OfflineLease(models.Model):
    id = models.UUIDField(primary_key=True)
    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.PROTECT,
        related_name="offline_leases",
    )
    membership = models.ForeignKey(
        "shops.Membership",
        on_delete=models.PROTECT,
        related_name="offline_leases",
    )
    device_id = models.UUIDField()
    allowed_ops = ArrayField(models.CharField(max_length=40))
    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    renewed_from = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "offline_lease"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expires_at__gt=F("issued_at")),
                name="ck_offline_lease_expires_after_issue",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    expires_at__lte=F("issued_at") + timedelta(days=7),
                ),
                name="ck_offline_lease_max_seven_days",
            ),
        ]


class RefreshToken(models.Model):
    id = models.UUIDField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="refresh_tokens",
    )
    device_id = models.UUIDField()
    hash = models.CharField(max_length=64, unique=True)
    family_id = models.UUIDField()
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "refresh_token"
