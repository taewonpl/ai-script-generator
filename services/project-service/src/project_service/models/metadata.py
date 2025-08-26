"""
Project Metadata SQLAlchemy Model for Project Service
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .project import Project


class ProjectMetadata(Base, TimestampMixin):
    """프로젝트 메타데이터 테이블 (캐릭터, 설정 등)"""

    __tablename__ = "project_metadata"

    # 기본 필드
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # "characters", "settings", "themes" 등

    # 데이터 (JSON 형태로 저장)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # 추가 정보
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 관계 설정
    project: Mapped["Project"] = relationship(
        "Project", back_populates="project_metadata"
    )

    def __repr__(self) -> str:
        return f"<ProjectMetadata(id='{self.id}', key='{self.key}', project_id='{self.project_id}')>"

    def to_dict(self) -> dict[str, Any]:
        """메타데이터를 딕셔너리로 변환"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
