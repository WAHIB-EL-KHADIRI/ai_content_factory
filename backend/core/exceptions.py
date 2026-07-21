"""Custom exception hierarchy for AI Content OS"""

from typing import Any, Dict, Optional


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        status_code: int = 500,
        detail: str = "An unexpected error occurred",
        code: str = "INTERNAL_ERROR",
        headers: Optional[Dict[str, str]] = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.headers = headers
        super().__init__(detail)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "detail": self.detail,
                "status_code": self.status_code,
            }
        }


class NotFoundError(AppError):
    def __init__(self, detail: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(status_code=404, detail=detail, code=code)


class ValidationError(AppError):
    def __init__(self, detail: str = "Validation failed", code: str = "VALIDATION_ERROR"):
        super().__init__(status_code=422, detail=detail, code=code)


class AuthenticationError(AppError):
    def __init__(self, detail: str = "Authentication required", code: str = "AUTHENTICATION_ERROR"):
        super().__init__(status_code=401, detail=detail, code=code)


class AuthorizationError(AppError):
    def __init__(self, detail: str = "Insufficient permissions", code: str = "AUTHORIZATION_ERROR"):
        super().__init__(status_code=403, detail=detail, code=code)


class ConflictError(AppError):
    def __init__(self, detail: str = "Resource conflict", code: str = "CONFLICT"):
        super().__init__(status_code=409, detail=detail, code=code)


class RateLimitError(AppError):
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        code: str = "RATE_LIMIT_EXCEEDED",
        retry_after: int = 60,
    ):
        headers = {"Retry-After": str(retry_after)}
        super().__init__(status_code=429, detail=detail, code=code, headers=headers)
        self.retry_after = retry_after


class ServiceError(AppError):
    def __init__(self, detail: str = "Service unavailable", code: str = "SERVICE_ERROR"):
        super().__init__(status_code=503, detail=detail, code=code)
