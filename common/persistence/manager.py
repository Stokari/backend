from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Generic, TypeVar

from django.db import transaction
from django.db.models import Model, QuerySet

from common.kernel.types import ShopId

T = TypeVar("T", bound=Model)


class TransactionManager:
    @staticmethod
    @contextmanager
    def atomic(shop_id: ShopId):
        with transaction.atomic():
            yield

    @staticmethod
    @contextmanager
    def atomic_with_lock(shop_id: ShopId, *models: type[Model], order_by: str = "id"):
        with transaction.atomic():
            for model in models:
                model.objects.select_for_update(of=("self",)).order_by(order_by).exists()
            yield

    @staticmethod
    def run_in_transaction(
        shop_id: ShopId,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        with TransactionManager.atomic(shop_id):
            return func(*args, **kwargs)

    @staticmethod
    def run_in_transaction_with_lock(
        shop_id: ShopId,
        func: Callable[..., T],
        *models: type[Model],
        order_by: str = "id",
        **kwargs: Any,
    ) -> T:
        with TransactionManager.atomic_with_lock(shop_id, *models, order_by=order_by):
            return func(**kwargs)


class ShopScopedQuerySet(QuerySet, Generic[T]):
    def for_shop(self, shop_id: ShopId) -> "ShopScopedQuerySet[T]":
        return self.filter(shop_id=shop_id)


class ShopScopedRepository(Generic[T]):
    def __init__(self, shop_id: ShopId, model: type[T]):
        self.shop_id = shop_id
        self.model = model

    def get_queryset(self) -> ShopScopedQuerySet[T]:
        return ShopScopedQuerySet(self.model, using=self.model._db).for_shop(self.shop_id)

    def get(self, **kwargs: Any) -> T:
        return self.get_queryset().get(**kwargs)

    def filter(self, **kwargs: Any) -> ShopScopedQuerySet[T]:
        return self.get_queryset().filter(**kwargs)

    def first(self, **kwargs: Any) -> T | None:
        return self.get_queryset().filter(**kwargs).first()

    def exists(self, **kwargs: Any) -> bool:
        return self.get_queryset().filter(**kwargs).exists()

    def count(self, **kwargs: Any) -> int:
        return self.get_queryset().filter(**kwargs).count()

    def create(self, **kwargs: Any) -> T:
        kwargs.setdefault("shop_id", self.shop_id)
        return self.model.objects.create(**kwargs)

    def update_or_create(
        self, defaults: dict[str, Any] | None = None, **kwargs: Any
    ) -> tuple[T, bool]:
        kwargs.setdefault("shop_id", self.shop_id)
        return self.model.objects.update_or_create(defaults=defaults, **kwargs)

    def bulk_create(self, objs: list[T], **kwargs: Any) -> list[T]:
        for obj in objs:
            if not hasattr(obj, "shop_id") or obj.shop_id is None:
                obj.shop_id = self.shop_id
        return self.model.objects.bulk_create(objs, **kwargs)

    def bulk_update(self, objs: list[T], fields: list[str], **kwargs: Any) -> int:
        return self.model.objects.bulk_update(objs, fields, **kwargs)
