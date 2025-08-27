"""
Automated integrity check jobs for episode numbering system
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from .episode_alerting import Alert, AlertSeverity, AlertType, get_alert_manager
from .episode_metrics import IntegrityCheckResult, get_integrity_checker

try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("project-service.integrity-jobs")
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]


@dataclass
class IntegrityJobConfig:
    """Configuration for integrity check jobs"""

    enabled: bool = True
    check_interval_minutes: int = 30
    deep_check_interval_hours: int = 6
    alert_on_issues: bool = True
    auto_fix_enabled: bool = False
    max_projects_per_run: int = 100


class EpisodeIntegrityJob:
    """Background job for checking episode numbering integrity"""

    def __init__(self, db: Session, config: Optional[IntegrityJobConfig] = None):
        self.db = db
        self.config = config or IntegrityJobConfig()
        self.is_running = False
        self.last_check: Optional[datetime] = None
        self.last_deep_check: Optional[datetime] = None
        self.stats: dict[str, Any] = {
            "total_runs": 0,
            "total_projects_checked": 0,
            "total_issues_found": 0,
            "last_run_duration": 0.0,
            "avg_run_duration": 0.0,
        }

    async def run_basic_check(self) -> dict[str, Any]:
        """Run basic integrity check on all projects"""
        if not self.config.enabled:
            return {"status": "disabled"}

        start_time = time.time()
        logger.info("Starting basic episode integrity check")

        try:
            checker = get_integrity_checker(self.db)
            alert_manager = get_alert_manager(self.db)

            # Get integrity summary
            summary = checker.get_integrity_summary()

            # Check if we need to trigger alerts
            if (
                self.config.alert_on_issues
                and summary["total_gaps"] + summary["total_duplicates"] > 0
            ):
                # Create summary alert
                alert = Alert(
                    alert_id=f"integrity_summary_{int(datetime.utcnow().timestamp())}",
                    rule_id="episode_integrity",
                    alert_type=AlertType.INTEGRITY_VIOLATION,
                    severity=AlertSeverity.WARNING,
                    title="Episode Integrity Issues Found",
                    description=f"Found {summary['total_gaps']} gaps and {summary['total_duplicates']} duplicates across {summary['unhealthy_projects']} projects",
                    timestamp=datetime.utcnow(),
                    metadata=summary,
                )

                alert_manager.trigger_alert(alert)

            duration = time.time() - start_time
            self.last_check = datetime.utcnow()
            self.stats["total_runs"] += 1
            self.stats["last_run_duration"] = duration
            self.stats["avg_run_duration"] = (
                self.stats["avg_run_duration"] * (self.stats["total_runs"] - 1)
                + duration
            ) / self.stats["total_runs"]

            result = {
                "status": "completed",
                "duration_seconds": duration,
                "summary": summary,
                "timestamp": self.last_check.isoformat() if self.last_check else "",
            }

            logger.info(f"Basic integrity check completed in {duration:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Basic integrity check failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def run_deep_check(self) -> dict[str, Any]:
        """Run detailed integrity check with project-by-project analysis"""
        if not self.config.enabled:
            return {"status": "disabled"}

        start_time = time.time()
        logger.info("Starting deep episode integrity check")

        try:
            checker = get_integrity_checker(self.db)
            alert_manager = get_alert_manager(self.db)

            # Get detailed results for all projects
            results = checker.check_all_projects_integrity()

            # Analyze results
            project_issues = []
            total_issues = 0

            for result in results[: self.config.max_projects_per_run]:
                if not result.is_healthy:
                    issue_count = len(result.gaps) + len(result.duplicates)
                    total_issues += issue_count

                    project_issues.append(
                        {
                            "project_id": result.project_id,
                            "total_episodes": result.total_episodes,
                            "gaps": result.gaps,
                            "duplicates": result.duplicates,
                            "issue_count": issue_count,
                            "health_score": self._calculate_health_score(result),
                        }
                    )

                    # Create individual project alert for severe issues
                    if issue_count > 5 and self.config.alert_on_issues:
                        alert = Alert(
                            alert_id=f"severe_integrity_{result.project_id}_{int(datetime.utcnow().timestamp())}",
                            rule_id="episode_integrity",
                            alert_type=AlertType.INTEGRITY_VIOLATION,
                            severity=AlertSeverity.CRITICAL,
                            title=f"Severe Episode Integrity Issues in Project {result.project_id}",
                            description=f"Project has {len(result.gaps)} gaps and {len(result.duplicates)} duplicates affecting {issue_count} episodes",
                            timestamp=datetime.utcnow(),
                            project_id=result.project_id,
                            metadata={
                                "gaps": result.gaps,
                                "duplicates": result.duplicates,
                                "total_episodes": result.total_episodes,
                                "health_score": self._calculate_health_score(result),
                            },
                        )

                        alert_manager.trigger_alert(alert)

            duration = time.time() - start_time
            self.last_deep_check = datetime.utcnow()
            self.stats["total_projects_checked"] += len(results)
            self.stats["total_issues_found"] += total_issues

            deep_check_result: dict[str, Any] = {
                "status": "completed",
                "duration_seconds": duration,
                "projects_checked": len(results),
                "projects_with_issues": len(project_issues),
                "total_issues": total_issues,
                "project_issues": project_issues,
                "timestamp": (
                    self.last_deep_check.isoformat() if self.last_deep_check else ""
                ),
            }

            logger.info(
                f"Deep integrity check completed in {duration:.2f}s - "
                f"found issues in {len(project_issues)}/{len(results)} projects"
            )
            return deep_check_result

        except Exception as e:
            logger.error(f"Deep integrity check failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _calculate_health_score(self, result: IntegrityCheckResult) -> float:
        """Calculate health score for a project (0-100)"""
        if result.total_episodes == 0:
            return 100.0

        issue_count = len(result.gaps) + len(result.duplicates)
        health_score = max(0, 100 - (issue_count / result.total_episodes * 100))
        return round(health_score, 2)

    async def run_continuous_monitoring(self) -> None:
        """Run continuous monitoring loop"""
        self.is_running = True
        logger.info("Starting continuous episode integrity monitoring")

        try:
            while self.is_running:
                try:
                    # Run basic check
                    await self.run_basic_check()

                    # Check if it's time for deep check
                    if (
                        not self.last_deep_check
                        or datetime.utcnow() - self.last_deep_check
                        > timedelta(hours=self.config.deep_check_interval_hours)
                    ):
                        await self.run_deep_check()

                    # Wait for next check interval
                    await asyncio.sleep(self.config.check_interval_minutes * 60)

                except Exception as e:
                    logger.error(f"Error in integrity monitoring loop: {e}")
                    await asyncio.sleep(60)  # Wait 1 minute on error

        except asyncio.CancelledError:
            logger.info("Integrity monitoring cancelled")
        finally:
            self.is_running = False

    def stop_monitoring(self) -> None:
        """Stop continuous monitoring"""
        self.is_running = False

    def get_stats(self) -> dict[str, Any]:
        """Get monitoring statistics"""
        return {
            **self.stats,
            "is_running": self.is_running,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_deep_check": (
                self.last_deep_check.isoformat() if self.last_deep_check else None
            ),
            "config": {
                "enabled": self.config.enabled,
                "check_interval_minutes": self.config.check_interval_minutes,
                "deep_check_interval_hours": self.config.deep_check_interval_hours,
                "alert_on_issues": self.config.alert_on_issues,
            },
        }


class IntegrityAutoFixer:
    """Automated fixer for episode numbering issues (use with caution)"""

    def __init__(self, db: Session):
        self.db = db

    async def fix_gaps(self, project_id: str, dry_run: bool = True) -> dict[str, Any]:
        """Attempt to fix episode number gaps by renumbering"""
        logger.warning(
            f"Gap fixing requested for project {project_id} (dry_run={dry_run})"
        )

        try:
            # Get current episodes ordered by their creation time or order field
            from sqlalchemy import text

            query = text(
                """
                SELECT id, number, title, "order"
                FROM episodes
                WHERE project_id = :project_id
                ORDER BY "order", created_at
            """
            )

            result = self.db.execute(query, {"project_id": project_id})
            episodes = result.fetchall()

            if not episodes:
                return {"status": "no_episodes", "changes": []}

            changes = []

            # Renumber episodes sequentially
            for i, episode in enumerate(episodes, 1):
                if episode.number != i:
                    changes.append(
                        {
                            "episode_id": episode.id,
                            "old_number": episode.number,
                            "new_number": i,
                            "title": episode.title,
                        }
                    )

            if not dry_run and changes:
                # Apply changes
                for change in changes:
                    update_query = text(
                        """
                        UPDATE episodes
                        SET number = :new_number
                        WHERE id = :episode_id
                    """
                    )

                    self.db.execute(
                        update_query,
                        {
                            "new_number": change["new_number"],
                            "episode_id": change["episode_id"],
                        },
                    )

                self.db.commit()
                logger.info(
                    f"Applied {len(changes)} numbering fixes for project {project_id}"
                )

            return {
                "status": "completed",
                "dry_run": dry_run,
                "changes_needed": len(changes),
                "changes": changes,
            }

        except Exception as e:
            logger.error(f"Failed to fix gaps for project {project_id}: {e}")
            if not dry_run:
                self.db.rollback()
            return {"status": "failed", "error": str(e)}


# Global instances
_global_integrity_job: Optional[EpisodeIntegrityJob] = None


def get_integrity_job(
    db: Session, config: Optional[IntegrityJobConfig] = None
) -> EpisodeIntegrityJob:
    """Get global integrity job instance"""
    global _global_integrity_job
    if _global_integrity_job is None:
        _global_integrity_job = EpisodeIntegrityJob(db, config)
    return _global_integrity_job


async def start_integrity_monitoring(
    db: Session, config: Optional[IntegrityJobConfig] = None
) -> Optional[asyncio.Task[None]]:
    """Start integrity monitoring background job"""
    job = get_integrity_job(db, config)
    if not job.is_running:
        task = asyncio.create_task(job.run_continuous_monitoring())
        logger.info("Episode integrity monitoring started")
        return task
    else:
        logger.info("Episode integrity monitoring already running")
        return None


def stop_integrity_monitoring(db: Session) -> None:
    """Stop integrity monitoring background job"""
    job = get_integrity_job(db)
    job.stop_monitoring()
    logger.info("Episode integrity monitoring stopped")
