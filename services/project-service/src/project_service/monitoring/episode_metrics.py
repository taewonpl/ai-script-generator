"""
Episode numbering system monitoring and metrics collection
"""

import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("project-service.episode-metrics")
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]


class EpisodeMetricType(str, Enum):
    """Types of episode metrics"""

    GAPS_DETECTED = "episode_number_gaps_detected"
    DUPLICATES_DETECTED = "episode_number_duplicates_detected"
    CREATION_DURATION = "episode_creation_duration_seconds"
    CREATION_CONFLICTS = "episode_creation_conflicts_total"
    CREATION_RETRIES = "episode_creation_retry_count_total"
    CREATION_SUCCESS = "episode_creation_success_total"
    CREATION_FAILURES = "episode_creation_failures_total"


@dataclass
class EpisodeMetric:
    """Episode metric data point"""

    metric_type: EpisodeMetricType
    value: float
    project_id: str | None = None
    episode_id: str | None = None
    timestamp: datetime | None = None
    labels: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.labels is None:
            self.labels = {}


@dataclass
class IntegrityCheckResult:
    """Result of episode numbering integrity check"""

    project_id: str
    total_episodes: int
    expected_sequence: list[int]
    actual_numbers: list[int]
    gaps: list[int]
    duplicates: list[int]
    is_healthy: bool
    check_timestamp: datetime


class EpisodeMetricsCollector:
    """Collector for episode-related metrics"""

    def __init__(self, db: Session):
        self.db = db
        self.metrics_buffer: list[EpisodeMetric] = []

    def record_metric(self, metric: EpisodeMetric) -> None:
        """Record a single metric"""
        self.metrics_buffer.append(metric)
        logger.debug(f"Recorded metric: {metric.metric_type} = {metric.value}")

    def record_creation_duration(
        self,
        duration_seconds: float,
        project_id: str,
        episode_id: str,
        success: bool = True,
    ) -> None:
        """Record episode creation duration"""
        self.record_metric(
            EpisodeMetric(
                metric_type=EpisodeMetricType.CREATION_DURATION,
                value=duration_seconds,
                project_id=project_id,
                episode_id=episode_id,
                labels={"success": str(success).lower()},
            )
        )

        # Also record success/failure count
        if success:
            self.record_metric(
                EpisodeMetric(
                    metric_type=EpisodeMetricType.CREATION_SUCCESS,
                    value=1,
                    project_id=project_id,
                    episode_id=episode_id,
                )
            )
        else:
            self.record_metric(
                EpisodeMetric(
                    metric_type=EpisodeMetricType.CREATION_FAILURES,
                    value=1,
                    project_id=project_id,
                    episode_id=episode_id,
                )
            )

    def record_concurrency_conflict(
        self, project_id: str, episode_id: str | None = None
    ) -> None:
        """Record a concurrency conflict event"""
        self.record_metric(
            EpisodeMetric(
                metric_type=EpisodeMetricType.CREATION_CONFLICTS,
                value=1,
                project_id=project_id,
                episode_id=episode_id,
            )
        )

    def record_retry_attempt(self, project_id: str, episode_id: str | None = None) -> None:
        """Record a retry attempt"""
        self.record_metric(
            EpisodeMetric(
                metric_type=EpisodeMetricType.CREATION_RETRIES,
                value=1,
                project_id=project_id,
                episode_id=episode_id,
            )
        )

    def record_gaps_detected(self, project_id: str, gap_count: int) -> None:
        """Record episode number gaps detected"""
        self.record_metric(
            EpisodeMetric(
                metric_type=EpisodeMetricType.GAPS_DETECTED,
                value=gap_count,
                project_id=project_id,
            )
        )

    def record_duplicates_detected(self, project_id: str, duplicate_count: int) -> None:
        """Record episode number duplicates detected"""
        self.record_metric(
            EpisodeMetric(
                metric_type=EpisodeMetricType.DUPLICATES_DETECTED,
                value=duplicate_count,
                project_id=project_id,
            )
        )

    def flush_metrics(self) -> list[EpisodeMetric]:
        """Flush accumulated metrics and return them"""
        metrics = self.metrics_buffer.copy()
        self.metrics_buffer.clear()
        return metrics


