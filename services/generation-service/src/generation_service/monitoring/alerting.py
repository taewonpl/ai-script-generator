"""
Alerting system for performance and health monitoring
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, Union

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.alerting")
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


class AlertSeverity(str, Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertCondition(str, Enum):
    """Alert trigger conditions"""

    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    REGEX_MATCH = "regex"


class AlertChannel(str, Enum):
    """Alert delivery channels"""

    LOG = "log"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    CONSOLE = "console"


@dataclass
class AlertRule:
    """Alert rule configuration"""

    name: str
    description: str
    metric_name: str
    condition: AlertCondition
    threshold: Union[float, str]
    severity: AlertSeverity
    enabled: bool = True

    # Evaluation settings
    evaluation_window: int = 300  # seconds
    evaluation_frequency: int = 60  # seconds
    consecutive_breaches: int = 1

    # Alert settings
    cooldown_period: int = 300  # seconds
    channels: list[AlertChannel] = field(default_factory=list)

    # Metadata
    tags: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Active alert instance"""

    rule_name: str
    severity: AlertSeverity
    message: str
    triggered_at: datetime
    metric_name: str
    current_value: Union[float, str]
    threshold: Union[float, str]
    details: dict[str, Any] = field(default_factory=dict)
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "triggered_at": self.triggered_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "details": self.details,
        }


@dataclass
class AlertStats:
    """Alert system statistics"""

    total_alerts: int = 0
    active_alerts: int = 0
    resolved_alerts: int = 0
    alerts_by_severity: dict[str, int] = field(default_factory=dict)
    alerts_by_rule: dict[str, int] = field(default_factory=dict)
    false_positive_rate: float = 0.0


