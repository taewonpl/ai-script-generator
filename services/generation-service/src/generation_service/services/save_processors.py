"""
Save processors for retry queue system
"""

from typing import Any

import httpx

from .retry_queue import JobType, get_retry_queue

try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("generation-service.save-processors")
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class SaveProcessors:
    """Collection of save processors for different job types"""

    def __init__(self, project_service_url: str = "http://localhost:8002"):
        self.project_service_url = project_service_url.rstrip("/")

    async def save_generation_processor(self, payload: dict[str, Any]) -> None:
        """Process generation save job"""
        generation_id = payload.get("generation_id")
        project_id = payload.get("project_id")
        episode_id = payload.get("episode_id")
        generation_data = payload.get("generation_data")

        if not all([generation_id, project_id, generation_data]):
            raise ValueError("Missing required fields for generation save")

        logger.info(f"Processing generation save: {generation_id}")

        # Simulate save to project service
        async with httpx.AsyncClient() as client:
            # Save generation result
            save_url = f"{self.project_service_url}/generations/{generation_id}/save"
            response = await client.post(
                save_url,
                json={
                    "project_id": project_id,
                    "episode_id": episode_id,
                    "generation_data": generation_data,
                    "status": "completed",
                },
                timeout=30.0,
            )

            if response.status_code not in [200, 201]:
                raise httpx.HTTPStatusError(
                    f"Failed to save generation {generation_id}: {response.status_code}",
                    request=response.request,
                    response=response,
                )

        logger.info(f"Successfully saved generation: {generation_id}")

    async def save_episode_processor(self, payload: dict[str, Any]) -> None:
        """Process episode save job"""
        project_id = payload.get("project_id")
        episode_data = payload.get("episode_data")

        if not all([project_id, episode_data]):
            raise ValueError("Missing required fields for episode save")

        episode_id = episode_data.get("id")
        logger.info(f"Processing episode save: {episode_id}")

        # Save to project service
        async with httpx.AsyncClient() as client:
            save_url = f"{self.project_service_url}/projects/{project_id}/episodes"

            # Check if episode exists (update) or create new
            if episode_id:
                # Update existing episode
                response = await client.put(
                    f"{save_url}/{episode_id}", json=episode_data, timeout=30.0
                )
            else:
                # Create new episode
                response = await client.post(save_url, json=episode_data, timeout=30.0)

            if response.status_code not in [200, 201]:
                raise httpx.HTTPStatusError(
                    f"Failed to save episode {episode_id}: {response.status_code}",
                    request=response.request,
                    response=response,
                )

        logger.info(f"Successfully saved episode: {episode_id}")

    async def save_project_processor(self, payload: dict[str, Any]) -> None:
        """Process project save job"""
        project_data = payload.get("project_data")

        if not project_data:
            raise ValueError("Missing required fields for project save")

        project_id = project_data.get("id")
        logger.info(f"Processing project save: {project_id}")

        # Save to project service
        async with httpx.AsyncClient() as client:
            if project_id:
                # Update existing project
                response = await client.put(
                    f"{self.project_service_url}/projects/{project_id}",
                    json=project_data,
                    timeout=30.0,
                )
            else:
                # Create new project
                response = await client.post(
                    f"{self.project_service_url}/projects",
                    json=project_data,
                    timeout=30.0,
                )

            if response.status_code not in [200, 201]:
                raise httpx.HTTPStatusError(
                    f"Failed to save project {project_id}: {response.status_code}",
                    request=response.request,
                    response=response,
                )

        logger.info(f"Successfully saved project: {project_id}")

    async def cleanup_cache_processor(self, payload: dict[str, Any]) -> None:
        """Process cache cleanup job"""
        cache_keys = payload.get("cache_keys", [])
        cache_patterns = payload.get("cache_patterns", [])

        logger.info(
            f"Processing cache cleanup: {len(cache_keys)} keys, {len(cache_patterns)} patterns"
        )

        # Implement cache cleanup logic here
        # This is a placeholder - actual implementation would clean Redis cache

        logger.info("Cache cleanup completed")


def register_save_processors(project_service_url: str = "http://localhost:8002"):
    """Register all save processors with the retry queue"""
    processors = SaveProcessors(project_service_url)
    queue = get_retry_queue()

    queue.register_processor(
        JobType.SAVE_GENERATION, processors.save_generation_processor
    )
    queue.register_processor(JobType.SAVE_EPISODE, processors.save_episode_processor)
    queue.register_processor(JobType.SAVE_PROJECT, processors.save_project_processor)
    queue.register_processor(JobType.CLEANUP_CACHE, processors.cleanup_cache_processor)

    logger.info("Registered all save processors")


# Utility functions for enqueueing specific job types
async def enqueue_generation_save(
    generation_id: str,
    project_id: str,
    episode_id: str,
    generation_data: dict[str, Any],
    delay_seconds: float = 0,
) -> str:
    """Enqueue generation save job"""
    queue = get_retry_queue()

    payload = {
        "generation_id": generation_id,
        "project_id": project_id,
        "episode_id": episode_id,
        "generation_data": generation_data,
    }

    return await queue.enqueue_job(
        JobType.SAVE_GENERATION, payload, delay_seconds=delay_seconds
    )


async def enqueue_episode_save(
    project_id: str, episode_data: dict[str, Any], delay_seconds: float = 0
) -> str:
    """Enqueue episode save job"""
    queue = get_retry_queue()

    payload = {"project_id": project_id, "episode_data": episode_data}

    return await queue.enqueue_job(
        JobType.SAVE_EPISODE, payload, delay_seconds=delay_seconds
    )


async def enqueue_project_save(
    project_data: dict[str, Any], delay_seconds: float = 0
) -> str:
    """Enqueue project save job"""
    queue = get_retry_queue()

    payload = {"project_data": project_data}

    return await queue.enqueue_job(
        JobType.SAVE_PROJECT, payload, delay_seconds=delay_seconds
    )
