"""
Project Business Logic Service
"""

import uuid
from typing import Any

# Use fallback DTOs - Core integration disabled for type stability
from pydantic import BaseModel
from sqlalchemy.orm import Session


class ProjectDTO(BaseModel):
    id: str
    name: str
    type: str
    status: str | None = None
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    logline: str | None = None
    deadline: str | None = None


class ProjectCreateDTO(BaseModel):
    name: str
    type: str
    description: str | None = None


class ProjectUpdateDTO(BaseModel):
    name: str | None = None
    type: str | None = None
    description: str | None = None
    status: str | None = None


class BaseServiceException(Exception): ...


from ..models.project import Project, ProjectStatus, ProjectType
from ..repositories.project import ProjectRepository


class NotFoundError(BaseServiceException):
    def __init__(
        self,
        entity: str = "Resource",
        resource_id: str | None = None,
        message: str | None = None,
    ):
        self.message = message or (
            f"{entity} not found" + (f": {resource_id}" if resource_id else "")
        )
        super().__init__(self.message)


class ValidationError(BaseServiceException):
    def __init__(self, field: str | None = None, message: str = "Validation error"):
        self.message = f"{field}: {message}" if field else message
        super().__init__(self.message)


# Temporary utility function
def generate_id(prefix: str | None = None) -> str:
    base_id = str(uuid.uuid4())
    return f"{prefix}_{base_id}" if prefix else base_id


class ProjectService:
    """프로젝트 비즈니스 로직 서비스"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = ProjectRepository(db)

    def create_project(self, project_data: ProjectCreateDTO) -> ProjectDTO:
        """프로젝트 생성"""
        # 프로젝트 ID 생성
        project_id = generate_id("proj")

        # 데이터베이스 객체 생성
        db_data: dict[str, Any] = {
            "id": project_id,
            "name": project_data.name,
            "type": project_data.type,
            "description": project_data.description,
            "progress_percentage": 0,
        }

        # 프로젝트 생성
        project = self.repository.create(db_data)

        return self._to_dto(project)

    def get_project(
        self, project_id: str, include_episodes: bool = False
    ) -> ProjectDTO:
        """프로젝트 조회"""
        if include_episodes:
            project = self.repository.get_with_episodes(project_id)
        else:
            project = self.repository.get(project_id)

        if not project:
            raise NotFoundError("Project", project_id)

        return self._to_dto(project)

    def get_projects(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        project_type: ProjectType | None = None,
        status: ProjectStatus | None = None,
    ) -> list[ProjectDTO]:
        """프로젝트 목록 조회"""
        if search or project_type or status:
            projects = self.repository.search_projects(
                query=search,
                project_type=project_type,
                status=status,
                skip=skip,
                limit=limit,
            )
        else:
            projects = self.repository.get_all(skip=skip, limit=limit)

        return [self._to_dto(project) for project in projects]

    def search_projects_simple(
        self, search_term: str, skip: int = 0, limit: int = 100
    ) -> list[ProjectDTO]:
        """간단한 텍스트 검색 (표준 Repository 패턴 사용)"""
        projects = self.repository.search(search_term, skip=skip, limit=limit)
        return [self._to_dto(project) for project in projects]

    def update_project(
        self, project_id: str, project_data: ProjectUpdateDTO
    ) -> ProjectDTO:
        """프로젝트 수정"""
        # 프로젝트 존재 확인
        if not self.repository.exists(project_id):
            raise NotFoundError("Project", project_id)

        # 업데이트할 데이터 필터링 (None이 아닌 값만)
        update_data = {}
        for field, value in project_data.model_dump().items():
            if value is not None:
                update_data[field] = value

        # 프로젝트 업데이트
        project = self.repository.update(project_id, update_data)
        if not project:
            raise NotFoundError("Project", project_id)

        return self._to_dto(project)

    def delete_project(self, project_id: str) -> bool:
        """프로젝트 삭제"""
        if not self.repository.exists(project_id):
            raise NotFoundError("Project", project_id)

        return self.repository.delete(project_id)

    def update_progress(self, project_id: str, progress: float) -> ProjectDTO:
        """프로젝트 진행률 업데이트"""
        if not (0.0 <= progress <= 100.0):
            raise ValidationError(
                "progress", f"Progress must be between 0 and 100, got {progress}"
            )

        project = self.repository.update_progress(project_id, progress)
        if not project:
            raise NotFoundError("Project", project_id)

        return self._to_dto(project)

    def get_recent_projects(self, limit: int = 10) -> list[ProjectDTO]:
        """최근 프로젝트 조회"""
        projects = self.repository.get_recent_projects(limit)
        return [self._to_dto(project) for project in projects]

    def get_project_stats(self) -> dict[str, Any]:
        """프로젝트 통계"""
        return self.repository.get_project_stats()

    def _to_dto(self, project: Project) -> ProjectDTO:
        """Project 모델을 DTO로 변환"""
        return ProjectDTO(
            id=project.id,
            name=project.name,
            type=project.type,
            status=project.status,
            description=project.description,
            created_at=project.created_at.isoformat() if project.created_at else None,
            updated_at=project.updated_at.isoformat() if project.updated_at else None,
            logline=None,  # Core module compatibility
            deadline=None,  # Core module compatibility
        )
