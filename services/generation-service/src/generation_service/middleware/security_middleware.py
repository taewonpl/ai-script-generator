"""
Security middleware for Generation Service
Implements security best practices including rate limiting, input validation, and security headers.
"""

import asyncio
import hashlib
import hmac
import logging
import time
from typing import Any, Callable, Optional

from fastapi import HTTPException, Request, Response
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    def __init__(
        self,
        app: ASGIApp,
        strict_transport_security: str = "max-age=31536000; includeSubDomains",
        content_type_options: str = "nosniff",
        frame_options: str = "DENY",
        xss_protection: str = "1; mode=block",
        referrer_policy: str = "strict-origin-when-cross-origin",
        content_security_policy: Optional[str] = None,
    ) -> None:
        super().__init__(app)
        self.security_headers = {
            "Strict-Transport-Security": strict_transport_security,
            "X-Content-Type-Options": content_type_options,
            "X-Frame-Options": frame_options,
            "X-XSS-Protection": xss_protection,
            "Referrer-Policy": referrer_policy,
        }
        if content_security_policy:
            self.security_headers["Content-Security-Policy"] = content_security_policy

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value

        # Remove server header to avoid information disclosure
        if "server" in response.headers:
            del response.headers["server"]

        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware"""

    def __init__(
        self,
        app: ASGIApp,
        calls: int = 100,
        period: int = 60,
        per_ip: bool = True,
        excluded_paths: Optional[list[str]] = None,
    ) -> None:
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.per_ip = per_ip
        self.excluded_paths = excluded_paths or [
            "/health",
            "/api/v1/health",
            "/docs",
            "/redoc",
        ]
        self.requests: dict[str, list[float]] = {}
        self.lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Get client identifier
        if self.per_ip:
            client_id = self._get_client_ip(request)
        else:
            client_id = "global"

        # Check rate limit
        async with self.lock:
            current_time = time.time()

            # Initialize or clean old requests
            if client_id not in self.requests:
                self.requests[client_id] = []

            # Remove old requests
            self.requests[client_id] = [
                req_time
                for req_time in self.requests[client_id]
                if current_time - req_time < self.period
            ]

            # Check if limit exceeded
            if len(self.requests[client_id]) >= self.calls:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": self.calls,
                        "period": self.period,
                        "retry_after": self.period,
                    },
                    headers={"Retry-After": str(self.period)},
                )

            # Add current request
            self.requests[client_id].append(current_time)

        response = await call_next(request)

        # Add rate limit headers
        remaining = max(0, self.calls - len(self.requests[client_id]))
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.period))

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP considering proxy headers"""
        # Check for forwarded headers (in order of preference)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (client)
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fallback to client host
        return request.client.host if request.client else "unknown"


