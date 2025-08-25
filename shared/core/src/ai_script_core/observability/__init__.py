"""
Observability module for unified error handling, tracing, and logging
across all AI Script Generator services.
"""

from .errors import (
    ErrorCode,
    ErrorDetail,
    HttpStatusCode,
    StandardErrorResponse,
    create_error_response,
    create_success_response,
)
from .health import (
    DependencyHealth,
    HealthStatus,
    ServiceHealth,
    check_dependency_health,
    create_health_response,
)
from .idempotency import (
    IdempotencyKey,
    IdempotencyManager,
    IdempotentResponse,
    check_idempotency,
    generate_idempotency_key,
)
from .logging import (
    LogLevel,
    ServiceContext,
    StructuredLogger,
    create_service_logger,
    log_error,
    log_event,
    log_performance,
)
from .metrics import (
    ErrorMetrics,
    MetricsCollector,
    PerformanceMetrics,
    RequestMetrics,
    track_error,
    track_performance,
    track_request,
)
from .tracing import (
    TraceContext,
    TraceHeaders,
    extract_trace_context,
    generate_job_id,
    generate_trace_id,
    inject_trace_headers,
)

__all__ = [
    # Error handling
    "StandardErrorResponse",
    "ErrorDetail",
    "ErrorCode",
    "HttpStatusCode",
    "create_error_response",
    "create_success_response",
    # Tracing
    "TraceContext",
    "TraceHeaders",
    "generate_trace_id",
    "generate_job_id",
    "extract_trace_context",
    "inject_trace_headers",
    # Logging
    "StructuredLogger",
    "LogLevel",
    "ServiceContext",
    "create_service_logger",
    "log_event",
    "log_error",
    "log_performance",
    # Health checks
    "HealthStatus",
    "DependencyHealth",
    "ServiceHealth",
    "create_health_response",
    "check_dependency_health",
    # Metrics
    "MetricsCollector",
    "RequestMetrics",
    "ErrorMetrics",
    "PerformanceMetrics",
    "track_request",
    "track_error",
    "track_performance",
    # Idempotency
    "IdempotencyKey",
    "IdempotencyManager",
    "IdempotentResponse",
    "generate_idempotency_key",
    "check_idempotency",
]
