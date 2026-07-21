"""Tests for the custom exception hierarchy."""


from backend.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ServiceError,
    ValidationError,
)


class TestAppErrorDefaults:
    def test_default_status_code(self):
        err = AppError()
        assert err.status_code == 500

    def test_default_detail(self):
        err = AppError()
        assert err.detail == "An unexpected error occurred"

    def test_default_code(self):
        err = AppError()
        assert err.code == "INTERNAL_ERROR"

    def test_default_headers(self):
        err = AppError()
        assert err.headers is None

    def test_custom_values(self):
        err = AppError(status_code=418, detail="teapot", code="TEAPOT", headers={"X-Custom": "yes"})
        assert err.status_code == 418
        assert err.detail == "teapot"
        assert err.code == "TEAPOT"
        assert err.headers == {"X-Custom": "yes"}

    def test_is_exception(self):
        err = AppError()
        assert isinstance(err, Exception)


class TestAppErrorToDict:
    def test_to_dict_format(self):
        err = AppError(status_code=500, detail="something broke", code="BROKEN")
        d = err.to_dict()
        assert d == {
            "error": {
                "code": "BROKEN",
                "detail": "something broke",
                "status_code": 500,
            }
        }

    def test_to_dict_nested_structure(self):
        err = AppError()
        d = err.to_dict()
        assert "error" in d
        assert isinstance(d["error"], dict)
        assert set(d["error"].keys()) == {"code", "detail", "status_code"}


class TestNotFoundError:
    def test_404_status(self):
        err = NotFoundError()
        assert err.status_code == 404

    def test_default_message(self):
        err = NotFoundError()
        assert err.detail == "Resource not found"

    def test_default_code(self):
        err = NotFoundError()
        assert err.code == "NOT_FOUND"

    def test_custom_message(self):
        err = NotFoundError(detail="Widget #42 not found")
        assert err.detail == "Widget #42 not found"

    def test_to_dict(self):
        err = NotFoundError()
        d = err.to_dict()
        assert d["error"]["status_code"] == 404


class TestValidationError:
    def test_422_status(self):
        err = ValidationError()
        assert err.status_code == 422

    def test_default_message(self):
        err = ValidationError()
        assert err.detail == "Validation failed"

    def test_default_code(self):
        err = ValidationError()
        assert err.code == "VALIDATION_ERROR"

    def test_custom_message(self):
        err = ValidationError(detail="Field 'email' is required")
        assert err.detail == "Field 'email' is required"


class TestAuthenticationError:
    def test_401_status(self):
        err = AuthenticationError()
        assert err.status_code == 401

    def test_default_message(self):
        err = AuthenticationError()
        assert err.detail == "Authentication required"

    def test_default_code(self):
        err = AuthenticationError()
        assert err.code == "AUTHENTICATION_ERROR"

    def test_custom_message(self):
        err = AuthenticationError(detail="Token has expired")
        assert err.detail == "Token has expired"


class TestAuthorizationError:
    def test_403_status(self):
        err = AuthorizationError()
        assert err.status_code == 403

    def test_default_message(self):
        err = AuthorizationError()
        assert err.detail == "Insufficient permissions"

    def test_default_code(self):
        err = AuthorizationError()
        assert err.code == "AUTHORIZATION_ERROR"

    def test_custom_message(self):
        err = AuthorizationError(detail="Requires admin role")
        assert err.detail == "Requires admin role"


class TestConflictError:
    def test_409_status(self):
        err = ConflictError()
        assert err.status_code == 409

    def test_default_message(self):
        err = ConflictError()
        assert err.detail == "Resource conflict"

    def test_default_code(self):
        err = ConflictError()
        assert err.code == "CONFLICT"

    def test_custom_message(self):
        err = ConflictError(detail="Email already registered")
        assert err.detail == "Email already registered"


class TestRateLimitError:
    def test_429_status(self):
        err = RateLimitError()
        assert err.status_code == 429

    def test_default_message(self):
        err = RateLimitError()
        assert err.detail == "Rate limit exceeded"

    def test_default_code(self):
        err = RateLimitError()
        assert err.code == "RATE_LIMIT_EXCEEDED"

    def test_retry_after_header(self):
        err = RateLimitError(retry_after=120)
        assert err.headers == {"Retry-After": "120"}

    def test_retry_after_stored(self):
        err = RateLimitError(retry_after=30)
        assert err.retry_after == 30

    def test_to_dict(self):
        err = RateLimitError(retry_after=45)
        d = err.to_dict()
        assert d["error"]["status_code"] == 429
        assert d["error"]["code"] == "RATE_LIMIT_EXCEEDED"


class TestServiceError:
    def test_503_status(self):
        err = ServiceError()
        assert err.status_code == 503

    def test_default_message(self):
        err = ServiceError()
        assert err.detail == "Service unavailable"

    def test_default_code(self):
        err = ServiceError()
        assert err.code == "SERVICE_ERROR"

    def test_custom_message(self):
        err = ServiceError(detail="LLM provider is down")
        assert err.detail == "LLM provider is down"


class TestExceptionInheritance:
    def test_all_inherit_app_error(self):
        for cls in [
            NotFoundError,
            ValidationError,
            AuthenticationError,
            AuthorizationError,
            ConflictError,
            RateLimitError,
            ServiceError,
        ]:
            assert issubclass(cls, AppError)

    def test_all_inherit_exception(self):
        for cls in [
            AppError,
            NotFoundError,
            ValidationError,
            AuthenticationError,
            AuthorizationError,
            ConflictError,
            RateLimitError,
            ServiceError,
        ]:
            assert issubclass(cls, Exception)
