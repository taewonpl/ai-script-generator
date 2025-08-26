"""
FastAPI middleware integration for unified observability system.
"""

import time
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .errors import (
    ErrorCode,
    create_error_response,
)
from .events import EventLogger, EventSeverity, create_event_logger
from .health import HealthChecker
from .idempotency import IdempotencyConflictError, get_idempotency_manager
from .logging import create_service_logger
from .metrics import get_metrics_collector
from .tracing import (
    TraceContext,
    TraceHeaders,
    TracingMiddleware,
    inject_trace_headers,
)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive observability middleware for FastAPI applications.
    Integrates tracing, logging, metrics, and error handling.
    """

    def __init__(
        self,
        app: FastAPI,
        service_name: str,
        version: str = "1.0.0",
        enable_tracing: bool = True,
        enable_metrics: bool = True,
        enable_idempotency: bool = True,
        idempotent_methods: set[str] | None = None,
        excluded_paths: set[str] | None = None,
    ):
        super().__init__(app)
        self.service_name = service_name
        self.version = version
        self.enable_tracing = enable_tracing
        self.enable_metrics = enable_metrics
        self.enable_idempotency = enable_idempotency
        self.idempotent_methods = idempotent_methods or {"POST", "PUT", "PATCH"}
        self.excluded_paths = excluded_paths or {
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
        }

        # Initialize components
        self.structured_logger = create_service_logger(service_name, version)
        self.tracing_middleware = TracingMiddleware(service_name)

        if enable_metrics:
            self.metrics_collector = get_metrics_collector(service_name)

        if enable_idempotency:
            self.idempotency_manager = get_idempotency_manager()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """Process request with full observability."""
        start_time = time.time()

        # Skip excluded paths
        if request.url.path in self.excluded_paths:
            result = await call_next(request)
            return result  # type: ignore[no-any-return]

        # Extract request information
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else None

        # Initialize trace context
        trace_context = None
        if self.enable_tracing:
            headers_dict = dict(request.headers)
            trace_context = self.tracing_middleware.extract_context(headers_dict)

        # Create event logger with trace context
        event_logger = create_event_logger(
            self.structured_logger, self.service_name, trace_context
        )

        # Log API request started
        event_logger.log_api_request_started(
            method=method, endpoint=path, client_ip=client_ip
        )

        # Handle idempotency for applicable methods
        if (
            self.enable_idempotency
            and method in self.idempotent_methods
            and TraceHeaders.TRACE_ID in request.headers
        ):
            try:
                idempotency_key = request.headers.get("Idempotency-Key")
                if idempotency_key:
                    # Check for existing response
                    existing_response = self.idempotency_manager.check_idempotency(
                        idempotency_key,
                        {
                            "method": method,
                            "path": path,
                            "headers": dict(request.headers),
                        },
                    )

                    if existing_response:
                        # Return cached response
                        response = JSONResponse(
                            content=existing_response.response_data,
                            status_code=existing_response.status_code,
                            headers=existing_response.headers,
                        )

                        # Add trace headers
                        if self.enable_tracing and trace_context:
                            processing_time = int((time.time() - start_time) * 1000)
                            trace_headers = inject_trace_headers(
                                trace_context, processing_time
                            )
                            for key, value in trace_headers.items():
                                response.headers[key] = value

                        return response

            except IdempotencyConflictError as e:
                # Return idempotency conflict error
                error_response = create_error_response(
                    ErrorCode.RESOURCE_ALREADY_EXISTS,
                    str(e),
                    trace_id=trace_context.trace_id if trace_context else None,
                )

                response = JSONResponse(
                    content=error_response.model_dump(), status_code=409
                )

                if self.enable_tracing and trace_context:
                    processing_time = int((time.time() - start_time) * 1000)
                    trace_headers = inject_trace_headers(trace_context, processing_time)
                    for key, value in trace_headers.items():
                        response.headers[key] = value

                return response

        # Process request
        try:
            # Attach observability context to request state
            request.state.trace_context = trace_context
            request.state.event_logger = event_logger
            request.state.start_time = start_time

            api_response: Response = await call_next(request)

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Add tracing headers to response
            if self.enable_tracing and trace_context:
                trace_headers = inject_trace_headers(trace_context, processing_time_ms)
                for key, value in trace_headers.items():
                    api_response.headers[key] = value

            # Log successful API request
            event_logger.log_api_request_completed(
                method=method,
                endpoint=path,
                status_code=api_response.status_code,
                response_size=(
                    len(api_response.body) if hasattr(api_response, "body") else 0
                ),
                duration_ms=processing_time_ms,
            )

            # Track metrics
            if self.enable_metrics:
                self.metrics_collector.track_request(
                    endpoint=path,
                    method=method,
                    status_code=api_response.status_code,
                    response_time_ms=processing_time_ms,
                    trace_context=trace_context,
                )

            # Store idempotent response if applicable
            if (
                self.enable_idempotency
                and method in self.idempotent_methods
                and api_response.status_code < 400
            ):
                idempotency_key = request.headers.get("Idempotency-Key")
                if idempotency_key:
                    self.idempotency_manager.store_response(
                        key=idempotency_key,
                        status_code=api_response.status_code,
                        response_data=(
                            api_response.body if hasattr(api_response, "body") else {}
                        ),
                        headers=dict(api_response.headers),
                    )

            return api_response

        except Exception as e:
            # Calculate processing time for error
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Determine error details
            if isinstance(e, HTTPException):
                status_code = e.status_code
                error_code = f"HTTP_{status_code}"
                error_message = e.detail
            else:
                status_code = 500
                error_code = ErrorCode.INTERNAL_ERROR.value
                error_message = str(e)

            # Log failed API request
            event_logger.log_api_request_failed(
                method=method,
                endpoint=path,
                error_code=error_code,
                error_message=error_message,
                duration_ms=processing_time_ms,
            )

            # Track error metrics
            if self.enable_metrics:
                self.metrics_collector.track_error(
                    endpoint=path,
                    error_code=error_code,
                    error_type=e.__class__.__name__,
                    message=error_message,
                    trace_context=trace_context,
                )

                self.metrics_collector.track_request(
                    endpoint=path,
                    method=method,
                    status_code=status_code,
                    response_time_ms=processing_time_ms,
                    trace_context=trace_context,
                )

            # Create standardized error response
            if isinstance(e, HTTPException):
                http_error_code = (
                    ErrorCode.VALIDATION_FAILED
                    if isinstance(e, HTTPException) and e.status_code == 422
                    else ErrorCode.INTERNAL_ERROR
                )
                error_response = create_error_response(
                    http_error_code,
                    error_message,
                    trace_id=trace_context.trace_id if trace_context else None,
                )
            else:
                error_response = create_error_response(
                    ErrorCode.INTERNAL_ERROR,
                    "Internal server error occurred",
                    details={"original_error": error_message},
                    trace_id=trace_context.trace_id if trace_context else None,
                )

            # Create JSON response
            response = JSONResponse(
                content=error_response.model_dump(), status_code=status_code
            )

            # Add tracing headers to error response
            if self.enable_tracing and trace_context:
                trace_headers = inject_trace_headers(trace_context, processing_time_ms)
                for key, value in trace_headers.items():
                    response.headers[key] = value

            return response


def setup_observability(
    app: FastAPI,
    service_name: str,
    version: str = "1.0.0",
    health_dependencies: list[Any] | None = None,
) -> dict[str, Any]:
    """
    Set up comprehensive observability for a FastAPI application.

    Returns:
        dict: Observability components (logger, metrics, health_checker)
    """

    # Add observability middleware
    from functools import partial

    middleware_class = partial(
        ObservabilityMiddleware, service_name=service_name, version=version
    )
    app.add_middleware(middleware_class)

    # Create health checker
    health_checker = HealthChecker(service_name, version)  # type: ignore[operator]

    # Add health endpoint
    @app.get("/health")
    async def health_check() -> JSONResponse:
        """Health check endpoint."""
        health_status = await health_checker.get_overall_health(health_dependencies)
        status_code = 200

        if health_status.status == "unhealthy":
            status_code = 503
        elif health_status.status == "degraded":
            status_code = 200  # Still accepting traffic

        return JSONResponse(content=health_status.model_dump(), status_code=status_code)

    # Add metrics endpoint
    @app.get("/metrics")
    async def get_metrics() -> dict[str, Any] | JSONResponse:
        """Metrics endpoint."""
        try:
            metrics_collector = get_metrics_collector()
            overview = metrics_collector.get_service_overview()
            operation_metrics = metrics_collector.get_all_operation_metrics()
            endpoint_stats = metrics_collector.get_endpoint_stats()

            return {
                "service_overview": overview,
                "operation_metrics": [m.model_dump() for m in operation_metrics],
                "endpoint_statistics": endpoint_stats,
            }
        except Exception as e:
            return JSONResponse(
                content={"error": f"Failed to get metrics: {e!s}"}, status_code=500
            )

    # Create service logger
    logger = create_service_logger(service_name, version)

    # Create event logger for application use
    event_logger = create_event_logger(logger, service_name)

    # Log service startup
    event_logger.log_service_started(
        version, 8000
    )  # Default port, should be configurable

    return {
        "logger": logger,
        "event_logger": event_logger,
        "metrics_collector": get_metrics_collector(),
        "health_checker": health_checker,
    }


# Dependency injection for FastAPI routes
def get_trace_context(request: Request) -> TraceContext | None:
    """Get trace context from request state."""
    return getattr(request.state, "trace_context", None)


def get_event_logger(request: Request) -> EventLogger | None:
    """Get event logger from request state."""
    return getattr(request.state, "event_logger", None)


def get_request_start_time(request: Request) -> float | None:
    """Get request start time from request state."""
    return getattr(request.state, "start_time", None)


# Exception handlers
def create_exception_handlers() -> dict[type[Exception], Callable[..., Any]]:
    """Create standardized exception handlers."""

    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        trace_context = get_trace_context(request)

        http_error_code = (
            ErrorCode.VALIDATION_FAILED
            if exc.status_code == 422
            else ErrorCode.INTERNAL_ERROR
        )
        error_response = create_error_response(
            http_error_code,
            exc.detail,
            trace_id=trace_context.trace_id if trace_context else None,
        )

        return JSONResponse(
            content=error_response.model_dump(), status_code=exc.status_code
        )

    async def validation_exception_handler(request: Request, exc: Any) -> JSONResponse:
        """Handle validation exceptions."""
        trace_context = get_trace_context(request)

        error_response = create_error_response(
            ErrorCode.VALIDATION_FAILED,
            "Request validation failed",
            details=(
                {"validation_errors": exc.errors()} if hasattr(exc, "errors") else {}
            ),
            trace_id=trace_context.trace_id if trace_context else None,
        )

        return JSONResponse(content=error_response.model_dump(), status_code=422)

    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle general exceptions."""
        trace_context = get_trace_context(request)

        error_response = create_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Internal server error",
            details={"error_type": exc.__class__.__name__},
            trace_id=trace_context.trace_id if trace_context else None,
        )

        return JSONResponse(content=error_response.model_dump(), status_code=500)

    return {HTTPException: http_exception_handler, Exception: general_exception_handler}


