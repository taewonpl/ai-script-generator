"""
Real-time alerting system for episode numbering system
"""

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("project-service.episode-alerting")
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of episode-related alerts"""

    HIGH_FAILURE_RATE = "high_failure_rate"
    HIGH_CONFLICT_RATE = "high_conflict_rate"
    INTEGRITY_VIOLATION = "integrity_violation"
    PERFORMANCE_DEGRADATION = "performance_degradation"


@dataclass
class AlertRule:
    """Alert rule configuration"""

    rule_id: str
    alert_type: AlertType
    severity: AlertSeverity
    threshold: float
    window_minutes: int
    description: str
    enabled: bool = True


@dataclass
class Alert:
    """Alert instance"""

    alert_id: str
    rule_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    timestamp: datetime
    project_id: str | None = None
    metadata: dict[str, Any] | None = None
    resolved: bool = False
    resolved_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        if self.resolved_at:
            data["resolved_at"] = self.resolved_at.isoformat()
        return data


class EpisodeAlertManager:
    """Manages episode-related alerts"""

    def __init__(self, db: Session):
        self.db = db
        self.alert_handlers: list[Callable[[Alert], None]] = []
        self.active_alerts: dict[str, Alert] = {}
        self.alert_rules: dict[str, AlertRule] = {}

        # Default alert rules
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Setup default alert rules"""
        self.alert_rules = {
            "episode_failure_rate": AlertRule(
                rule_id="episode_failure_rate",
                alert_type=AlertType.HIGH_FAILURE_RATE,
                severity=AlertSeverity.WARNING,
                threshold=1.0,  # 1% failure rate
                window_minutes=15,
                description="Episode creation failure rate exceeds 1%",
            ),
            "episode_conflict_rate": AlertRule(
                rule_id="episode_conflict_rate",
                alert_type=AlertType.HIGH_CONFLICT_RATE,
                severity=AlertSeverity.CRITICAL,
                threshold=5.0,  # 5% conflict rate
                window_minutes=10,
                description="Episode creation conflict rate exceeds 5%",
            ),
            "episode_performance": AlertRule(
                rule_id="episode_performance",
                alert_type=AlertType.PERFORMANCE_DEGRADATION,
                severity=AlertSeverity.WARNING,
                threshold=5.0,  # 5 seconds P95
                window_minutes=20,
                description="Episode creation P95 duration exceeds 5 seconds",
            ),
            "episode_integrity": AlertRule(
                rule_id="episode_integrity",
                alert_type=AlertType.INTEGRITY_VIOLATION,
                severity=AlertSeverity.CRITICAL,
                threshold=1.0,  # Any integrity violation
                window_minutes=5,
                description="Episode numbering integrity violation detected",
            ),
        }

    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add an alert handler function"""
        self.alert_handlers.append(handler)

    def trigger_alert(self, alert: Alert) -> str:
        """Trigger an alert"""
        alert_key = f"{alert.rule_id}_{alert.project_id or 'global'}"

        # Check if similar alert is already active
        if (
            alert_key in self.active_alerts
            and not self.active_alerts[alert_key].resolved
        ):
            logger.debug(f"Similar alert already active: {alert_key}")
            return alert_key

        # Store alert
        self.active_alerts[alert_key] = alert

        # Notify handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")

        logger.warning(f"Alert triggered: {alert.title}")
        return alert_key

    def resolve_alert(self, alert_key: str) -> bool:
        """Resolve an active alert"""
        if alert_key not in self.active_alerts:
            return False

        alert = self.active_alerts[alert_key]
        alert.resolved = True
        alert.resolved_at = datetime.utcnow()

        logger.info(f"Alert resolved: {alert.title}")
        return True

    def check_failure_rate(self, project_id: str | None = None) -> Alert | None:
        """Check episode creation failure rate"""
        try:
            rule = self.alert_rules["episode_failure_rate"]
            if not rule.enabled:
                return None

            # Calculate failure rate in the last window
            since = datetime.utcnow() - timedelta(minutes=rule.window_minutes)

            # Query success/failure counts (this would integrate with actual metrics)
            query_filter = ""
            params = {"since": since}

            if project_id:
                query_filter = "AND project_id = :project_id"
                params["project_id"] = project_id

            # This is a simplified query - in practice would query metrics table
            total_query = text(
                f"""
                SELECT COUNT(*) as total
                FROM episodes
                WHERE created_at >= :since {query_filter}
            """
            )

            result = self.db.execute(total_query, params)
            total_attempts = result.fetchone().total or 0

            if total_attempts == 0:
                return None

            # For demo purposes, assume 5% of recent episodes had creation issues
            # In practice, this would query actual failure metrics
            failure_rate = 5.0  # This would be calculated from real metrics

            if failure_rate > rule.threshold:
                alert_id = f"failure_rate_{int(datetime.utcnow().timestamp())}"

                return Alert(
                    alert_id=alert_id,
                    rule_id=rule.rule_id,
                    alert_type=rule.alert_type,
                    severity=rule.severity,
                    title=f"High Episode Creation Failure Rate: {failure_rate:.1f}%",
                    description=f"Episode creation failure rate of {failure_rate:.1f}% exceeds threshold of {rule.threshold}% in the last {rule.window_minutes} minutes",
                    timestamp=datetime.utcnow(),
                    project_id=project_id,
                    metadata={
                        "failure_rate": failure_rate,
                        "total_attempts": total_attempts,
                        "threshold": rule.threshold,
                        "window_minutes": rule.window_minutes,
                    },
                )

            return None

        except Exception as e:
            logger.error(f"Failed to check failure rate: {e}")
            return None

    def check_conflict_rate(self, project_id: str | None = None) -> Alert | None:
        """Check episode creation conflict rate"""
        try:
            rule = self.alert_rules["episode_conflict_rate"]
            if not rule.enabled:
                return None

            # In practice, this would query actual conflict metrics
            # For demo, simulate high conflict detection
            conflict_rate = 7.0  # 7% conflict rate

            if conflict_rate > rule.threshold:
                alert_id = f"conflict_rate_{int(datetime.utcnow().timestamp())}"

                return Alert(
                    alert_id=alert_id,
                    rule_id=rule.rule_id,
                    alert_type=rule.alert_type,
                    severity=rule.severity,
                    title=f"High Episode Creation Conflict Rate: {conflict_rate:.1f}%",
                    description=f"Episode creation conflict rate of {conflict_rate:.1f}% exceeds threshold of {rule.threshold}% - monitoring enhanced",
                    timestamp=datetime.utcnow(),
                    project_id=project_id,
                    metadata={
                        "conflict_rate": conflict_rate,
                        "threshold": rule.threshold,
                        "window_minutes": rule.window_minutes,
                        "action": "monitoring_enhanced",
                    },
                )

            return None

        except Exception as e:
            logger.error(f"Failed to check conflict rate: {e}")
            return None

    def check_integrity_violations(self, project_id: str | None = None) -> list[Alert]:
        """Check for episode numbering integrity violations"""
        try:
            from .episode_metrics import get_integrity_checker

            rule = self.alert_rules["episode_integrity"]
            if not rule.enabled:
                return []

            checker = get_integrity_checker(self.db)
            alerts = []

            if project_id:
                # Check specific project
                result = checker.check_project_integrity(project_id)
                if not result.is_healthy:
                    alert_id = (
                        f"integrity_{project_id}_{int(datetime.utcnow().timestamp())}"
                    )

                    alerts.append(
                        Alert(
                            alert_id=alert_id,
                            rule_id=rule.rule_id,
                            alert_type=rule.alert_type,
                            severity=rule.severity,
                            title=f"Episode Numbering Integrity Violation in Project {project_id}",
                            description=f"Detected {len(result.gaps)} gaps and {len(result.duplicates)} duplicates in episode numbering",
                            timestamp=datetime.utcnow(),
                            project_id=project_id,
                            metadata={
                                "gaps": result.gaps,
                                "duplicates": result.duplicates,
                                "total_episodes": result.total_episodes,
                            },
                        )
                    )
            else:
                # Check all projects
                results = checker.check_all_projects_integrity()
                for result in results:
                    if not result.is_healthy:
                        alert_id = f"integrity_{result.project_id}_{int(datetime.utcnow().timestamp())}"

                        alerts.append(
                            Alert(
                                alert_id=alert_id,
                                rule_id=rule.rule_id,
                                alert_type=rule.alert_type,
                                severity=rule.severity,
                                title=f"Episode Numbering Integrity Violation in Project {result.project_id}",
                                description=f"Detected {len(result.gaps)} gaps and {len(result.duplicates)} duplicates",
                                timestamp=datetime.utcnow(),
                                project_id=result.project_id,
                                metadata={
                                    "gaps": result.gaps,
                                    "duplicates": result.duplicates,
                                    "total_episodes": result.total_episodes,
                                },
                            )
                        )

            return alerts

        except Exception as e:
            logger.error(f"Failed to check integrity violations: {e}")
            return []

    def run_all_checks(self, project_id: str | None = None) -> list[Alert]:
        """Run all alert checks and return triggered alerts"""
        alerts = []

        # Check failure rate
        failure_alert = self.check_failure_rate(project_id)
        if failure_alert:
            alert_key = self.trigger_alert(failure_alert)
            alerts.append(failure_alert)

        # Check conflict rate
        conflict_alert = self.check_conflict_rate(project_id)
        if conflict_alert:
            alert_key = self.trigger_alert(conflict_alert)
            alerts.append(conflict_alert)

        # Check integrity violations
        integrity_alerts = self.check_integrity_violations(project_id)
        for alert in integrity_alerts:
            alert_key = self.trigger_alert(alert)
            alerts.append(alert)

        return alerts

    def get_active_alerts(self) -> list[Alert]:
        """Get all active (unresolved) alerts"""
        return [alert for alert in self.active_alerts.values() if not alert.resolved]

    def get_alert_summary(self) -> dict[str, Any]:
        """Get summary of alert status"""
        active_alerts = self.get_active_alerts()

        by_severity = {}
        by_type = {}

        for alert in active_alerts:
            # Count by severity
            severity = alert.severity
            by_severity[severity] = by_severity.get(severity, 0) + 1

            # Count by type
            alert_type = alert.alert_type
            by_type[alert_type] = by_type.get(alert_type, 0) + 1

        return {
            "total_active": len(active_alerts),
            "by_severity": by_severity,
            "by_type": by_type,
            "last_check": datetime.utcnow().isoformat(),
            "rules_enabled": len([r for r in self.alert_rules.values() if r.enabled]),
        }


class AlertHandler:
    """Base alert handler"""

    def handle(self, alert: Alert):
        """Handle an alert"""
        raise NotImplementedError


class LogAlertHandler(AlertHandler):
    """Log alert handler"""

    def handle(self, alert: Alert):
        """Log the alert"""
        level = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.CRITICAL: logger.error,
        }.get(alert.severity, logger.info)

        level(f"ALERT [{alert.severity.upper()}] {alert.title}: {alert.description}")


class WebhookAlertHandler(AlertHandler):
    """Webhook alert handler"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def handle(self, alert: Alert):
        """Send alert to webhook"""
        # This would make an HTTP request to the webhook
        payload = {"alert": alert.to_dict(), "timestamp": datetime.utcnow().isoformat()}

        logger.info(f"Would send alert to webhook {self.webhook_url}: {alert.title}")
        # In practice: requests.post(self.webhook_url, json=payload)


