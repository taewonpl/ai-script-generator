"""
Startup initialization for retry queue system
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from ..services.retry_queue import start_retry_worker, stop_retry_worker
from ..services.save_processors import register_save_processors

try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("generation-service.retry-system")
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


async def initialize_retry_system() -> None:
    """Initialize the retry queue system"""
    try:
        # Register processors
        project_service_url = "http://localhost:8002"  # TODO: Get from config
        register_save_processors(project_service_url)

        # Start worker
        await start_retry_worker()

        logger.info("Retry queue system initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize retry system: {e}")
        raise


async def shutdown_retry_system() -> None:
    """Shutdown the retry queue system"""
    try:
        await stop_retry_worker()
        logger.info("Retry queue system shutdown complete")

    except Exception as e:
        logger.error(f"Error during retry system shutdown: {e}")


@asynccontextmanager
async def retry_system_lifespan() -> AsyncGenerator[None, None]:
    """Lifespan context manager for retry system"""
    try:
        await initialize_retry_system()
        yield
    finally:
        await shutdown_retry_system()


# For FastAPI lifespan integration
async def startup_event() -> None:
    """FastAPI startup event handler"""
    await initialize_retry_system()


async def shutdown_event() -> None:
    """FastAPI shutdown event handler"""
    await shutdown_retry_system()
