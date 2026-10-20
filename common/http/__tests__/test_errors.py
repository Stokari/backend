from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from common.http.errors import (
    ProblemDetail,
    ProblemDetailException,
    domain_error_to_problem_detail,
    exception_handler,
)
from common.kernel.errors import (
    NotFoundError,
    ValidationError,
)


class TestProblemDetail:
    def test_to_dict_minimal(self):
        pd = ProblemDetail(
            type="https://example.com/error",
            title="Error",
            status=400,
            detail="Something went wrong",
        )
        d = pd.to_dict()
        assert d == {
            "type": "https://example.com/error",
            "title": "Error",
            "status": 400,
            "detail": "Something went wrong",
        }

    def test_to_dict_with_instance_and_extensions(self):
        pd = ProblemDetail(
            type="https://example.com/error",
            title="Error",
            status=400,
            detail="Something went wrong",
            instance="/api/products/123",
            extensions={"code": "NOT_FOUND", "resource_id": 123},
        )
        d = pd.to_dict()
        assert d == {
            "type": "https://example.com/error",
            "title": "Error",
            "status": 400,
            "detail": "Something went wrong",
            "instance": "/api/products/123",
            "code": "NOT_FOUND",
            "resource_id": 123,
        }


class TestProblemDetailException:
    def test_default_values(self):
        exc = ProblemDetailException()
        assert exc.status_code == 500
        assert exc.default_code == "INTERNAL_ERROR"
        assert exc.code == "INTERNAL_ERROR"

    def test_custom_values(self):
        exc = ProblemDetailException(
            detail="Custom error",
            code="CUSTOM_ERROR",
            type_uri="https://example.com/custom",
            title="Custom Title",
            extensions={"key": "value"},
        )
        assert exc.detail == "Custom error"
        assert exc.code == "CUSTOM_ERROR"
        assert exc.type_uri == "https://example.com/custom"
        assert exc.title == "Custom Title"
        assert exc.extensions == {"key": "value"}

    def test_to_problem_detail(self):
        factory = APIRequestFactory()
        request = Request(factory.get("/api/test"))

        exc = ProblemDetailException(detail="Test error", code="TEST_ERROR")
        problem = exc.to_problem_detail(request)

        assert problem.type == "https://stokari.io/errors/test_error"
        assert problem.title == "Test error"
        assert problem.status == 500
        assert problem.detail == "Test error"
        assert problem.instance == "/api/test"


class TestDomainErrorToProblemDetail:
    def test_not_found_error(self):
        factory = APIRequestFactory()
        request = Request(factory.get("/api/products/123"))

        error = NotFoundError("Product not found", resource_type="Product", resource_id=123)
        problem = domain_error_to_problem_detail(error, request)

        assert problem.type == "https://stokari.io/errors/not_found"
        assert problem.title == "Product not found"
        assert problem.status == 404
        assert problem.detail == "Product not found"
        assert problem.instance == "/api/products/123"
        assert problem.extensions == {
            "code": "NOT_FOUND",
            "resource_type": "Product",
            "resource_id": 123,
        }

    def test_validation_error(self):
        factory = APIRequestFactory()
        request = Request(factory.post("/api/products/"))

        error = ValidationError("Invalid data", field_errors={"name": ["required"]})
        problem = domain_error_to_problem_detail(error, request)

        assert problem.status == 400
        assert problem.extensions == {
            "code": "VALIDATION_ERROR",
            "field_errors": {"name": ["required"]},
        }


class TestExceptionHandler:
    def test_handles_domain_error(self):
        factory = APIRequestFactory()
        request = Request(factory.get("/api/products/123"))
        context = {"request": request}

        error = NotFoundError("Not found", resource_type="Product", resource_id=123)
        response = exception_handler(error, context)

        assert response is not None
        assert response.status_code == 404
        assert response.data["code"] == "NOT_FOUND"
        assert response.data["title"] == "Not found"
        assert response.data["detail"] == "Not found"

    def test_handles_validation_error(self):
        factory = APIRequestFactory()
        request = Request(factory.post("/api/products/"))
        context = {"request": request}

        error = ValidationError("Invalid", field_errors={"name": ["required"]})
        response = exception_handler(error, context)

        assert response is not None
        assert response.status_code == 400
        assert response.data["code"] == "VALIDATION_ERROR"
        assert response.data["field_errors"] == {"name": ["required"]}

    def test_handles_unknown_exception(self):
        factory = APIRequestFactory()
        request = Request(factory.get("/api/test"))
        context = {"request": request}

        error = RuntimeError("Unexpected")
        response = exception_handler(error, context)

        assert response is not None
        assert response.status_code == 500
        assert response.data["code"] == "INTERNAL_ERROR"
        assert response.data["title"] == "Internal server error"
