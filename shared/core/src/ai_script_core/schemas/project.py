"""
Project Schemas for AI Script Generator v3.0

프로젝트 관련 서비스 간 통신용 DTO를 정의합니다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from .base import BaseSchema, IDMixin, PaginatedResponse, TimestampMixin
from .common import ProjectStatus, ProjectType


class ProjectDTO(BaseSchema, IDMixin, TimestampMixin):
    """프로젝트 DTO (서비스 간 통신용)"""

    name: str = Field(..., description="프로젝트 이름")
    type: ProjectType = Field(..., description="프로젝트 타입")
    status: ProjectStatus = Field(..., description="프로젝트 상태")
    description: str | None = Field(None, description="프로젝트 설명")
    logline: str | None = Field(None, description="프로젝트 로그라인")
    progress_percentage: float = Field(
        default=0.0, ge=0.0, le=100.0, description="진행률"
    )
    deadline: datetime | None = Field(None, description="마감일")
    settings: dict[str, Any] = Field(default_factory=dict, description="프로젝트 설정")

    # 관계형 데이터 (서비스 간 통신시 포함 여부 결정)
    episodes_count: int = Field(default=0, description="에피소드 개수")
    metadata_count: int = Field(default=0, description="메타데이터 개수")


class ProjectCreateRequest(BaseSchema):
    """프로젝트 생성 요청 DTO"""

    name: str = Field(..., min_length=1, max_length=200, description="프로젝트 이름")
    type: ProjectType = Field(..., description="프로젝트 타입")
    description: str | None = Field(None, max_length=2000, description="프로젝트 설명")
    logline: str | None = Field(None, max_length=500, description="프로젝트 로그라인")
    deadline: datetime | None = Field(None, description="마감일")
    settings: dict[str, Any] = Field(default_factory=dict, description="프로젝트 설정")


class ProjectUpdateRequest(BaseSchema):
    """프로젝트 수정 요청 DTO"""

    name: str | None = Field(
        None, min_length=1, max_length=200, description="프로젝트 이름"
    )
    type: ProjectType | None = Field(None, description="프로젝트 타입")
    status: ProjectStatus | None = Field(None, description="프로젝트 상태")
    description: str | None = Field(None, max_length=2000, description="프로젝트 설명")
    logline: str | None = Field(None, max_length=500, description="프로젝트 로그라인")
    deadline: datetime | None = Field(None, description="마감일")
    settings: dict[str, Any] | None = Field(None, description="프로젝트 설정")


class ProjectListResponse(PaginatedResponse[ProjectDTO]):
    """프로젝트 목록 응답 DTO"""

    pass


class EpisodeDTO(BaseSchema, IDMixin, TimestampMixin):
    """에피소드 DTO (서비스 간 통신용)"""

    project_id: str = Field(..., description="프로젝트 ID")
    episode_number: int = Field(..., ge=1, description="에피소드 번호")
    title: str = Field(..., description="에피소드 제목")
    description: str | None = Field(None, description="에피소드 설명")
    duration_minutes: int | None = Field(None, ge=1, description="예상 재생 시간(분)")
    status: str = Field(default="draft", description="에피소드 상태")

    # 스크립트 관련
    script_content: str | None = Field(None, description="스크립트 내용")
    character_count: int = Field(default=0, description="등장인물 수")
    scene_count: int = Field(default=0, description="씬 개수")

    # 메타데이터
    tags: list[str] = Field(default_factory=list, description="태그 목록")
    notes: str | None = Field(None, description="에피소드 노트")


class EpisodeCreateRequest(BaseSchema):
    """에피소드 생성 요청 DTO"""

    project_id: str = Field(..., description="프로젝트 ID")
    episode_number: int = Field(..., ge=1, description="에피소드 번호")
    title: str = Field(..., min_length=1, max_length=200, description="에피소드 제목")
    description: str | None = Field(None, max_length=2000, description="에피소드 설명")
    duration_minutes: int | None = Field(
        None, ge=1, le=1440, description="예상 재생 시간(분)"
    )


class EpisodeUpdateRequest(BaseSchema):
    """에피소드 수정 요청 DTO"""

    title: str | None = Field(
        None, min_length=1, max_length=200, description="에피소드 제목"
    )
    description: str | None = Field(None, max_length=2000, description="에피소드 설명")
    duration_minutes: int | None = Field(
        None, ge=1, le=1440, description="예상 재생 시간(분)"
    )
    status: str | None = Field(None, description="에피소드 상태")
    script_content: str | None = Field(None, description="스크립트 내용")
    tags: list[str] | None = Field(None, description="태그 목록")
    notes: str | None = Field(None, description="에피소드 노트")


# 별칭(Alias) DTOs for backward compatibility
ProjectResponseDTO = ProjectDTO
ProjectCreateDTO = ProjectCreateRequest
ProjectUpdateDTO = ProjectUpdateRequest
EpisodeResponseDTO = EpisodeDTO
EpisodeCreateDTO = EpisodeCreateRequest
EpisodeUpdateDTO = EpisodeUpdateRequest
