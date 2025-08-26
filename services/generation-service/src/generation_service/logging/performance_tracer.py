"""
Performance tracing system for detailed execution analysis
"""

import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, Dict, List, Union

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.performance_tracer")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]

    # Fallback utility functions
    def utc_now() -> datetime:
        """Fallback UTC timestamp"""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)

    def generate_uuid() -> str:
        """Fallback UUID generation"""
        import uuid

        return str(uuid.uuid4())

    def generate_id() -> str:
        """Fallback ID generation"""
        import uuid

        return str(uuid.uuid4())[:8]

    # Fallback base classes
    class BaseDTO:
        """Fallback base DTO class"""

        pass

    class SuccessResponseDTO:
        """Fallback success response DTO"""

        pass

    class ErrorResponseDTO:
        """Fallback error response DTO"""

        pass


class SpanType(str, Enum):
    """Types of trace spans"""

    WORKFLOW = "workflow"
    NODE = "node"
    AI_API = "ai_api"
    CACHE = "cache"
    DATABASE = "database"
    HTTP = "http"
    COMPUTATION = "computation"
    IO = "io"


@dataclass
class TraceContext:
    """Distributed tracing context"""

    trace_id: str
    parent_span_id: str | None = None
    baggage: dict[str, str] = field(default_factory=dict)

    def create_child_context(self, span_id: str) -> "TraceContext":
        """Create child context with new span ID"""
        return TraceContext(
            trace_id=self.trace_id, parent_span_id=span_id, baggage=self.baggage.copy()
        )


@dataclass
class Span:
    """Individual trace span"""

    span_id: str
    trace_id: str
    parent_span_id: str | None
    operation_name: str
    span_type: SpanType
    start_time: datetime
    end_time: datetime | None = None
    duration: float | None = None
    success: bool = True
    error: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def finish(self, error: Optional[Exception] = None) -> None:
        """Finish the span"""
        self.end_time = utc_now() if CORE_AVAILABLE else datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()

        if error:
            self.success = False
            self.error = str(error)
            self.tags["error"] = "true"

    def add_tag(self, key: str, value: str) -> None:
        """Add tag to span"""
        self.tags[key] = value

    def add_log(self, message: str, **kwargs: Any) -> None:
        """Add log entry to span"""
        log_entry = {
            "timestamp": (utc_now() if CORE_AVAILABLE else datetime.now()).isoformat(),
            "message": message,
            **kwargs,
        }
        self.logs.append(log_entry)

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary"""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "span_type": self.span_type.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "success": self.success,
            "error": self.error,
            "tags": self.tags,
            "logs": self.logs,
            "metadata": self.metadata,
        }


@dataclass
class Trace:
    """Complete trace with multiple spans"""

    trace_id: str
    root_span_id: str
    spans: dict[str, Span] = field(default_factory=dict)
    start_time: datetime | None = None
    end_time: datetime | None = None
    total_duration: float | None = None

    def add_span(self, span: Span) -> None:
        """Add span to trace"""
        self.spans[span.span_id] = span

        # Update trace timing
        if not self.start_time or span.start_time < self.start_time:
            self.start_time = span.start_time

        if span.end_time and (not self.end_time or span.end_time > self.end_time):
            self.end_time = span.end_time

        if self.start_time and self.end_time:
            self.total_duration = (self.end_time - self.start_time).total_seconds()

    def get_root_span(self) -> Optional[Span]:
        """Get root span of trace"""
        return self.spans.get(self.root_span_id)

    def get_child_spans(self, parent_span_id: str) -> List[Span]:
        """Get child spans of given parent"""
        return [
            span
            for span in self.spans.values()
            if span.parent_span_id == parent_span_id
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary"""
        return {
            "trace_id": self.trace_id,
            "root_span_id": self.root_span_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration": self.total_duration,
            "spans": [span.to_dict() for span in self.spans.values()],
        }


