"""
Standardized event logging for critical application events.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .logging import EventTypes, StructuredLogger
from .tracing import TraceContext


class EventSeverity(str, Enum):
    """Event severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApplicationEvent(BaseModel):
    """Standardized application event."""

    event_type: str = Field(..., description="Event type identifier")
    event_name: str = Field(..., description="Human-readable event name")
    severity: EventSeverity = Field(
        default=EventSeverity.MEDIUM, description="Event severity"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )

    # Context information
    service: str = Field(..., description="Service name")
    trace_id: str | None = Field(default=None, description="Request trace ID")
    job_id: str | None = Field(default=None, description="Job/task ID")
    project_id: str | None = Field(default=None, description="Project context")
    user_id: str | None = Field(default=None, description="User ID")

    # Event data
    metadata: dict[str, Any] = Field(default_factory=dict, description="Event metadata")
    duration_ms: int | None = Field(default=None, description="Operation duration")

    # Error information (if applicable)
    error_code: str | None = Field(default=None, description="Error code")
    error_message: str | None = Field(default=None, description="Error message")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


class EventLogger:
    """Centralized event logging system."""

    def __init__(
        self,
        logger: StructuredLogger,
        service_name: str,
        trace_context: TraceContext | None = None,
    ):
        self.logger = logger
        self.service_name = service_name
        self.trace_context = trace_context

    def log_event(
        self,
        event_type: str,
        event_name: str,
        severity: EventSeverity = EventSeverity.MEDIUM,
        metadata: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Log a standardized application event."""

        event = ApplicationEvent(
            event_type=event_type,
            event_name=event_name,
            severity=severity,
            service=self.service_name,
            trace_id=self.trace_context.trace_id if self.trace_context else None,
            job_id=self.trace_context.job_id if self.trace_context else None,
            project_id=self.trace_context.project_id if self.trace_context else None,
            user_id=self.trace_context.user_id if self.trace_context else None,
            metadata=metadata or {},
            duration_ms=duration_ms,
            error_code=error_code,
            error_message=error_message,
        )

        # Log with appropriate level based on severity
        log_message = f"[{event_type}] {event_name}"
        log_metadata = event.model_dump()

        if severity == EventSeverity.CRITICAL:
            self.logger.critical(log_message, **log_metadata)
        elif severity == EventSeverity.HIGH:
            self.logger.error(log_message, **log_metadata)
        elif severity == EventSeverity.MEDIUM:
            self.logger.warning(log_message, **log_metadata)
        else:  # LOW
            self.logger.info(log_message, **log_metadata)

    # Episode lifecycle events
    def log_episode_created(
        self,
        project_id: str,
        episode_id: str,
        episode_number: int,
        title: str,
        duration_ms: int | None = None,
    ) -> None:
        """Log episode creation event."""
        self.log_event(
            event_type=EventTypes.CREATE,
            event_name="Episode Created",
            severity=EventSeverity.MEDIUM,
            metadata={
                "resource_type": "episode",
                "project_id": project_id,
                "episode_id": episode_id,
                "episode_number": episode_number,
                "title": title,
            },
            duration_ms=duration_ms,
        )

    def log_episode_updated(
        self,
        project_id: str,
        episode_id: str,
        changes: dict[str, Any],
        duration_ms: int | None = None,
    ) -> None:
        """Log episode update event."""
        self.log_event(
            event_type=EventTypes.UPDATE,
            event_name="Episode Updated",
            severity=EventSeverity.LOW,
            metadata={
                "resource_type": "episode",
                "project_id": project_id,
                "episode_id": episode_id,
                "changes": changes,
            },
            duration_ms=duration_ms,
        )

    def log_episode_deleted(
        self,
        project_id: str,
        episode_id: str,
        episode_number: int,
        duration_ms: int | None = None,
    ) -> None:
        """Log episode deletion event."""
        self.log_event(
            event_type=EventTypes.DELETE,
            event_name="Episode Deleted",
            severity=EventSeverity.HIGH,
            metadata={
                "resource_type": "episode",
                "project_id": project_id,
                "episode_id": episode_id,
                "episode_number": episode_number,
            },
            duration_ms=duration_ms,
        )

    # Generation lifecycle events
    def log_generation_started(
        self,
        generation_id: str,
        project_id: str,
        episode_id: str,
        model: str,
        prompt_length: int,
    ) -> None:
        """Log generation start event."""
        self.log_event(
            event_type=EventTypes.GENERATION_STARTED,
            event_name="Generation Started",
            severity=EventSeverity.MEDIUM,
            metadata={
                "generation_id": generation_id,
                "project_id": project_id,
                "episode_id": episode_id,
                "model": model,
                "prompt_length": prompt_length,
            },
        )

    def log_generation_progress(
        self,
        generation_id: str,
        progress_percentage: float,
        current_step: str,
        estimated_remaining_ms: int | None = None,
    ) -> None:
        """Log generation progress event."""
        self.log_event(
            event_type=EventTypes.GENERATION_PROGRESS,
            event_name="Generation Progress",
            severity=EventSeverity.LOW,
            metadata={
                "generation_id": generation_id,
                "progress_percentage": progress_percentage,
                "current_step": current_step,
                "estimated_remaining_ms": estimated_remaining_ms,
            },
        )

    def log_generation_completed(
        self,
        generation_id: str,
        output_length: int,
        total_tokens: int,
        duration_ms: int,
        cost_estimate: float | None = None,
    ) -> None:
        """Log generation completion event."""
        self.log_event(
            event_type=EventTypes.GENERATION_COMPLETED,
            event_name="Generation Completed",
            severity=EventSeverity.MEDIUM,
            metadata={
                "generation_id": generation_id,
                "output_length": output_length,
                "total_tokens": total_tokens,
                "cost_estimate": cost_estimate,
            },
            duration_ms=duration_ms,
        )

    def log_generation_failed(
        self,
        generation_id: str,
        error_code: str,
        error_message: str,
        duration_ms: int,
        retry_count: int = 0,
    ) -> None:
        """Log generation failure event."""
        self.log_event(
            event_type=EventTypes.GENERATION_FAILED,
            event_name="Generation Failed",
            severity=EventSeverity.HIGH,
            metadata={
                "generation_id": generation_id,
                "retry_count": retry_count,
            },
            duration_ms=duration_ms,
            error_code=error_code,
            error_message=error_message,
        )

    def log_generation_cancelled(
        self, generation_id: str, reason: str, duration_ms: int
    ) -> None:
        """Log generation cancellation event."""
        self.log_event(
            event_type=EventTypes.GENERATION_CANCELLED,
            event_name="Generation Cancelled",
            severity=EventSeverity.MEDIUM,
            metadata={
                "generation_id": generation_id,
                "reason": reason,
            },
            duration_ms=duration_ms,
        )

    # SSE connection events
    def log_sse_connection_opened(
        self, client_id: str, endpoint: str, user_agent: str | None = None
    ) -> None:
        """Log SSE connection opened event."""
        self.log_event(
            event_type=EventTypes.SSE_CONNECTION_OPENED,
            event_name="SSE Connection Opened",
            severity=EventSeverity.LOW,
            metadata={
                "client_id": client_id,
                "endpoint": endpoint,
                "user_agent": user_agent,
            },
        )

    def log_sse_connection_closed(
        self, client_id: str, duration_ms: int, reason: str = "normal"
    ) -> None:
        """Log SSE connection closed event."""
        self.log_event(
            event_type=EventTypes.SSE_CONNECTION_CLOSED,
            event_name="SSE Connection Closed",
            severity=EventSeverity.LOW,
            metadata={
                "client_id": client_id,
                "reason": reason,
            },
            duration_ms=duration_ms,
        )

    def log_sse_connection_error(
        self, client_id: str, error_code: str, error_message: str
    ) -> None:
        """Log SSE connection error event."""
        self.log_event(
            event_type=EventTypes.SSE_CONNECTION_ERROR,
            event_name="SSE Connection Error",
            severity=EventSeverity.HIGH,
            metadata={
                "client_id": client_id,
            },
            error_code=error_code,
            error_message=error_message,
        )

    def log_sse_message_sent(
        self, client_id: str, message_type: str, message_size: int
    ) -> None:
        """Log SSE message sent event."""
        self.log_event(
            event_type=EventTypes.SSE_MESSAGE_SENT,
            event_name="SSE Message Sent",
            severity=EventSeverity.LOW,
            metadata={
                "client_id": client_id,
                "message_type": message_type,
                "message_size": message_size,
            },
        )

    # API request events
    def log_api_request_started(
        self,
        method: str,
        endpoint: str,
        request_size: int | None = None,
        client_ip: str | None = None,
    ) -> None:
        """Log API request started event."""
        self.log_event(
            event_type=EventTypes.API_REQUEST_STARTED,
            event_name="API Request Started",
            severity=EventSeverity.LOW,
            metadata={
                "method": method,
                "endpoint": endpoint,
                "request_size": request_size,
                "client_ip": client_ip,
            },
        )

    def log_api_request_completed(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        response_size: int,
        duration_ms: int,
    ) -> None:
        """Log API request completed event."""
        severity = EventSeverity.LOW
        if status_code >= 500:
            severity = EventSeverity.HIGH
        elif status_code >= 400:
            severity = EventSeverity.MEDIUM

        self.log_event(
            event_type=EventTypes.API_REQUEST_COMPLETED,
            event_name="API Request Completed",
            severity=severity,
            metadata={
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "response_size": response_size,
            },
            duration_ms=duration_ms,
        )

    def log_api_request_failed(
        self,
        method: str,
        endpoint: str,
        error_code: str,
        error_message: str,
        duration_ms: int,
    ) -> None:
        """Log API request failed event."""
        self.log_event(
            event_type=EventTypes.API_REQUEST_FAILED,
            event_name="API Request Failed",
            severity=EventSeverity.HIGH,
            metadata={
                "method": method,
                "endpoint": endpoint,
            },
            duration_ms=duration_ms,
            error_code=error_code,
            error_message=error_message,
        )

    # System events
    def log_service_started(self, version: str, port: int) -> None:
        """Log service started event."""
        self.log_event(
            event_type=EventTypes.SERVICE_STARTED,
            event_name="Service Started",
            severity=EventSeverity.HIGH,
            metadata={
                "version": version,
                "port": port,
            },
        )

    def log_service_stopped(self, uptime_ms: int) -> None:
        """Log service stopped event."""
        self.log_event(
            event_type=EventTypes.SERVICE_STOPPED,
            event_name="Service Stopped",
            severity=EventSeverity.HIGH,
            metadata={
                "uptime_ms": uptime_ms,
            },
        )

    def log_health_check(
        self,
        status: str,
        dependencies_healthy: int,
        dependencies_total: int,
        response_time_ms: int,
    ) -> None:
        """Log health check event."""
        severity = EventSeverity.LOW
        if status == "unhealthy":
            severity = EventSeverity.HIGH
        elif status == "degraded":
            severity = EventSeverity.MEDIUM

        self.log_event(
            event_type=EventTypes.HEALTH_CHECK,
            event_name="Health Check",
            severity=severity,
            metadata={
                "status": status,
                "dependencies_healthy": dependencies_healthy,
                "dependencies_total": dependencies_total,
            },
            duration_ms=response_time_ms,
        )


# Convenience functions for common event patterns
def create_event_logger(
    structured_logger: StructuredLogger,
    service_name: str,
    trace_context: TraceContext | None = None,
) -> EventLogger:
    """Create an event logger instance."""
    return EventLogger(structured_logger, service_name, trace_context)


def log_resource_lifecycle_event(
    event_logger: EventLogger,
    resource_type: str,
    resource_id: str,
    action: str,
    metadata: dict[str, Any] | None = None,
    duration_ms: int | None = None,
) -> None:
    """Log generic resource lifecycle event."""
    event_type_map = {
        "created": EventTypes.CREATE,
        "updated": EventTypes.UPDATE,
        "deleted": EventTypes.DELETE,
        "read": EventTypes.READ,
    }

    event_type = event_type_map.get(action.lower(), action.upper())
    event_name = f"{resource_type.title()} {action.title()}"

    severity = EventSeverity.MEDIUM
    if action.lower() == "deleted":
        severity = EventSeverity.HIGH
    elif action.lower() in ["read"]:
        severity = EventSeverity.LOW

    combined_metadata = {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "action": action,
        **(metadata or {}),
    }

    event_logger.log_event(
        event_type=event_type,
        event_name=event_name,
        severity=severity,
        metadata=combined_metadata,
        duration_ms=duration_ms,
    )


def log_integration_event(
    event_logger: EventLogger,
    integration_name: str,
    action: str,
    success: bool,
    duration_ms: int,
    metadata: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    """Log external integration event."""
    event_name = f"{integration_name} {action.title()}"
    severity = EventSeverity.LOW if success else EventSeverity.HIGH

    combined_metadata = {
        "integration": integration_name,
        "action": action,
        "success": success,
        **(metadata or {}),
    }

    event_logger.log_event(
        event_type="INTEGRATION",
        event_name=event_name,
        severity=severity,
        metadata=combined_metadata,
        duration_ms=duration_ms,
        error_message=error_message if not success else None,
    )
