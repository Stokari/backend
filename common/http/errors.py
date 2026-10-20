from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from common.kernel.errors import ERROR_CODES, DomainError


@dataclass(frozen=True, slots=True)
class ProblemDetail:
    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None
    extensions: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
        }
        if self.instance:
            result["instance"] = self.instance
        if self.extensions:
            result.update(self.extensions)
        return result


class ProblemDetailException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Internal server error"
    default_code = "INTERNAL_ERROR"

    def __init__(
        self,
        detail: str | None = None,
        *,
        code: str | None = None,
        type_uri: str | None = None,
        title: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail or self.default_detail
        self.code = code or self.default_code
        self.type_uri = type_uri or f"https://stokari.io/errors/{self.code.lower()}"
        self.title = title or self.detail
        self.extensions = extensions
        super().__init__(detail, code)

    def to_problem_detail(self, request: Request | None = None) -> ProblemDetail:
        instance = request.path if request else None
        return ProblemDetail(
            type=self.type_uri,
            title=self.title,
            status=self.status_code,
            detail=self.detail,
            instance=instance,
            extensions=self.extensions,
        )


def domain_error_to_problem_detail(
    error: DomainError, request: Request | None = None
) -> ProblemDetail:
    error_code = ERROR_CODES.get(error.code, ERROR_CODES["INTERNAL_ERROR"])
    return ProblemDetail(
        type=f"https://stokari.io/errors/{error.code.lower()}",
        title=error.message,
        status=error_code.http_status,
        detail=error.message,
        instance=request.path if request else None,
        extensions={"code": error.code, **(error.details or {})},
    )


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    request = context.get("request")

    if isinstance(exc, DomainError):
        problem = domain_error_to_problem_detail(exc, request)
        return Response(problem.to_dict(), status=problem.status)

    if isinstance(exc, ProblemDetailException):
        problem = exc.to_problem_detail(request)
        return Response(problem.to_dict(), status=problem.status)

    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    problem = ProblemDetail(
        type="https://stokari.io/errors/internal_error",
        title="Internal server error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred",
        instance=request.path if request else None,
        extensions={"code": "INTERNAL_ERROR"},
    )
    return Response(problem.to_dict(), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
