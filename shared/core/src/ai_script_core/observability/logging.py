"""
Structured logging system for unified log format across all services.
"""

import json
import logging
import sys
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict

from pydantic import BaseModel, Field

from .tracing import TraceContext


class LogLevel(str, Enum):
    """Standard log levels."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ServiceContext(BaseModel):
    """Service context information for logging."""

    service_name: str = Field(..., description="Service name")
    version: str = Field(default="1.0.0", description="Service version")
    instance_id: Optional[str] = Field(default=None, description="Service instance ID")
    environment: str = Field(default="production", description="Deployment environment")


class StructuredLogEntry(BaseModel):
    """Structured log entry format."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: LogLevel = Field(..., description="Log level")
    service: str = Field(..., description="Service name")

    # Tracing information
    trace_id: Optional[str] = Field(default=None, description="Request trace ID")
    job_id: Optional[str] = Field(default=None, description="Job/task ID")
    project_id: Optional[str] = Field(default=None, description="Project context")

    # Log content
    message: str = Field(..., description="Log message")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional log metadata"
    )

    # Performance data
    duration_ms: Optional[int] = Field(
        default=None, description="Operation duration in milliseconds"
    )

    # Error information (if applicable)
    error_code: Optional[str] = Field(default=None, description="Error code")
    error_type: Optional[str] = Field(default=None, description="Error class name")
    stack_trace: Optional[str] = Field(default=None, description="Error stack trace")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


class StructuredLogger:
    """Structured logger with unified format."""

    def __init__(
        self,
        service_context: ServiceContext,
        trace_context: Optional[TraceContext] = None,
    ):
        self.service_context = service_context
        self.trace_context = trace_context

        # Configure Python logger
        self.logger = logging.getLogger(service_context.service_name)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredLogFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _create_log_entry(
        self,
        level: LogLevel,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        error_code: Optional[str] = None,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ) -> StructuredLogEntry:
        """Create a structured log entry."""

        return StructuredLogEntry(
            level=level,
            service=self.service_context.service_name,
            trace_id=self.trace_context.trace_id if self.trace_context else None,
            job_id=self.trace_context.job_id if self.trace_context else None,
            project_id=self.trace_context.project_id if self.trace_context else None,
            message=message,
            metadata={
                **(metadata or {}),
                "service_version": self.service_context.version,
                "environment": self.service_context.environment,
                "instance_id": self.service_context.instance_id,
            },
            duration_ms=duration_ms,
            error_code=error_code,
            error_type=error_type,
            stack_trace=stack_trace,
        )

    def trace(self, message: str, **metadata: Any) -> None:
        """Log trace level message."""
        entry = self._create_log_entry(LogLevel.TRACE, message, metadata)
        self.logger.debug(entry.model_dump_json())

    def debug(self, message: str, **metadata: Any) -> None:
        """Log debug level message."""
        entry = self._create_log_entry(LogLevel.DEBUG, message, metadata)
        self.logger.debug(entry.model_dump_json())

    def info(self, message: str, **metadata: Any) -> None:
        """Log info level message."""
        entry = self._create_log_entry(LogLevel.INFO, message, metadata)
        self.logger.info(entry.model_dump_json())

    def warning(self, message: str, **metadata: Any) -> None:
        """Log warning level message."""
        entry = self._create_log_entry(LogLevel.WARNING, message, metadata)
        self.logger.warning(entry.model_dump_json())

    def error(
        self,
        message: str,
        error_code: Optional[str] = None,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None,
        **metadata: Any,
    ) -> None:
        """Log error level message."""
        entry = self._create_log_entry(
            LogLevel.ERROR,
            message,
            metadata,
            error_code=error_code,
            error_type=error_type,
            stack_trace=stack_trace,
        )
        self.logger.error(entry.model_dump_json())

    def critical(
        self,
        message: str,
        error_code: Optional[str] = None,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None,
        **metadata: Any,
    ) -> None:
        """Log critical level message."""
        entry = self._create_log_entry(
            LogLevel.CRITICAL,
            message,
            metadata,
            error_code=error_code,
            error_type=error_type,
            stack_trace=stack_trace,
        )
        self.logger.critical(entry.model_dump_json())

    def log_performance(
        self, operation: str, duration_ms: int, success: bool = True, **metadata: Any
    ) -> None:
        """Log performance metrics."""
        level = LogLevel.INFO if success else LogLevel.WARNING
        message = f"{operation} completed in {duration_ms}ms"

        entry = self._create_log_entry(
            level,
            message,
            {
                **metadata,
                "operation": operation,
                "success": success,
                "performance": True,
            },
            duration_ms=duration_ms,
        )

        if success:
            self.logger.info(entry.model_dump_json())
        else:
            self.logger.warning(entry.model_dump_json())

    def log_event(self, event_type: str, event_name: str, **metadata: Any) -> None:
        """Log structured events (CRUD, lifecycle, etc)."""
        message = f"{event_type}: {event_name}"

        entry = self._create_log_entry(
            LogLevel.INFO,
            message,
            {
                **metadata,
                "event_type": event_type,
                "event_name": event_name,
                "event": True,
            },
        )

        self.logger.info(entry.model_dump_json())

    def with_context(self, trace_context: TraceContext) -> "StructuredLogger":
        """Create a new logger with updated trace context."""
        return StructuredLogger(self.service_context, trace_context)