# Context manager for operation tracking
class OperationTracker:
    """Context manager for tracking operations with observability."""

    def __init__(
        self,
        operation_name: str,
        event_logger: EventLogger,
        trace_context: TraceContext | None = None,
    ):
        self.operation_name = operation_name
        self.event_logger = event_logger
        self.trace_context = trace_context
        self.start_time: float | None = None
        self.success = True

    def __enter__(self) -> "OperationTracker":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time is None:
            return
        duration_ms = int((time.time() - self.start_time) * 1000)

        if exc_type is not None:
            self.success = False
            # Log operation failure
            self.event_logger.log_event(
                event_type="OPERATION_FAILED",
                event_name=f"{self.operation_name} Failed",
                severity=EventSeverity.HIGH,
                metadata={
                    "operation": self.operation_name,
                    "error_type": exc_type.__name__,
                    "error_message": str(exc_val),
                },
                duration_ms=duration_ms,
            )
        else:
            # Log operation success
            self.event_logger.log_event(
                event_type="OPERATION_COMPLETED",
                event_name=f"{self.operation_name} Completed",
                severity=EventSeverity.LOW,
                metadata={"operation": self.operation_name},
                duration_ms=duration_ms,
            )

        # Track performance metrics
        metrics_collector = get_metrics_collector()
        metrics_collector.track_performance(
            operation=self.operation_name, duration_ms=duration_ms, success=self.success
        )

    def add_metadata(self, **metadata: Any) -> None:
        """Add metadata to the operation (for logging context)."""
        # This could be enhanced to store metadata for final logging
        pass
