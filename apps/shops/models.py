from django.db import models


class ShopStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    CLOSED = "CLOSED", "Closed"


class MembershipRole(models.TextChoices):
    OWNER = "OWNER", "Owner"
    ATTENDANT = "ATTENDANT", "Attendant"


class MembershipStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    DEACTIVATED = "DEACTIVATED", "Deactivated"


class Shop(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=ShopStatus,
        default=ShopStatus.ACTIVE,
    )
    sync_seq = models.BigIntegerField(default=0)
    attendant_limit = models.PositiveSmallIntegerField(default=5)
    closed_at = models.DateTimeField(null=True)
    retain_until = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "shop"


class Membership(models.Model):
    id = models.UUIDField(primary_key=True)
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name="memberships")
    user = models.ForeignKey(
        "identity.User",
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    role = models.CharField(max_length=10, choices=MembershipRole)
    status = models.CharField(
        max_length=12,
        choices=MembershipStatus,
        default=MembershipStatus.ACTIVE,
    )
    deactivated_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "membership"
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "user"],
                name="uq_membership_shop_user",
            ),
            models.UniqueConstraint(
                fields=["shop", "id"],
                name="uq_membership_shop_id",
            ),
        ]
        indexes = [models.Index(fields=["user", "status"])]


class Device(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name="devices")
    id = models.UUIDField()
    pk = models.CompositePrimaryKey("shop", "id")
    user_id = models.UUIDField()
    last_seen_at = models.DateTimeField()

    class Meta:
        db_table = "device"


class Invite(models.Model):
    id = models.UUIDField(primary_key=True)
    shop = models.ForeignKey(Shop, on_delete=models.PROTECT, related_name="invites")
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "invite"
