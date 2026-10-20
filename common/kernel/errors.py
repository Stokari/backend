from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class DomainError(Exception):
    code: str
    message: str
    details: dict[str, Any] | None

    def __init__(
        self,
        message: str,
        *,
        code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = self.details
        return result


class NotFoundError(DomainError):
    def __init__(
        self,
        message: str,
        *,
        resource_type: str | None = None,
        resource_id: str | int | None = None,
    ) -> None:
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id is not None:
            details["resource_id"] = resource_id
        super().__init__(message, code="NOT_FOUND", details=details or None)


class ConflictError(DomainError):
    def __init__(
        self,
        message: str,
        *,
        resource_type: str | None = None,
        resource_id: str | int | None = None,
        conflicting_field: str | None = None,
    ) -> None:
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id is not None:
            details["resource_id"] = resource_id
        if conflicting_field:
            details["conflicting_field"] = conflicting_field
        super().__init__(message, code="CONFLICT", details=details or None)


class ValidationError(DomainError):
    def __init__(
        self,
        message: str,
        *,
        field_errors: dict[str, list[str]] | None = None,
    ) -> None:
        details = {}
        if field_errors:
            details["field_errors"] = field_errors
        super().__init__(message, code="VALIDATION_ERROR", details=details or None)


class UnauthorizedError(DomainError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, code="UNAUTHORIZED")


class ForbiddenError(DomainError):
    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message, code="FORBIDDEN")


class PreconditionFailedError(DomainError):
    def __init__(
        self,
        message: str,
        *,
        expected_version: int | None = None,
        current_version: int | None = None,
    ) -> None:
        details = {}
        if expected_version is not None:
            details["expected_version"] = expected_version
        if current_version is not None:
            details["current_version"] = current_version
        super().__init__(message, code="PRECONDITION_FAILED", details=details or None)


class IdempotencyError(DomainError):
    def __init__(self, message: str = "Idempotency key already used") -> None:
        super().__init__(message, code="IDEMPOTENCY_ERROR")


@dataclass(frozen=True, slots=True)
class ErrorCode:
    value: str
    http_status: int
    description: str


ERROR_CODES: dict[str, ErrorCode] = {
    "NOT_FOUND": ErrorCode("NOT_FOUND", 404, "Resource not found"),
    "CONFLICT": ErrorCode("CONFLICT", 409, "Resource conflict"),
    "VALIDATION_ERROR": ErrorCode("VALIDATION_ERROR", 400, "Validation failed"),
    "UNAUTHORIZED": ErrorCode("UNAUTHORIZED", 401, "Authentication required"),
    "FORBIDDEN": ErrorCode("FORBIDDEN", 403, "Permission denied"),
    "PRECONDITION_FAILED": ErrorCode("PRECONDITION_FAILED", 412, "Precondition failed"),
    "IDEMPOTENCY_ERROR": ErrorCode("IDEMPOTENCY_ERROR", 409, "Idempotency key conflict"),
    "INTERNAL_ERROR": ErrorCode("INTERNAL_ERROR", 500, "Internal server error"),
    "SHOP_CLOSED": ErrorCode("SHOP_CLOSED", 403, "Shop is closed"),
    "LEASE_EXPIRED": ErrorCode("LEASE_EXPIRED", 403, "Offline lease expired"),
    "STAFF_LIMIT_EXCEEDED": ErrorCode("STAFF_LIMIT_EXCEEDED", 400, "Maximum staff limit reached"),
    "INSUFFICIENT_STOCK": ErrorCode("INSUFFICIENT_STOCK", 409, "Insufficient stock for operation"),
    "NEGATIVE_STOCK_CONFLICT": ErrorCode("NEGATIVE_STOCK_CONFLICT", 409, "Stock would go negative"),
}