class AlertManager:
    """
    Comprehensive alerting system for monitoring

    Features:
    - Rule-based alert configuration
    - Multiple alert channels
    - Alert aggregation and deduplication
    - Cooldown and suppression
    - Alert history and statistics
    - Custom alert handlers
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}

        # Alert rules and state
        self._alert_rules: dict[str, AlertRule] = {}
        self._active_alerts: dict[str, Alert] = {}
        self._alert_history: list[Alert] = []

        # Evaluation state
        self._evaluation_tasks: dict[str, asyncio.Task[None]] = {}
        self._metric_buffer: dict[str, list[tuple]] = {}  # (timestamp, value)
        self._last_alert_time: dict[str, datetime] = {}

        # Alert handlers
        self._alert_handlers: dict[AlertChannel, list[Callable]] = {
            channel: [] for channel in AlertChannel
        }

        # Configuration
        self.max_history_size = self.config.get("max_history_size", 1000)
        self.history_retention_hours = self.config.get(
            "history_retention_hours", 168
        )  # 1 week
        self.default_channels = self.config.get("default_channels", [AlertChannel.LOG])

        # Monitoring state
        self._monitoring_enabled = False
        self._cleanup_task: asyncio.Task[None] | None = None

        # Initialize default alert rules
        self._initialize_default_rules()

        # Initialize default handlers
        self._initialize_default_handlers()

    def _initialize_default_rules(self) -> None:
        """Initialize default alert rules based on performance targets"""

        default_rules = [
            AlertRule(
                name="workflow_execution_time_high",
                description="Workflow execution time exceeds target",
                metric_name="workflow_execution_time",
                condition=AlertCondition.GREATER_THAN,
                threshold=30.0,  # 30 seconds target
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.CONSOLE],
            ),
            AlertRule(
                name="workflow_execution_time_critical",
                description="Workflow execution time critically high",
                metric_name="workflow_execution_time",
                condition=AlertCondition.GREATER_THAN,
                threshold=60.0,  # 60 seconds critical
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.CONSOLE],
                consecutive_breaches=2,
            ),
            AlertRule(
                name="memory_usage_high",
                description="Memory usage exceeds limit",
                metric_name="memory_usage_mb",
                condition=AlertCondition.GREATER_THAN,
                threshold=2048.0,  # 2GB limit
                severity=AlertSeverity.ERROR,
                channels=[AlertChannel.LOG, AlertChannel.CONSOLE],
            ),
            AlertRule(
                name="cache_hit_ratio_low",
                description="Cache hit ratio below target",
                metric_name="cache_hit_ratio",
                condition=AlertCondition.LESS_THAN,
                threshold=0.7,  # 70% target
                severity=AlertSeverity.WARNING,
                evaluation_window=600,  # 10 minutes
                channels=[AlertChannel.LOG],
            ),
            AlertRule(
                name="concurrent_workflows_high",
                description="Too many concurrent workflows",
                metric_name="concurrent_workflows",
                condition=AlertCondition.GREATER_THAN,
                threshold=20,  # 20 concurrent limit
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.CONSOLE],
            ),
            AlertRule(
                name="ai_api_error_rate_high",
                description="AI API error rate too high",
                metric_name="ai_api_error_rate",
                condition=AlertCondition.GREATER_THAN,
                threshold=5.0,  # 5% error rate
                severity=AlertSeverity.ERROR,
                evaluation_window=300,  # 5 minutes
                channels=[AlertChannel.LOG, AlertChannel.CONSOLE],
            ),
        ]

        for rule in default_rules:
            self.add_alert_rule(rule)

    def _initialize_default_handlers(self) -> None:
        """Initialize default alert handlers"""

        # Log handler
        self.add_alert_handler(AlertChannel.LOG, self._log_alert_handler)

        # Console handler
        self.add_alert_handler(AlertChannel.CONSOLE, self._console_alert_handler)

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add or update an alert rule"""

        self._alert_rules[rule.name] = rule

        logger.info(
            f"Added alert rule: {rule.name}",
            extra={
                "metric": rule.metric_name,
                "condition": rule.condition.value,
                "threshold": rule.threshold,
                "severity": rule.severity.value,
            },
        )

    def remove_alert_rule(self, rule_name: str) -> bool:
        """Remove an alert rule"""

        if rule_name in self._alert_rules:
            del self._alert_rules[rule_name]

            # Stop evaluation task
            if rule_name in self._evaluation_tasks:
                task = self._evaluation_tasks[rule_name]
                if not task.done():
                    task.cancel()
                del self._evaluation_tasks[rule_name]

            logger.info(f"Removed alert rule: {rule_name}")
            return True

        return False

    def add_alert_handler(
        self, channel: AlertChannel, handler: Callable[[Alert], Any]
    ) -> None:
        """Add alert handler for specific channel"""

        if channel not in self._alert_handlers:
            self._alert_handlers[channel] = []

        self._alert_handlers[channel].append(handler)
        logger.debug(f"Added alert handler for channel: {channel.value}")

    async def start_monitoring(self) -> None:
        """Start alert monitoring"""

        if self._monitoring_enabled:
            return

        self._monitoring_enabled = True

        # Start evaluation tasks for each rule
        for rule_name, rule in self._alert_rules.items():
            if rule.enabled:
                task = asyncio.create_task(self._evaluate_rule(rule))
                self._evaluation_tasks[rule_name] = task

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())

        logger.info(
            "AlertManager monitoring started",
            extra={"active_rules": len(self._evaluation_tasks)},
        )

    async def stop_monitoring(self) -> None:
        """Stop alert monitoring"""

        self._monitoring_enabled = False

        # Cancel all evaluation tasks
        for task in self._evaluation_tasks.values():
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        for task in self._evaluation_tasks.values():
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._evaluation_tasks.clear()

        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("AlertManager monitoring stopped")

    async def _evaluate_rule(self, rule: AlertRule) -> None:
        """Evaluate alert rule continuously"""

        consecutive_breaches = 0

        while self._monitoring_enabled:
            try:
                # Get metric value from buffer
                current_value = await self._get_current_metric_value(
                    rule.metric_name, rule.evaluation_window
                )

                if current_value is not None:
                    # Evaluate condition
                    is_breach = self._evaluate_condition(
                        current_value, rule.condition, rule.threshold
                    )

                    if is_breach:
                        consecutive_breaches += 1

                        if consecutive_breaches >= rule.consecutive_breaches:
                            await self._trigger_alert(rule, current_value)
                            consecutive_breaches = 0  # Reset after triggering
                    else:
                        consecutive_breaches = 0

                        # Check if we should resolve existing alert
                        await self._check_alert_resolution(rule.name, current_value)

                # Wait for next evaluation
                await asyncio.sleep(rule.evaluation_frequency)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Alert rule evaluation error for {rule.name}: {e}")
                await asyncio.sleep(rule.evaluation_frequency)

    def _evaluate_condition(
        self,
        value: Union[float, str],
        condition: AlertCondition,
        threshold: Union[float, str],
    ) -> bool:
        """Evaluate alert condition"""

        try:
            if condition == AlertCondition.GREATER_THAN:
                return float(value) > float(threshold)
            elif condition == AlertCondition.LESS_THAN:
                return float(value) < float(threshold)
            elif condition == AlertCondition.EQUALS:
                return value == threshold
            elif condition == AlertCondition.NOT_EQUALS:
                return value != threshold
            elif condition == AlertCondition.CONTAINS:
                return str(threshold) in str(value)
            elif condition == AlertCondition.REGEX_MATCH:
                import re

                return bool(re.search(str(threshold), str(value)))
            else:
                return False
        except (ValueError, TypeError):
            return False

    async def _get_current_metric_value(
        self, metric_name: str, window_seconds: int
    ) -> Optional[str]:
        """Get current metric value from metrics collector"""

        try:
            # Import metrics collector
            from .metrics_collector import get_metrics_collector

            collector = get_metrics_collector()
            if not collector:
                return None

            # Get recent values within window
            since = (utc_now() if CORE_AVAILABLE else datetime.now()) - timedelta(
                seconds=window_seconds
            )
            history = collector.get_metric_history(metric_name, since)

            if not history:
                return None

            # For most metrics, use the latest value
            # For some metrics, we might want to use average
            if metric_name in [
                "workflow_execution_time",
                "ai_api_response_time",
                "cache_hit_ratio",
            ]:
                # Use average for time-based metrics
                values = [h.value for h in history]
                return sum(values) / len(values)
            else:
                # Use latest value for counters and gauges
                return history[-1].value

        except Exception as e:
            logger.error(f"Failed to get metric value for {metric_name}: {e}")
            return None

    async def _trigger_alert(
        self, rule: AlertRule, current_value: Union[float, str]
    ) -> None:
        """Trigger an alert"""

        # Check cooldown
        if rule.name in self._last_alert_time:
            time_since_last = (
                utc_now() if CORE_AVAILABLE else datetime.now()
            ) - self._last_alert_time[rule.name]
            if time_since_last.total_seconds() < rule.cooldown_period:
                return

        # Create alert
        alert = Alert(
            rule_name=rule.name,
            severity=rule.severity,
            message=f"{rule.description}: {current_value} {rule.condition.value} {rule.threshold}",
            triggered_at=utc_now() if CORE_AVAILABLE else datetime.now(),
            metric_name=rule.metric_name,
            current_value=current_value,
            threshold=rule.threshold,
            details={
                "rule_description": rule.description,
                "evaluation_window": rule.evaluation_window,
                "tags": rule.tags,
            },
        )

        # Store active alert
        self._active_alerts[rule.name] = alert
        self._alert_history.append(alert)
        self._last_alert_time[rule.name] = alert.triggered_at

        # Send alert through channels
        await self._send_alert(alert, rule.channels)

        logger.warning(
            f"Alert triggered: {rule.name}",
            extra={
                "severity": rule.severity.value,
                "metric": rule.metric_name,
                "current_value": current_value,
                "threshold": rule.threshold,
            },
        )

    async def _check_alert_resolution(
        self, rule_name: str, current_value: Union[float, str]
    ) -> None:
        """Check if active alert should be resolved"""

        if rule_name in self._active_alerts:
            alert = self._active_alerts[rule_name]
            rule = self._alert_rules[rule_name]

            # Check if condition is no longer met
            is_breach = self._evaluate_condition(
                current_value, rule.condition, rule.threshold
            )

            if not is_breach:
                # Resolve alert
                alert.resolved_at = utc_now() if CORE_AVAILABLE else datetime.now()
                del self._active_alerts[rule_name]

                # Send resolution notification
                resolution_alert = Alert(
                    rule_name=f"{rule.name}_resolved",
                    severity=AlertSeverity.INFO,
                    message=f"Alert resolved: {rule.description}. Current value: {current_value}",
                    triggered_at=alert.resolved_at,
                    metric_name=rule.metric_name,
                    current_value=current_value,
                    threshold=rule.threshold,
                )

                await self._send_alert(resolution_alert, rule.channels)

                logger.info(
                    f"Alert resolved: {rule_name}",
                    extra={
                        "current_value": current_value,
                        "duration": (
                            alert.resolved_at - alert.triggered_at
                        ).total_seconds(),
                    },
                )

    async def _send_alert(self, alert: Alert, channels: list[AlertChannel]) -> None:
        """Send alert through specified channels"""

        for channel in channels:
            handlers = self._alert_handlers.get(channel, [])

            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(alert)
                    else:
                        handler(alert)
                except Exception as e:
                    logger.error(
                        f"Alert handler failed for channel {channel.value}: {e}"
                    )

    async def _cleanup_worker(self) -> None:
        """Background worker for cleaning old alerts"""

        while self._monitoring_enabled:
            try:
                await asyncio.sleep(3600)  # Cleanup every hour

                cutoff_time = (
                    utc_now() if CORE_AVAILABLE else datetime.now()
                ) - timedelta(hours=self.history_retention_hours)

                # Remove old alerts from history
                original_size = len(self._alert_history)
                self._alert_history = [
                    alert
                    for alert in self._alert_history
                    if alert.triggered_at > cutoff_time
                ]

                # Trim if still too large
                if len(self._alert_history) > self.max_history_size:
                    self._alert_history = self._alert_history[-self.max_history_size :]

                cleaned_count = original_size - len(self._alert_history)
                if cleaned_count > 0:
                    logger.debug(f"Cleaned {cleaned_count} old alerts from history")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Alert cleanup worker error: {e}")

    # Default alert handlers
    async def _log_alert_handler(self, alert: Alert) -> None:
        """Default log alert handler"""

        log_level = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical,
        }

        log_func = log_level.get(alert.severity, logger.info)
        log_func(
            f"ALERT: {alert.message}",
            extra={
                "alert_rule": alert.rule_name,
                "severity": alert.severity.value,
                "metric": alert.metric_name,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
            },
        )

    async def _console_alert_handler(self, alert: Alert) -> None:
        """Default console alert handler"""

        severity_colors = {
            AlertSeverity.INFO: "\033[96m",  # Cyan
            AlertSeverity.WARNING: "\033[93m",  # Yellow
            AlertSeverity.ERROR: "\033[91m",  # Red
            AlertSeverity.CRITICAL: "\033[95m",  # Magenta
        }

        color = severity_colors.get(alert.severity, "")
        reset = "\033[0m"

        print(f"{color}[{alert.severity.value.upper()}] {alert.message}{reset}")

    async def _webhook_alert_handler(self, alert: Alert, webhook_url: str) -> None:
        """Webhook alert handler"""

        try:
            import aiohttp

            payload = {
                "alert": alert.to_dict(),
                "timestamp": alert.triggered_at.isoformat(),
                "service": "generation-service",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url, json=payload, timeout=30
                ) as response:
                    if response.status >= 400:
                        logger.error(f"Webhook alert failed: HTTP {response.status}")

        except Exception as e:
            logger.error(f"Webhook alert handler error: {e}")

    # Public API methods
    def get_active_alerts(self) -> list[Alert]:
        """Get all active alerts"""
        return list(self._active_alerts.values())

    def get_alert_history(self, hours: int = 24) -> list[Alert]:
        """Get alert history for specified hours"""

        since = (utc_now() if CORE_AVAILABLE else datetime.now()) - timedelta(
            hours=hours
        )

        return [alert for alert in self._alert_history if alert.triggered_at >= since]

    def get_alert_stats(self) -> AlertStats:
        """Get alert system statistics"""

        total_alerts = len(self._alert_history)
        active_alerts = len(self._active_alerts)
        resolved_alerts = len([a for a in self._alert_history if a.resolved_at])

        # Count by severity
        severity_counts = {}
        for alert in self._alert_history:
            severity_counts[alert.severity.value] = (
                severity_counts.get(alert.severity.value, 0) + 1
            )

        # Count by rule
        rule_counts = {}
        for alert in self._alert_history:
            rule_counts[alert.rule_name] = rule_counts.get(alert.rule_name, 0) + 1

        return AlertStats(
            total_alerts=total_alerts,
            active_alerts=active_alerts,
            resolved_alerts=resolved_alerts,
            alerts_by_severity=severity_counts,
            alerts_by_rule=rule_counts,
        )

    def get_alert_summary(self) -> dict[str, Any]:
        """Get comprehensive alert summary"""

        stats = self.get_alert_stats()

        return {
            "monitoring_enabled": self._monitoring_enabled,
            "active_rules": len(self._alert_rules),
            "enabled_rules": len([r for r in self._alert_rules.values() if r.enabled]),
            "active_alerts": stats.active_alerts,
            "recent_alerts": [
                alert.to_dict() for alert in self.get_alert_history(hours=1)
            ],
            "statistics": {
                "total_alerts": stats.total_alerts,
                "resolved_alerts": stats.resolved_alerts,
                "alerts_by_severity": stats.alerts_by_severity,
                "alerts_by_rule": stats.alerts_by_rule,
            },
            "rules": {
                name: {
                    "description": rule.description,
                    "metric": rule.metric_name,
                    "condition": f"{rule.condition.value} {rule.threshold}",
                    "severity": rule.severity.value,
                    "enabled": rule.enabled,
                }
                for name, rule in self._alert_rules.items()
            },
        }


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> Optional[AlertManager]:
    """Get global alert manager instance"""
    global _alert_manager
    return _alert_manager


def initialize_alert_manager(config: Optional[dict[str, Any]] = None) -> AlertManager:
    """Initialize global alert manager"""
    global _alert_manager

    _alert_manager = AlertManager(config)
    return _alert_manager


async def shutdown_alert_manager() -> None:
    """Shutdown global alert manager"""
    global _alert_manager

    if _alert_manager:
        await _alert_manager.stop_monitoring()
        _alert_manager = None
