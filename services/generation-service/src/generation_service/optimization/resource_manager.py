"""
Resource management and monitoring for Generation Service
"""

import asyncio
import gc
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.resource_manager")
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


class ResourceLevel(str, Enum):
    """Resource usage levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Resource alert types"""

    MEMORY_HIGH = "memory_high"
    MEMORY_CRITICAL = "memory_critical"
    CPU_HIGH = "cpu_high"
    DISK_HIGH = "disk_high"
    CONNECTION_LIMIT = "connection_limit"
    TASK_QUEUE_FULL = "task_queue_full"


@dataclass
class ResourceMetrics:
    """System resource metrics"""

    timestamp: datetime
    memory_used: float  # in MB
    memory_percent: float
    memory_available: float  # in MB
    cpu_percent: float
    disk_used: float  # in GB
    disk_percent: float
    disk_available: float  # in GB
    process_count: int
    thread_count: int
    open_files: int
    network_connections: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "memory_used_mb": self.memory_used,
            "memory_percent": self.memory_percent,
            "memory_available_mb": self.memory_available,
            "cpu_percent": self.cpu_percent,
            "disk_used_gb": self.disk_used,
            "disk_percent": self.disk_percent,
            "disk_available_gb": self.disk_available,
            "process_count": self.process_count,
            "thread_count": self.thread_count,
            "open_files": self.open_files,
            "network_connections": self.network_connections,
        }


@dataclass
class ResourceLimits:
    """Resource usage limits and thresholds"""

    memory_limit_mb: float | None = 2048  # 2GB
    memory_warning_percent: float = 80.0
    memory_critical_percent: float = 90.0
    cpu_warning_percent: float = 80.0
    cpu_critical_percent: float = 95.0
    disk_warning_percent: float = 80.0
    disk_critical_percent: float = 90.0
    max_connections: int = 1000
    max_open_files: int = 1024