class StructuredLogFormatter(logging.Formatter):
    """Custom formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # The record.getMessage() should already be JSON from StructuredLogger
        try:
            # Validate it's JSON
            json.loads(record.getMessage())
            return record.getMessage()
        except (json.JSONDecodeError, AttributeError):
            # Fallback for non-structured logs
            return json.dumps(
                {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "service": record.name,
                    "message": record.getMessage(),
                    "metadata": {
                        "module": record.module,
                        "function": record.funcName,
                        "line": record.lineno,
                    },
                }
            )


def create_service_logger(
    service_name: str,
    version: str = "1.0.0",
    environment: str = "production",
    instance_id: Optional[str] = None,
    trace_context: Optional[TraceContext] = None,
) -> StructuredLogger:
    """Create a structured logger for a service."""

    service_context = ServiceContext(
        service_name=service_name,
        version=version,
        instance_id=instance_id,
        environment=environment,
    )

    return StructuredLogger(service_context, trace_context)


# Convenience functions for common logging patterns


def log_event(
    logger: StructuredLogger, event_type: str, event_name: str, **metadata: Any
) -> None:
    """Log a structured event."""
    logger.log_event(event_type, event_name, **metadata)


def log_error(
    logger: StructuredLogger, error: Exception, context: str, **metadata: Any
) -> None:
    """Log an error with full context."""
    import traceback

    logger.error(
        f"{context}: {error!s}",
        error_code=getattr(error, "code", None),
        error_type=error.__class__.__name__,
        stack_trace=traceback.format_exc(),
        **metadata,
    )


def log_performance(
    logger: StructuredLogger,
    operation: str,
    start_time: datetime,
    success: bool = True,
    **metadata: Any,
) -> None:
    """Log performance metrics."""
    duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    logger.log_performance(operation, duration_ms, success, **metadata)


# Event type constants for consistency
class EventTypes:
    """Standard event types for logging."""

    # CRUD Operations
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

    # Generation Lifecycle
    GENERATION_STARTED = "GENERATION_STARTED"
    GENERATION_PROGRESS = "GENERATION_PROGRESS"
    GENERATION_COMPLETED = "GENERATION_COMPLETED"
    GENERATION_FAILED = "GENERATION_FAILED"
    GENERATION_CANCELLED = "GENERATION_CANCELLED"

    # SSE Events
    SSE_CONNECTION_OPENED = "SSE_CONNECTION_OPENED"
    SSE_CONNECTION_CLOSED = "SSE_CONNECTION_CLOSED"
    SSE_CONNECTION_ERROR = "SSE_CONNECTION_ERROR"
    SSE_MESSAGE_SENT = "SSE_MESSAGE_SENT"

    # API Events
    API_REQUEST_STARTED = "API_REQUEST_STARTED"
    API_REQUEST_COMPLETED = "API_REQUEST_COMPLETED"
    API_REQUEST_FAILED = "API_REQUEST_FAILED"

    # System Events
    SERVICE_STARTED = "SERVICE_STARTED"
    SERVICE_STOPPED = "SERVICE_STOPPED"
    HEALTH_CHECK = "HEALTH_CHECK"