class PerformanceTracer:
    """
    Distributed tracing system for performance analysis

    Features:
    - Distributed trace tracking
    - Hierarchical span relationships
    - Performance bottleneck identification
    - Async operation tracing
    - Custom span attributes and logs
    - Trace sampling and filtering
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

        # Tracing configuration
        self.enabled = self.config.get("enabled", True)
        self.sample_rate = self.config.get(
            "sample_rate", 1.0
        )  # 100% sampling by default
        self.max_traces = self.config.get("max_traces", 1000)
        self.trace_retention_hours = self.config.get("trace_retention_hours", 24)

        # Trace storage
        self._traces: dict[str, Trace] = {}
        self._active_spans: dict[str, Span] = {}

        # Current context (thread-local alternative)
        self._current_context: TraceContext | None = None
        self._context_stack: list[TraceContext] = []

        # Performance analysis
        self._span_statistics: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_duration": 0.0,
                "min_duration": float("inf"),
                "max_duration": 0.0,
                "error_count": 0,
                "durations": [],
            }
        )

        # Background cleanup
        self._cleanup_task: asyncio.Task | None = None
        self._tracing_enabled = False

    async def start_tracing(self) -> None:
        """Start tracing system"""

        if not self.enabled or self._tracing_enabled:
            return

        self._tracing_enabled = True
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())

        logger.info("PerformanceTracer started")

    async def stop_tracing(self) -> None:
        """Stop tracing system"""

        self._tracing_enabled = False

        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("PerformanceTracer stopped")

    def create_trace(
        self, operation_name: str, span_type: SpanType = SpanType.WORKFLOW
    ) -> Optional[TraceContext]:
        """Create new trace"""

        if not self.enabled or not self._should_sample():
            return None

        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        # Create root span
        root_span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=None,
            operation_name=operation_name,
            span_type=span_type,
            start_time=utc_now() if CORE_AVAILABLE else datetime.now(),
        )

        # Create trace
        trace = Trace(trace_id=trace_id, root_span_id=span_id)
        trace.add_span(root_span)

        # Store trace and span
        self._traces[trace_id] = trace
        self._active_spans[span_id] = root_span

        # Create context
        context = TraceContext(trace_id=trace_id, parent_span_id=span_id)

        logger.debug(f"Created trace: {trace_id} for operation: {operation_name}")

        return context

    def start_span(
        self,
        operation_name: str,
        span_type: SpanType = SpanType.COMPUTATION,
        context: Optional[TraceContext] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Optional[Span]:
        """Start new span"""

        if not self.enabled:
            return None

        # Use provided context or current context
        trace_context = context or self._current_context
        if not trace_context:
            return None

        span_id = str(uuid.uuid4())

        span = Span(
            span_id=span_id,
            trace_id=trace_context.trace_id,
            parent_span_id=trace_context.parent_span_id,
            operation_name=operation_name,
            span_type=span_type,
            start_time=utc_now() if CORE_AVAILABLE else datetime.now(),
            tags=tags or {},
        )

        # Add to trace
        if trace_context.trace_id in self._traces:
            self._traces[trace_context.trace_id].add_span(span)

        self._active_spans[span_id] = span

        logger.debug(f"Started span: {span_id} for operation: {operation_name}")

        return span

    def finish_span(self, span: Span, error: Optional[Exception] = None) -> None:
        """Finish span"""

        if not span:
            return

        span.finish(error)

        # Remove from active spans
        self._active_spans.pop(span.span_id, None)

        # Update statistics
        self._update_span_statistics(span)

        logger.debug(f"Finished span: {span.span_id}, duration: {span.duration:.3f}s")

    def _update_span_statistics(self, span: Span) -> None:
        """Update span statistics for analysis"""

        operation_key = f"{span.span_type.value}:{span.operation_name}"
        stats = self._span_statistics[operation_key]

        stats["count"] += 1
        stats["total_duration"] += span.duration
        stats["min_duration"] = min(stats["min_duration"], span.duration)
        stats["max_duration"] = max(stats["max_duration"], span.duration)

        if not span.success:
            stats["error_count"] += 1

        # Store duration for percentile calculation
        stats["durations"].append(span.duration)

        # Limit stored durations to prevent memory growth
        if len(stats["durations"]) > 1000:
            stats["durations"] = stats["durations"][-1000:]

    def set_current_context(self, context: TraceContext) -> None:
        """Set current trace context"""
        self._current_context = context

    def get_current_context(self) -> Optional[TraceContext]:
        """Get current trace context"""
        return self._current_context

    def push_context(self, context: TraceContext) -> None:
        """Push context to stack"""
        if self._current_context:
            self._context_stack.append(self._current_context)
        self._current_context = context

    def pop_context(self) -> Optional[TraceContext]:
        """Pop context from stack"""
        previous = self._current_context

        if self._context_stack:
            self._current_context = self._context_stack.pop()
        else:
            self._current_context = None

        return previous

    def _should_sample(self) -> bool:
        """Check if trace should be sampled"""
        import random

        return random.random() < self.sample_rate

    async def _cleanup_worker(self) -> None:
        """Background worker for cleaning old traces"""

        while self._tracing_enabled:
            try:
                await asyncio.sleep(3600)  # Cleanup every hour

                cutoff_time = (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ) - timedelta(hours=self.trace_retention_hours)

                # Remove old traces
                to_remove = []
                for trace_id, trace in self._traces.items():
                    if trace.end_time and trace.end_time < cutoff_time:
                        to_remove.append(trace_id)

                for trace_id in to_remove:
                    del self._traces[trace_id]

                # Trim if still too many traces
                if len(self._traces) > self.max_traces:
                    # Keep most recent traces
                    sorted_traces = sorted(
                        self._traces.items(),
                        key=lambda x: x[1].end_time or datetime.min,
                        reverse=True,
                    )

                    self._traces = dict(sorted_traces[: self.max_traces])

                if to_remove:
                    logger.debug(f"Cleaned up {len(to_remove)} old traces")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Trace cleanup worker error: {e}")

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get trace by ID"""
        return self._traces.get(trace_id)

    def get_recent_traces(self, count: int = 100) -> List[Trace]:
        """Get recent traces"""

        sorted_traces = sorted(
            self._traces.values(),
            key=lambda x: x.start_time or datetime.min,
            reverse=True,
        )

        return sorted_traces[:count]

    def get_performance_analysis(self) -> Dict[str, Any]:
        """Get performance analysis from traces"""

        analysis = {
            "total_traces": len(self._traces),
            "active_spans": len(self._active_spans),
            "operations": {},
        }

        # Calculate operation statistics
        for operation_key, stats in self._span_statistics.items():
            if stats["count"] > 0:
                avg_duration = stats["total_duration"] / stats["count"]
                error_rate = stats["error_count"] / stats["count"]

                operation_analysis = {
                    "count": stats["count"],
                    "avg_duration": avg_duration,
                    "min_duration": stats["min_duration"],
                    "max_duration": stats["max_duration"],
                    "error_rate": error_rate,
                    "total_duration": stats["total_duration"],
                }

                # Calculate percentiles
                if len(stats["durations"]) > 1:
                    sorted_durations = sorted(stats["durations"])
                    n = len(sorted_durations)
                    operation_analysis.update(
                        {
                            "p50": sorted_durations[int(n * 0.5)],
                            "p95": sorted_durations[int(n * 0.95)],
                            "p99": sorted_durations[int(n * 0.99)],
                        }
                    )

                analysis["operations"][operation_key] = operation_analysis

        return analysis

    def find_slow_traces(
        self, threshold_seconds: float = 5.0, limit: int = 10
    ) -> List[Trace]:
        """Find traces that exceed duration threshold"""

        slow_traces = [
            trace
            for trace in self._traces.values()
            if trace.total_duration and trace.total_duration > threshold_seconds
        ]

        # Sort by duration (slowest first)
        slow_traces.sort(key=lambda x: x.total_duration or 0, reverse=True)

        return slow_traces[:limit]

    def find_error_traces(self, limit: int = 10) -> List[Trace]:
        """Find traces with errors"""

        error_traces = []

        for trace in self._traces.values():
            has_error = any(not span.success for span in trace.spans.values())
            if has_error:
                error_traces.append(trace)

        # Sort by most recent
        error_traces.sort(key=lambda x: x.start_time or datetime.min, reverse=True)

        return error_traces[:limit]

    def export_traces(self, file_path: str, trace_ids: Optional[List[str]] = None) -> None:
        """Export traces to JSON file"""

        import json

        if trace_ids:
            traces_to_export = [
                self._traces[trace_id].to_dict()
                for trace_id in trace_ids
                if trace_id in self._traces
            ]
        else:
            traces_to_export = [trace.to_dict() for trace in self._traces.values()]

        with open(file_path, "w") as f:
            json.dump(
                {
                    "traces": traces_to_export,
                    "export_time": (
                        utc_now() if CORE_AVAILABLE else datetime.now()
                    ).isoformat(),
                    "total_traces": len(traces_to_export),
                },
                f,
                indent=2,
            )

        logger.info(f"Exported {len(traces_to_export)} traces to {file_path}")


