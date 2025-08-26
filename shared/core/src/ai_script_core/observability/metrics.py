"""
Metrics collection system for monitoring API performance and errors.
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import datetime, timedelta
from threading import Lock
from typing import Any

from pydantic import BaseModel, Field

from .tracing import TraceContext


class RequestMetrics(BaseModel):
    """Metrics for individual API requests."""

    endpoint: str = Field(..., description="API endpoint path")
    method: str = Field(..., description="HTTP method")
    status_code: int = Field(..., description="HTTP status code")
    response_time_ms: int = Field(..., description="Response time in milliseconds")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Request timestamp"
    )
    trace_id: str | None = Field(default=None, description="Request trace ID")
    user_id: str | None = Field(default=None, description="User ID if available")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


class ErrorMetrics(BaseModel):
    """Metrics for API errors."""

    service: str = Field(..., description="Service name")
    endpoint: str = Field(..., description="API endpoint path")
    error_code: str = Field(..., description="Error code")
    error_type: str = Field(..., description="Error type/class")
    message: str = Field(..., description="Error message")
    count: int = Field(default=1, description="Error occurrence count")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )
    trace_id: str | None = Field(default=None, description="Request trace ID")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


class PerformanceMetrics(BaseModel):
    """Aggregated performance metrics."""

    operation: str = Field(..., description="Operation name")
    request_count: int = Field(..., description="Total request count")
    avg_response_time_ms: float = Field(..., description="Average response time")
    p50_response_time_ms: float = Field(
        ..., description="50th percentile response time"
    )
    p95_response_time_ms: float = Field(
        ..., description="95th percentile response time"
    )
    p99_response_time_ms: float = Field(
        ..., description="99th percentile response time"
    )
    error_count: int = Field(..., description="Total error count")
    error_rate: float = Field(..., description="Error rate (0-1)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Metrics timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


class OperationStats:
    """Statistics for a single operation."""

    def __init__(self, operation: str, max_history: int = 1000):
        self.operation = operation
        self.max_history = max_history
        self.response_times: deque[float] = deque(maxlen=max_history)
        self.error_count = 0
        self.total_count = 0
        self.last_updated = datetime.utcnow()
        self._lock = Lock()

    def record_request(self, response_time_ms: float, success: bool) -> None:
        """Record a request."""
        with self._lock:
            self.response_times.append(response_time_ms)
            self.total_count += 1
            if not success:
                self.error_count += 1
            self.last_updated = datetime.utcnow()

    def get_percentile(self, percentile: float) -> float:
        """Calculate response time percentile."""
        with self._lock:
            if not self.response_times:
                return 0.0

            sorted_times = sorted(self.response_times)
            index = int(len(sorted_times) * percentile / 100)
            index = min(index, len(sorted_times) - 1)
            return sorted_times[index]

    def get_average(self) -> float:
        """Calculate average response time."""
        with self._lock:
            if not self.response_times:
                return 0.0
            return sum(self.response_times) / len(self.response_times)

    def get_error_rate(self) -> float:
        """Calculate error rate."""
        with self._lock:
            if self.total_count == 0:
                return 0.0
            return self.error_count / self.total_count

    def to_performance_metrics(self) -> PerformanceMetrics:
        """Convert to PerformanceMetrics model."""
        return PerformanceMetrics(
            operation=self.operation,
            request_count=self.total_count,
            avg_response_time_ms=self.get_average(),
            p50_response_time_ms=self.get_percentile(50),
            p95_response_time_ms=self.get_percentile(95),
            p99_response_time_ms=self.get_percentile(99),
            error_count=self.error_count,
            error_rate=self.get_error_rate(),
        )


class MetricsCollector:
    """Centralized metrics collection system."""

    def __init__(
        self,
        service_name: str,
        max_operation_history: int = 1000,
        max_request_history: int = 10000,
        max_error_history: int = 1000,
    ):
        self.service_name = service_name
        self.max_operation_history = max_operation_history
        self.max_request_history = max_request_history
        self.max_error_history = max_error_history

        # Operation statistics
        self.operations: dict[str, OperationStats] = {}

        # Recent request history
        self.recent_requests: deque[RequestMetrics] = deque(maxlen=max_request_history)

        # Recent errors
        self.recent_errors: deque[ErrorMetrics] = deque(maxlen=max_error_history)

        # Error frequency tracking
        self.error_frequency: dict[str, int] = defaultdict(int)

        # Thread safety
        self._lock = Lock()

        # Start time for uptime calculation
        self.start_time = datetime.utcnow()

    def track_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
        trace_context: TraceContext | None = None,
        user_id: str | None = None,
    ) -> None:
        """Track an API request."""
        operation = f"{method} {endpoint}"
        success = status_code < 400

        # Record request metrics
        request_metric = RequestMetrics(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            trace_id=trace_context.trace_id if trace_context else None,
            user_id=user_id,
        )

        with self._lock:
            # Add to recent requests
            self.recent_requests.append(request_metric)

            # Update operation statistics
            if operation not in self.operations:
                self.operations[operation] = OperationStats(
                    operation, self.max_operation_history
                )

            self.operations[operation].record_request(response_time_ms, success)

    def track_error(
        self,
        endpoint: str,
        error_code: str,
        error_type: str,
        message: str,
        trace_context: TraceContext | None = None,
    ) -> None:
        """Track an API error."""
        error_metric = ErrorMetrics(
            service=self.service_name,
            endpoint=endpoint,
            error_code=error_code,
            error_type=error_type,
            message=message,
            trace_id=trace_context.trace_id if trace_context else None,
        )

        with self._lock:
            # Add to recent errors
            self.recent_errors.append(error_metric)

            # Update error frequency
            error_key = f"{endpoint}:{error_code}"
            self.error_frequency[error_key] += 1

    def track_performance(
        self,
        operation: str,
        duration_ms: int,
        success: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Track performance of a custom operation."""
        with self._lock:
            if operation not in self.operations:
                self.operations[operation] = OperationStats(
                    operation, self.max_operation_history
                )

            self.operations[operation].record_request(duration_ms, success)

    def get_operation_metrics(self, operation: str) -> PerformanceMetrics | None:
        """Get performance metrics for a specific operation."""
        with self._lock:
            if operation not in self.operations:
                return None

            return self.operations[operation].to_performance_metrics()

    def get_all_operation_metrics(self) -> list[PerformanceMetrics]:
        """Get performance metrics for all operations."""
        with self._lock:
            return [
                stats.to_performance_metrics() for stats in self.operations.values()
            ]

    def get_recent_requests(self, limit: int | None = None) -> list[RequestMetrics]:
        """Get recent request metrics."""
        with self._lock:
            requests = list(self.recent_requests)
            if limit:
                requests = requests[-limit:]
            return requests

    def get_recent_errors(self, limit: int | None = None) -> list[ErrorMetrics]:
        """Get recent error metrics."""
        with self._lock:
            errors = list(self.recent_errors)
            if limit:
                errors = errors[-limit:]
            return errors

    def get_error_frequency(self) -> dict[str, int]:
        """Get error frequency statistics."""
        with self._lock:
            return dict(self.error_frequency)

    def get_service_overview(self) -> dict[str, Any]:
        """Get overall service metrics overview."""
        with self._lock:
            total_requests = sum(op.total_count for op in self.operations.values())
            total_errors = sum(op.error_count for op in self.operations.values())

            if total_requests > 0:
                overall_error_rate = total_errors / total_requests
                avg_response_time = (
                    sum(
                        op.get_average() * op.total_count
                        for op in self.operations.values()
                    )
                    / total_requests
                )
            else:
                overall_error_rate = 0.0
                avg_response_time = 0.0

            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()

            return {
                "service": self.service_name,
                "uptime_seconds": int(uptime_seconds),
                "total_requests": total_requests,
                "total_errors": total_errors,
                "overall_error_rate": overall_error_rate,
                "avg_response_time_ms": avg_response_time,
                "active_operations": len(self.operations),
                "requests_per_second": total_requests / max(uptime_seconds, 1),
                "timestamp": datetime.utcnow(),
            }

    def get_endpoint_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics grouped by endpoint."""
        endpoint_stats: defaultdict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "request_count": 0,
                "error_count": 0,
                "total_response_time": 0,
                "methods": set(),
            }
        )

        with self._lock:
            for request in self.recent_requests:
                stats = endpoint_stats[request.endpoint]
                stats["request_count"] += 1
                stats["total_response_time"] += request.response_time_ms
                stats["methods"].add(request.method)

                if request.status_code >= 400:
                    stats["error_count"] += 1

        # Calculate averages and convert sets to lists
        result = {}
        for endpoint, stats in endpoint_stats.items():
            if stats["request_count"] > 0:
                result[endpoint] = {
                    "request_count": stats["request_count"],
                    "error_count": stats["error_count"],
                    "error_rate": stats["error_count"] / stats["request_count"],
                    "avg_response_time_ms": stats["total_response_time"]
                    / stats["request_count"],
                    "methods": list(stats["methods"]),
                }

        return result

    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        with self._lock:
            self.operations.clear()
            self.recent_requests.clear()
            self.recent_errors.clear()
            self.error_frequency.clear()
            self.start_time = datetime.utcnow()

    def cleanup_old_data(self, max_age_hours: int = 24) -> int:
        """Clean up old data beyond specified age."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned_count = 0

        with self._lock:
            # Clean old requests
            while (
                self.recent_requests and self.recent_requests[0].timestamp < cutoff_time
            ):
                self.recent_requests.popleft()
                cleaned_count += 1

            # Clean old errors
            while self.recent_errors and self.recent_errors[0].timestamp < cutoff_time:
                self.recent_errors.popleft()
                cleaned_count += 1

        return cleaned_count


