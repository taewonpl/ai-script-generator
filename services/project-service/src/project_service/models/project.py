from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .episode import Episode
    from .metadata import ProjectMetadata


class ProjectType(str, Enum):
    DRAMA = "drama"
    COMEDY = "comedy"
    ROMANCE = "romance"
    THRILLER = "thriller"
    DOCUMENTARY = "documentary"
    WEB_SERIES = "web_series"
    SHORT_FILM = "short_film"
    ADVERTISEMENT = "advertisement"
    EDUCATION = "education"


class ProjectStatus(str, Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[ProjectType] = mapped_column(
        SAEnum(ProjectType, name="project_type", native_enum=False), nullable=False
    )
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus, name="project_status", native_enum=False),
        nullable=False,
        default=ProjectStatus.PLANNING,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_episode_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    episodes: Mapped[list[Episode]] = relationship(
        "Episode", back_populates="project", cascade="all, delete-orphan"
    )
    project_metadata: Mapped[list[ProjectMetadata]] = relationship(
        "ProjectMetadata", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"
