"""
Episode Service with ChromaDB integration
"""

import logging
import os
from typing import Any

import tiktoken

from ..storage.chroma_store import ChromaStoreError, EpisodeChromaStore

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """Estimate token count for text"""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
        return len(encoding.encode(text))
    except Exception:
        # Fallback: rough estimation (1 token ≈ 4 characters)
        return len(text) // 4


class EpisodeChromaError(Exception):
    """Episode service error"""

    pass


class EpisodeChromaService:
    """Episode service with ChromaDB backend"""

    def __init__(self, chroma_db_path: str | None = None):
        self.chroma_db_path = chroma_db_path or os.getenv(
            "CHROMA_DB_PATH", "./data/chroma"
        )

        try:
            self.chroma_store = EpisodeChromaStore(
                db_path=self.chroma_db_path or "./data/chroma"
            )
            logger.info(
                f"EpisodeChromaService initialized with ChromaDB at {self.chroma_db_path}"
            )
        except ChromaStoreError as e:
            logger.error(f"Failed to initialize ChromaDB: {e!s}")
            raise EpisodeChromaError(f"Failed to initialize ChromaDB: {e!s}")

    def create_episode(
        self,
        project_id: str,
        title: str | None = None,
        script: dict[str, Any] | None = None,
        prompt_snapshot: str = "",
    ) -> dict[str, Any]:
        """
        Create episode with automatic number assignment

        Args:
            project_id: Project ID
            title: Optional episode title (auto-generated if not provided)
            script: Optional script data with 'markdown' and 'tokens' keys
            prompt_snapshot: Prompt used for generation

        Returns:
            Dict with episode data including auto-assigned number
        """
        try:
            # Extract script data
            script_markdown = ""
            tokens = 0

            if script:
                script_markdown = script.get("markdown", "")
                tokens = script.get("tokens", 0)

                # Auto-calculate tokens if not provided
                if tokens == 0 and script_markdown:
                    tokens = estimate_tokens(script_markdown)

            # Create episode in ChromaDB
            result = self.chroma_store.create_episode(
                project_id=project_id,
                title=title,
                script_markdown=script_markdown,
                tokens=tokens,
                prompt_snapshot=prompt_snapshot,
            )

            logger.info(
                f"Created episode {result['episode_id']} for project {project_id}"
            )

            return {
                "id": result["episode_id"],
                "projectId": project_id,
                "number": result["number"],
                "title": result["title"],
                "script": (
                    {"markdown": script_markdown, "tokens": tokens}
                    if script_markdown
                    else None
                ),
                "promptSnapshot": prompt_snapshot,
                "createdAt": result["created_at"],
            }

        except ChromaStoreError as e:
            logger.error(f"ChromaDB error creating episode: {e!s}")
            raise EpisodeChromaError(f"Failed to create episode: {e!s}")
        except Exception as e:
            logger.error(f"Unexpected error creating episode: {e!s}")
            raise EpisodeChromaError(f"Failed to create episode: {e!s}")

    def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        """Get episode by ID"""
        try:
            episode = self.chroma_store.get_episode(episode_id)

            if not episode:
                return None

            return {
                "id": episode["episode_id"],
                "projectId": episode["project_id"],
                "number": episode["number"],
                "title": episode["title"],
                "script": (
                    {
                        "markdown": episode["script_markdown"],
                        "tokens": episode["tokens"],
                    }
                    if episode["script_markdown"]
                    else None
                ),
                "promptSnapshot": episode["prompt_snapshot"],
                "createdAt": episode["created_at"],
            }

        except ChromaStoreError as e:
            logger.error(f"ChromaDB error getting episode {episode_id}: {e!s}")
            raise EpisodeChromaError(f"Failed to get episode: {e!s}")
        except Exception as e:
            logger.error(f"Unexpected error getting episode {episode_id}: {e!s}")
            raise EpisodeChromaError(f"Failed to get episode: {e!s}")

    def get_episodes_by_project(self, project_id: str) -> list[dict[str, Any]]:
        """Get all episodes for a project, sorted by episode number"""
        try:
            episodes = self.chroma_store.get_episodes_by_project(project_id)

            # Convert to API format
            result = []
            for episode in episodes:
                result.append(
                    {
                        "id": episode["episode_id"],
                        "projectId": episode["project_id"],
                        "number": episode["number"],
                        "title": episode["title"],
                        "script": (
                            {
                                "markdown": episode["script_markdown"],
                                "tokens": episode["tokens"],
                            }
                            if episode["script_markdown"]
                            else None
                        ),
                        "promptSnapshot": episode["prompt_snapshot"],
                        "createdAt": episode["created_at"],
                    }
                )

            logger.debug(f"Retrieved {len(result)} episodes for project {project_id}")
            return result

        except ChromaStoreError as e:
            logger.error(
                f"ChromaDB error getting episodes for project {project_id}: {e!s}"
            )
            raise EpisodeChromaError(f"Failed to get episodes: {e!s}")
        except Exception as e:
            logger.error(
                f"Unexpected error getting episodes for project {project_id}: {e!s}"
            )
            raise EpisodeChromaError(f"Failed to get episodes: {e!s}")

    def update_episode_script(
        self,
        episode_id: str,
        script: dict[str, Any],
        prompt_snapshot: str | None = None,
    ) -> bool:
        """Update episode script content"""
        try:
            script_markdown = script.get("markdown", "")
            tokens = script.get("tokens", 0)

            # Auto-calculate tokens if not provided
            if tokens == 0 and script_markdown:
                tokens = estimate_tokens(script_markdown)

            result = self.chroma_store.update_episode(
                episode_id=episode_id,
                script_markdown=script_markdown,
                tokens=tokens,
                prompt_snapshot=prompt_snapshot,
            )

            if result:
                logger.info(f"Updated script for episode {episode_id}")

            return result

        except ChromaStoreError as e:
            logger.error(f"ChromaDB error updating episode {episode_id}: {e!s}")
            raise EpisodeChromaError(f"Failed to update episode: {e!s}")
        except Exception as e:
            logger.error(f"Unexpected error updating episode {episode_id}: {e!s}")
            raise EpisodeChromaError(f"Failed to update episode: {e!s}")

    def delete_episode(self, episode_id: str) -> bool:
        """Delete episode"""
        try:
            result = self.chroma_store.delete_episode(episode_id)

            if result:
                logger.info(f"Deleted episode {episode_id}")

            return result

        except ChromaStoreError as e:
            logger.error(f"ChromaDB error deleting episode {episode_id}: {e!s}")
            raise EpisodeChromaError(f"Failed to delete episode: {e!s}")
        except Exception as e:
            logger.error(f"Unexpected error deleting episode {episode_id}: {e!s}")
            raise EpisodeChromaError(f"Failed to delete episode: {e!s}")

    def register_project(self, project_id: str, project_name: str) -> bool:
        """Register a project for episode tracking"""
        try:
            result = self.chroma_store.register_project(project_id, project_name)

            if result:
                logger.info(f"Registered project {project_id}: {project_name}")

            return result

        except ChromaStoreError as e:
            logger.error(f"ChromaDB error registering project {project_id}: {e!s}")
            raise EpisodeChromaError(f"Failed to register project: {e!s}")
        except Exception as e:
            logger.error(f"Unexpected error registering project {project_id}: {e!s}")
            raise EpisodeChromaError(f"Failed to register project: {e!s}")

    def get_next_episode_number(self, project_id: str) -> int:
        """Get the next episode number for a project"""
        try:
            episodes = self.chroma_store.get_episodes_by_project(project_id)

            if not episodes:
                return 1

            # Find the maximum episode number
            max_number: int = max(episode["number"] for episode in episodes)
            return max_number + 1

        except ChromaStoreError as e:
            logger.error(
                f"ChromaDB error getting next episode number for project {project_id}: {e!s}"
            )
            raise EpisodeChromaError(f"Failed to get next episode number: {e!s}")
        except Exception as e:
            logger.error(
                f"Unexpected error getting next episode number for project {project_id}: {e!s}"
            )
            raise EpisodeChromaError(f"Failed to get next episode number: {e!s}")

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics"""
        try:
            return self.chroma_store.get_collection_stats()
        except Exception as e:
            logger.error(f"Error getting stats: {e!s}")
            return {
                "episodes_count": 0,
                "projects_count": 0,
                "status": "error",
                "error": str(e),
            }
