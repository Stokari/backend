import pytest

from common.kernel.errors import (
    ERROR_CODES,
    ConflictError,
    DomainError,
    ForbiddenError,
    IdempotencyError,
    NotFoundError,
    PreconditionFailedError,
    UnauthorizedError,
    ValidationError,
)
from common.kernel.result import Result, err, from_bool, from_optional, ok


class TestResult:
    def test_ok_is_ok(self):
        result: Result[int, Exception] = ok(42)
        assert result.is_ok()
        assert not result.is_err()
        assert result.unwrap() == 42

    def test_ok_unwrap_err_raises(self):
        result: Result[int, Exception] = ok(42)
        with pytest.raises(RuntimeError):
            result.unwrap_err()

    def test_ok_map(self):
        result: Result[int, Exception] = ok(21)
        mapped = result.map(lambda x: ok(x * 2))
        assert mapped.is_ok()
        assert mapped.unwrap() == 42

    def test_ok_and_then(self):
        result: Result[int, Exception] = ok(21)
        chained = result.and_then(lambda x: ok(x * 2))
        assert chained.is_ok()
        assert chained.unwrap() == 42

    def test_ok_map_err_returns_self(self):
        result: Result[int, Exception] = ok(42)
        mapped = result.map_err(lambda e: ValueError("new"))
        assert mapped is result

    def test_err_is_err(self):
        error = ValueError("fail")
        result: Result[int, ValueError] = err(error)
        assert result.is_err()
        assert not result.is_ok()
        assert result.unwrap_err() is error

    def test_err_unwrap_raises(self):
        error = ValueError("fail")
        result: Result[int, ValueError] = err(error)
        with pytest.raises(ValueError, match="fail"):
            result.unwrap()

    def test_err_map_returns_err(self):
        error = ValueError("fail")
        result: Result[int, ValueError] = err(error)
        mapped = result.map(lambda x: ok(x * 2))
        assert mapped.is_err()
        assert mapped.unwrap_err() is error

    def test_err_and_then_returns_err(self):
        error = ValueError("fail")
        result: Result[int, ValueError] = err(error)
        chained = result.and_then(lambda x: ok(x * 2))
        assert chained.is_err()
        assert chained.unwrap_err() is error

    def test_err_map_err(self):
        error = ValueError("fail")
        result: Result[int, ValueError] = err(error)
        mapped = result.map_err(lambda e: RuntimeError("wrapped"))
        assert mapped.is_err()
        assert isinstance(mapped.unwrap_err(), RuntimeError)

    def test_from_optional_some(self):
        result = from_optional(42, ValueError("none"))
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_from_optional_none(self):
        error = ValueError("none")
        result = from_optional(None, error)
        assert result.is_err()
        assert result.unwrap_err() is error

    def test_from_bool_true(self):
        result = from_bool(True, ValueError("false"))
        assert result.is_ok()
        assert result.unwrap() is None

    def test_from_bool_false(self):
        error = ValueError("false")
        result = from_bool(False, error)
        assert result.is_err()
        assert result.unwrap_err() is error


class TestDomainError:
    def test_domain_error_to_dict(self):
        error = DomainError("test", code="TEST_CODE", details={"key": "value"})
        d = error.to_dict()
        assert d == {"code": "TEST_CODE", "message": "test", "details": {"key": "value"}}

    def test_domain_error_to_dict_no_details(self):
        error = DomainError("test", code="TEST_CODE")
        d = error.to_dict()
        assert d == {"code": "TEST_CODE", "message": "test"}

    def test_not_found_error(self):
        error = NotFoundError("Not found", resource_type="Product", resource_id=123)
        assert error.code == "NOT_FOUND"
        assert error.details == {"resource_type": "Product", "resource_id": 123}

    def test_conflict_error(self):
        error = ConflictError(
            "Conflict",
            resource_type="Product",
            resource_id=123,
            conflicting_field="sku",
        )
        assert error.code == "CONFLICT"
        assert error.details == {
            "resource_type": "Product",
            "resource_id": 123,
            "conflicting_field": "sku",
        }

    def test_validation_error(self):
        error = ValidationError(
            "Invalid",
            field_errors={"name": ["required"], "price": ["must be positive"]},
        )
        assert error.code == "VALIDATION_ERROR"
        assert error.details == {
            "field_errors": {"name": ["required"], "price": ["must be positive"]}
        }

    def test_unauthorized_error(self):
        error = UnauthorizedError()
        assert error.code == "UNAUTHORIZED"
        assert error.message == "Authentication required"

    def test_forbidden_error(self):
        error = ForbiddenError("No access")
        assert error.code == "FORBIDDEN"
        assert error.message == "No access"

    def test_precondition_failed_error(self):
        error = PreconditionFailedError("Version mismatch", expected_version=5, current_version=3)
        assert error.code == "PRECONDITION_FAILED"
        assert error.details == {"expected_version": 5, "current_version": 3}

    def test_idempotency_error(self):
        error = IdempotencyError()
        assert error.code == "IDEMPOTENCY_ERROR"


class TestErrorCodes:
    def test_error_codes_exist(self):
        assert "NOT_FOUND" in ERROR_CODES
        assert "CONFLICT" in ERROR_CODES
        assert "VALIDATION_ERROR" in ERROR_CODES
        assert "UNAUTHORIZED" in ERROR_CODES
        assert "FORBIDDEN" in ERROR_CODES
        assert "PRECONDITION_FAILED" in ERROR_CODES
        assert "IDEMPOTENCY_ERROR" in ERROR_CODES
        assert "INTERNAL_ERROR" in ERROR_CODES
        assert "SHOP_CLOSED" in ERROR_CODES
        assert "LEASE_EXPIRED" in ERROR_CODES
        assert "STAFF_LIMIT_EXCEEDED" in ERROR_CODES
        assert "INSUFFICIENT_STOCK" in ERROR_CODES
        assert "NEGATIVE_STOCK_CONFLICT" in ERROR_CODES

    def test_error_codes_have_http_status(self):
        for code in ERROR_CODES.values():
            assert isinstance(code.http_status, int)
            assert 100 <= code.http_status < 600
