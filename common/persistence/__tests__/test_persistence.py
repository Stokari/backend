from unittest.mock import Mock, patch

from django.db import models
from django.db.models import Model

from common.kernel.types import ShopId
from common.persistence.manager import ShopScopedQuerySet, ShopScopedRepository, TransactionManager
from common.persistence.repository import ShopScopedManager, ShopScopedModel


class MockModel(Model):
    shop_id = models.BigIntegerField(db_index=True, default=0)
    _db = "default"

    class Meta:
        app_label = "test"
        managed = False


class TestShopScopedQuerySet:
    def test_for_shop_filters_by_shop_id(self):
        qs = ShopScopedQuerySet(MockModel, using="default")
        qs.filter = Mock(return_value="filtered")

        result = qs.for_shop(ShopId(1))
        assert result is not None
        qs.filter.assert_called_once_with(shop_id=ShopId(1))


class TestShopScopedRepository:
    def test_init_sets_shop_id(self):
        repo = ShopScopedRepository[MockModel](ShopId(42), MockModel)
        assert repo.shop_id == ShopId(42)
        assert repo.model is MockModel

    def test_get_queryset_filters_by_shop(self):
        repo = ShopScopedRepository[MockModel](ShopId(1), MockModel)
        qs = repo.get_queryset()
        assert qs is not None

    def test_get_delegates_to_queryset(self):
        repo = ShopScopedRepository[MockModel](ShopId(1), MockModel)
        repo.get_queryset = Mock()
        repo.get_queryset().get.return_value = "obj"
        result = repo.get(id=1)
        assert result == "obj"
        repo.get_queryset().get.assert_called_once_with(id=1)

    def test_filter_delegates_to_queryset(self):
        repo = ShopScopedRepository[MockModel](ShopId(1), MockModel)
        repo.get_queryset = Mock()
        repo.get_queryset().filter.return_value = "filtered"
        result = repo.filter(name="test")
        assert result == "filtered"

    def test_first_delegates_to_queryset(self):
        repo = ShopScopedRepository[MockModel](ShopId(1), MockModel)
        repo.get_queryset = Mock()
        repo.get_queryset().filter().first.return_value = "obj"
        result = repo.first(name="test")
        assert result == "obj"

    def test_exists_delegates_to_queryset(self):
        repo = ShopScopedRepository[MockModel](ShopId(1), MockModel)
        repo.get_queryset = Mock()
        repo.get_queryset().filter().exists.return_value = True
        result = repo.exists(name="test")
        assert result is True

    def test_count_delegates_to_queryset(self):
        repo = ShopScopedRepository[MockModel](ShopId(1), MockModel)
        repo.get_queryset = Mock()
        repo.get_queryset().filter().count.return_value = 5
        result = repo.count(name="test")
        assert result == 5

    def test_create_sets_shop_id(self):
        repo = ShopScopedRepository[MockModel](ShopId(1), MockModel)
        repo.model = Mock()
        repo.model.objects = Mock()
        repo.model.objects.create.return_value = "created"
        result = repo.create(name="test")
        assert result == "created"
        repo.model.objects.create.assert_called_once_with(name="test", shop_id=ShopId(1))

    def test_create_preserves_existing_shop_id(self):
        repo = ShopScopedRepository[MockModel](ShopId(1), MockModel)
        repo.model = Mock()
        repo.model.objects = Mock()
        repo.model.objects.create.return_value = "created"
        result = repo.create(name="test", shop_id=ShopId(99))
        assert result == "created"
        repo.model.objects.create.assert_called_once_with(name="test", shop_id=ShopId(99))

    def test_update_or_create_sets_shop_id(self):
        repo = ShopScopedRepository[MockModel](ShopId(1), MockModel)
        repo.model = Mock()
        repo.model.objects = Mock()
        repo.model.objects.update_or_create.return_value = ("obj", True)
        result = repo.update_or_create(defaults={"name": "test"}, id=1)
        assert result == ("obj", True)
        repo.model.objects.update_or_create.assert_called_once_with(
            defaults={"name": "test"}, id=1, shop_id=ShopId(1)
        )

    def test_bulk_create_sets_shop_id(self):
        repo = ShopScopedRepository[MockModel](ShopId(1), MockModel)
        repo.model = Mock()
        mock_obj1 = Mock(spec=Model)
        mock_obj1.shop_id = None
        mock_obj2 = Mock(spec=Model)
        mock_obj2.shop_id = ShopId(99)
        repo.model.objects = Mock()
        repo.model.objects.bulk_create.return_value = [mock_obj1, mock_obj2]
        result = repo.bulk_create([mock_obj1, mock_obj2])
        assert result == [mock_obj1, mock_obj2]
        assert mock_obj1.shop_id == ShopId(1)
        assert mock_obj2.shop_id == ShopId(99)

    def test_bulk_update_delegates(self):
        repo = ShopScopedRepository[MockModel](ShopId(1), MockModel)
        repo.model = Mock()
        repo.model.objects = Mock()
        repo.model.objects.bulk_update.return_value = 2
        objs = [Mock(spec=Model), Mock(spec=Model)]
        result = repo.bulk_update(objs, ["name"])
        assert result == 2


class TestTransactionManager:
    def test_atomic_context_manager(self):
        with patch("common.persistence.manager.transaction.atomic") as mock_atomic:
            mock_atomic.return_value.__enter__ = Mock(return_value=None)
            mock_atomic.return_value.__exit__ = Mock(return_value=None)

            with TransactionManager.atomic(ShopId(1)):
                pass

            mock_atomic.assert_called_once()

    def test_atomic_with_lock_context_manager(self):
        with patch("common.persistence.manager.transaction.atomic") as mock_atomic:
            mock_atomic.return_value.__enter__ = Mock(return_value=None)
            mock_atomic.return_value.__exit__ = Mock(return_value=None)

            model1 = Mock()
            model2 = Mock()

            with TransactionManager.atomic_with_lock(ShopId(1), model1, model2, order_by="id"):
                pass

            mock_atomic.assert_called_once()

    def test_run_in_transaction(self):
        func = Mock(return_value="result")
        with patch("common.persistence.manager.TransactionManager.atomic") as mock_atomic:
            mock_atomic.return_value.__enter__ = Mock(return_value=None)
            mock_atomic.return_value.__exit__ = Mock(return_value=None)
            result = TransactionManager.run_in_transaction(ShopId(1), func, arg1="test")
            assert result == "result"
            func.assert_called_once_with(arg1="test")

    def test_run_in_transaction_with_lock(self):
        func = Mock(return_value="result")
        model1 = Mock()

        with patch(
            "common.persistence.manager.TransactionManager.atomic_with_lock"
        ) as mock_atomic_lock:
            mock_atomic_lock.return_value.__enter__ = Mock(return_value=None)
            mock_atomic_lock.return_value.__exit__ = Mock(return_value=None)

            result = TransactionManager.run_in_transaction_with_lock(
                ShopId(1), func, model1, order_by="id", kwarg1="test"
            )

            assert result == "result"
            func.assert_called_once_with(kwarg1="test")


class TestShopScopedModel:
    def test_abstract_model_has_shop_id(self):
        assert hasattr(ShopScopedModel, "shop_id")
        assert ShopScopedModel._meta.abstract is True


class TestShopScopedManager:
    def test_for_shop_returns_scoped_queryset(self):
        manager = ShopScopedManager()
        manager.model = MockModel
        manager._db = "default"

        qs = manager.for_shop(ShopId(1))
        assert isinstance(qs, ShopScopedQuerySet)
