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


class UnauthenticatedError(DomainError):
    def __init__(self, message: str = "Access token missing or expired") -> None:
        super().__init__(message, code="UNAUTHENTICATED")


class GoogleTokenInvalidError(DomainError):
    def __init__(self, message: str = "Google token invalid, expired, or unverified") -> None:
        super().__init__(message, code="GOOGLE_TOKEN_INVALID")


class NonceInvalidError(DomainError):
    def __init__(self, message: str = "Nonce unknown, used or expired") -> None:
        super().__init__(message, code="NONCE_INVALID")


class RefreshTokenInvalidError(DomainError):
    def __init__(self, message: str = "Refresh token unknown, expired or wrong device") -> None:
        super().__init__(message, code="REFRESH_TOKEN_INVALID")


class RefreshTokenReusedError(DomainError):
    def __init__(self, message: str = "Refresh token was already used; family revoked") -> None:
        super().__init__(message, code="REFRESH_TOKEN_REUSED")


class AccountDeactivatedError(DomainError):
    def __init__(
        self,
        message: str = "Membership is deactivated.",
        *,
        drain_token: str | None = None,
        drain_token_expires_at: str | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if drain_token is not None:
            details["drainToken"] = drain_token
        if drain_token_expires_at is not None:
            details["drainTokenExpiresAt"] = drain_token_expires_at
        super().__init__(message, code="ACCOUNT_DEACTIVATED", details=details or None)


class MembershipSelectionRequiredError(DomainError):
    def __init__(
        self,
        message: str = "Multiple active memberships found; selection required",
        *,
        memberships: list[dict[str, Any]] | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if memberships is not None:
            details["memberships"] = memberships
        super().__init__(message, code="MEMBERSHIP_SELECTION_REQUIRED", details=details or None)


class ShopRequiredError(DomainError):
    def __init__(self, message: str = "Shop session required for this operation") -> None:
        super().__init__(message, code="SHOP_REQUIRED")


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
    "UNAUTHENTICATED": ErrorCode("UNAUTHENTICATED", 401, "Access token missing or expired"),
    "FORBIDDEN": ErrorCode("FORBIDDEN", 403, "Permission denied"),
    "PRECONDITION_FAILED": ErrorCode("PRECONDITION_FAILED", 412, "Precondition failed"),
    "IDEMPOTENCY_ERROR": ErrorCode("IDEMPOTENCY_ERROR", 409, "Idempotency key conflict"),
    "INTERNAL_ERROR": ErrorCode("INTERNAL_ERROR", 500, "Internal server error"),
    "SHOP_CLOSED": ErrorCode("SHOP_CLOSED", 403, "Shop is closed"),
    "LEASE_EXPIRED": ErrorCode("LEASE_EXPIRED", 403, "Offline lease expired"),
    "STAFF_LIMIT_EXCEEDED": ErrorCode("STAFF_LIMIT_EXCEEDED", 400, "Maximum staff limit reached"),
    "INSUFFICIENT_STOCK": ErrorCode("INSUFFICIENT_STOCK", 409, "Insufficient stock for operation"),
    "NEGATIVE_STOCK_CONFLICT": ErrorCode("NEGATIVE_STOCK_CONFLICT", 409, "Stock would go negative"),
    "GOOGLE_TOKEN_INVALID": ErrorCode("GOOGLE_TOKEN_INVALID", 401, "Google token invalid"),
    "NONCE_INVALID": ErrorCode("NONCE_INVALID", 401, "Nonce unknown, used or expired"),
    "REFRESH_TOKEN_INVALID": ErrorCode(
        "REFRESH_TOKEN_INVALID", 401, "Refresh token unknown or expired"
    ),
    "REFRESH_TOKEN_REUSED": ErrorCode("REFRESH_TOKEN_REUSED", 401, "Refresh token already used"),
    "ACCOUNT_DEACTIVATED": ErrorCode("ACCOUNT_DEACTIVATED", 403, "Membership deactivated"),
    "MEMBERSHIP_SELECTION_REQUIRED": ErrorCode(
        "MEMBERSHIP_SELECTION_REQUIRED", 409, "Multiple memberships require selection"
    ),
    "SHOP_REQUIRED": ErrorCode("SHOP_REQUIRED", 403, "Shop session required"),
}
