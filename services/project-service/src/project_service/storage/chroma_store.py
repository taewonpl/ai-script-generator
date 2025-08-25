"""
ChromaDB integration for Episodes and Projects storage
"""

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

logger = logging.getLogger(__name__)


class ChromaStoreError(Exception):
    """ChromaDB store error"""

    pass


class EpisodeChromaStore:
    """ChromaDB store for Episodes with automatic number assignment"""

    def __init__(
        self, db_path: str = "./data/chroma", embedding_function: Any | None = None
    ):
        if not CHROMADB_AVAILABLE:
            raise ChromaStoreError(
                "ChromaDB is not available. Install with: pip install chromadb"
            )

        self.db_path = db_path
        self._client = None
        self._episodes_collection = None
        self._projects_collection = None
        self._lock = threading.Lock()  # For concurrency control

        # Initialize embedding function
        self.embedding_function = (
            embedding_function or embedding_functions.DefaultEmbeddingFunction()
        )

        # Initialize client
        self._initialize_client()

    def _initialize_client(self):
        """Initialize ChromaDB client and collections"""
        try:
            # Ensure directory exists
            os.makedirs(self.db_path, exist_ok=True)

            # Initialize client with persistent storage
            self._client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )

            # Get or create Episodes collection
            self._episodes_collection = self._client.get_or_create_collection(
                name="episodes",
                embedding_function=self.embedding_function,
                metadata={"created_by": "project_service", "type": "episodes"},
            )

            # Get or create Projects collection for metadata tracking
            self._projects_collection = self._client.get_or_create_collection(
                name="projects",
                embedding_function=self.embedding_function,
                metadata={"created_by": "project_service", "type": "projects"},
            )

            logger.info(
                f"ChromaDB initialized - Episodes: {self._episodes_collection.count()}, Projects: {self._projects_collection.count()}"
            )

        except Exception as e:
            error_msg = f"Failed to initialize ChromaDB client: {e!s}"
            logger.error(error_msg)
            raise ChromaStoreError(error_msg)

    def _get_next_episode_number(self, project_id: str) -> int:
        """Get next episode number for a project with concurrency handling"""
        with self._lock:
            try:
                # Get all episodes for this project
                existing_episodes = self._episodes_collection.get(
                    where={"project_id": project_id}, include=["metadatas"]
                )

                if not existing_episodes["metadatas"]:
                    return 1

                # Find maximum episode number
                max_number = 0
                for metadata in existing_episodes["metadatas"]:
                    episode_number = metadata.get("number", 0)
                    if episode_number > max_number:
                        max_number = episode_number

                return max_number + 1

            except Exception as e:
                logger.error(f"Error getting next episode number: {e!s}")
                raise ChromaStoreError(f"Failed to get next episode number: {e!s}")

    def create_episode(
        self,
        project_id: str,
        title: str | None = None,
        script_markdown: str = "",
        tokens: int = 0,
        prompt_snapshot: str = "",
    ) -> dict[str, Any]:
        """Create episode with automatic number assignment"""

        # Retry logic for concurrency handling
        max_retries = 3
        for attempt in range(max_retries):
            try:
                episode_id = str(uuid4())
                episode_number = self._get_next_episode_number(project_id)

                # Generate title if not provided
                if not title:
                    # Get project name for title generation
                    project_name = self._get_project_name(project_id)
                    title = f"{project_name} - Ep. {episode_number}"

                # Create episode metadata
                metadata = {
                    "project_id": project_id,
                    "number": episode_number,
                    "title": title,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "tokens": tokens,
                    "prompt_snapshot": prompt_snapshot,
                }

                # Add to ChromaDB
                self._episodes_collection.add(
                    documents=[script_markdown or f"Episode {episode_number}: {title}"],
                    metadatas=[metadata],
                    ids=[episode_id],
                )

                # Update project episode count
                self._update_project_episode_count(project_id)

                logger.info(
                    f"Created episode {episode_id} for project {project_id} with number {episode_number}"
                )

                return {
                    "episode_id": episode_id,
                    "project_id": project_id,
                    "number": episode_number,
                    "title": title,
                    "tokens": tokens,
                    "created_at": metadata["created_at"],
                }

            except Exception as e:
                if attempt < max_retries - 1:
                    # Brief delay before retry
                    time.sleep(0.1 * (attempt + 1))
                    logger.warning(
                        f"Episode creation attempt {attempt + 1} failed, retrying: {e!s}"
                    )
                    continue
                else:
                    logger.error(
                        f"Failed to create episode after {max_retries} attempts: {e!s}"
                    )
                    raise ChromaStoreError(f"Failed to create episode: {e!s}")

    def get_episodes_by_project(self, project_id: str) -> list[dict[str, Any]]:
        """Get all episodes for a project, sorted by number"""
        try:
            results = self._episodes_collection.get(
                where={"project_id": project_id}, include=["documents", "metadatas"]
            )

            episodes = []
            if results["metadatas"]:
                for i, metadata in enumerate(results["metadatas"]):
                    episode = {
                        "episode_id": results["ids"][i],
                        "project_id": metadata["project_id"],
                        "number": metadata["number"],
                        "title": metadata["title"],
                        "script_markdown": (
                            results["documents"][i] if results["documents"] else ""
                        ),
                        "tokens": metadata.get("tokens", 0),
                        "created_at": metadata["created_at"],
                        "prompt_snapshot": metadata.get("prompt_snapshot", ""),
                    }
                    episodes.append(episode)

            # Sort by episode number
            episodes.sort(key=lambda x: x["number"])

            logger.debug(f"Retrieved {len(episodes)} episodes for project {project_id}")
            return episodes

        except Exception as e:
            logger.error(f"Failed to get episodes for project {project_id}: {e!s}")
            raise ChromaStoreError(f"Failed to get episodes: {e!s}")

    def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        """Get a single episode by ID"""
        try:
            results = self._episodes_collection.get(
                ids=[episode_id], include=["documents", "metadatas"]
            )

            if not results["metadatas"]:
                return None

            metadata = results["metadatas"][0]
            return {
                "episode_id": episode_id,
                "project_id": metadata["project_id"],
                "number": metadata["number"],
                "title": metadata["title"],
                "script_markdown": (
                    results["documents"][0] if results["documents"] else ""
                ),
                "tokens": metadata.get("tokens", 0),
                "created_at": metadata["created_at"],
                "prompt_snapshot": metadata.get("prompt_snapshot", ""),
            }

        except Exception as e:
            logger.error(f"Failed to get episode {episode_id}: {e!s}")
            raise ChromaStoreError(f"Failed to get episode: {e!s}")

    def update_episode(
        self,
        episode_id: str,
        script_markdown: str | None = None,
        tokens: int | None = None,
        prompt_snapshot: str | None = None,
    ) -> bool:
        """Update episode content"""
        try:
            # Get current metadata
            current = self._episodes_collection.get(
                ids=[episode_id], include=["documents", "metadatas"]
            )

            if not current["metadatas"]:
                return False

            # Prepare updates
            metadata = current["metadatas"][0].copy()
            metadata["updated_at"] = datetime.now(timezone.utc).isoformat()

            if tokens is not None:
                metadata["tokens"] = tokens
            if prompt_snapshot is not None:
                metadata["prompt_snapshot"] = prompt_snapshot

            document = (
                script_markdown
                if script_markdown is not None
                else current["documents"][0]
            )

            # Update in ChromaDB
            self._episodes_collection.update(
                ids=[episode_id], documents=[document], metadatas=[metadata]
            )

            logger.info(f"Updated episode {episode_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update episode {episode_id}: {e!s}")
            raise ChromaStoreError(f"Failed to update episode: {e!s}")

    def delete_episode(self, episode_id: str) -> bool:
        """Delete an episode"""
        try:
            # Get episode info before deletion for project count update
            episode = self.get_episode(episode_id)
            if not episode:
                return False

            project_id = episode["project_id"]

            # Delete from ChromaDB
            self._episodes_collection.delete(ids=[episode_id])

            # Update project episode count
            self._update_project_episode_count(project_id)

            logger.info(f"Deleted episode {episode_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete episode {episode_id}: {e!s}")
            raise ChromaStoreError(f"Failed to delete episode: {e!s}")

    def _get_project_name(self, project_id: str) -> str:
        """Get project name from Projects collection"""
        try:
            results = self._projects_collection.get(
                ids=[project_id], include=["metadatas"]
            )

            if results["metadatas"]:
                return results["metadatas"][0].get("name", f"Project {project_id[:8]}")
            else:
                return f"Project {project_id[:8]}"

        except Exception:
            return f"Project {project_id[:8]}"

    def _update_project_episode_count(self, project_id: str):
        """Update episode count for a project"""
        try:
            # Count episodes for this project
            episodes = self._episodes_collection.get(
                where={"project_id": project_id}, include=["metadatas"]
            )
            episode_count = len(episodes["metadatas"]) if episodes["metadatas"] else 0

            # Check if project exists in Projects collection
            existing = self._projects_collection.get(
                ids=[project_id], include=["metadatas"]
            )

            if existing["metadatas"]:
                # Update existing project
                metadata = existing["metadatas"][0].copy()
                metadata["episode_count"] = episode_count
                metadata["updated_at"] = datetime.now(timezone.utc).isoformat()

                self._projects_collection.update(ids=[project_id], metadatas=[metadata])
            else:
                # Create new project entry
                metadata = {
                    "name": f"Project {project_id[:8]}",
                    "episode_count": episode_count,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

                self._projects_collection.add(
                    documents=[f"Project {project_id}"],
                    metadatas=[metadata],
                    ids=[project_id],
                )

            logger.debug(
                f"Updated project {project_id} episode count to {episode_count}"
            )

        except Exception as e:
            logger.warning(f"Failed to update project episode count: {e!s}")

    def register_project(self, project_id: str, project_name: str) -> bool:
        """Register a project in the Projects collection"""
        try:
            # Check if project already exists
            existing = self._projects_collection.get(
                ids=[project_id], include=["metadatas"]
            )

            if existing["metadatas"]:
                # Update existing project name
                metadata = existing["metadatas"][0].copy()
                metadata["name"] = project_name
                metadata["updated_at"] = datetime.now(timezone.utc).isoformat()

                self._projects_collection.update(ids=[project_id], metadatas=[metadata])
            else:
                # Create new project
                metadata = {
                    "name": project_name,
                    "episode_count": 0,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

                self._projects_collection.add(
                    documents=[f"Project: {project_name}"],
                    metadatas=[metadata],
                    ids=[project_id],
                )

            logger.info(f"Registered project {project_id}: {project_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to register project {project_id}: {e!s}")
            raise ChromaStoreError(f"Failed to register project: {e!s}")

    def get_collection_stats(self) -> dict[str, Any]:
        """Get collection statistics"""
        try:
            episodes_count = self._episodes_collection.count()
            projects_count = self._projects_collection.count()

            return {
                "episodes_count": episodes_count,
                "projects_count": projects_count,
                "db_path": self.db_path,
                "status": "healthy",
            }

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e!s}")
            return {
                "episodes_count": 0,
                "projects_count": 0,
                "db_path": self.db_path,
                "status": "unhealthy",
                "error": str(e),
            }
