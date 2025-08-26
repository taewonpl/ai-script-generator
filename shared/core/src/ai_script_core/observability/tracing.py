"""
Request tracing and distributed tracing support.
"""

import uuid
from datetime import datetime
from typing import Any, Optional, Dict

from pydantic import BaseModel, Field


class TraceHeaders:
    """Standard tracing header names."""

    TRACE_ID = "X-Trace-Id"
    JOB_ID = "X-Job-Id"
    PROJECT_ID = "X-Project-Id"
    USER_ID = "X-User-Id"

    # Response headers
    PROCESSING_TIME = "X-Processing-Time"
    SERVICE = "X-Service"


class TraceContext(BaseModel):
    """Request trace context information."""

    trace_id: str = Field(
        ..., description="Unique trace ID for the entire request flow"
    )
    job_id: Optional[str] = Field(
        default=None, description="Generation job ID if applicable"
    )
    project_id: Optional[str] = Field(default=None, description="Project context ID")
    user_id: Optional[str] = Field(default=None, description="User ID for the request")
    service: Optional[str] = Field(default=None, description="Originating service name")

    # Request metadata
    request_timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_path: Optional[str] = Field(default=None, description="API endpoint path")
    request_method: Optional[str] = Field(default=None, description="HTTP method")

    # Additional context
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional trace metadata"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


def generate_trace_id() -> str:
    """Generate a unique trace ID."""
    return f"trace_{uuid.uuid4().hex[:12]}"


def generate_job_id() -> str:
    """Generate a unique job ID for generation tasks."""
    return f"job_{uuid.uuid4().hex[:10]}"


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req_{uuid.uuid4().hex[:8]}"


def extract_trace_context(
    headers: Dict[str, str], service_name: Optional[str] = None
) -> TraceContext:
    """Extract trace context from HTTP headers."""

    trace_id = headers.get(TraceHeaders.TRACE_ID)
    if not trace_id:
        trace_id = generate_trace_id()

    return TraceContext(
        trace_id=trace_id,
        job_id=headers.get(TraceHeaders.JOB_ID),
        project_id=headers.get(TraceHeaders.PROJECT_ID),
        user_id=headers.get(TraceHeaders.USER_ID),
        service=service_name,
        metadata={
            "source_headers": {
                key: value for key, value in headers.items() if key.startswith("X-")
            }
        },
    )


def inject_trace_headers(
    trace_context: TraceContext, processing_time_ms: Optional[int] = None
) -> dict[str, str]:
    """Inject trace context into HTTP response headers."""

    headers = {
        TraceHeaders.TRACE_ID: trace_context.trace_id,
    }

    if trace_context.job_id:
        headers[TraceHeaders.JOB_ID] = trace_context.job_id

    if trace_context.project_id:
        headers[TraceHeaders.PROJECT_ID] = trace_context.project_id

    if trace_context.service:
        headers[TraceHeaders.SERVICE] = trace_context.service

    if processing_time_ms is not None:
        headers[TraceHeaders.PROCESSING_TIME] = str(processing_time_ms)

    return headers


def create_child_trace_context(
    parent_context: TraceContext, service_name: str, job_id: Optional[str] = None
) -> TraceContext:
    """Create a child trace context for service-to-service calls."""

    return TraceContext(
        trace_id=parent_context.trace_id,  # Keep same trace ID
        job_id=job_id or parent_context.job_id,
        project_id=parent_context.project_id,
        user_id=parent_context.user_id,
        service=service_name,
        metadata={**parent_context.metadata, "parent_service": parent_context.service},
    )


def enrich_trace_context(
    context: TraceContext, **additional_metadata: Any
) -> TraceContext:
    """Add additional metadata to trace context."""

    updated_metadata = {**context.metadata, **additional_metadata}

    return context.model_copy(update={"metadata": updated_metadata})


class TracingMiddleware:
    """Base class for service tracing middleware."""

    def __init__(self, service_name: str):
        self.service_name = service_name

    def extract_context(self, headers: dict[str, str]) -> TraceContext:
        """Extract trace context from request headers."""
        return extract_trace_context(headers, self.service_name)

    def inject_headers(
        self, context: TraceContext, processing_time_ms: Optional[int] = None
    ) -> dict[str, str]:
        """Inject trace headers into response."""
        return inject_trace_headers(context, processing_time_ms)

    def create_child_context(
        self, parent_context: TraceContext, job_id: Optional[str] = None
    ) -> TraceContext:
        """Create child context for downstream calls."""
        return create_child_trace_context(parent_context, self.service_name, job_id)