# Global metrics collector instance
_global_collector: MetricsCollector | None = None


def get_metrics_collector(service_name: str | None = None) -> MetricsCollector:
    """Get global metrics collector instance."""
    global _global_collector
    if _global_collector is None:
        if not service_name:
            raise ValueError(
                "Service name required for first call to get_metrics_collector"
            )
        _global_collector = MetricsCollector(service_name)
    return _global_collector


def track_request(
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: int,
    trace_context: TraceContext | None = None,
    user_id: str | None = None,
) -> None:
    """Track request using global collector."""
    collector = get_metrics_collector()
    collector.track_request(
        endpoint, method, status_code, response_time_ms, trace_context, user_id
    )


def track_error(
    endpoint: str,
    error_code: str,
    error_type: str,
    message: str,
    trace_context: TraceContext | None = None,
) -> None:
    """Track error using global collector."""
    collector = get_metrics_collector()
    collector.track_error(endpoint, error_code, error_type, message, trace_context)


def track_performance(
    operation: str,
    duration_ms: int,
    success: bool = True,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Track performance using global collector."""
    collector = get_metrics_collector()
    collector.track_performance(operation, duration_ms, success, metadata)


# Decorator for automatic performance tracking
def track_performance_decorator(
    operation: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to automatically track function performance."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            success = True

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration_ms = int((time.time() - start_time) * 1000)
                track_performance(operation, duration_ms, success)

        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            success = True

            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration_ms = int((time.time() - start_time) * 1000)
                track_performance(operation, duration_ms, success)

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Context manager for performance tracking
class PerformanceTracker:
    """Context manager for tracking operation performance."""

    def __init__(self, operation: str, auto_track: bool = True):
        self.operation = operation
        self.auto_track = auto_track
        self.start_time: float | None = None
        self.success = True

    def __enter__(self) -> "PerformanceTracker":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time is not None and self.auto_track:
            duration_ms = int((time.time() - self.start_time) * 1000)
            success = exc_type is None
            track_performance(self.operation, duration_ms, success)

    def mark_failed(self) -> None:
        """Mark operation as failed."""
        self.success = False

    def get_duration_ms(self) -> int:
        """Get current duration in milliseconds."""
        if self.start_time is None:
            return 0
        return int((time.time() - self.start_time) * 1000)
