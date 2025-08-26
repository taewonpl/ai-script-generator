"""
FastAPI middleware for handling idempotency keys in project service
"""

import json
from collections.abc import Callable

# Always use fallback implementation for type stability
from datetime import datetime
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

CORE_AVAILABLE = False


class IdempotencyConflictError(Exception):
    """Idempotency key conflict error"""

    pass


class InMemoryIdempotencyManager:
    def __init__(self) -> None:
        self._responses: dict[str, dict[str, Any]] = {}

    def check_idempotency(
        self, key: str, request_data: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        return self._responses.get(key)

    def store_response(
        self,
        key: str,
        status_code: int,
        response_data: dict[str, Any],
        headers: dict[str, str] | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        self._responses[key] = {
            "status_code": status_code,
            "response_data": response_data,
            "headers": headers or {},
            "created_at": datetime.utcnow(),
        }


_fallback_manager = InMemoryIdempotencyManager()


def check_idempotency(
    key: str, request_data: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    return _fallback_manager.check_idempotency(key, request_data)


def store_idempotent_response(
    key: str,
    status_code: int,
    response_data: dict[str, Any],
    headers: dict[str, str] | None = None,
    ttl_seconds: int | None = None,
) -> None:
    _fallback_manager.store_response(
        key, status_code, response_data, headers, ttl_seconds
    )


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for handling idempotency keys in project service"""

    def __init__(
        self,
        app: Any,
        header_name: str = "Idempotency-Key",
        ttl_seconds: int = 24 * 3600,  # 24 hours
        methods: set[str] | None = None,
        enabled_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.header_name = header_name
        self.ttl_seconds = ttl_seconds
        self.methods = methods or {"POST", "PUT", "PATCH"}
        self.enabled_paths = enabled_paths or {"/projects", "/episodes"}

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Any:
        """Handle idempotency for applicable requests"""

        # Only process applicable methods and paths
        if request.method not in self.methods or not any(
            path in request.url.path for path in self.enabled_paths
        ):
            return await call_next(request)

        # Extract idempotency key from headers
        idempotency_key = request.headers.get(self.header_name)

        if not idempotency_key:
            # No idempotency key provided - proceed normally
            return await call_next(request)

        # Validate key format
        if not self._is_valid_key(idempotency_key):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Invalid idempotency key format",
                },
            )

        # Get request body for comparison
        request_body = await self._get_request_body(request)

        try:
            # Check for existing response
            existing_response = check_idempotency(idempotency_key, request_body)

            if existing_response:
                # Return cached response with 200 status instead of 201
                # existing_response is always a dict in our fallback implementation
                response_dict: dict[str, Any] = existing_response
                status_code = (
                    200
                    if response_dict.get("status_code") == 201
                    else response_dict.get("status_code", 200)
                )
                response = JSONResponse(
                    status_code=status_code,
                    content=response_dict.get("response_data", {}),
                )

                # Add idempotency headers
                response.headers["Idempotency-Key"] = idempotency_key
                response.headers["Idempotency-Replayed"] = "true"

                return response

        except IdempotencyConflictError:
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "error": "Idempotency key conflict - request data differs from original",
                },
            )

        except Exception:
            # Continue without idempotency on errors
            pass

        # Store idempotency key in request state
        request.state.idempotency_key = idempotency_key
        request.state.request_body = request_body

        # Process request normally
        response = await call_next(request)

        # Cache successful responses
        if response.status_code in [200, 201, 202] and hasattr(response, "body"):
            try:
                # Get response body
                response_data = await self._get_response_body(response)

                # Store in cache
                store_idempotent_response(
                    key=idempotency_key,
                    status_code=response.status_code,
                    response_data=response_data,
                    headers=dict(response.headers),
                    ttl_seconds=self.ttl_seconds,
                )

            except Exception:
                # Ignore caching errors
                pass

        return response

    def _is_valid_key(self, key: str) -> bool:
        """Validate idempotency key format"""
        return (
            isinstance(key, str)
            and 1 <= len(key) <= 255
            and key.replace("-", "").replace("_", "").isalnum()
        )

    async def _get_request_body(self, request: Request) -> dict[str, Any]:
        """Get request body for idempotency comparison"""
        try:
            body = await request.body()
            if body:
                result: dict[str, Any] = json.loads(body.decode())
                return result
            return {}
        except Exception:
            return {}

    async def _get_response_body(self, response: Response) -> dict[str, Any]:
        """Get response body for caching"""
        try:
            if hasattr(response, "body"):
                body = response.body
                if isinstance(body, bytes):
                    result: dict[str, Any] = json.loads(body.decode())
                    return result
            return {}
        except Exception:
            return {}
