"""
Episode SQLAlchemy Model for Project Service
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .project import Project


class EpisodeStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"


class Episode(Base, TimestampMixin):
    """에피소드 테이블"""

    __tablename__ = "episodes"
    __table_args__ = (
        UniqueConstraint("project_id", "number", name="uq_episode_project_number"),
    )

    # 기본 필드
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )

    # 에피소드 번호 및 순서, 상태
    number: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 자동 할당될 에피소드 번호
    order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 표시 순서
    status: Mapped[EpisodeStatus] = mapped_column(
        SAEnum(EpisodeStatus, name="episode_status", native_enum=False),
        nullable=False,
        default=EpisodeStatus.DRAFT,
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 상세 정보
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 분 단위
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 관계 설정
    project: Mapped[Project] = relationship("Project", back_populates="episodes")

    def __repr__(self) -> str:
        return f"<Episode(id='{self.id}', title='{self.title}', number={self.number})>"

    def to_dict(self) -> dict[str, Any]:
        """에피소드를 딕셔너리로 변환"""
        return {
            "id": self.id,
            "title": self.title,
            "project_id": self.project_id,
            "number": self.number,
            "order": self.order,
            "status": self.status.value,
            "is_published": self.is_published,
            "description": self.description,
            "duration": self.duration,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
