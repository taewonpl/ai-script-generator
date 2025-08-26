"""
Structured logging system with performance tracking and debugging support
"""

import asyncio
import json
import logging
import logging.handlers
import time
import traceback
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List, Union

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.structured_logger")
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


class LogLevel(str, Enum):
    """Log levels"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogContext:
    """Logging context with request/session tracking"""

    request_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    workflow_id: str | None = None
    node_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for logging"""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class LogEntry:
    """Structured log entry"""

    timestamp: datetime
    level: LogLevel
    message: str
    component: str
    context: LogContext
    extra_data: dict[str, Any] = field(default_factory=dict)
    exception: str | None = None
    performance_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "component": self.component,
            "context": self.context.to_dict(),
        }

        if self.extra_data:
            data["extra"] = self.extra_data

        if self.exception:
            data["exception"] = self.exception

        if self.performance_data:
            data["performance"] = self.performance_data

        return data


class StructuredLogger:
    """
    Structured logging system with performance tracking and debugging support

    Features:
    - Structured JSON logging
    - Context-aware logging (request, session, workflow)
    - Performance measurement integration
    - Automatic error tracking
    - Log aggregation and querying
    - Debug mode with enhanced details
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

        # Logger configuration
        self.component_name = self.config.get("component", "generation-service")
        self.log_level = LogLevel(self.config.get("log_level", "info"))
        self.debug_mode = self.config.get("debug_mode", False)

        # File logging configuration
        self.log_file = self.config.get("log_file")
        self.max_file_size = self.config.get(
            "max_file_size", 100 * 1024 * 1024
        )  # 100MB
        self.backup_count = self.config.get("backup_count", 5)

        # Structured logging storage
        self._log_entries: list[LogEntry] = []
        self.max_entries = self.config.get("max_log_entries", 10000)

        # Current context
        self._current_context = LogContext()

        # Performance tracking
        self._performance_timers: dict[str, float] = {}

        # Event handlers
        self._log_handlers: list[Callable[[LogEntry], None]] = []

        # Initialize loggers
        self._setup_loggers()

        # Log buffer for async processing
        self._log_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._log_processor_task: asyncio.Task[None] | None = None
        self._logging_enabled = False

    def _setup_loggers(self) -> None:
        """Setup underlying loggers"""

        # Create structured logger
        self.logger = logging.getLogger(f"{self.component_name}.structured")
        self.logger.setLevel(getattr(logging, self.log_level.value.upper()))

        # Console handler with JSON formatting
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self._get_json_formatter())
        self.logger.addHandler(console_handler)

        # File handler if configured
        if self.log_file:
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
            )
            file_handler.setFormatter(self._get_json_formatter())
            self.logger.addHandler(file_handler)

        # Prevent duplicate logs
        self.logger.propagate = False

    def _get_json_formatter(self) -> logging.Formatter:
        """Get JSON formatter for structured logging"""

        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                # Extract structured data if available
                log_data = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname.lower(),
                    "message": record.getMessage(),
                    "component": record.name,
                }

                # Add extra data if available
                if hasattr(record, "extra_data"):
                    log_data.update(record.extra_data)

                # Add exception info
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)

                return json.dumps(log_data)

        return JSONFormatter()

    async def start_logging(self) -> None:
        """Start async log processing"""

        if self._logging_enabled:
            return

        self._logging_enabled = True
        self._log_processor_task = asyncio.create_task(self._log_processor())

        logger.info("StructuredLogger started")

    async def stop_logging(self) -> None:
        """Stop async log processing"""

        self._logging_enabled = False

        if self._log_processor_task and not self._log_processor_task.done():
            self._log_processor_task.cancel()
            try:
                await self._log_processor_task
            except asyncio.CancelledError:
                pass

        logger.info("StructuredLogger stopped")

    async def _log_processor(self) -> None:
        """Background processor for log entries"""

        while self._logging_enabled:
            try:
                # Process queued log entries
                try:
                    entry = await asyncio.wait_for(self._log_queue.get(), timeout=1.0)
                    await self._process_log_entry(entry)
                except asyncio.TimeoutError:
                    continue

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Log processor error: {e}")

    async def _process_log_entry(self, entry: LogEntry) -> None:
        """Process individual log entry"""

        # Store in memory
        self._log_entries.append(entry)

        # Trim if too many entries
        if len(self._log_entries) > self.max_entries:
            self._log_entries = self._log_entries[-self.max_entries :]

        # Call handlers
        for handler in self._log_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(entry)
                else:
                    handler(entry)
            except Exception as e:
                logger.error(f"Log handler failed: {e}")

        # Log to underlying logger
        log_data = entry.to_dict()

        log_level = getattr(self.logger, entry.level.value)
        log_level(entry.message, extra={"extra_data": log_data})

    def set_context(self, context: LogContext) -> None:
        """Set current logging context"""
        self._current_context = context

    def update_context(self, **kwargs: Any) -> None:
        """Update current context with new values"""
        for key, value in kwargs.items():
            if hasattr(self._current_context, key):
                setattr(self._current_context, key, value)

    def clear_context(self) -> None:
        """Clear current logging context"""
        self._current_context = LogContext()

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message"""
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message"""
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message"""
        self._log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message"""
        self._log(LogLevel.CRITICAL, message, **kwargs)

    def _log(self, level: LogLevel, message: str, **kwargs: Any) -> None:
        """Internal logging method"""

        # Skip if level too low
        if self._should_skip_level(level):
            return

        # Extract special kwargs
        context = kwargs.pop("context", self._current_context)
        extra_data = kwargs.pop("extra", {})
        exception = kwargs.pop("exception", None)
        performance_data = kwargs.pop("performance", None)

        # Add remaining kwargs to extra data
        extra_data.update(kwargs)

        # Handle exception formatting
        if exception and isinstance(exception, Exception):
            exception = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
            exception = "".join(exception)

        # Create log entry
        entry = LogEntry(
            timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
            level=level,
            message=message,
            component=self.component_name,
            context=context,
            extra_data=extra_data,
            exception=exception,
            performance_data=performance_data,
        )

        # Queue for async processing if enabled
        if self._logging_enabled:
            try:
                self._log_queue.put_nowait(entry)
            except asyncio.QueueFull:
                # Fallback to sync processing
                asyncio.create_task(self._process_log_entry(entry))
        else:
            # Sync processing
            asyncio.create_task(self._process_log_entry(entry))

    def _should_skip_level(self, level: LogLevel) -> bool:
        """Check if log level should be skipped"""

        level_priorities = {
            LogLevel.DEBUG: 1,
            LogLevel.INFO: 2,
            LogLevel.WARNING: 3,
            LogLevel.ERROR: 4,
            LogLevel.CRITICAL: 5,
        }

        return level_priorities[level] < level_priorities[self.log_level]

    def start_timer(self, operation_name: str) -> str:
        """Start performance timer"""

        timer_id = f"{operation_name}_{time.time()}"
        self._performance_timers[timer_id] = time.time()

        if self.debug_mode:
            self.debug(f"Started timer: {operation_name}", timer_id=timer_id)

        return timer_id

    def end_timer(self, timer_id: str, operation_name: str = None) -> float:
        """End performance timer and log result"""

        if timer_id not in self._performance_timers:
            self.warning(f"Timer not found: {timer_id}")
            return 0.0

        start_time = self._performance_timers.pop(timer_id)
        duration = time.time() - start_time

        performance_data = {
            "operation": operation_name or "unknown",
            "duration_seconds": duration,
            "timer_id": timer_id,
        }

        self.info(
            f"Operation completed: {operation_name or 'unknown'} in {duration:.3f}s",
            performance=performance_data,
        )

        return duration

    def log_workflow_start(self, workflow_id: str, workflow_type: Optional[str] = None) -> None:
        """Log workflow start"""

        self.update_context(workflow_id=workflow_id)

        self.info(
            f"Workflow started: {workflow_id}",
            workflow_type=workflow_type,
            event_type="workflow_start",
        )

    def log_workflow_end(
        self, workflow_id: str, success: bool = True, error: Optional[str] = None
    ) -> None:
        """Log workflow completion"""

        if success:
            self.info(
                f"Workflow completed: {workflow_id}",
                event_type="workflow_end",
                success=True,
            )
        else:
            self.error(
                f"Workflow failed: {workflow_id}",
                event_type="workflow_end",
                success=False,
                error=error,
            )

    def log_node_execution(
        self,
        node_id: str,
        node_type: str,
        success: bool = True,
        duration: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log workflow node execution"""

        self.update_context(node_id=node_id)

        log_data = {
            "event_type": "node_execution",
            "node_type": node_type,
            "success": success,
        }

        if duration is not None:
            log_data["duration_seconds"] = duration

        if error:
            log_data["error"] = error

        if success:
            self.info(f"Node executed: {node_id} ({node_type})", **log_data)
        else:
            self.error(f"Node failed: {node_id} ({node_type})", **log_data)

    def log_ai_api_call(
        self,
        provider: str,
        model: str,
        tokens_used: Optional[int] = None,
        success: bool = True,
        duration: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log AI API call"""

        log_data = {
            "event_type": "ai_api_call",
            "provider": provider,
            "model": model,
            "success": success,
        }

        if tokens_used is not None:
            log_data["tokens_used"] = tokens_used

        if duration is not None:
            log_data["duration_seconds"] = duration

        if error:
            log_data["error"] = error

        if success:
            self.info(f"AI API call: {provider}/{model}", **log_data)
        else:
            self.error(f"AI API call failed: {provider}/{model}", **log_data)

    def log_cache_operation(
        self, operation: str, cache_key: str, hit: Optional[bool] = None, duration: Optional[float] = None
    ) -> None:
        """Log cache operation"""

        log_data = {
            "event_type": "cache_operation",
            "operation": operation,
            "cache_key": cache_key,
        }

        if hit is not None:
            log_data["cache_hit"] = hit

        if duration is not None:
            log_data["duration_seconds"] = duration

        self.debug(f"Cache {operation}: {cache_key}", **log_data)

    def add_log_handler(self, handler: Callable[[LogEntry], None]) -> None:
        """Add custom log handler"""
        self._log_handlers.append(handler)

    def get_recent_logs(
        self, count: int = 100, level: Optional[LogLevel] = None
    ) -> List[LogEntry]:
        """Get recent log entries"""

        logs = self._log_entries

        if level:
            logs = [entry for entry in logs if entry.level == level]

        return logs[-count:]

    def search_logs(self, query: str, max_results: int = 100) -> List[LogEntry]:
        """Search log entries by message content"""

        results = []
        query_lower = query.lower()

        for entry in self._log_entries:
            if (
                query_lower in entry.message.lower()
                or query_lower in str(entry.extra_data).lower()
            ):
                results.append(entry)

                if len(results) >= max_results:
                    break

        return results

    def get_logs_by_context(self, **context_filters: Any) -> List[LogEntry]:
        """Get logs filtered by context"""

        results = []

        for entry in self._log_entries:
            match = True

            for key, value in context_filters.items():
                context_value = getattr(entry.context, key, None)
                if context_value != value:
                    match = False
                    break

            if match:
                results.append(entry)

        return results

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics from logs"""

        operations = {}

        for entry in self._log_entries:
            if entry.performance_data:
                operation = entry.performance_data.get("operation", "unknown")
                duration = entry.performance_data.get("duration_seconds", 0)

                if operation not in operations:
                    operations[operation] = {
                        "count": 0,
                        "total_duration": 0,
                        "min_duration": float("inf"),
                        "max_duration": 0,
                        "durations": [],
                    }

                op_data = operations[operation]
                op_data["count"] += 1
                op_data["total_duration"] += duration
                op_data["min_duration"] = min(op_data["min_duration"], duration)
                op_data["max_duration"] = max(op_data["max_duration"], duration)
                op_data["durations"].append(duration)

        # Calculate averages
        for operation, data in operations.items():
            if data["count"] > 0:
                data["avg_duration"] = data["total_duration"] / data["count"]

                # Calculate percentiles
                if len(data["durations"]) > 1:
                    sorted_durations = sorted(data["durations"])
                    n = len(sorted_durations)
                    data["p50"] = sorted_durations[int(n * 0.5)]
                    data["p95"] = sorted_durations[int(n * 0.95)]
                    data["p99"] = sorted_durations[int(n * 0.99)]

                # Remove raw durations to save space
                del data["durations"]

        return operations

    def export_logs(self, file_path: str, format_type: str = "json") -> None:
        """Export logs to file"""

        if format_type == "json":
            with open(file_path, "w") as f:
                log_data = [entry.to_dict() for entry in self._log_entries]
                json.dump(log_data, f, indent=2)

        elif format_type == "csv":
            import csv

            with open(file_path, "w", newline="") as f:
                if self._log_entries:
                    fieldnames = ["timestamp", "level", "message", "component"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()

                    for entry in self._log_entries:
                        row = {
                            "timestamp": entry.timestamp.isoformat(),
                            "level": entry.level.value,
                            "message": entry.message,
                            "component": entry.component,
                        }
                        writer.writerow(row)

        self.info(f"Exported {len(self._log_entries)} log entries to {file_path}")


# Context manager for automatic context setting
class LogContextManager:
    """Context manager for temporary logging context"""

    def __init__(self, logger: StructuredLogger, context: LogContext) -> None:
        self.logger = logger
        self.new_context = context
        self.previous_context = None

    def __enter__(self) -> "LogContextManager":
        self.previous_context = self.logger._current_context
        self.logger.set_context(self.new_context)
        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        self.logger.set_context(self.previous_context)


# Context manager for performance timing
class PerformanceTimer:
    """Context manager for automatic performance timing"""

    def __init__(self, logger: StructuredLogger, operation_name: str) -> None:
        self.logger = logger
        self.operation_name = operation_name
        self.timer_id = None

    def __enter__(self) -> "PerformanceTimer":
        self.timer_id = self.logger.start_timer(self.operation_name)
        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        if self.timer_id:
            self.logger.end_timer(self.timer_id, self.operation_name)


# Global structured logger instance
_structured_logger: StructuredLogger | None = None


def get_structured_logger() -> Optional[StructuredLogger]:
    """Get global structured logger instance"""
    global _structured_logger
    return _structured_logger


def initialize_structured_logger(
    config: Optional[Dict[str, Any]] = None,
) -> StructuredLogger:
    """Initialize global structured logger"""
    global _structured_logger

    _structured_logger = StructuredLogger(config)
    return _structured_logger


async def shutdown_structured_logger() -> None:
    """Shutdown global structured logger"""
    global _structured_logger

    if _structured_logger:
        await _structured_logger.stop_logging()
        _structured_logger = None
