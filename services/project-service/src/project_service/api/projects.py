"""
Projects API Router
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

try:
    # Prefer Core
    from ai_script_core import (
        ProjectCreateDTO,
        ProjectDTO,
        ProjectUpdateDTO,
        SuccessResponseDTO,
    )
except Exception:  # fallback
    from typing import Any

    from pydantic import BaseModel

    class ProjectDTO(BaseModel):
        id: str
        name: str
        type: str
        status: str | None = None
        description: str | None = None
        created_at: str | None = None
        updated_at: str | None = None

    class ProjectCreateDTO(BaseModel):
        name: str
        type: str
        description: str | None = None

    class ProjectUpdateDTO(BaseModel):
        name: str | None = None
        type: str | None = None
        description: str | None = None
        status: str | None = None

    class SuccessResponseDTO(BaseModel):
        success: bool = True
        message: str = "Success"
        data: Any = None


from ..database import get_db
from ..models.project import ProjectStatus, ProjectType
from ..services.project_service import NotFoundError, ProjectService, ValidationError

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=SuccessResponseDTO)
async def get_projects(
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(20, ge=1, le=100, description="가져올 항목 수"),
    search: str | None = Query(None, description="검색어"),
    project_type: ProjectType | None = Query(None, description="프로젝트 타입"),
    status: ProjectStatus | None = Query(None, description="프로젝트 상태"),
    db: Session = Depends(get_db),
):
    """프로젝트 목록 조회"""
    try:
        service = ProjectService(db)
        projects = service.get_projects(
            skip=skip,
            limit=limit,
            search=search,
            project_type=project_type,
            status=status,
        )

        return SuccessResponseDTO(
            success=True,
            message="프로젝트 목록을 성공적으로 조회했습니다.",
            data=projects,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/", response_model=SuccessResponseDTO, status_code=status.HTTP_201_CREATED
)
async def create_project(project_data: ProjectCreateDTO, db: Session = Depends(get_db)):
    """프로젝트 생성"""
    try:
        service = ProjectService(db)
        project = service.create_project(project_data)

        return SuccessResponseDTO(
            success=True, message="프로젝트가 성공적으로 생성되었습니다.", data=project
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{project_id}", response_model=SuccessResponseDTO)
async def get_project(
    project_id: str,
    include_episodes: bool = Query(False, description="에피소드 포함 여부"),
    db: Session = Depends(get_db),
):
    """프로젝트 상세 조회"""
    try:
        service = ProjectService(db)
        project = service.get_project(project_id, include_episodes=include_episodes)

        return SuccessResponseDTO(
            success=True, message="프로젝트를 성공적으로 조회했습니다.", data=project
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.put("/{project_id}", response_model=SuccessResponseDTO)
async def update_project(
    project_id: str, project_data: ProjectUpdateDTO, db: Session = Depends(get_db)
):
    """프로젝트 수정"""
    try:
        service = ProjectService(db)
        project = service.update_project(project_id, project_data)

        return SuccessResponseDTO(
            success=True, message="프로젝트가 성공적으로 수정되었습니다.", data=project
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete("/{project_id}", response_model=SuccessResponseDTO)
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """프로젝트 삭제"""
    try:
        service = ProjectService(db)
        success = service.delete_project(project_id)

        if success:
            return SuccessResponseDTO(
                success=True,
                message="프로젝트가 성공적으로 삭제되었습니다.",
                data={"deleted": True, "project_id": project_id},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="프로젝트 삭제에 실패했습니다.",
            )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.patch("/{project_id}/progress", response_model=SuccessResponseDTO)
async def update_project_progress(
    project_id: str,
    progress: float = Query(..., ge=0.0, le=100.0, description="진행률 (0-100)"),
    db: Session = Depends(get_db),
):
    """프로젝트 진행률 업데이트"""
    try:
        service = ProjectService(db)
        project = service.update_progress(project_id, progress)

        return SuccessResponseDTO(
            success=True,
            message="프로젝트 진행률이 성공적으로 업데이트되었습니다.",
            data=project,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/stats/summary", response_model=SuccessResponseDTO)
async def get_project_stats(db: Session = Depends(get_db)):
    """프로젝트 통계 조회"""
    try:
        service = ProjectService(db)
        stats = service.get_project_stats()

        return SuccessResponseDTO(
            success=True, message="프로젝트 통계를 성공적으로 조회했습니다.", data=stats
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/recent", response_model=SuccessResponseDTO)
async def get_recent_projects(
    limit: int = Query(10, ge=1, le=50, description="가져올 프로젝트 수"),
    db: Session = Depends(get_db),
):
    """최근 프로젝트 조회"""
    try:
        service = ProjectService(db)
        projects = service.get_recent_projects(limit)

        return SuccessResponseDTO(
            success=True,
            message="최근 프로젝트를 성공적으로 조회했습니다.",
            data=projects,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