# Context managers for automatic span management
class SpanContext:
    """Context manager for automatic span lifecycle"""

    def __init__(
        self,
        tracer: PerformanceTracer,
        operation_name: str,
        span_type: SpanType = SpanType.COMPUTATION,
        tags: Optional[Dict[str, str]] = None,
    ):
        self.tracer = tracer
        self.operation_name = operation_name
        self.span_type = span_type
        self.tags = tags
        self.span: Optional[Span] = None

    def __enter__(self) -> Optional[Span]:
        self.span = self.tracer.start_span(
            self.operation_name, self.span_type, tags=self.tags
        )
        return self.span

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        if self.span:
            error = exc_val if exc_type else None
            self.tracer.finish_span(self.span, error)


class TraceContextManager:
    """Context manager for trace context"""

    def __init__(self, tracer: PerformanceTracer, context: TraceContext) -> None:
        self.tracer = tracer
        self.context = context
        self.previous_context = None

    def __enter__(self) -> "TraceContextManager":
        self.previous_context = self.tracer.get_current_context()
        self.tracer.set_current_context(self.context)
        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        self.tracer.set_current_context(self.previous_context)


# Global performance tracer instance
_performance_tracer: PerformanceTracer | None = None


def get_performance_tracer() -> Optional[PerformanceTracer]:
    """Get global performance tracer instance"""
    global _performance_tracer
    return _performance_tracer


def initialize_performance_tracer(
    config: Optional[Dict[str, Any]] = None,
) -> PerformanceTracer:
    """Initialize global performance tracer"""
    global _performance_tracer

    _performance_tracer = PerformanceTracer(config)
    return _performance_tracer


async def shutdown_performance_tracer() -> None:
    """Shutdown global performance tracer"""
    global _performance_tracer

    if _performance_tracer:
        await _performance_tracer.stop_tracing()
        _performance_tracer = None
