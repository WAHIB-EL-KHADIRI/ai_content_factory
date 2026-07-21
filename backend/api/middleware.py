"""Middleware for error handling, request logging, and rate limiting."""

import logging
import time
from collections import defaultdict
from typing import Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.core.exceptions import AppError

logger = logging.getLogger("ai_content_os.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs method, path, status code, and duration for every request."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "%s %s -> 500 (%.1fms)",
                method,
                path,
                duration_ms,
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        status = response.status_code

        if status >= 500:
            logger.error("%s %s -> %d (%.1fms)", method, path, status, duration_ms)
        elif status >= 400:
            logger.warning("%s %s -> %d (%.1fms)", method, path, status, duration_ms)
        else:
            logger.info("%s %s -> %d (%.1fms)", method, path, status, duration_ms)

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catches unhandled exceptions and AppError instances, returns JSON response."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except AppError as exc:
            logger.warning(
                "AppError on %s %s: [%s] %s",
                request.method,
                request.url.path,
                exc.code,
                exc.detail,
            )
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.to_dict(),
                headers=exc.headers,
            )
        except Exception as exc:
            logger.exception(
                "Unhandled exception on %s %s: %s",
                request.method,
                request.url.path,
                exc,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "detail": "An unexpected error occurred",
                        "status_code": 500,
                    }
                },
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding window rate limiter, configurable per-IP."""

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        if request.client:
            return request.client.host
        return "unknown"

    def _cleanup(self, client_ip: str, now: float) -> None:
        cutoff = now - self.window_seconds
        timestamps = self._requests[client_ip]
        self._requests[client_ip] = [t for t in timestamps if t > cutoff]
        if not self._requests[client_ip]:
            del self._requests[client_ip]

    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)
        now = time.time()

        self._cleanup(client_ip, now)
        timestamps = self._requests[client_ip]

        if len(timestamps) >= self.max_requests:
            oldest = timestamps[0]
            retry_after = int(self.window_seconds - (now - oldest)) + 1
            retry_after = max(retry_after, 1)
            logger.warning(
                "Rate limit exceeded for %s: %d requests in %ds",
                client_ip,
                len(timestamps),
                self.window_seconds,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "detail": f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds}s",
                        "status_code": 429,
                        "retry_after": retry_after,
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)
        return await call_next(request)
