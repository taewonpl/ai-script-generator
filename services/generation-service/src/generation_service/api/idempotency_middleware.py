"""
FastAPI middleware for handling idempotency keys
"""

import json
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..cache.idempotency_cache import (
    IdempotencyConflictError,
    get_redis_idempotency_manager,
)

try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("generation-service.idempotency")
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for handling idempotency keys"""

    def __init__(
        self,
        app,
        header_name: str = "Idempotency-Key",
        ttl_seconds: int = 24 * 3600,  # 24 hours
        methods: set = None,
        enabled_paths: set = None,
    ):
        super().__init__(app)
        self.header_name = header_name
        self.ttl_seconds = ttl_seconds
        self.methods = methods or {"POST", "PUT", "PATCH"}
        self.enabled_paths = enabled_paths or {
            "/api/v1/generations",
            "/generate",
            "/hybrid-script",
            "/custom-workflow",
        }
        self.manager = get_redis_idempotency_manager()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle idempotency for applicable requests"""

        # Only process applicable methods and paths
        if request.method not in self.methods or not any(
            request.url.path.startswith(path) for path in self.enabled_paths
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
                    "error": {
                        "code": "INVALID_IDEMPOTENCY_KEY",
                        "message": "Idempotency key must be a valid string (1-255 characters)",
                    },
                },
            )

        # Get request body for comparison
        request_body = await self._get_request_body(request)

        try:
            # Check for existing response
            existing_response = self.manager.check_idempotency(
                idempotency_key, request_body
            )

            if existing_response:
                logger.info(f"Returning cached response for key: {idempotency_key}")

                # Return cached response with 200 status instead of 201
                status_code = (
                    200
                    if existing_response.status_code == 201
                    else existing_response.status_code
                )

                response = JSONResponse(
                    status_code=status_code, content=existing_response.response_data
                )

                # Add headers from cached response
                for key, value in existing_response.headers.items():
                    response.headers[key] = value

                # Add idempotency headers
                response.headers["Idempotency-Key"] = idempotency_key
                response.headers["Idempotency-Replayed"] = "true"

                return response

        except IdempotencyConflictError as e:
            logger.warning(f"Idempotency conflict for key {idempotency_key}: {e}")
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "error": {
                        "code": "IDEMPOTENCY_CONFLICT",
                        "message": str(e),
                    },
                },
            )

        except Exception as e:
            logger.error(f"Error checking idempotency: {e}")
            # Continue without idempotency on errors

        # Store idempotency key in request state for endpoint to use
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
                self.manager.store_response(
                    key=idempotency_key,
                    status_code=response.status_code,
                    response_data=response_data,
                    headers=dict(response.headers),
                    ttl_seconds=self.ttl_seconds,
                )

                logger.info(f"Cached response for idempotency key: {idempotency_key}")

            except Exception as e:
                logger.error(f"Error caching idempotent response: {e}")

        return response

    def _is_valid_key(self, key: str) -> bool:
        """Validate idempotency key format"""
        return (
            isinstance(key, str)
            and 1 <= len(key) <= 255
            and key.replace("-", "").replace("_", "").isalnum()
        )

    async def _get_request_body(self, request: Request) -> dict:
        """Get request body for idempotency comparison"""
        try:
            body = await request.body()
            if body:
                return json.loads(body.decode())
            return {}
        except Exception as e:
            logger.debug(f"Error parsing request body: {e}")
            return {}

    async def _get_response_body(self, response: Response) -> dict:
        """Get response body for caching"""
        try:
            if hasattr(response, "body"):
                body = response.body
                if isinstance(body, bytes):
                    return json.loads(body.decode())
            return {}
        except Exception as e:
            logger.debug(f"Error parsing response body: {e}")
            return {}


# Decorator for endpoints that support idempotency
def idempotent_endpoint(ttl_seconds: int = 24 * 3600):
    """Decorator to mark endpoint as supporting idempotency"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # Look in kwargs
                request = kwargs.get("request") or kwargs.get("http_request")

            # Check if idempotency key was provided and processed by middleware
            if request and hasattr(request.state, "idempotency_key"):
                idempotency_key = request.state.idempotency_key
                request_body = getattr(request.state, "request_body", {})

                # Create or update idempotency key entry
                manager = get_redis_idempotency_manager()
                manager.create_key(
                    operation=f"{request.method} {request.url.path}",
                    request_data=request_body,
                    ttl_seconds=ttl_seconds,
                    custom_key=idempotency_key,
                )

            # Execute the endpoint
            return await func(*args, **kwargs)

        return wrapper

    return decorator
