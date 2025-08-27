"""
Performance metrics collection and tracking system
"""

import asyncio
import statistics
import time
from collections import defaultdict
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
    logger = get_service_logger("generation-service.metrics_collector")
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


class MetricType(str, Enum):
    """Types of metrics that can be collected"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Individual metric measurement"""

    timestamp: datetime
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Core performance metrics for Generation Service"""

    # Workflow execution metrics
    workflow_execution_time: float = 0.0
    workflow_success_rate: float = 100.0
    workflow_error_rate: float = 0.0

    # AI API metrics
    ai_api_response_time: float = 0.0
    ai_api_success_rate: float = 100.0
    ai_api_error_rate: float = 0.0
    token_usage_per_request: float = 0.0

    # Cache metrics
    cache_hit_ratio: float = 0.0
    cache_miss_ratio: float = 0.0
    cache_response_time: float = 0.0

    # System metrics
    concurrent_workflows: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    # API throughput metrics
    api_throughput_rps: float = 0.0
    api_latency_p95: float = 0.0
    api_latency_p99: float = 0.0

    # Error tracking
    error_rate_by_node: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "workflow_execution_time": self.workflow_execution_time,
            "workflow_success_rate": self.workflow_success_rate,
            "workflow_error_rate": self.workflow_error_rate,
            "ai_api_response_time": self.ai_api_response_time,
            "ai_api_success_rate": self.ai_api_success_rate,
            "ai_api_error_rate": self.ai_api_error_rate,
            "token_usage_per_request": self.token_usage_per_request,
            "cache_hit_ratio": self.cache_hit_ratio,
            "cache_miss_ratio": self.cache_miss_ratio,
            "cache_response_time": self.cache_response_time,
            "concurrent_workflows": self.concurrent_workflows,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "api_throughput_rps": self.api_throughput_rps,
            "api_latency_p95": self.api_latency_p95,
            "api_latency_p99": self.api_latency_p99,
            "error_rate_by_node": self.error_rate_by_node.copy(),
        }


class MetricsCollector:
    """
    Comprehensive metrics collection system for performance monitoring

    Features:
    - Real-time metric collection
    - Multiple metric types (counter, gauge, histogram, timer)
    - Automatic aggregation and statistics
    - Performance target tracking
    - Custom metric registration
    - Time-series data storage
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}

        # Metric storage
        self._metrics: dict[str, list[MetricValue]] = defaultdict(list)
        self._metric_types: dict[str, MetricType] = {}
        self._metric_descriptions: dict[str, str] = {}

        # Time-series storage configuration
        self.max_history_size = self.config.get("max_history_size", 10000)
        self.retention_hours = self.config.get("retention_hours", 24)

        # Aggregation intervals
        self.aggregation_intervals = {
            "1min": timedelta(minutes=1),
            "5min": timedelta(minutes=5),
            "15min": timedelta(minutes=15),
            "1hour": timedelta(hours=1),
        }

        # Performance targets from user requirements
        self.performance_targets = {
            "workflow_execution_time": 30.0,  # 30 seconds
            "concurrent_workflows": 20,  # 20 concurrent requests
            "api_response_time_cached": 0.1,  # 100ms for cached
            "memory_limit_mb": 2048,  # 2GB limit
            "cache_hit_ratio": 0.7,  # 70% cache hit ratio
            "ai_api_success_rate": 0.95,  # 95% success rate
        }

        # Current aggregated metrics
        self._current_metrics = PerformanceMetrics()

        # Collection state
        self._collection_enabled = False
        self._collection_task: asyncio.Task[None] | None = None
        self._cleanup_task: asyncio.Task[None] | None = None

        # Event handlers
        self._metric_handlers: list[Callable[[str, MetricValue], None]] = []

        # Initialize core metrics
        self._initialize_core_metrics()

    def _initialize_core_metrics(self) -> None:
        """Initialize core performance metrics"""

        core_metrics = [
            (
                "workflow_execution_time",
                MetricType.TIMER,
                "Time taken to execute workflow",
            ),
            ("ai_api_response_time", MetricType.TIMER, "AI API response time"),
            ("token_usage_per_request", MetricType.GAUGE, "Token usage per AI request"),
            ("error_rate_by_node", MetricType.COUNTER, "Error count by workflow node"),
            ("cache_hit_ratio", MetricType.GAUGE, "Cache hit ratio percentage"),
            (
                "concurrent_workflows",
                MetricType.GAUGE,
                "Number of concurrent workflows",
            ),
            ("memory_usage", MetricType.GAUGE, "Memory usage in MB"),
            ("api_throughput", MetricType.COUNTER, "API requests per second"),
            ("api_latency", MetricType.HISTOGRAM, "API request latency"),
        ]

        for metric_name, metric_type, description in core_metrics:
            self.register_metric(metric_name, metric_type, description)

    def register_metric(
        self, name: str, metric_type: MetricType, description: str = ""
    ) -> None:
        """Register a new metric for collection"""

        self._metric_types[name] = metric_type
        self._metric_descriptions[name] = description

        logger.debug(f"Registered metric: {name} ({metric_type.value})")

    def record_counter(
        self, name: str, value: float = 1.0, labels: Optional[dict[str, str]] = None
    ) -> None:
        """Record a counter metric (cumulative value)"""
        self._record_metric(name, MetricType.COUNTER, value, labels)

    def record_gauge(
        self, name: str, value: float, labels: Optional[dict[str, str]] = None
    ) -> None:
        """Record a gauge metric (current value)"""
        self._record_metric(name, MetricType.GAUGE, value, labels)

    def record_histogram(
        self, name: str, value: float, labels: Optional[dict[str, str]] = None
    ) -> None:
        """Record a histogram metric (distribution of values)"""
        self._record_metric(name, MetricType.HISTOGRAM, value, labels)

    def record_timer(
        self, name: str, duration: float, labels: Optional[dict[str, str]] = None
    ) -> None:
        """Record a timer metric (duration measurement)"""
        self._record_metric(name, MetricType.TIMER, duration, labels)

    def _record_metric(
        self,
        name: str,
        expected_type: MetricType,
        value: float,
        labels: Optional[dict[str, str]] = None,
    ) -> None:
        """Internal method to record metric value"""

        # Verify metric type
        if name in self._metric_types and self._metric_types[name] != expected_type:
            logger.warning(
                f"Metric type mismatch for {name}: expected {expected_type}, got {self._metric_types[name]}"
            )
            return

        # Create metric value
        metric_value = MetricValue(
            timestamp=utc_now() if CORE_AVAILABLE else datetime.now(),
            value=value,
            labels=labels or {},
        )

        # Store metric
        self._metrics[name].append(metric_value)

        # Trim history if too large
        if len(self._metrics[name]) > self.max_history_size:
            self._metrics[name] = self._metrics[name][-self.max_history_size :]

        # Call event handlers
        for handler in self._metric_handlers:
            try:
                handler(name, metric_value)
            except Exception as e:
                logger.error(f"Metric handler failed: {e}")

    async def start_collection(self) -> None:
        """Start metrics collection"""

        if self._collection_enabled:
            return

        self._collection_enabled = True
        self._collection_task = asyncio.create_task(self._collection_worker())
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())

        logger.info("MetricsCollector started")

    async def stop_collection(self) -> None:
        """Stop metrics collection"""

        self._collection_enabled = False

        if self._collection_task and not self._collection_task.done():
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("MetricsCollector stopped")

    async def _collection_worker(self) -> None:
        """Background worker for metric aggregation"""

        while self._collection_enabled:
            try:
                # Update current aggregated metrics
                await self._update_current_metrics()

                # Wait for next collection cycle
                await asyncio.sleep(5.0)  # Collect every 5 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection worker error: {e}")
                await asyncio.sleep(10.0)

    async def _cleanup_worker(self) -> None:
        """Background worker for cleaning old metrics"""

        while self._collection_enabled:
            try:
                await asyncio.sleep(300.0)  # Cleanup every 5 minutes

                cutoff_time = (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ) - timedelta(hours=self.retention_hours)

                cleaned_count = 0
                for metric_name, values in self._metrics.items():
                    original_size = len(values)
                    self._metrics[metric_name] = [
                        v for v in values if v.timestamp > cutoff_time
                    ]
                    cleaned_count += original_size - len(self._metrics[metric_name])

                if cleaned_count > 0:
                    logger.debug(f"Cleaned {cleaned_count} old metric values")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics cleanup worker error: {e}")

    async def _update_current_metrics(self) -> None:
        """Update current aggregated metrics"""

        try:
            now = utc_now() if CORE_AVAILABLE else datetime.now()
            window = now - timedelta(minutes=5)  # 5-minute window

            # Workflow execution time
            workflow_times = self._get_recent_values("workflow_execution_time", window)
            if workflow_times:
                self._current_metrics.workflow_execution_time = statistics.mean(
                    workflow_times
                )

            # AI API response time
            api_times = self._get_recent_values("ai_api_response_time", window)
            if api_times:
                self._current_metrics.ai_api_response_time = statistics.mean(api_times)

            # Token usage
            token_usage = self._get_recent_values("token_usage_per_request", window)
            if token_usage:
                self._current_metrics.token_usage_per_request = statistics.mean(
                    token_usage
                )

            # Cache hit ratio
            cache_hits = self._get_recent_values("cache_hit_ratio", window)
            if cache_hits:
                self._current_metrics.cache_hit_ratio = statistics.mean(cache_hits)
                self._current_metrics.cache_miss_ratio = (
                    1.0 - self._current_metrics.cache_hit_ratio
                )

            # Concurrent workflows (latest value)
            concurrent_values = self._get_recent_values("concurrent_workflows", window)
            if concurrent_values:
                self._current_metrics.concurrent_workflows = int(concurrent_values[-1])

            # Memory usage
            memory_values = self._get_recent_values("memory_usage", window)
            if memory_values:
                self._current_metrics.memory_usage_mb = statistics.mean(memory_values)

            # API throughput and latency
            api_latencies = self._get_recent_values("api_latency", window)
            if api_latencies:
                self._current_metrics.api_latency_p95 = (
                    statistics.quantiles(api_latencies, n=20)[18]
                    if len(api_latencies) > 20
                    else max(api_latencies)
                )
                self._current_metrics.api_latency_p99 = (
                    statistics.quantiles(api_latencies, n=100)[98]
                    if len(api_latencies) > 100
                    else max(api_latencies)
                )

            # Calculate success/error rates
            await self._calculate_success_rates(window)

        except Exception as e:
            logger.error(f"Failed to update current metrics: {e}")

    def _get_recent_values(self, metric_name: str, since: datetime) -> list[float]:
        """Get metric values since specified time"""

        if metric_name not in self._metrics:
            return []

        return [m.value for m in self._metrics[metric_name] if m.timestamp >= since]

    async def _calculate_success_rates(self, window: datetime) -> None:
        """Calculate success and error rates"""

        # This would integrate with actual error tracking
        # For now, we'll use dummy calculation

        total_workflows = len(
            self._get_recent_values("workflow_execution_time", window)
        )
        if total_workflows > 0:
            # Assume 95% success rate as baseline
            self._current_metrics.workflow_success_rate = 95.0
            self._current_metrics.workflow_error_rate = 5.0

        total_api_calls = len(self._get_recent_values("ai_api_response_time", window))
        if total_api_calls > 0:
            # Assume 98% success rate for AI API
            self._current_metrics.ai_api_success_rate = 98.0
            self._current_metrics.ai_api_error_rate = 2.0

    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current aggregated performance metrics"""
        return self._current_metrics

    def get_metric_history(
        self, metric_name: str, since: Optional[datetime] = None
    ) -> list[MetricValue]:
        """Get historical metric values"""

        if metric_name not in self._metrics:
            return []

        values = self._metrics[metric_name]

        if since:
            values = [v for v in values if v.timestamp >= since]

        return values

    def get_aggregated_metrics(
        self, metric_name: str, interval: str = "5min"
    ) -> dict[str, float]:
        """Get aggregated metrics for specified interval"""

        if interval not in self.aggregation_intervals:
            raise ValueError(f"Invalid interval: {interval}")

        now = utc_now() if CORE_AVAILABLE else datetime.now()
        since = now - self.aggregation_intervals[interval]

        values = self._get_recent_values(metric_name, since)

        if not values:
            return {}

        aggregation = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
        }

        if len(values) > 1:
            aggregation["stddev"] = statistics.stdev(values)

        # Add percentiles for histogram metrics
        if (
            self._metric_types.get(metric_name) == MetricType.HISTOGRAM
            and len(values) > 10
        ):
            try:
                quantiles = statistics.quantiles(values, n=100)
                aggregation.update(
                    {
                        "p50": quantiles[49],
                        "p90": quantiles[89],
                        "p95": quantiles[94],
                        "p99": quantiles[98],
                    }
                )
            except statistics.StatisticsError:
                pass

        return aggregation

    def check_performance_targets(self) -> dict[str, Any]:
        """Check current metrics against performance targets"""

        current = self._current_metrics
        target_status = {}

        # Check each performance target
        checks = [
            (
                "workflow_execution_time",
                current.workflow_execution_time,
                self.performance_targets["workflow_execution_time"],
                "<=",
            ),
            (
                "concurrent_workflows",
                current.concurrent_workflows,
                self.performance_targets["concurrent_workflows"],
                "<=",
            ),
            (
                "memory_usage_mb",
                current.memory_usage_mb,
                self.performance_targets["memory_limit_mb"],
                "<=",
            ),
            (
                "cache_hit_ratio",
                current.cache_hit_ratio,
                self.performance_targets["cache_hit_ratio"],
                ">=",
            ),
            (
                "ai_api_success_rate",
                current.ai_api_success_rate / 100.0,
                self.performance_targets["ai_api_success_rate"],
                ">=",
            ),
        ]

        for metric_name, current_value, target_value, operator in checks:
            if operator == "<=":
                is_meeting_target = current_value <= target_value
            else:  # ">="
                is_meeting_target = current_value >= target_value

            target_status[metric_name] = {
                "current": current_value,
                "target": target_value,
                "meeting_target": is_meeting_target,
                "deviation": current_value - target_value,
            }

        return target_status

    def add_metric_handler(self, handler: Callable[[str, MetricValue], None]) -> None:
        """Add event handler for metric updates"""
        self._metric_handlers.append(handler)

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get comprehensive metrics summary"""

        return {
            "current_metrics": self._current_metrics.to_dict(),
            "performance_targets": self.check_performance_targets(),
            "collection_enabled": self._collection_enabled,
            "registered_metrics": {
                name: {
                    "type": self._metric_types[name].value,
                    "description": self._metric_descriptions[name],
                    "data_points": len(self._metrics.get(name, [])),
                }
                for name in self._metric_types.keys()
            },
            "storage_stats": {
                "total_metrics": len(self._metrics),
                "total_data_points": sum(
                    len(values) for values in self._metrics.values()
                ),
                "retention_hours": self.retention_hours,
            },
        }


# Context managers for automatic metric recording
class MetricTimer:
    """Context manager for timing operations"""

    def __init__(
        self,
        collector: MetricsCollector,
        metric_name: str,
        labels: Optional[dict[str, str]] = None,
    ):
        self.collector = collector
        self.metric_name = metric_name
        self.labels = labels
        self.start_time = None

    def __enter__(self) -> "MetricTimer":
        self.start_time = time.time()
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.record_timer(self.metric_name, duration, self.labels)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get global metrics collector instance"""
    global _metrics_collector
    return _metrics_collector


def initialize_metrics_collector(
    config: Optional[dict[str, Any]] = None,
) -> MetricsCollector:
    """Initialize global metrics collector"""
    global _metrics_collector

    _metrics_collector = MetricsCollector(config)
    return _metrics_collector


async def shutdown_metrics_collector() -> None:
    """Shutdown global metrics collector"""
    global _metrics_collector

    if _metrics_collector:
        await _metrics_collector.stop_collection()
        _metrics_collector = None