class EpisodeIntegrityChecker:
    """Checks episode numbering integrity"""

    def __init__(self, db: Session):
        self.db = db

    def check_project_integrity(self, project_id: str) -> IntegrityCheckResult:
        """Check episode numbering integrity for a specific project"""
        try:
            # Get all episode numbers for the project
            query = text(
                """
                SELECT number, id, title
                FROM episodes
                WHERE project_id = :project_id
                ORDER BY number
            """
            )

            db_result = self.db.execute(query, {"project_id": project_id})
            episodes = db_result.fetchall()

            if not episodes:
                return IntegrityCheckResult(
                    project_id=project_id,
                    total_episodes=0,
                    expected_sequence=[],
                    actual_numbers=[],
                    gaps=[],
                    duplicates=[],
                    is_healthy=True,
                    check_timestamp=datetime.utcnow(),
                )

            actual_numbers = [episode.number for episode in episodes]
            total_episodes = len(actual_numbers)

            # Expected sequence should be 1, 2, 3, ..., max_number
            max_number = max(actual_numbers)
            expected_sequence = list(range(1, max_number + 1))

            # Find gaps (missing numbers)
            gaps = [num for num in expected_sequence if num not in actual_numbers]

            # Find duplicates
            seen = set()
            duplicates = []
            for num in actual_numbers:
                if num in seen and num not in duplicates:
                    duplicates.append(num)
                seen.add(num)

            is_healthy = len(gaps) == 0 and len(duplicates) == 0

            result = IntegrityCheckResult(
                project_id=project_id,
                total_episodes=total_episodes,
                expected_sequence=expected_sequence,
                actual_numbers=actual_numbers,
                gaps=gaps,
                duplicates=duplicates,
                is_healthy=is_healthy,
                check_timestamp=datetime.utcnow(),
            )

            # Record metrics
            metrics_collector = EpisodeMetricsCollector(self.db)
            metrics_collector.record_gaps_detected(project_id, len(gaps))
            metrics_collector.record_duplicates_detected(project_id, len(duplicates))

            if not is_healthy:
                logger.warning(
                    f"Integrity issues found in project {project_id}: "
                    f"{len(gaps)} gaps, {len(duplicates)} duplicates"
                )

            return result

        except Exception as e:
            logger.error(f"Failed to check integrity for project {project_id}: {e}")
            raise

    def check_all_projects_integrity(self) -> list[IntegrityCheckResult]:
        """Check integrity for all projects with episodes"""
        try:
            # Get all project IDs that have episodes
            query = text(
                """
                SELECT DISTINCT project_id
                FROM episodes
            """
            )

            result = self.db.execute(query)
            project_ids = [row.project_id for row in result.fetchall()]

            results = []
            for project_id in project_ids:
                try:
                    check_result = self.check_project_integrity(project_id)
                    results.append(check_result)
                except Exception as e:
                    logger.error(f"Failed to check project {project_id}: {e}")

            return results

        except Exception as e:
            logger.error(f"Failed to check all projects integrity: {e}")
            raise

    def get_integrity_summary(self) -> dict[str, Any]:
        """Get a summary of integrity status across all projects"""
        try:
            results = self.check_all_projects_integrity()

            total_projects = len(results)
            healthy_projects = len([r for r in results if r.is_healthy])
            total_gaps = sum(len(r.gaps) for r in results)
            total_duplicates = sum(len(r.duplicates) for r in results)
            total_episodes = sum(r.total_episodes for r in results)

            health_percentage = (
                (healthy_projects / total_projects * 100) if total_projects > 0 else 100
            )

            return {
                "total_projects": total_projects,
                "healthy_projects": healthy_projects,
                "unhealthy_projects": total_projects - healthy_projects,
                "health_percentage": health_percentage,
                "total_episodes": total_episodes,
                "total_gaps": total_gaps,
                "total_duplicates": total_duplicates,
                "check_timestamp": datetime.utcnow().isoformat(),
                "projects_with_issues": [
                    {
                        "project_id": r.project_id,
                        "gaps": len(r.gaps),
                        "duplicates": len(r.duplicates),
                    }
                    for r in results
                    if not r.is_healthy
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get integrity summary: {e}")
            raise


class EpisodePerformanceTracker:
    """Tracks episode creation performance metrics"""

    def __init__(self) -> None:
        self.active_operations: dict[str, float] = {}

    def start_operation(self, operation_id: str) -> str:
        """Start tracking an episode creation operation"""
        self.active_operations[operation_id] = time.time()
        return operation_id

    def end_operation(
        self,
        operation_id: str,
        db: Session,
        project_id: str,
        episode_id: str | None = None,
        success: bool = True,
        retry_count: int = 0,
        had_conflict: bool = False,
    ) -> float:
        """End tracking an operation and record metrics"""
        if operation_id not in self.active_operations:
            logger.warning(f"Unknown operation ID: {operation_id}")
            return 0.0

        start_time = self.active_operations.pop(operation_id)
        duration = time.time() - start_time

        # Record metrics
        collector = EpisodeMetricsCollector(db)
        collector.record_creation_duration(duration, project_id, episode_id or "unknown", success)

        if retry_count > 0:
            for _ in range(retry_count):
                collector.record_retry_attempt(project_id, episode_id or "unknown")

        if had_conflict:
            collector.record_concurrency_conflict(project_id, episode_id or "unknown")

        # Flush metrics (in a real implementation, this would send to monitoring system)
        metrics = collector.flush_metrics()

        return duration


# Global instances
_global_integrity_checker: EpisodeIntegrityChecker | None = None
_global_performance_tracker: EpisodePerformanceTracker | None = None


def get_integrity_checker(db: Session) -> EpisodeIntegrityChecker:
    """Get integrity checker instance"""
    return EpisodeIntegrityChecker(db)


def get_performance_tracker() -> EpisodePerformanceTracker:
    """Get global performance tracker instance"""
    global _global_performance_tracker
    if _global_performance_tracker is None:
        _global_performance_tracker = EpisodePerformanceTracker()
    return _global_performance_tracker


def get_metrics_collector(db: Session) -> EpisodeMetricsCollector:
    """Get metrics collector instance"""
    return EpisodeMetricsCollector(db)
