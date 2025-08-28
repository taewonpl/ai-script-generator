from __future__ import annotations

from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, selectinload

from ..models.project import Project, ProjectStatus, ProjectType
from .base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project model with domain-specific methods"""

    def __init__(self, db: Session):
        super().__init__(Project, db)

    def get_by_name(self, name: str) -> Project | None:
        """Get project by name"""
        return self.db.query(Project).filter(Project.name == name).first()

    def get_by_type(self, project_type: ProjectType) -> list[Project]:
        """Get all projects of a specific type"""
        return self.db.query(Project).filter(Project.type == project_type).all()

    def get_by_status(self, status: ProjectStatus) -> list[Project]:
        """Get all projects with a specific status"""
        return self.db.query(Project).filter(Project.status == status).all()

    def search_by_name(self, name_pattern: str) -> list[Project]:
        """Search projects by name pattern (case-insensitive)"""
        return (
            self.db.query(Project).filter(Project.name.ilike(f"%{name_pattern}%")).all()
        )

    def get_in_progress(self) -> list[Project]:
        """Get all projects that are currently in progress"""
        return (
            self.db.query(Project)
            .filter(Project.status == ProjectStatus.IN_PROGRESS)
            .all()
        )

    def get_completed(self) -> list[Project]:
        """Get all completed projects"""
        return (
            self.db.query(Project)
            .filter(Project.status == ProjectStatus.COMPLETED)
            .all()
        )

    def get_by_progress_range(
        self, min_progress: int, max_progress: int
    ) -> list[Project]:
        """Get projects within a specific progress percentage range"""
        return (
            self.db.query(Project)
            .filter(
                and_(
                    Project.progress_percentage >= min_progress,
                    Project.progress_percentage <= max_progress,
                )
            )
            .all()
        )

    def get_active_projects(self) -> list[Project]:
        """Get all active projects (planning, in_progress)"""
        return (
            self.db.query(Project)
            .filter(
                or_(
                    Project.status == ProjectStatus.PLANNING,
                    Project.status == ProjectStatus.IN_PROGRESS,
                )
            )
            .all()
        )

    def get_with_episodes(self, project_id: str) -> Project | None:
        """Get project with episodes loaded"""
        return (
            self.db.query(Project)
            .options(selectinload(Project.episodes))
            .filter(Project.id == project_id)
            .first()
        )

    def get_with_metadata(self, project_id: str) -> Project | None:
        """Get project with metadata loaded"""
        return (
            self.db.query(Project)
            .options(selectinload(Project.project_metadata))
            .filter(Project.id == project_id)
            .first()
        )

    def get_full_project(self, project_id: str) -> Project | None:
        """Get project with episodes and metadata loaded"""
        return (
            self.db.query(Project)
            .options(
                selectinload(Project.episodes), selectinload(Project.project_metadata)
            )
            .filter(Project.id == project_id)
            .first()
        )

    def search_projects(
        self,
        query: str | None = None,
        project_type: ProjectType | None = None,
        status: ProjectStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Project]:
        """Advanced project search with filters"""
        db_query = self.db.query(Project)

        if query:
            search_filter = or_(
                Project.name.ilike(f"%{query}%"),
                Project.description.ilike(f"%{query}%"),
            )
            db_query = db_query.filter(search_filter)

        if project_type:
            db_query = db_query.filter(Project.type == project_type)

        if status:
            db_query = db_query.filter(Project.status == status)

        return db_query.offset(skip).limit(limit).all()

    def get_recent_projects(self, limit: int = 10) -> list[Project]:
        """Get most recently updated projects"""
        return (
            self.db.query(Project)
            .order_by(Project.updated_at.desc())
            .limit(limit)
            .all()
        )

    def search(
        self, search_term: str, skip: int = 0, limit: int = 100
    ) -> list[Project]:
        return (
            self.db.query(Project)
            .filter(Project.name.ilike(f"%{search_term}%"))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_progress(
        self, project_id: str, progress_percentage: float | int
    ) -> Project | None:
        try:
            val = float(progress_percentage)
        except Exception:
            raise ValueError("Progress percentage must be a number between 0 and 100") from e
        if not (0.0 <= val <= 100.0):
            raise ValueError("Progress percentage must be between 0 and 100") from e
        progress_int = int(round(val))

        project = self.get_by_id(project_id)
        if not project:
            return None
        project.progress_percentage = progress_int

        if progress_int >= 100 and project.status != ProjectStatus.COMPLETED:
            project.status = ProjectStatus.COMPLETED

        self.db.commit()
        self.db.refresh(project)
        return project

    def update_status(self, project_id: str, status: ProjectStatus) -> Project | None:
        """Update project status"""
        return self.update(project_id, {"status": status})

    def get_project_stats(self) -> dict[str, Any]:
        """Get project statistics"""
        total_count = self.db.query(Project).count()

        # Status counts
        status_counts = {}
        for status in ProjectStatus:
            count = self.db.query(Project).filter(Project.status == status).count()
            status_counts[status.value] = count

        # Type counts
        type_counts = {}
        for project_type in ProjectType:
            count = self.db.query(Project).filter(Project.type == project_type).count()
            type_counts[project_type.value] = count

        # Average progress
        result = self.db.query(Project.progress_percentage).all()
        avg_progress = sum(p[0] for p in result) / len(result) if result else 0

        return {
            "total_projects": total_count,
            "status_counts": status_counts,
            "type_counts": type_counts,
            "average_progress": round(avg_progress, 2),
        }