class APIKeyValidationMiddleware(BaseHTTPMiddleware):
    """Validate API keys for protected endpoints"""

    def __init__(
        self,
        app: ASGIApp,
        protected_paths: Optional[list[str]] = None,
        api_key_header: str = "X-API-Key",
        valid_keys: Optional[set[str]] = None,
    ) -> None:
        super().__init__(app)
        self.protected_paths = protected_paths or ["/api/v1/generate"]
        self.api_key_header = api_key_header
        self.valid_keys = valid_keys or set()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip validation for non-protected paths
        if not any(request.url.path.startswith(path) for path in self.protected_paths):
            return await call_next(request)

        # Extract API key
        api_key = request.headers.get(self.api_key_header)
        if not api_key:
            # Check Authorization header as fallback
            authorization = request.headers.get("Authorization")
            if authorization:
                scheme, credentials = get_authorization_scheme_param(authorization)
                if scheme.lower() == "bearer":
                    api_key = credentials

        # Validate API key
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Missing API key",
                    "message": f"API key required in {self.api_key_header} header or Authorization header",
                },
            )

        if self.valid_keys and api_key not in self.valid_keys:
            # Log failed authentication attempt
            logger.warning(
                f"Invalid API key attempt from {self._get_client_ip(request)}: {api_key[:8]}..."
            )
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Invalid API key",
                    "message": "The provided API key is not valid",
                },
            )

        # Add API key info to request state for downstream use
        request.state.api_key = api_key
        request.state.authenticated = True

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP considering proxy headers"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "unknown"


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize incoming requests"""

    def __init__(
        self,
        app: ASGIApp,
        max_content_length: int = 16 * 1024 * 1024,  # 16MB
        allowed_content_types: Optional[set[str]] = None,
    ) -> None:
        super().__init__(app)
        self.max_content_length = max_content_length
        self.allowed_content_types = allowed_content_types or {
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_content_length:
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "error": "Request entity too large",
                            "max_size": self.max_content_length,
                            "actual_size": length,
                        },
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "Invalid content-length header"},
                )

        # Check content type for POST/PUT requests
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "").split(";")[0].strip()
            if content_type and content_type not in self.allowed_content_types:
                raise HTTPException(
                    status_code=415,
                    detail={
                        "error": "Unsupported media type",
                        "supported_types": list(self.allowed_content_types),
                    },
                )

        # Validate common suspicious patterns
        self._validate_request_headers(request)

        return await call_next(request)

    def _validate_request_headers(self, request: Request) -> None:
        """Validate request headers for suspicious patterns"""
        suspicious_patterns = [
            "<script",
            "javascript:",
            "vbscript:",
            "onload=",
            "onerror=",
            "../",
            "..\\",
        ]

        for header_name, header_value in request.headers.items():
            if isinstance(header_value, str):
                header_lower = header_value.lower()
                for pattern in suspicious_patterns:
                    if pattern in header_lower:
                        logger.warning(
                            f"Suspicious pattern '{pattern}' detected in header '{header_name}': {header_value}"
                        )
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "error": "Invalid request",
                                "message": "Suspicious content detected in headers",
                            },
                        )


class RequestSignatureMiddleware(BaseHTTPMiddleware):
    """Verify request signatures for webhook-like endpoints"""

    def __init__(
        self,
        app: ASGIApp,
        secret_key: str,
        signature_header: str = "X-Signature-256",
        signed_paths: Optional[list[str]] = None,
    ) -> None:
        super().__init__(app)
        self.secret_key = secret_key.encode()
        self.signature_header = signature_header
        self.signed_paths = signed_paths or []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip signature verification for non-signed paths
        if not any(request.url.path.startswith(path) for path in self.signed_paths):
            return await call_next(request)

        # Get signature from header
        signature = request.headers.get(self.signature_header)
        if not signature:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Missing signature",
                    "message": f"Request signature required in {self.signature_header} header",
                },
            )

        # Read request body
        body = await request.body()

        # Verify signature
        if not self._verify_signature(body, signature):
            logger.warning(f"Invalid signature from {self._get_client_ip(request)}")
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Invalid signature",
                    "message": "Request signature verification failed",
                },
            )

        return await call_next(request)

    def _verify_signature(self, body: bytes, signature: str) -> bool:
        """Verify HMAC signature"""
        try:
            # Remove 'sha256=' prefix if present
            if signature.startswith("sha256="):
                signature = signature[7:]

            # Compute expected signature
            expected = hmac.new(self.secret_key, body, hashlib.sha256).hexdigest()

            # Constant-time comparison
            return hmac.compare_digest(signature, expected)
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP considering proxy headers"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "unknown"


def setup_security_middleware(
    app: Any,
    enable_rate_limiting: bool = True,
    enable_api_key_validation: bool = False,
    enable_request_signing: bool = False,
    rate_limit_calls: int = 100,
    rate_limit_period: int = 60,
    api_keys: Optional[set[str]] = None,
    signing_secret: Optional[str] = None,
) -> None:
    """Setup all security middleware for the FastAPI app"""

    # Security headers (always enabled)
    app.add_middleware(SecurityHeadersMiddleware)

    # Request validation (always enabled)
    app.add_middleware(RequestValidationMiddleware)

    # Rate limiting (optional)
    if enable_rate_limiting:
        app.add_middleware(
            RateLimitingMiddleware,
            calls=rate_limit_calls,
            period=rate_limit_period,
        )

    # API key validation (optional)
    if enable_api_key_validation and api_keys:
        app.add_middleware(
            APIKeyValidationMiddleware,
            valid_keys=api_keys,
        )

    # Request signing (optional)
    if enable_request_signing and signing_secret:
        app.add_middleware(
            RequestSignatureMiddleware,
            secret_key=signing_secret,
        )

    logger.info("Security middleware configured")
    logger.info(f"Rate limiting: {'enabled' if enable_rate_limiting else 'disabled'}")
    logger.info(
        f"API key validation: {'enabled' if enable_api_key_validation else 'disabled'}"
    )
    logger.info(
        f"Request signing: {'enabled' if enable_request_signing else 'disabled'}"
    )
