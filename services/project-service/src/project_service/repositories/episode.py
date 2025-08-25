from __future__ import annotations

from typing import Any

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from ..models.episode import Episode, EpisodeStatus
from .base import BaseRepository


class EpisodeRepository(BaseRepository[Episode]):
    """Repository for Episode model with domain-specific methods"""

    def __init__(self, db: Session):
        super().__init__(Episode, db)

    def get_by_project_id(self, project_id: str) -> list[Episode]:
        """Get all episodes for a specific project"""
        return self.db.query(Episode).filter(Episode.project_id == project_id).all()

    def get_by_status(self, status: EpisodeStatus) -> list[Episode]:
        """Get all episodes with a specific status"""
        return self.db.query(Episode).filter(Episode.status == status).all()

    def get_by_project_and_status(
        self, project_id: str, status: EpisodeStatus
    ) -> list[Episode]:
        """Get episodes for a project with specific status"""
        return (
            self.db.query(Episode)
            .filter(and_(Episode.project_id == project_id, Episode.status == status))
            .all()
        )

    def get_by_episode_number(
        self, project_id: str, episode_number: int
    ) -> Episode | None:
        """Get episode by project and episode number"""
        return (
            self.db.query(Episode)
            .filter(
                and_(Episode.project_id == project_id, Episode.number == episode_number)
            )
            .first()
        )

    def get_published_episodes(self, project_id: str) -> list[Episode]:
        """Get all published episodes for a project"""
        return (
            self.db.query(Episode)
            .filter(
                and_(Episode.project_id == project_id, Episode.is_published == True)
            )
            .order_by(Episode.order)
            .all()
        )

    def get_draft_episodes(self, project_id: str) -> list[Episode]:
        """Get all draft episodes for a project"""
        return (
            self.db.query(Episode)
            .filter(
                and_(Episode.project_id == project_id, Episode.is_published == False)
            )
            .order_by(Episode.order)
            .all()
        )

    def search_by_title(
        self, title_pattern: str, project_id: str | None = None
    ) -> list[Episode]:
        """Search episodes by title pattern"""
        query = self.db.query(Episode).filter(Episode.title.ilike(f"%{title_pattern}%"))

        if project_id:
            query = query.filter(Episode.project_id == project_id)

        return query.all()

    def get_episodes_by_duration_range(
        self, min_duration: int, max_duration: int
    ) -> list[Episode]:
        """Get episodes within a specific duration range"""
        return (
            self.db.query(Episode)
            .filter(
                and_(Episode.duration >= min_duration, Episode.duration <= max_duration)
            )
            .all()
        )

    def update_episode_order(self, episode_id: str, new_order: int) -> Episode | None:
        """Update episode order"""
        return self.update(episode_id, {"order": new_order})

    def publish_episode(self, episode_id: str) -> Episode | None:
        """Publish an episode"""
        return self.update(episode_id, {"is_published": True})

    def unpublish_episode(self, episode_id: str) -> Episode | None:
        """Unpublish an episode"""
        return self.update(episode_id, {"is_published": False})

    def get_by_project(self, project_id: str) -> list[Episode]:
        return self.get_by_project_id(project_id)

    def get_next_order(self, project_id: str) -> int:
        row = (
            self.db.query(Episode.order)
            .filter(Episode.project_id == project_id)
            .order_by(Episode.order.desc())
            .first()
        )
        return (row[0] + 1) if row and row[0] is not None else 1

    def get_next_episode_number_atomic(self, project_id: str) -> int:
        """Get the next available episode number atomically using project counter"""
        from sqlalchemy import text

        # Use atomic UPDATE to increment and return the counter
        result = self.db.execute(
            text(
                """
            UPDATE projects
            SET next_episode_number = next_episode_number + 1
            WHERE id = :project_id
            RETURNING next_episode_number - 1
            """
            ),
            {"project_id": project_id},
        )

        episode_number = result.fetchone()
        if episode_number is None:
            raise ValueError(f"Project {project_id} not found")

        return int(episode_number[0])

    def get_next_episode_number(self, project_id: str) -> int:
        """Get the next available episode number for a project (legacy method)"""
        max_number = (
            self.db.query(func.max(Episode.number))
            .filter(Episode.project_id == project_id)
            .scalar()
        )
        return (max_number + 1) if max_number is not None else 1

    def reorder_episodes(
        self, project_id: str, episode_orders: list[dict[str, Any]]
    ) -> bool:
        changed = False
        for item in episode_orders:
            eid = item.get("id")
            new_order = item.get("order")
            if eid is None or new_order is None:
                continue
            ep = self.get_by_id(eid)
            if ep and ep.project_id == project_id:
                ep.order = int(new_order)
                changed = True
        if changed:
            self.db.commit()
        return True