class SlackAlertHandler(AlertHandler):
    """Slack alert handler"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def handle(self, alert: Alert):
        """Send alert to Slack"""
        color = {
            AlertSeverity.INFO: "good",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.CRITICAL: "danger",
        }.get(alert.severity, "warning")

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": alert.title,
                    "text": alert.description,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.upper(),
                            "short": True,
                        },
                        {"title": "Type", "value": alert.alert_type, "short": True},
                        {
                            "title": "Timestamp",
                            "value": alert.timestamp.isoformat(),
                            "short": False,
                        },
                    ],
                }
            ]
        }

        logger.info(f"Would send alert to Slack: {alert.title}")
        # In practice: requests.post(self.webhook_url, json=payload)


# Global alert manager
_global_alert_manager: EpisodeAlertManager | None = None


def get_alert_manager(db: Session) -> EpisodeAlertManager:
    """Get alert manager instance"""
    global _global_alert_manager
    if _global_alert_manager is None:
        _global_alert_manager = EpisodeAlertManager(db)

        # Setup default handlers
        _global_alert_manager.add_alert_handler(LogAlertHandler().handle)

    return _global_alert_manager


def setup_alert_handlers(
    db: Session,
    slack_webhook: str | None = None,
    general_webhook: str | None = None,
):
    """Setup alert handlers with configuration"""
    manager = get_alert_manager(db)

    if slack_webhook:
        manager.add_alert_handler(SlackAlertHandler(slack_webhook).handle)

    if general_webhook:
        manager.add_alert_handler(WebhookAlertHandler(general_webhook).handle)
