"""
Episodes API Router
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

try:
    # Prefer Core
    from ai_script_core import (
        EpisodeCreateDTO,
        EpisodeDTO,
        EpisodeUpdateDTO,
        SuccessResponseDTO,
    )
except Exception:  # fallback
    from typing import Any

    from pydantic import BaseModel

    class EpisodeDTO(BaseModel):
        id: str
        title: str
        project_id: str
        number: int  # 에피소드 번호 (자동 할당)
        order: int  # 표시 순서
        status: str | None = None
        description: str | None = None
        created_at: str | None = None
        updated_at: str | None = None

    class SuccessResponseDTO(BaseModel):
        success: bool = True
        message: str = "Success"
        data: Any = None

    class EpisodeCreateDTO(BaseModel):
        title: str
        description: str | None = None

    class EpisodeUpdateDTO(BaseModel):
        title: str | None = None
        description: str | None = None
        duration: int | None = None
        notes: str | None = None


from ..database import get_db
from ..services.episode_service import EpisodeService, NotFoundError, ValidationError

router = APIRouter(prefix="/projects/{project_id}/episodes", tags=["Episodes"])


@router.get("/", response_model=SuccessResponseDTO)
async def get_episodes(
    project_id: str,
    published_only: bool = Query(False, description="공개된 에피소드만 조회"),
    db: Session = Depends(get_db),
):
    """프로젝트의 에피소드 목록 조회"""
    try:
        service = EpisodeService(db)
        episodes = service.get_episodes_by_project(project_id, published_only)

        return SuccessResponseDTO(
            success=True,
            message="에피소드 목록을 성공적으로 조회했습니다.",
            data=episodes,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/", response_model=SuccessResponseDTO, status_code=status.HTTP_201_CREATED
)
async def create_episode(
    project_id: str,
    episode_data: EpisodeCreateDTO,
    request: Request,
    db: Session = Depends(get_db),
):
    """에피소드 생성"""
    try:
        service = EpisodeService(db)
        episode = service.create_episode(
            project_id=project_id,
            title=episode_data.title,
            description=episode_data.description,
        )

        return SuccessResponseDTO(
            success=True, message="에피소드가 성공적으로 생성되었습니다.", data=episode
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{episode_id}", response_model=SuccessResponseDTO)
async def get_episode(project_id: str, episode_id: str, db: Session = Depends(get_db)):
    """에피소드 상세 조회"""
    try:
        service = EpisodeService(db)
        episode = service.get_episode(episode_id)

        return SuccessResponseDTO(
            success=True, message="에피소드를 성공적으로 조회했습니다.", data=episode
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.put("/{episode_id}", response_model=SuccessResponseDTO)
async def update_episode(
    project_id: str,
    episode_id: str,
    episode_data: EpisodeUpdateDTO,
    db: Session = Depends(get_db),
):
    """에피소드 수정"""
    try:
        service = EpisodeService(db)

        # None이 아닌 값만 필터링
        update_data = {
            k: v for k, v in episode_data.model_dump().items() if v is not None
        }

        episode = service.update_episode(episode_id, update_data)

        return SuccessResponseDTO(
            success=True, message="에피소드가 성공적으로 수정되었습니다.", data=episode
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete("/{episode_id}", response_model=SuccessResponseDTO)
async def delete_episode(
    project_id: str, episode_id: str, db: Session = Depends(get_db)
):
    """에피소드 삭제"""
    try:
        service = EpisodeService(db)
        success = service.delete_episode(episode_id)

        if success:
            return SuccessResponseDTO(
                success=True,
                message="에피소드가 성공적으로 삭제되었습니다.",
                data={"deleted": True, "episode_id": episode_id},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="에피소드 삭제에 실패했습니다.",
            )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.patch("/{episode_id}/publish", response_model=SuccessResponseDTO)
async def publish_episode(
    project_id: str, episode_id: str, db: Session = Depends(get_db)
):
    """에피소드 공개"""
    try:
        service = EpisodeService(db)
        episode = service.publish_episode(episode_id)

        return SuccessResponseDTO(
            success=True, message="에피소드가 성공적으로 공개되었습니다.", data=episode
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.patch("/{episode_id}/unpublish", response_model=SuccessResponseDTO)
async def unpublish_episode(
    project_id: str, episode_id: str, db: Session = Depends(get_db)
):
    """에피소드 비공개"""
    try:
        service = EpisodeService(db)
        episode = service.unpublish_episode(episode_id)

        return SuccessResponseDTO(
            success=True,
            message="에피소드가 성공적으로 비공개되었습니다.",
            data=episode,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
