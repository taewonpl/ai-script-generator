"""
Startup configuration for episode monitoring system
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from ..database.connection import get_session
from ..monitoring.episode_alerting import setup_alert_handlers
from ..monitoring.integrity_jobs import (
    IntegrityJobConfig,
    start_integrity_monitoring,
    stop_integrity_monitoring,
)

try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("project-service.monitoring-setup")
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]


async def initialize_episode_monitoring() -> None:
    """Initialize the episode monitoring system"""
    try:
        logger.info("Initializing episode monitoring system...")

        # Get database session
        db = get_session()

        try:
            # Setup alert handlers
            slack_webhook = None  # TODO: Get from environment
            general_webhook = None  # TODO: Get from environment

            setup_alert_handlers(
                db=db, slack_webhook=slack_webhook, general_webhook=general_webhook
            )

            # Configure integrity monitoring
            integrity_config = IntegrityJobConfig(
                enabled=True,
                check_interval_minutes=30,  # Run basic checks every 30 minutes
                deep_check_interval_hours=6,  # Run deep checks every 6 hours
                alert_on_issues=True,
                auto_fix_enabled=False,  # Keep disabled for safety
                max_projects_per_run=100,
            )

            # Start integrity monitoring background job
            await start_integrity_monitoring(db, integrity_config)

            logger.info("Episode monitoring system initialized successfully")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to initialize episode monitoring: {e}")
        raise


async def shutdown_episode_monitoring() -> None:
    """Shutdown the episode monitoring system"""
    try:
        logger.info("Shutting down episode monitoring system...")

        db = get_session()
        try:
            stop_integrity_monitoring(db)
            logger.info("Episode monitoring system shutdown complete")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error during monitoring system shutdown: {e}")


@asynccontextmanager
async def monitoring_lifespan() -> AsyncIterator[None]:
    """Lifespan context manager for monitoring system"""
    try:
        await initialize_episode_monitoring()
        yield
    finally:
        await shutdown_episode_monitoring()


# For FastAPI lifespan integration
async def monitoring_startup_event() -> None:
    """FastAPI startup event handler"""
    await initialize_episode_monitoring()


async def monitoring_shutdown_event() -> None:
    """FastAPI shutdown event handler"""
    await shutdown_episode_monitoring()


def register_monitoring_routes(app: Any) -> None:
    """Register monitoring routes with FastAPI app"""
    from ..api.monitoring import router as monitoring_router

    app.include_router(monitoring_router)
    logger.info("Episode monitoring routes registered")
