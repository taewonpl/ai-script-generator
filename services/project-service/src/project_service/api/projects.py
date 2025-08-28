"""
Projects API Router
"""

# Use service DTOs for consistency
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi import status as http_status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..services.project_service import ProjectCreateDTO, ProjectUpdateDTO

logger = logging.getLogger(__name__)


class SuccessResponseDTO(BaseModel):
    success: bool = True
    message: str = "Success"
    data: Any = None
    error: str | None = None


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
) -> SuccessResponseDTO:
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
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None


@router.post(
    "/", response_model=SuccessResponseDTO, status_code=http_status.HTTP_201_CREATED
)
async def create_project(
    project_data: ProjectCreateDTO, db: Session = Depends(get_db)
) -> SuccessResponseDTO:
    """프로젝트 생성"""
    try:
        service = ProjectService(db)
        project = service.create_project(project_data)

        return SuccessResponseDTO(
            success=True, message="프로젝트가 성공적으로 생성되었습니다.", data=project
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None


@router.get("/{project_id}", response_model=SuccessResponseDTO)
async def get_project(
    project_id: str,
    include_episodes: bool = Query(False, description="에피소드 포함 여부"),
    db: Session = Depends(get_db),
) -> SuccessResponseDTO:
    """프로젝트 상세 조회"""
    try:
        service = ProjectService(db)
        project = service.get_project(project_id, include_episodes=include_episodes)

        return SuccessResponseDTO(
            success=True, message="프로젝트를 성공적으로 조회했습니다.", data=project
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None


@router.put("/{project_id}", response_model=SuccessResponseDTO)
async def update_project(
    project_id: str, project_data: ProjectUpdateDTO, db: Session = Depends(get_db)
) -> SuccessResponseDTO:
    """프로젝트 수정"""
    try:
        service = ProjectService(db)
        project = service.update_project(project_id, project_data)

        return SuccessResponseDTO(
            success=True, message="프로젝트가 성공적으로 수정되었습니다.", data=project
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None


@router.delete("/{project_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    request: Request,
    x_delete_id: str = Header(None, alias="X-Delete-Id"),
    db: Session = Depends(get_db),
) -> None:
    """
    프로젝트 삭제 (production-grade with idempotency and business logic guards)
    
    - Idempotency: X-Delete-Id 헤더로 중복 방지
    - Business Logic: 활성 생성 작업 체크
    - 404는 성공으로 처리 (already deleted)
    - 409는 충돌 (active generation jobs)
    """
    request_id = str(uuid4())
    trace_id = getattr(request.state, 'trace_id', str(uuid4()))
    delete_id = x_delete_id or str(uuid4())

    # Structured logging context
    log_context = {
        "action": "delete_project",
        "project_id": project_id,
        "delete_id": delete_id,
        "request_id": request_id,
        "trace_id": trace_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    logger.info("Project deletion requested", extra=log_context)

    try:
        # Check for idempotency - if this delete_id was already processed
        idempotency_check_query = text("""
            SELECT COUNT(*) as count FROM project_deletions
            WHERE delete_id = :delete_id
        """)
        result = db.execute(idempotency_check_query, {"delete_id": delete_id})
        existing_count = result.fetchone()[0]

        if existing_count > 0:
            logger.info("Duplicate delete request ignored", extra={**log_context, "idempotent": True})
            return  # 204 No Content - idempotent success

        # Create deletions tracking table if not exists
        create_table_query = text("""
            CREATE TABLE IF NOT EXISTS project_deletions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                delete_id TEXT UNIQUE NOT NULL,
                project_id TEXT NOT NULL,
                deleted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                request_id TEXT NOT NULL,
                trace_id TEXT NOT NULL
            )
        """)
        db.execute(create_table_query)

        # Check if project exists
        service = ProjectService(db)
        try:
            project = service.get_project(project_id, include_episodes=False)
        except NotFoundError:
            # 404 treated as success (already deleted)
            # Still record the deletion attempt for idempotency
            record_deletion_query = text("""
                INSERT INTO project_deletions (delete_id, project_id, request_id, trace_id)
                VALUES (:delete_id, :project_id, :request_id, :trace_id)
            """)
            db.execute(record_deletion_query, {
                "delete_id": delete_id,
                "project_id": project_id,
                "request_id": request_id,
                "trace_id": trace_id
            })
            db.commit()

            logger.info("Project already deleted", extra={**log_context, "already_deleted": True})
            return  # 204 No Content - success

        # Business Logic Guard: Check for active generation jobs
        active_jobs_query = text("""
            SELECT COUNT(*) as count FROM generation_jobs 
            WHERE project_id = :project_id 
            AND status IN ('pending', 'processing', 'streaming')
        """)
        try:
            result = db.execute(active_jobs_query, {"project_id": project_id})
            active_jobs_count = result.fetchone()[0]

            if active_jobs_count > 0:
                logger.warning("Cannot delete project with active generation jobs", extra={
                    **log_context,
                    "active_jobs": active_jobs_count,
                    "conflict": True
                })
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail={
                        "code": "ACTIVE_GENERATION_JOBS",
                        "message": "프로젝트에 활성 생성 작업이 있습니다. 먼저 작업을 중단하세요.",
                        "active_jobs_count": active_jobs_count,
                        "request_id": request_id,
                        "trace_id": trace_id
                    }
                )
        except Exception:
            # If generation jobs table doesn't exist, continue with deletion
            logger.debug("Generation jobs table not found, proceeding with deletion", extra=log_context)

        # Proceed with deletion
        success = service.delete_project(project_id)

        if not success:
            logger.error("Project deletion failed at service layer", extra={**log_context, "service_failure": True})
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "DELETION_FAILED",
                    "message": "프로젝트 삭제에 실패했습니다.",
                    "request_id": request_id,
                    "trace_id": trace_id
                }
            )

        # Record successful deletion for idempotency
        record_deletion_query = text("""
            INSERT INTO project_deletions (delete_id, project_id, request_id, trace_id)
            VALUES (:delete_id, :project_id, :request_id, :trace_id)
        """)
        db.execute(record_deletion_query, {
            "delete_id": delete_id,
            "project_id": project_id,
            "request_id": request_id,
            "trace_id": trace_id
        })
        db.commit()

        logger.info("Project deleted successfully", extra={**log_context, "success": True})
        return  # 204 No Content

    except HTTPException:
        # Re-raise HTTP exceptions (409, etc.)
        raise
    except Exception as e:
        logger.error("Unexpected error during project deletion", extra={
            **log_context,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "프로젝트 삭제 중 예상치 못한 오류가 발생했습니다.",
                "request_id": request_id,
                "trace_id": trace_id
            }
        ) from e


@router.patch("/{project_id}/progress", response_model=SuccessResponseDTO)
async def update_project_progress(
    project_id: str,
    progress: float = Query(..., ge=0.0, le=100.0, description="진행률 (0-100)"),
    db: Session = Depends(get_db),
) -> SuccessResponseDTO:
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
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None


@router.get("/stats/summary", response_model=SuccessResponseDTO)
async def get_project_stats(db: Session = Depends(get_db)) -> SuccessResponseDTO:
    """프로젝트 통계 조회"""
    try:
        service = ProjectService(db)
        stats = service.get_project_stats()

        return SuccessResponseDTO(
            success=True, message="프로젝트 통계를 성공적으로 조회했습니다.", data=stats
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None


@router.get("/recent", response_model=SuccessResponseDTO)
async def get_recent_projects(
    limit: int = Query(10, ge=1, le=50, description="가져올 프로젝트 수"),
    db: Session = Depends(get_db),
) -> SuccessResponseDTO:
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
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None
