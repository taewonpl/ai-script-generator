"""
Idempotency support for ensuring safe API operations.
"""

import hashlib
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Set

from pydantic import BaseModel, Field


class IdempotencyKey(BaseModel):
    """Idempotency key with metadata."""

    key: str = Field(..., description="Unique idempotency key")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Key creation timestamp"
    )
    expires_at: datetime = Field(..., description="Key expiration timestamp")
    operation: Optional[str] = Field(default=None, description="Associated operation")
    request_hash: Optional[str] = Field(
        default=None, description="Hash of the original request"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


class IdempotentResponse(BaseModel):
    """Cached response for idempotent operations."""

    key: str = Field(..., description="Idempotency key")
    status_code: int = Field(..., description="HTTP status code")
    response_data: Any = Field(..., description="Response payload")
    headers: dict[str, str] = Field(
        default_factory=dict, description="Response headers"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Response creation timestamp"
    )
    expires_at: datetime = Field(..., description="Response expiration timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


def generate_idempotency_key() -> str:
    """Generate a unique idempotency key."""
    timestamp = str(int(time.time() * 1000))
    random_part = uuid.uuid4().hex[:8]
    return f"idem_{timestamp}_{random_part}"


def create_request_hash(data: Any) -> str:
    """Create a hash of request data for idempotency matching."""
    import json

    # Convert data to stable JSON representation
    if isinstance(data, dict):
        # Sort keys for consistent hashing
        sorted_data = json.dumps(data, sort_keys=True, separators=(",", ":"))
    elif isinstance(data, (list, tuple)):
        sorted_data = json.dumps(data, separators=(",", ":"))
    elif isinstance(data, str):
        sorted_data = data
    else:
        sorted_data = str(data)

    # Create SHA-256 hash
    return hashlib.sha256(sorted_data.encode("utf-8")).hexdigest()


class IdempotencyManager:
    """In-memory idempotency manager for development/testing."""

    def __init__(self, default_ttl_seconds: int = 3600):  # 1 hour default
        self.default_ttl_seconds = default_ttl_seconds
        self._keys: dict[str, IdempotencyKey] = {}
        self._responses: dict[str, IdempotentResponse] = {}

    def create_key(
        self,
        operation: Optional[str] = None,
        request_data: Optional[Any] = None,
        ttl_seconds: Optional[int] = None,
    ) -> IdempotencyKey:
        """Create a new idempotency key."""
        key = generate_idempotency_key()
        ttl = ttl_seconds or self.default_ttl_seconds

        request_hash = None
        if request_data is not None:
            request_hash = create_request_hash(request_data)

        idempotency_key = IdempotencyKey(
            key=key,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl),
            operation=operation,
            request_hash=request_hash,
        )

        self._keys[key] = idempotency_key
        return idempotency_key

    def get_key(self, key: str) -> Optional[IdempotencyKey]:
        """Get idempotency key by key string."""
        idempotency_key = self._keys.get(key)
        if not idempotency_key:
            return None

        # Check if expired
        if datetime.utcnow() > idempotency_key.expires_at:
            self.delete_key(key)
            return None

        return idempotency_key

    def delete_key(self, key: str) -> bool:
        """Delete idempotency key and associated response."""
        deleted_key = self._keys.pop(key, None)
        deleted_response = self._responses.pop(key, None)

        return deleted_key is not None or deleted_response is not None

    def store_response(
        self,
        key: str,
        status_code: int,
        response_data: Any,
        headers: Optional[Dict[str, str]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> IdempotentResponse:
        """Store response for idempotent operation."""
        ttl = ttl_seconds or self.default_ttl_seconds

        response = IdempotentResponse(
            key=key,
            status_code=status_code,
            response_data=response_data,
            headers=headers or {},
            expires_at=datetime.utcnow() + timedelta(seconds=ttl),
        )

        self._responses[key] = response
        return response

    def get_response(self, key: str) -> Optional[IdempotentResponse]:
        """Get stored response for idempotency key."""
        response = self._responses.get(key)
        if not response:
            return None

        # Check if expired
        if datetime.utcnow() > response.expires_at:
            self.delete_key(key)
            return None

        return response

    def check_idempotency(
        self, key: str, request_data: Optional[Any] = None
    ) -> Optional[IdempotentResponse]:
        """Check if operation is idempotent and return cached response if available."""
        # Check if key exists
        idempotency_key = self.get_key(key)
        if not idempotency_key:
            return None

        # Validate request matches if hash is stored
        if request_data is not None and idempotency_key.request_hash:
            current_hash = create_request_hash(request_data)
            if current_hash != idempotency_key.request_hash:
                # Request doesn't match - this is a conflict
                raise IdempotencyConflictError(
                    f"Idempotency key {key} was used with different request data"
                )

        # Check if response is cached
        return self.get_response(key)

    def cleanup_expired(self) -> int:
        """Clean up expired keys and responses."""
        now = datetime.utcnow()
        expired_keys = []

        # Find expired keys
        for key, idempotency_key in self._keys.items():
            if now > idempotency_key.expires_at:
                expired_keys.append(key)

        # Find expired responses
        for key, response in self._responses.items():
            if now > response.expires_at and key not in expired_keys:
                expired_keys.append(key)

        # Delete expired entries
        for key in expired_keys:
            self.delete_key(key)

        return len(expired_keys)

    def get_stats(self) -> dict[str, int]:
        """Get idempotency manager statistics."""
        return {
            "active_keys": len(self._keys),
            "cached_responses": len(self._responses),
            "total_entries": len(self._keys) + len(self._responses),
        }


class IdempotencyConflictError(Exception):
    """Raised when idempotency key is reused with different request data."""

    pass


# Singleton instance for global use
_global_manager: Optional[IdempotencyManager] = None


def get_idempotency_manager() -> IdempotencyManager:
    """Get global idempotency manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = IdempotencyManager()
    return _global_manager


def check_idempotency(
    key: str, request_data: Optional[Any] = None
) -> Optional[IdempotentResponse]:
    """Check idempotency using global manager."""
    manager = get_idempotency_manager()
    return manager.check_idempotency(key, request_data)


def store_idempotent_response(
    key: str,
    status_code: int,
    response_data: Any,
    headers: Optional[Dict[str, str]] = None,
    ttl_seconds: Optional[int] = None,
) -> IdempotentResponse:
    """Store idempotent response using global manager."""
    manager = get_idempotency_manager()
    return manager.store_response(key, status_code, response_data, headers, ttl_seconds)


# Decorator for idempotent operations
def idempotent(
    ttl_seconds: int = 3600,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to make functions idempotent."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract idempotency key from kwargs
            key = kwargs.get("idempotency_key")
            if not key:
                # Generate key from function name and arguments
                key = generate_idempotency_key()

            # Check for existing response
            manager = get_idempotency_manager()
            existing_response = manager.check_idempotency(
                key, {"args": args, "kwargs": kwargs}
            )

            if existing_response:
                return existing_response.response_data

            # Execute function
            try:
                result = await func(*args, **kwargs)

                # Store result
                manager.store_response(
                    key=key,
                    status_code=200,
                    response_data=result,
                    ttl_seconds=ttl_seconds,
                )

                return result

            except Exception as e:
                # Store error response
                manager.store_response(
                    key=key,
                    status_code=500,
                    response_data={"error": str(e)},
                    ttl_seconds=ttl_seconds,
                )
                raise

        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract idempotency key from kwargs
            key = kwargs.get("idempotency_key")
            if not key:
                # Generate key from function name and arguments
                key = generate_idempotency_key()

            # Check for existing response
            manager = get_idempotency_manager()
            existing_response = manager.check_idempotency(
                key, {"args": args, "kwargs": kwargs}
            )

            if existing_response:
                return existing_response.response_data

            # Execute function
            try:
                result = func(*args, **kwargs)

                # Store result
                manager.store_response(
                    key=key,
                    status_code=200,
                    response_data=result,
                    ttl_seconds=ttl_seconds,
                )

                return result

            except Exception as e:
                # Store error response
                manager.store_response(
                    key=key,
                    status_code=500,
                    response_data={"error": str(e)},
                    ttl_seconds=ttl_seconds,
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# FastAPI middleware for idempotency
class IdempotencyMiddleware:
    """FastAPI middleware for handling idempotency keys."""

    def __init__(
        self,
        app: Any,
        header_name: str = "Idempotency-Key",
        ttl_seconds: int = 3600,
        methods: Optional[Set[str]] = None,
    ) -> None:
        self.app = app
        self.header_name = header_name
        self.ttl_seconds = ttl_seconds
        self.methods = methods or {"POST", "PUT", "PATCH"}
        self.manager = get_idempotency_manager()

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        if method not in self.methods:
            await self.app(scope, receive, send)
            return

        # Extract idempotency key from headers
        headers = dict(scope["headers"])
        key = None

        for name, value in headers.items():
            if name.decode().lower() == self.header_name.lower():
                key = value.decode()
                break

        if not key:
            await self.app(scope, receive, send)
            return

        # Check for existing response
        try:
            existing_response = self.manager.get_response(key)
            if existing_response:
                # Return cached response
                await self._send_cached_response(send, existing_response)
                return

        except IdempotencyConflictError:
            # Return conflict error
            await self._send_conflict_response(send)
            return

        # Proceed with normal request processing
        await self.app(scope, receive, send)

    async def _send_cached_response(
        self, send: Any, response: IdempotentResponse
    ) -> None:
        """Send cached idempotent response."""
        await send(
            {
                "type": "http.response.start",
                "status": response.status_code,
                "headers": [
                    (k.encode(), v.encode()) for k, v in response.headers.items()
                ],
            }
        )

        import json

        body = json.dumps(response.response_data).encode()

        await send({"type": "http.response.body", "body": body})

    async def _send_conflict_response(self, send: Any) -> None:
        """Send idempotency conflict response."""
        await send(
            {
                "type": "http.response.start",
                "status": 409,
                "headers": [(b"content-type", b"application/json")],
            }
        )

        import json

        error_response = {
            "success": False,
            "error": {
                "code": "IDEMPOTENCY_CONFLICT",
                "message": "Idempotency key was used with different request data",
            },
        }

        body = json.dumps(error_response).encode()

        await send({"type": "http.response.body", "body": body})


# Utility functions for common idempotent operations
def create_episode_idempotency_key(project_id: str, episode_number: int) -> str:
    """Create idempotency key for episode creation."""
    data = f"create_episode_{project_id}_{episode_number}"
    return f"idem_ep_{create_request_hash(data)[:12]}"


def create_generation_idempotency_key(
    project_id: str, episode_id: str, prompt_hash: str
) -> str:
    """Create idempotency key for generation requests."""
    data = f"generate_{project_id}_{episode_id}_{prompt_hash}"
    return f"idem_gen_{create_request_hash(data)[:12]}"


def create_project_idempotency_key(user_id: str, project_name: str) -> str:
    """Create idempotency key for project creation."""
    data = f"create_project_{user_id}_{project_name.lower()}"
    return f"idem_proj_{create_request_hash(data)[:12]}"
