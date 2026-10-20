import pytest
from django.http import HttpResponse
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from common.http.middleware import REQUEST_ID_HEADER, RequestIDMiddleware
from common.http.pagination import CursorPagination, OffsetPagination
from common.http.serializers import (
    DecimalSantimField,
    MilliUnitsField,
    SantimField,
    StrictIntegerField,
)


class TestRequestIDMiddleware:
    def test_generates_request_id_if_missing(self):
        factory = APIRequestFactory()
        request = Request(factory.get("/api/test"))

        middleware = RequestIDMiddleware(lambda r: HttpResponse())
        response = middleware(request)

        assert hasattr(request, "request_id")
        assert len(request.request_id) == 32
        assert response[REQUEST_ID_HEADER] == request.request_id

    def test_uses_existing_request_id(self):
        factory = APIRequestFactory()
        request = Request(factory.get("/api/test", HTTP_X_REQUEST_ID="custom-request-id"))

        middleware = RequestIDMiddleware(lambda r: HttpResponse())
        response = middleware(request)

        assert request.request_id == "custom-request-id"
        assert response[REQUEST_ID_HEADER] == "custom-request-id"


class TestStrictIntegerField:
    def test_accepts_integer(self):
        field = StrictIntegerField()
        assert field.to_internal_value(42) == 42

    def test_accepts_string_integer(self):
        field = StrictIntegerField()
        assert field.to_internal_value("42") == 42

    def test_rejects_float(self):
        field = StrictIntegerField()
        with pytest.raises(Exception, match="Float values are not allowed"):
            field.to_internal_value(42.5)

    def test_rejects_float_string(self):
        field = StrictIntegerField()
        with pytest.raises(Exception, match="Float values are not allowed"):
            field.to_internal_value("42.5")

    def test_rejects_invalid_string(self):
        field = StrictIntegerField()
        with pytest.raises(Exception, match="A valid integer is required"):
            field.to_internal_value("abc")


class TestSantimField:
    def test_accepts_valid_santim(self):
        field = SantimField()
        assert field.run_validation(10000) == 10000

    def test_rejects_negative(self):
        field = SantimField()
        with pytest.raises(Exception, match="non-negative"):
            field.run_validation(-1)

    def test_rejects_too_large(self):
        field = SantimField()
        with pytest.raises(Exception, match="exceeds maximum"):
            field.run_validation(999_999_999_99 + 1)


class TestMilliUnitsField:
    def test_accepts_valid_milli(self):
        field = MilliUnitsField()
        assert field.run_validation(1000) == 1000

    def test_rejects_negative(self):
        field = MilliUnitsField()
        with pytest.raises(Exception, match="non-negative"):
            field.run_validation(-1)

    def test_rejects_too_large(self):
        field = MilliUnitsField()
        with pytest.raises(Exception, match="exceeds maximum"):
            field.run_validation(1_000_000_000 + 1)


class TestDecimalSantimField:
    def test_representation_from_int(self):
        field = DecimalSantimField()
        assert field.to_representation(10000) == "100.00"

    def test_representation_from_decimal(self):
        from decimal import Decimal

        field = DecimalSantimField()
        assert field.to_representation(Decimal("100.50")) == "100.50"


class DummyCursorPagination(CursorPagination):
    def apply_cursor(self, queryset, cursor):
        return queryset

    def encode_cursor(self, item):
        return str(item)


class TestCursorPagination:
    def test_paginate_without_cursor(self):
        paginator = DummyCursorPagination()
        paginator.page_size = 2

        factory = APIRequestFactory()
        request = Request(factory.get("/api/items/"))

        items = list(range(10))
        page = paginator.paginate_queryset(items, request)

        assert page == [0, 1]
        assert paginator.has_next is True
        assert paginator.has_previous is False

    def test_paginate_exact_page_size(self):
        paginator = DummyCursorPagination()
        paginator.page_size = 5

        factory = APIRequestFactory()
        request = Request(factory.get("/api/items/"))

        items = list(range(5))
        page = paginator.paginate_queryset(items, request)

        assert page == [0, 1, 2, 3, 4]
        assert paginator.has_next is False


class TestOffsetPagination:
    def test_paginate_with_offset(self):
        paginator = OffsetPagination()
        paginator.page_size = 3

        factory = APIRequestFactory()
        request = Request(factory.get("/api/items/?offset=3"))

        items = list(range(10))
        page = paginator.paginate_queryset(items, request)

        assert page == [3, 4, 5]

    def test_paginate_default_offset(self):
        paginator = OffsetPagination()
        paginator.page_size = 3

        factory = APIRequestFactory()
        request = Request(factory.get("/api/items/"))

        items = list(range(10))
        page = paginator.paginate_queryset(items, request)

        assert page == [0, 1, 2]
