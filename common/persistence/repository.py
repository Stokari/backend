from typing import TypeVar

from django.db import models

from common.core.types import ShopId
from common.persistence.manager import ShopScopedQuerySet

T = TypeVar("T", bound=models.Model)


class ShopScopedModel(models.Model):
    shop_id = models.BigIntegerField(db_index=True)

    class Meta:
        abstract = True


class ShopScopedManager(models.Manager):
    def for_shop(self, shop_id: ShopId) -> ShopScopedQuerySet:
        return ShopScopedQuerySet(self.model, using=self._db).for_shop(shop_id)
