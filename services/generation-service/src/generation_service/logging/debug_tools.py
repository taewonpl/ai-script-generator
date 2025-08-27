"""
Debug tools and utilities for development and troubleshooting
"""

import inspect
import sys
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.debug_tools")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)

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


@dataclass
class DebugSession:
    """Debug session for tracking debugging activities"""

    session_id: str
    started_at: datetime
    debug_mode: bool = True
    breakpoints: list[str] = field(default_factory=list)
    watches: dict[str, Any] = field(default_factory=dict)
    call_stack: list[dict[str, Any]] = field(default_factory=list)
    performance_data: dict[str, list[float]] = field(default_factory=dict)


class DebugTools:
    """
    Comprehensive debugging tools and utilities

    Features:
    - Interactive debugging support
    - Performance profiling
    - Call stack tracing
    - Variable watching
    - Memory usage tracking
    - Function timing
    - Debug logging with enhanced details
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        self.config = config or {}

        # Debug configuration
        self.debug_enabled = self.config.get("debug_enabled", False)
        self.profile_enabled = self.config.get("profile_enabled", False)
        self.trace_calls = self.config.get("trace_calls", False)

        # Debug session
        self.current_session: Optional[DebugSession] = None

        # Performance profiling
        self._function_timings: dict[str, list[float]] = {}
        self._call_counts: dict[str, int] = {}

        # Memory tracking
        self._memory_snapshots: list[dict[str, Any]] = []

        # Debugging hooks
        self._breakpoint_handlers: list[Callable] = []
        self._watch_handlers: list[Callable] = []

        # Original trace function (for call tracing)
        self._original_trace_func = None
        self._trace_depth = 0

    def start_debug_session(self, session_id: Optional[str] = None) -> DebugSession:
        """Start new debug session"""

        if not session_id:
            session_id = f"debug_{int(time.time())}"

        self.current_session = DebugSession(
            session_id=session_id,
            started_at=utc_now() if CORE_AVAILABLE else datetime.now(),
            debug_mode=self.debug_enabled,
        )

        if self.trace_calls:
            self._enable_call_tracing()

        logger.info(f"Debug session started: {session_id}")
        return self.current_session

    def stop_debug_session(self) -> Optional[DebugSession]:
        """Stop current debug session"""

        if not self.current_session:
            return None

        if self.trace_calls:
            self._disable_call_tracing()

        session = self.current_session
        self.current_session = None

        logger.info(f"Debug session stopped: {session.session_id}")
        return session

    def _enable_call_tracing(self) -> None:
        """Enable function call tracing"""

        def trace_calls(frame: Any, event: str, arg: Any) -> Callable:
            if event == "call":
                self._trace_depth += 1
                func_name = frame.f_code.co_name
                filename = frame.f_code.co_filename
                lineno = frame.f_lineno

                if self.current_session:
                    call_info = {
                        "function": func_name,
                        "file": filename,
                        "line": lineno,
                        "depth": self._trace_depth,
                        "timestamp": (
                            utc_now() if CORE_AVAILABLE else datetime.now()
                        ).isoformat(),
                    }
                    self.current_session.call_stack.append(call_info)

                # Limit call stack size
                if self.current_session and len(self.current_session.call_stack) > 1000:
                    self.current_session.call_stack = self.current_session.call_stack[
                        -1000:
                    ]

            elif event == "return":
                self._trace_depth = max(0, self._trace_depth - 1)

            return trace_calls

        self._original_trace_func = sys.gettrace()
        sys.settrace(trace_calls)

    def _disable_call_tracing(self) -> None:
        """Disable function call tracing"""

        sys.settrace(self._original_trace_func)
        self._trace_depth = 0

    def add_breakpoint(self, identifier: str) -> None:
        """Add breakpoint for debugging"""

        if self.current_session:
            self.current_session.breakpoints.append(identifier)
            logger.debug(f"Breakpoint added: {identifier}")

    def hit_breakpoint(
        self, identifier: str, locals_dict: Optional[dict[str, Any]] = None
    ) -> None:
        """Handle breakpoint hit"""

        if (
            not self.current_session
            or identifier not in self.current_session.breakpoints
        ):
            return

        logger.info(f"Breakpoint hit: {identifier}")

        # Get caller frame for context
        frame = inspect.currentframe().f_back

        debug_info = {
            "breakpoint": identifier,
            "timestamp": (utc_now() if CORE_AVAILABLE else datetime.now()).isoformat(),
            "file": frame.f_code.co_filename,
            "line": frame.f_lineno,
            "function": frame.f_code.co_name,
            "locals": locals_dict or dict(frame.f_locals),
            "stack_trace": traceback.format_stack(),
        }

        # Call breakpoint handlers
        for handler in self._breakpoint_handlers:
            try:
                handler(debug_info)
            except Exception as e:
                logger.error(f"Breakpoint handler failed: {e}")

    def watch_variable(self, var_name: str, value: Any) -> None:
        """Watch variable value changes"""

        if not self.current_session:
            return

        previous_value = self.current_session.watches.get(var_name)
        self.current_session.watches[var_name] = value

        if previous_value != value:
            logger.debug(
                f"Variable changed: {var_name} = {value} (was: {previous_value})"
            )

            # Call watch handlers
            for handler in self._watch_handlers:
                try:
                    handler(var_name, value, previous_value)
                except Exception as e:
                    logger.error(f"Watch handler failed: {e}")

    def profile_function(self, func: Callable) -> Callable:
        """Decorator for function profiling"""

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.time()
                duration = end_time - start_time

                func_name = f"{func.__module__}.{func.__name__}"

                # Record timing
                if func_name not in self._function_timings:
                    self._function_timings[func_name] = []
                self._function_timings[func_name].append(duration)

                # Record call count
                self._call_counts[func_name] = self._call_counts.get(func_name, 0) + 1

                # Limit stored timings
                if len(self._function_timings[func_name]) > 1000:
                    self._function_timings[func_name] = self._function_timings[
                        func_name
                    ][-1000:]

                # Log performance data
                if self.profile_enabled:
                    logger.debug(
                        f"Function profiling: {func_name} took {duration:.4f}s",
                        extra={
                            "function": func_name,
                            "duration": duration,
                            "success": success,
                            "error": error,
                            "call_count": self._call_counts[func_name],
                        },
                    )

            return result

        return wrapper

    def profile_async_function(self, func: Callable) -> Callable:
        """Decorator for async function profiling"""

        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.time()
                duration = end_time - start_time

                func_name = f"{func.__module__}.{func.__name__}"

                # Record timing
                if func_name not in self._function_timings:
                    self._function_timings[func_name] = []
                self._function_timings[func_name].append(duration)

                # Record call count
                self._call_counts[func_name] = self._call_counts.get(func_name, 0) + 1

                # Limit stored timings
                if len(self._function_timings[func_name]) > 1000:
                    self._function_timings[func_name] = self._function_timings[
                        func_name
                    ][-1000:]

                # Log performance data
                if self.profile_enabled:
                    logger.debug(
                        f"Async function profiling: {func_name} took {duration:.4f}s",
                        extra={
                            "function": func_name,
                            "duration": duration,
                            "success": success,
                            "error": error,
                            "call_count": self._call_counts[func_name],
                        },
                    )

            return result

        return async_wrapper

    def capture_memory_snapshot(self, label: str = "") -> Optional[dict[str, Any]]:
        """Capture current memory usage snapshot"""

        try:
            import psutil

            process = psutil.Process()

            memory_info = {
                "label": label,
                "timestamp": (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ).isoformat(),
                "rss_mb": process.memory_info().rss / 1024 / 1024,
                "vms_mb": process.memory_info().vms / 1024 / 1024,
                "percent": process.memory_percent(),
            }

            # Add Python-specific memory info
            try:
                import tracemalloc

                if tracemalloc.is_tracing():
                    current, peak = tracemalloc.get_traced_memory()
                    memory_info.update(
                        {
                            "traced_current_mb": current / 1024 / 1024,
                            "traced_peak_mb": peak / 1024 / 1024,
                        }
                    )
            except ImportError:
                pass

            self._memory_snapshots.append(memory_info)

            # Limit snapshots
            if len(self._memory_snapshots) > 100:
                self._memory_snapshots = self._memory_snapshots[-100:]

            logger.debug(f"Memory snapshot: {label}", extra=memory_info)

            return memory_info

        except ImportError:
            logger.warning("psutil not available for memory monitoring")
            return None

    def debug_log(self, message: str, level: str = "DEBUG", **kwargs: Any) -> None:
        """Enhanced debug logging with context"""

        if not self.debug_enabled:
            return

        # Get caller information
        frame = inspect.currentframe().f_back
        caller_info = {
            "file": frame.f_code.co_filename,
            "line": frame.f_lineno,
            "function": frame.f_code.co_name,
        }

        # Combine with provided kwargs
        debug_data = {**caller_info, **kwargs}

        # Add session info if available
        if self.current_session:
            debug_data["session_id"] = self.current_session.session_id

        log_func = getattr(logger, level.lower(), logger.debug)
        log_func(f"DEBUG: {message}", extra=debug_data)

    def inspect_object(self, obj: Any, name: str = "object") -> dict[str, Any]:
        """Inspect object and return detailed information"""

        inspection = {
            "name": name,
            "type": type(obj).__name__,
            "module": getattr(type(obj), "__module__", "unknown"),
            "size_bytes": sys.getsizeof(obj),
            "attributes": [],
            "methods": [],
            "properties": [],
        }

        # Get attributes, methods, and properties
        for attr_name in dir(obj):
            try:
                attr_value = getattr(obj, attr_name)

                if callable(attr_value):
                    inspection["methods"].append(
                        {
                            "name": attr_name,
                            "signature": (
                                str(inspect.signature(attr_value))
                                if hasattr(inspect, "signature")
                                else "unknown"
                            ),
                        }
                    )
                elif isinstance(attr_value, property):
                    inspection["properties"].append(attr_name)
                elif not attr_name.startswith("_"):
                    inspection["attributes"].append(
                        {
                            "name": attr_name,
                            "type": type(attr_value).__name__,
                            "value": str(attr_value)[:100],  # Truncate long values
                        }
                    )
            except Exception:
                pass  # Skip attributes that can't be accessed

        if self.debug_enabled:
            logger.debug(f"Object inspection: {name}", extra=inspection)

        return inspection

    def get_function_performance_report(self) -> dict[str, Any]:
        """Get performance report for profiled functions"""

        report = {"total_functions": len(self._function_timings), "functions": {}}

        for func_name, timings in self._function_timings.items():
            if timings:
                stats = {
                    "call_count": self._call_counts.get(func_name, 0),
                    "total_time": sum(timings),
                    "avg_time": sum(timings) / len(timings),
                    "min_time": min(timings),
                    "max_time": max(timings),
                }

                # Calculate percentiles
                if len(timings) > 1:
                    sorted_timings = sorted(timings)
                    n = len(sorted_timings)
                    stats.update(
                        {
                            "p50": sorted_timings[int(n * 0.5)],
                            "p95": sorted_timings[int(n * 0.95)],
                            "p99": sorted_timings[int(n * 0.99)],
                        }
                    )

                report["functions"][func_name] = stats

        return report

    def get_memory_usage_report(self) -> dict[str, Any]:
        """Get memory usage report from snapshots"""

        if not self._memory_snapshots:
            return {"error": "No memory snapshots available"}

        # Calculate memory trends
        rss_values = [s["rss_mb"] for s in self._memory_snapshots]

        report = {
            "total_snapshots": len(self._memory_snapshots),
            "current_rss_mb": rss_values[-1] if rss_values else 0,
            "peak_rss_mb": max(rss_values) if rss_values else 0,
            "min_rss_mb": min(rss_values) if rss_values else 0,
            "avg_rss_mb": sum(rss_values) / len(rss_values) if rss_values else 0,
            "snapshots": self._memory_snapshots[-10:],  # Last 10 snapshots
        }

        # Calculate memory growth trend
        if len(rss_values) > 1:
            growth = rss_values[-1] - rss_values[0]
            report["memory_growth_mb"] = growth
            report["growth_trend"] = (
                "increasing" if growth > 0 else "decreasing" if growth < 0 else "stable"
            )

        return report

    def add_breakpoint_handler(self, handler: Callable) -> None:
        """Add handler for breakpoint events"""
        self._breakpoint_handlers.append(handler)

    def add_watch_handler(self, handler: Callable) -> None:
        """Add handler for variable watch events"""
        self._watch_handlers.append(handler)

    def export_debug_session(self, file_path: str) -> None:
        """Export debug session data to file"""

        if not self.current_session:
            logger.warning("No active debug session to export")
            return

        import json

        session_data = {
            "session_id": self.current_session.session_id,
            "started_at": self.current_session.started_at.isoformat(),
            "debug_mode": self.current_session.debug_mode,
            "breakpoints": self.current_session.breakpoints,
            "watches": self.current_session.watches,
            "call_stack": self.current_session.call_stack[-100:],  # Last 100 calls
            "function_performance": self.get_function_performance_report(),
            "memory_report": self.get_memory_usage_report(),
        }

        with open(file_path, "w") as f:
            json.dump(session_data, f, indent=2)

        logger.info(f"Debug session exported to {file_path}")

    def create_performance_summary(self) -> dict[str, Any]:
        """Create comprehensive performance summary"""

        return {
            "function_performance": self.get_function_performance_report(),
            "memory_usage": self.get_memory_usage_report(),
            "debug_session": {
                "active": self.current_session is not None,
                "session_id": (
                    self.current_session.session_id if self.current_session else None
                ),
                "breakpoints_count": (
                    len(self.current_session.breakpoints) if self.current_session else 0
                ),
                "watches_count": (
                    len(self.current_session.watches) if self.current_session else 0
                ),
            },
        }


# Context managers for debug sections
class DebugSection:
    """Context manager for debug sections with automatic timing"""

    def __init__(self, debug_tools: DebugTools, section_name: str) -> None:
        self.debug_tools = debug_tools
        self.section_name = section_name
        self.start_time = None

    def __enter__(self) -> "DebugSection":
        self.start_time = time.time()
        self.debug_tools.debug_log(f"Entering debug section: {self.section_name}")
        self.debug_tools.capture_memory_snapshot(f"start_{self.section_name}")
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        duration = time.time() - self.start_time
        self.debug_tools.capture_memory_snapshot(f"end_{self.section_name}")

        if exc_type:
            self.debug_tools.debug_log(
                f"Debug section failed: {self.section_name}",
                level="ERROR",
                duration=duration,
                error=str(exc_val),
            )
        else:
            self.debug_tools.debug_log(
                f"Debug section completed: {self.section_name}", duration=duration
            )


# Global debug tools instance
_debug_tools: Optional[DebugTools] = None


def get_debug_tools() -> Optional[DebugTools]:
    """Get global debug tools instance"""
    global _debug_tools
    return _debug_tools


def initialize_debug_tools(config: Optional[dict[str, Any]] = None) -> DebugTools:
    """Initialize global debug tools"""
    global _debug_tools

    _debug_tools = DebugTools(config)
    return _debug_tools


# Convenience functions for debugging
def debug_breakpoint(identifier: str) -> None:
    """Convenience function for hitting breakpoints"""
    debug_tools = get_debug_tools()
    if debug_tools:
        debug_tools.hit_breakpoint(identifier)


def debug_watch(var_name: str, value: Any) -> None:
    """Convenience function for watching variables"""
    debug_tools = get_debug_tools()
    if debug_tools:
        debug_tools.watch_variable(var_name, value)


def debug_profile(func: Callable) -> Callable:
    """Convenience decorator for function profiling"""
    debug_tools = get_debug_tools()
    if debug_tools:
        return debug_tools.profile_function(func)
    return func


def debug_profile_async(func: Callable) -> Callable:
    """Convenience decorator for async function profiling"""
    debug_tools = get_debug_tools()
    if debug_tools:
        return debug_tools.profile_async_function(func)
    return func
