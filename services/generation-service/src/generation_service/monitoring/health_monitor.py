"""
System health monitoring and status tracking
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.health_monitor")
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


class HealthStatus(str, Enum):
    """Health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ComponentType(str, Enum):
    """Types of system components"""

    CACHE = "cache"
    DATABASE = "database"
    AI_PROVIDER = "ai_provider"
    MEMORY = "memory"
    CPU = "cpu"
    DISK = "disk"
    NETWORK = "network"
    SERVICE = "service"


@dataclass
class HealthCheck:
    """Individual health check configuration"""

    name: str
    component_type: ComponentType
    check_function: Callable[[], Any]
    timeout: float = 30.0
    interval: float = 60.0
    critical: bool = False
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthResult:
    """Result of a health check"""

    name: str
    status: HealthStatus
    response_time: float
    timestamp: datetime
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ComponentHealth:
    """Health status of a system component"""

    name: str
    component_type: ComponentType
    status: HealthStatus
    last_check: datetime
    response_time: float
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    check_history: list[HealthResult] = field(default_factory=list)


class HealthMonitor:
    """
    Comprehensive system health monitoring

    Features:
    - Component health tracking
    - Automatic health checks
    - Health status aggregation
    - Dependency monitoring
    - Performance thresholds
    - Historical health data
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}

        # Health checks registry
        self._health_checks: dict[str, HealthCheck] = {}
        self._component_health: dict[str, ComponentHealth] = {}

        # Monitoring state
        self._monitoring_enabled = False
        self._monitoring_tasks: dict[str, asyncio.Task[None]] = {}
        self._health_history: list[dict[str, Any]] = []

        # Configuration
        self.check_interval = self.config.get("check_interval", 60.0)
        self.history_retention = self.config.get("history_retention_hours", 24)
        self.max_history_size = self.config.get("max_history_size", 1000)

        # Component dependencies
        self._dependencies: dict[str, set[str]] = {}

        # Health thresholds
        self.thresholds = {
            "response_time_warning": self.config.get("response_time_warning", 5.0),
            "response_time_critical": self.config.get("response_time_critical", 10.0),
            "failure_rate_warning": self.config.get("failure_rate_warning", 0.1),
            "failure_rate_critical": self.config.get("failure_rate_critical", 0.25),
        }

        # Health change callbacks
        self._status_change_callbacks: list[
            Callable[[str, HealthStatus, HealthStatus], None]
        ] = []

        # Initialize default health checks
        self._initialize_default_checks()

    def _initialize_default_checks(self) -> None:
        """Initialize default system health checks"""

        # Cache health check
        self.register_health_check(
            name="cache_health",
            component_type=ComponentType.CACHE,
            check_function=self._check_cache_health,
            interval=30.0,
            critical=False,
        )

        # Memory health check
        self.register_health_check(
            name="memory_health",
            component_type=ComponentType.MEMORY,
            check_function=self._check_memory_health,
            interval=60.0,
            critical=True,
        )

        # AI provider health check
        self.register_health_check(
            name="ai_provider_health",
            component_type=ComponentType.AI_PROVIDER,
            check_function=self._check_ai_provider_health,
            interval=120.0,
            critical=True,
        )

        # Service health check
        self.register_health_check(
            name="service_health",
            component_type=ComponentType.SERVICE,
            check_function=self._check_service_health,
            interval=30.0,
            critical=True,
        )

    def register_health_check(
        self,
        name: str,
        component_type: ComponentType,
        check_function: Callable[[], Any],
        timeout: float = 30.0,
        interval: float = 60.0,
        critical: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Register a new health check"""

        health_check = HealthCheck(
            name=name,
            component_type=component_type,
            check_function=check_function,
            timeout=timeout,
            interval=interval,
            critical=critical,
            metadata=metadata or {},
        )

        self._health_checks[name] = health_check

        # Initialize component health
        self._component_health[name] = ComponentHealth(
            name=name,
            component_type=component_type,
            status=HealthStatus.UNKNOWN,
            last_check=utc_now() if CORE_AVAILABLE else datetime.now(),
            response_time=0.0,
        )

        logger.info(f"Registered health check: {name} ({component_type.value})")

    def add_dependency(self, component: str, depends_on: str) -> None:
        """Add dependency relationship between components"""

        if component not in self._dependencies:
            self._dependencies[component] = set()

        self._dependencies[component].add(depends_on)
        logger.debug(f"Added dependency: {component} depends on {depends_on}")

    async def start_monitoring(self) -> None:
        """Start health monitoring"""

        if self._monitoring_enabled:
            return

        self._monitoring_enabled = True

        # Start monitoring tasks for each health check
        for check_name, health_check in self._health_checks.items():
            if health_check.enabled:
                task = asyncio.create_task(self._monitor_component(health_check))
                self._monitoring_tasks[check_name] = task

        logger.info(
            "HealthMonitor started",
            extra={
                "health_checks": len(self._health_checks),
                "monitoring_tasks": len(self._monitoring_tasks),
            },
        )

    async def stop_monitoring(self) -> None:
        """Stop health monitoring"""

        self._monitoring_enabled = False

        # Cancel all monitoring tasks
        for task in self._monitoring_tasks.values():
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        for task in self._monitoring_tasks.values():
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._monitoring_tasks.clear()
        logger.info("HealthMonitor stopped")

    async def _monitor_component(self, health_check: HealthCheck) -> None:
        """Monitor a specific component"""

        while self._monitoring_enabled:
            try:
                # Perform health check
                result = await self._perform_health_check(health_check)

                # Update component health
                await self._update_component_health(health_check.name, result)

                # Wait for next check
                await asyncio.sleep(health_check.interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error for {health_check.name}: {e}")
                await asyncio.sleep(health_check.interval)

    async def _perform_health_check(self, health_check: HealthCheck) -> HealthResult:
        """Perform individual health check"""

        start_time = time.time()

        try:
            # Execute health check with timeout
            if asyncio.iscoroutinefunction(health_check.check_function):
                result = await asyncio.wait_for(
                    health_check.check_function(), timeout=health_check.timeout
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(health_check.check_function),
                    timeout=health_check.timeout,
                )

            response_time = time.time() - start_time

            # Interpret result
            if isinstance(result, dict):
                status = HealthStatus(result.get("status", HealthStatus.HEALTHY))
                message = result.get("message", "OK")
                details = result.get("details", {})
            elif isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = "OK" if result else "Health check failed"
                details = {}
            else:
                status = HealthStatus.HEALTHY
                message = str(result)
                details = {}

            # Check response time thresholds
            if response_time > self.thresholds["response_time_critical"]:
                status = HealthStatus.CRITICAL
                message += f" (Response time: {response_time:.2f}s)"
            elif response_time > self.thresholds["response_time_warning"]:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                message += f" (Slow response: {response_time:.2f}s)"

            return HealthResult(
                name=health_check.name,
                status=status,
                response_time=response_time,
                timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
                message=message,
                details=details,
            )

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return HealthResult(
                name=health_check.name,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
                message=f"Health check timed out after {health_check.timeout}s",
                error="timeout",
            )

        except Exception as e:
            response_time = time.time() - start_time
            return HealthResult(
                name=health_check.name,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
                message=f"Health check failed: {e!s}",
                error=str(e),
            )

    async def _update_component_health(
        self, component_name: str, result: HealthResult
    ) -> None:
        """Update component health status"""

        component = self._component_health[component_name]
        previous_status = component.status

        # Update component health
        component.status = result.status
        component.last_check = result.timestamp
        component.response_time = result.response_time
        component.message = result.message
        component.details = result.details

        # Add to history
        component.check_history.append(result)

        # Trim history
        if len(component.check_history) > 100:  # Keep last 100 checks
            component.check_history = component.check_history[-100:]

        # Check for status changes
        if previous_status != result.status:
            logger.info(
                f"Component {component_name} status changed: {previous_status} -> {result.status}"
            )

            # Call status change callbacks
            for callback in self._status_change_callbacks:
                try:
                    callback(component_name, previous_status, result.status)
                except Exception as e:
                    logger.error(f"Status change callback failed: {e}")

        # Update overall health history
        await self._update_health_history()

    async def _update_health_history(self) -> None:
        """Update overall system health history"""

        overall_status = self.get_overall_health_status()

        health_snapshot = {
            "timestamp": (utc_now() if CORE_AVAILABLE else datetime.now()).isoformat(),
            "overall_status": overall_status.value,
            "components": {
                name: {
                    "status": comp.status.value,
                    "response_time": comp.response_time,
                    "message": comp.message,
                }
                for name, comp in self._component_health.items()
            },
        }

        self._health_history.append(health_snapshot)

        # Trim history
        if len(self._health_history) > self.max_history_size:
            self._health_history = self._health_history[-self.max_history_size :]

        # Remove old entries
        cutoff_time = (utc_now() if CORE_AVAILABLE else datetime.now()) - timedelta(
            hours=self.history_retention
        )
        self._health_history = [
            h
            for h in self._health_history
            if datetime.fromisoformat(h["timestamp"].replace("Z", "+00:00"))
            > cutoff_time
        ]

    def get_overall_health_status(self) -> HealthStatus:
        """Get overall system health status"""

        if not self._component_health:
            return HealthStatus.UNKNOWN

        # Check critical components first
        critical_components = [
            comp
            for check_name, comp in self._component_health.items()
            if self._health_checks.get(check_name, {}).critical
        ]

        # If any critical component is unhealthy, system is unhealthy
        for comp in critical_components:
            if comp.status in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]:
                return HealthStatus.UNHEALTHY

        # Aggregate status from all components
        statuses = [comp.status for comp in self._component_health.values()]

        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.DEGRADED
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def get_component_health(self, component_name: str) -> Optional[ComponentHealth]:
        """Get health status of specific component"""
        return self._component_health.get(component_name)

    def get_all_components_health(self) -> dict[str, ComponentHealth]:
        """Get health status of all components"""
        return self._component_health.copy()

    def get_health_summary(self) -> dict[str, Any]:
        """Get comprehensive health summary"""

        overall_status = self.get_overall_health_status()

        # Calculate component statistics
        status_counts: dict[str, int] = {}
        total_response_time = 0.0
        healthy_components = 0

        for comp in self._component_health.values():
            status_counts[comp.status.value] = (
                status_counts.get(comp.status.value, 0) + 1
            )
            total_response_time += comp.response_time
            if comp.status == HealthStatus.HEALTHY:
                healthy_components += 1

        avg_response_time = (
            total_response_time / len(self._component_health)
            if self._component_health
            else 0
        )

        return {
            "overall_status": overall_status.value,
            "components": {
                name: {
                    "type": comp.component_type.value,
                    "status": comp.status.value,
                    "last_check": comp.last_check.isoformat(),
                    "response_time": comp.response_time,
                    "message": comp.message,
                }
                for name, comp in self._component_health.items()
            },
            "statistics": {
                "total_components": len(self._component_health),
                "healthy_components": healthy_components,
                "average_response_time": avg_response_time,
                "status_distribution": status_counts,
            },
            "monitoring_enabled": self._monitoring_enabled,
            "active_checks": len(self._monitoring_tasks),
        }

    def add_status_change_callback(
        self, callback: Callable[[str, HealthStatus, HealthStatus], None]
    ) -> None:
        """Add callback for health status changes"""
        self._status_change_callbacks.append(callback)

    async def perform_immediate_check(
        self, component_name: str
    ) -> Optional[HealthResult]:
        """Perform immediate health check for specific component"""

        if component_name not in self._health_checks:
            return None

        health_check = self._health_checks[component_name]
        result = await self._perform_health_check(health_check)
        await self._update_component_health(component_name, result)

        return result

    # Default health check implementations
    async def _check_cache_health(self) -> dict[str, Any]:
        """Check cache system health"""

        try:
            # Import cache manager to check health
            from ..cache.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()
            if not cache_manager:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Cache manager not initialized",
                }

            health = await cache_manager.health_check()
            return {
                "status": (
                    HealthStatus.HEALTHY
                    if health["status"] == "healthy"
                    else HealthStatus.DEGRADED
                ),
                "message": f"Cache status: {health['status']}",
                "details": health,
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Cache check failed: {e}",
            }

    async def _check_memory_health(self) -> dict[str, Any]:
        """Check memory system health"""

        try:
            # Import resource manager to check memory
            from ..optimization.resource_manager import get_resource_manager

            resource_manager = get_resource_manager()
            if not resource_manager:
                return {
                    "status": HealthStatus.UNKNOWN,
                    "message": "Resource manager not available",
                }

            memory_stats = resource_manager.memory_monitor.get_memory_stats()
            current_memory = memory_stats["current"]

            memory_percent = current_memory.get("system_used_percent", 0)

            if memory_percent > 90:
                status = HealthStatus.CRITICAL
            elif memory_percent > 80:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY

            return {
                "status": status,
                "message": f"Memory usage: {memory_percent:.1f}%",
                "details": memory_stats,
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Memory check failed: {e}",
            }

    async def _check_ai_provider_health(self) -> dict[str, Any]:
        """Check AI provider health"""

        try:
            # Import AI provider pool to check health
            from ..optimization.connection_pool import get_ai_provider_pool

            ai_pool = get_ai_provider_pool()
            if not ai_pool:
                return {
                    "status": HealthStatus.UNKNOWN,
                    "message": "AI provider pool not available",
                }

            metrics = ai_pool.get_provider_metrics()

            # Check if any providers are in circuit breaker open state
            unhealthy_providers = [
                name
                for name, data in metrics.items()
                if data["circuit_breaker"]["state"] == "open"
            ]

            if unhealthy_providers:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": f"Providers with open circuit breaker: {', '.join(unhealthy_providers)}",
                    "details": metrics,
                }
            else:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "All AI providers healthy",
                    "details": metrics,
                }

        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"AI provider check failed: {e}",
            }

    async def _check_service_health(self) -> dict[str, Any]:
        """Check overall service health"""

        try:
            # Basic service health indicators
            from ..optimization.async_manager import get_async_manager

            async_manager = get_async_manager()
            if not async_manager:
                return {
                    "status": HealthStatus.UNKNOWN,
                    "message": "Async manager not available",
                }

            metrics = async_manager.get_system_metrics()
            current_load = metrics["current_load"]

            if current_load > 0.9:
                status = HealthStatus.CRITICAL
            elif current_load > 0.8:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY

            return {
                "status": status,
                "message": f"System load: {current_load:.1%}",
                "details": metrics,
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Service check failed: {e}",
            }


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> Optional[HealthMonitor]:
    """Get global health monitor instance"""
    global _health_monitor
    return _health_monitor


def initialize_health_monitor(config: Optional[dict[str, Any]] = None) -> HealthMonitor:
    """Initialize global health monitor"""
    global _health_monitor

    _health_monitor = HealthMonitor(config)
    return _health_monitor


async def shutdown_health_monitor() -> None:
    """Shutdown global health monitor"""
    global _health_monitor

    if _health_monitor:
        await _health_monitor.stop_monitoring()
        _health_monitor = None