@dataclass
class ResourceAlert:
    """Resource usage alert"""

    alert_type: AlertType
    level: ResourceLevel
    message: str
    current_value: float
    threshold: float
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryMonitor:
    """
    Memory usage monitoring and optimization

    Features:
    - Real-time memory tracking
    - Automatic garbage collection
    - Memory leak detection
    - Process memory limits
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

        self.limits = ResourceLimits(
            memory_limit_mb=self.config.get("memory_limit_mb", 2048),
            memory_warning_percent=self.config.get("memory_warning_percent", 80.0),
            memory_critical_percent=self.config.get("memory_critical_percent", 90.0),
        )

        # Memory tracking
        self.peak_memory = 0.0
        self.memory_history: list[tuple[datetime, float]] = []
        self.max_history_size = self.config.get("max_history_size", 1000)

        # GC optimization
        self.gc_threshold = self.config.get(
            "gc_threshold_mb", 100
        )  # MB increase before GC
        self.last_gc_memory = 0.0
        self.auto_gc_enabled = self.config.get("auto_gc_enabled", True)

        # Alerts
        self.alert_callbacks: list[Callable[[ResourceAlert], None]] = []
        self.last_alert_time: dict[AlertType, datetime] = {}
        self.alert_cooldown = timedelta(minutes=5)

    def get_current_memory(self) -> dict[str, float]:
        """Get current memory usage"""

        if PSUTIL_AVAILABLE:
            # System memory
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()

            return {
                "system_total_mb": memory.total / 1024 / 1024,
                "system_available_mb": memory.available / 1024 / 1024,
                "system_used_percent": memory.percent,
                "process_rss_mb": process_memory.rss / 1024 / 1024,
                "process_vms_mb": process_memory.vms / 1024 / 1024,
                "process_percent": process.memory_percent(),
            }
        else:
            # Fallback to basic memory info
            import tracemalloc

            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                return {
                    "process_traced_mb": current / 1024 / 1024,
                    "process_peak_mb": peak / 1024 / 1024,
                }
            else:
                return {"available": False}

    def check_memory_limits(self) -> list[ResourceAlert]:
        """Check if memory usage exceeds limits"""

        alerts = []
        memory_info = self.get_current_memory()

        if not memory_info.get("available", True):
            return alerts

        current_mb = memory_info.get("process_rss_mb", 0)
        system_percent = memory_info.get("system_used_percent", 0)

        # Update peak memory
        if current_mb > self.peak_memory:
            self.peak_memory = current_mb

        # Add to history
        now = utc_now() if CORE_AVAILABLE else datetime.now()
        self.memory_history.append((now, current_mb))

        # Trim history
        if len(self.memory_history) > self.max_history_size:
            self.memory_history = self.memory_history[-self.max_history_size :]

        # Check process memory limit
        if self.limits.memory_limit_mb and current_mb > self.limits.memory_limit_mb:
            alert = ResourceAlert(
                alert_type=AlertType.MEMORY_CRITICAL,
                level=ResourceLevel.CRITICAL,
                message=f"Process memory usage {current_mb:.1f}MB exceeds limit {self.limits.memory_limit_mb}MB",
                current_value=current_mb,
                threshold=self.limits.memory_limit_mb,
                timestamp=now,
            )
            alerts.append(alert)

        # Check system memory percentage
        elif system_percent > self.limits.memory_critical_percent:
            alert = ResourceAlert(
                alert_type=AlertType.MEMORY_CRITICAL,
                level=ResourceLevel.CRITICAL,
                message=f"System memory usage {system_percent:.1f}% exceeds critical threshold {self.limits.memory_critical_percent}%",
                current_value=system_percent,
                threshold=self.limits.memory_critical_percent,
                timestamp=now,
            )
            alerts.append(alert)

        elif system_percent > self.limits.memory_warning_percent:
            alert = ResourceAlert(
                alert_type=AlertType.MEMORY_HIGH,
                level=ResourceLevel.HIGH,
                message=f"System memory usage {system_percent:.1f}% exceeds warning threshold {self.limits.memory_warning_percent}%",
                current_value=system_percent,
                threshold=self.limits.memory_warning_percent,
                timestamp=now,
            )
            alerts.append(alert)

        # Trigger automatic GC if needed
        if self.auto_gc_enabled and self._should_trigger_gc(current_mb):
            self._trigger_garbage_collection()

        return alerts

    def _should_trigger_gc(self, current_mb: float) -> bool:
        """Check if garbage collection should be triggered"""

        if self.last_gc_memory == 0:
            self.last_gc_memory = current_mb
            return False

        memory_increase = current_mb - self.last_gc_memory
        return memory_increase > self.gc_threshold

    def _trigger_garbage_collection(self) -> None:
        """Trigger garbage collection and update tracking"""

        before_mb = self.get_current_memory().get("process_rss_mb", 0)

        # Force garbage collection
        collected = gc.collect()

        after_mb = self.get_current_memory().get("process_rss_mb", 0)
        freed_mb = before_mb - after_mb

        self.last_gc_memory = after_mb

        logger.info(
            "Garbage collection triggered",
            extra={
                "objects_collected": collected,
                "memory_before_mb": before_mb,
                "memory_after_mb": after_mb,
                "memory_freed_mb": freed_mb,
            },
        )

    def get_memory_stats(self) -> dict[str, Any]:
        """Get comprehensive memory statistics"""

        current_memory = self.get_current_memory()

        stats = {
            "current": current_memory,
            "peak_memory_mb": self.peak_memory,
            "gc_stats": {
                "counts": gc.get_count(),
                "thresholds": gc.get_threshold(),
                "last_gc_memory_mb": self.last_gc_memory,
            },
        }

        # Add memory trend if we have history
        if len(self.memory_history) > 1:
            recent_points = self.memory_history[-10:]  # Last 10 readings
            trend = self._calculate_memory_trend(recent_points)
            stats["trend"] = trend

        return stats

    def _calculate_memory_trend(
        self, points: list[tuple[datetime, float]]
    ) -> dict[str, Any]:
        """Calculate memory usage trend"""

        if len(points) < 2:
            return {"direction": "stable", "rate_mb_per_minute": 0.0}

        # Simple linear trend calculation
        first_time, first_memory = points[0]
        last_time, last_memory = points[-1]

        time_diff = (last_time - first_time).total_seconds() / 60.0  # minutes
        memory_diff = last_memory - first_memory

        if time_diff > 0:
            rate = memory_diff / time_diff

            if rate > 1.0:
                direction = "increasing"
            elif rate < -1.0:
                direction = "decreasing"
            else:
                direction = "stable"

            return {
                "direction": direction,
                "rate_mb_per_minute": rate,
                "total_change_mb": memory_diff,
                "time_span_minutes": time_diff,
            }

        return {"direction": "stable", "rate_mb_per_minute": 0.0}

    def add_alert_callback(self, callback: Callable[[ResourceAlert], None]) -> None:
        """Add callback for memory alerts"""
        self.alert_callbacks.append(callback)

    def _send_alerts(self, alerts: list[ResourceAlert]) -> None:
        """Send alerts to registered callbacks"""

        for alert in alerts:
            # Check cooldown
            last_alert = self.last_alert_time.get(alert.alert_type)
            if last_alert and (alert.timestamp - last_alert) < self.alert_cooldown:
                continue

            self.last_alert_time[alert.alert_type] = alert.timestamp

            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")


class ResourceManager:
    """
    Comprehensive resource management and monitoring system

    Features:
    - Memory, CPU, disk, and network monitoring
    - Resource limit enforcement
    - Automated cleanup and optimization
    - Performance alerts and notifications
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

        # Resource limits
        self.limits = ResourceLimits(**self.config.get("limits", {}))

        # Monitoring components
        self.memory_monitor = MemoryMonitor(self.config.get("memory", {}))

        # Monitoring state
        self.monitoring_enabled = False
        self.monitoring_interval = self.config.get(
            "monitoring_interval", 30.0
        )  # seconds
        self.monitoring_task: asyncio.Task | None = None

        # Metrics history
        self.metrics_history: list[ResourceMetrics] = []
        self.max_history_size = self.config.get("max_history_size", 1000)

        # Alert management
        self.alert_callbacks: list[Callable[[ResourceAlert], None]] = []
        self.alert_history: list[ResourceAlert] = []

        # Cleanup configuration
        self.auto_cleanup_enabled = self.config.get("auto_cleanup_enabled", True)
        self.cleanup_interval = self.config.get("cleanup_interval", 300.0)  # 5 minutes
        self.cleanup_task: asyncio.Task | None = None

    async def start_monitoring(self) -> None:
        """Start resource monitoring"""

        if self.monitoring_enabled:
            return

        self.monitoring_enabled = True
        self.monitoring_task = asyncio.create_task(self._monitoring_worker())

        if self.auto_cleanup_enabled:
            self.cleanup_task = asyncio.create_task(self._cleanup_worker())

        logger.info(
            "ResourceManager monitoring started",
            extra={
                "monitoring_interval": self.monitoring_interval,
                "auto_cleanup": self.auto_cleanup_enabled,
            },
        )

    async def stop_monitoring(self) -> None:
        """Stop resource monitoring"""

        self.monitoring_enabled = False

        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("ResourceManager monitoring stopped")

    def get_current_metrics(self) -> ResourceMetrics:
        """Get current system resource metrics"""

        now = utc_now() if CORE_AVAILABLE else datetime.now()

        if PSUTIL_AVAILABLE:
            try:
                # Memory metrics
                memory = psutil.virtual_memory()

                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=None)

                # Disk metrics
                disk = psutil.disk_usage("/")

                # Process metrics
                process = psutil.Process()

                return ResourceMetrics(
                    timestamp=now,
                    memory_used=memory.used / 1024 / 1024,
                    memory_percent=memory.percent,
                    memory_available=memory.available / 1024 / 1024,
                    cpu_percent=cpu_percent,
                    disk_used=disk.used / 1024 / 1024 / 1024,
                    disk_percent=(disk.used / disk.total) * 100,
                    disk_available=disk.free / 1024 / 1024 / 1024,
                    process_count=len(psutil.pids()),
                    thread_count=process.num_threads(),
                    open_files=len(process.open_files()),
                    network_connections=len(process.connections()),
                )

            except Exception as e:
                logger.error(f"Failed to get system metrics: {e}")

        # Fallback metrics
        return ResourceMetrics(
            timestamp=now,
            memory_used=0.0,
            memory_percent=0.0,
            memory_available=0.0,
            cpu_percent=0.0,
            disk_used=0.0,
            disk_percent=0.0,
            disk_available=0.0,
            process_count=0,
            thread_count=0,
            open_files=0,
            network_connections=0,
        )

    def check_resource_limits(self, metrics: ResourceMetrics) -> list[ResourceAlert]:
        """Check if current metrics exceed resource limits"""

        alerts = []

        # Memory alerts
        memory_alerts = self.memory_monitor.check_memory_limits()
        alerts.extend(memory_alerts)

        # CPU alerts
        if metrics.cpu_percent > self.limits.cpu_critical_percent:
            alert = ResourceAlert(
                alert_type=AlertType.CPU_HIGH,
                level=ResourceLevel.CRITICAL,
                message=f"CPU usage {metrics.cpu_percent:.1f}% exceeds critical threshold {self.limits.cpu_critical_percent}%",
                current_value=metrics.cpu_percent,
                threshold=self.limits.cpu_critical_percent,
                timestamp=metrics.timestamp,
            )
            alerts.append(alert)

        elif metrics.cpu_percent > self.limits.cpu_warning_percent:
            alert = ResourceAlert(
                alert_type=AlertType.CPU_HIGH,
                level=ResourceLevel.HIGH,
                message=f"CPU usage {metrics.cpu_percent:.1f}% exceeds warning threshold {self.limits.cpu_warning_percent}%",
                current_value=metrics.cpu_percent,
                threshold=self.limits.cpu_warning_percent,
                timestamp=metrics.timestamp,
            )
            alerts.append(alert)

        # Disk alerts
        if metrics.disk_percent > self.limits.disk_critical_percent:
            alert = ResourceAlert(
                alert_type=AlertType.DISK_HIGH,
                level=ResourceLevel.CRITICAL,
                message=f"Disk usage {metrics.disk_percent:.1f}% exceeds critical threshold {self.limits.disk_critical_percent}%",
                current_value=metrics.disk_percent,
                threshold=self.limits.disk_critical_percent,
                timestamp=metrics.timestamp,
            )
            alerts.append(alert)

        elif metrics.disk_percent > self.limits.disk_warning_percent:
            alert = ResourceAlert(
                alert_type=AlertType.DISK_HIGH,
                level=ResourceLevel.HIGH,
                message=f"Disk usage {metrics.disk_percent:.1f}% exceeds warning threshold {self.limits.disk_warning_percent}%",
                current_value=metrics.disk_percent,
                threshold=self.limits.disk_warning_percent,
                timestamp=metrics.timestamp,
            )
            alerts.append(alert)

        # Connection limits
        if metrics.network_connections > self.limits.max_connections:
            alert = ResourceAlert(
                alert_type=AlertType.CONNECTION_LIMIT,
                level=ResourceLevel.HIGH,
                message=f"Network connections {metrics.network_connections} exceeds limit {self.limits.max_connections}",
                current_value=metrics.network_connections,
                threshold=self.limits.max_connections,
                timestamp=metrics.timestamp,
            )
            alerts.append(alert)

        return alerts

    async def _monitoring_worker(self) -> None:
        """Background worker for resource monitoring"""

        while self.monitoring_enabled:
            try:
                # Get current metrics
                metrics = self.get_current_metrics()

                # Add to history
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > self.max_history_size:
                    self.metrics_history = self.metrics_history[
                        -self.max_history_size :
                    ]

                # Check limits and generate alerts
                alerts = self.check_resource_limits(metrics)

                # Send alerts
                if alerts:
                    self.alert_history.extend(alerts)
                    await self._send_alerts(alerts)

                # Wait for next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring worker error: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _cleanup_worker(self) -> None:
        """Background worker for resource cleanup"""

        while self.monitoring_enabled:
            try:
                await asyncio.sleep(self.cleanup_interval)

                # Perform cleanup operations
                await self.optimize_resources()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")

    async def optimize_resources(self) -> dict[str, Any]:
        """Optimize resource usage"""

        optimization_results = {
            "actions_taken": [],
            "memory_freed_mb": 0.0,
            "files_cleaned": 0,
            "connections_closed": 0,
        }

        try:
            # Memory optimization
            before_memory = self.memory_monitor.get_current_memory().get(
                "process_rss_mb", 0
            )
            self.memory_monitor._trigger_garbage_collection()
            after_memory = self.memory_monitor.get_current_memory().get(
                "process_rss_mb", 0
            )

            memory_freed = max(0, before_memory - after_memory)
            optimization_results["memory_freed_mb"] = memory_freed
            optimization_results["actions_taken"].append("garbage_collection")

            # Cleanup old metrics history if too large
            if len(self.metrics_history) > self.max_history_size:
                old_size = len(self.metrics_history)
                self.metrics_history = self.metrics_history[-self.max_history_size :]
                optimization_results["actions_taken"].append(
                    f"trimmed_metrics_history_{old_size - len(self.metrics_history)}"
                )

            # Cleanup old alerts
            if len(self.alert_history) > 100:
                old_size = len(self.alert_history)
                self.alert_history = self.alert_history[-100:]
                optimization_results["actions_taken"].append(
                    f"trimmed_alert_history_{old_size - len(self.alert_history)}"
                )

            logger.debug("Resource optimization completed", extra=optimization_results)

        except Exception as e:
            logger.error(f"Resource optimization failed: {e}")
            optimization_results["error"] = str(e)

        return optimization_results

    async def _send_alerts(self, alerts: list[ResourceAlert]) -> None:
        """Send alerts to registered callbacks"""

        for alert in alerts:
            for callback in self.alert_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(alert)
                    else:
                        callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

    def add_alert_callback(self, callback: Callable[[ResourceAlert], None]) -> None:
        """Add callback for resource alerts"""
        self.alert_callbacks.append(callback)

    def get_resource_summary(self) -> dict[str, Any]:
        """Get comprehensive resource usage summary"""

        current_metrics = self.get_current_metrics()
        memory_stats = self.memory_monitor.get_memory_stats()

        # Calculate resource levels
        levels = {
            "memory": self._get_resource_level(
                current_metrics.memory_percent,
                self.limits.memory_warning_percent,
                self.limits.memory_critical_percent,
            ),
            "cpu": self._get_resource_level(
                current_metrics.cpu_percent,
                self.limits.cpu_warning_percent,
                self.limits.cpu_critical_percent,
            ),
            "disk": self._get_resource_level(
                current_metrics.disk_percent,
                self.limits.disk_warning_percent,
                self.limits.disk_critical_percent,
            ),
        }

        # Recent alerts
        recent_alerts = [
            alert
            for alert in self.alert_history[-10:]
            if (utc_now() if CORE_AVAILABLE else datetime.now()) - alert.timestamp
            < timedelta(hours=1)
        ]

        return {
            "current_metrics": current_metrics.to_dict(),
            "memory_stats": memory_stats,
            "resource_levels": levels,
            "limits": {
                "memory_limit_mb": self.limits.memory_limit_mb,
                "memory_warning_percent": self.limits.memory_warning_percent,
                "memory_critical_percent": self.limits.memory_critical_percent,
                "cpu_warning_percent": self.limits.cpu_warning_percent,
                "cpu_critical_percent": self.limits.cpu_critical_percent,
                "disk_warning_percent": self.limits.disk_warning_percent,
                "disk_critical_percent": self.limits.disk_critical_percent,
            },
            "recent_alerts": [
                {
                    "type": alert.alert_type.value,
                    "level": alert.level.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                }
                for alert in recent_alerts
            ],
            "monitoring_enabled": self.monitoring_enabled,
            "auto_cleanup_enabled": self.auto_cleanup_enabled,
        }

    def _get_resource_level(
        self, current: float, warning: float, critical: float
    ) -> ResourceLevel:
        """Determine resource level based on thresholds"""

        if current >= critical:
            return ResourceLevel.CRITICAL
        elif current >= warning:
            return ResourceLevel.HIGH
        elif current >= warning * 0.5:
            return ResourceLevel.NORMAL
        else:
            return ResourceLevel.LOW


# Global resource manager instance
_resource_manager: ResourceManager | None = None


def get_resource_manager() -> ResourceManager | None:
    """Get global resource manager instance"""
    global _resource_manager
    return _resource_manager


def initialize_resource_manager(
    config: dict[str, Any] | None = None,
) -> ResourceManager:
    """Initialize global resource manager"""
    global _resource_manager

    _resource_manager = ResourceManager(config)
    return _resource_manager


async def shutdown_resource_manager() -> None:
    """Shutdown global resource manager"""
    global _resource_manager

    if _resource_manager:
        await _resource_manager.stop_monitoring()
        _resource_manager = None
