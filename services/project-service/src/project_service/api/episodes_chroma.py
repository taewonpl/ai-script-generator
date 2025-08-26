"""
Episodes API Router with ChromaDB backend
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..services.episode_chroma_service import EpisodeChromaError, EpisodeChromaService

router = APIRouter(prefix="/projects/{project_id}/episodes", tags=["Episodes"])

# Global service instance
_episode_service: EpisodeChromaService | None = None


def get_episode_service() -> EpisodeChromaService:
    """Get or create episode service instance"""
    global _episode_service
    if _episode_service is None:
        _episode_service = EpisodeChromaService()
    return _episode_service


# Request/Response Models
class ScriptData(BaseModel):
    """Script content with metadata"""

    markdown: str = Field(..., description="Script content in markdown format")
    tokens: int = Field(0, description="Token count (auto-calculated if not provided)")


class EpisodeCreateRequest(BaseModel):
    """Episode creation request"""

    title: str | None = Field(
        None, description="Episode title (auto-generated if not provided)"
    )
    script: ScriptData = Field(..., description="Script content and metadata")
    promptSnapshot: str = Field("", description="Prompt used for generation")


class EpisodeUpdateRequest(BaseModel):
    """Episode update request"""

    script: ScriptData = Field(..., description="Updated script content")
    promptSnapshot: str | None = Field(None, description="Updated prompt")


class EpisodeResponse(BaseModel):
    """Episode response"""

    id: str = Field(..., description="Episode ID")
    projectId: str = Field(..., description="Project ID")
    number: int = Field(..., description="Auto-assigned episode number")
    title: str = Field(..., description="Episode title")
    script: ScriptData | None = Field(None, description="Script content if available")
    promptSnapshot: str = Field("", description="Prompt used for generation")
    createdAt: str = Field(..., description="Creation timestamp")


class SuccessResponse(BaseModel):
    """Success response wrapper"""

    success: bool = True
    message: str = "Success"
    data: Any = None


@router.post("/", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_episode(project_id: str, request: EpisodeCreateRequest) -> SuccessResponse:
    """
    Create episode with automatic number assignment

    Request body excludes 'number' field - it's auto-assigned by server
    Response includes the auto-assigned 'number'
    """
    try:
        service = get_episode_service()

        # Convert script data
        script_data = {
            "markdown": request.script.markdown,
            "tokens": request.script.tokens,
        }

        episode = service.create_episode(
            project_id=project_id,
            title=request.title,
            script=script_data,
            prompt_snapshot=request.promptSnapshot,
        )

        return SuccessResponse(
            success=True,
            message=f"에피소드 {episode['number']}가 성공적으로 생성되었습니다.",
            data=episode,
        )

    except EpisodeChromaError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"에피소드 생성 중 오류가 발생했습니다: {e!s}",
        )


@router.get("/", response_model=SuccessResponse)
async def get_episodes(project_id: str) -> SuccessResponse:
    """
    Get all episodes for a project, sorted by episode number
    """
    try:
        service = get_episode_service()
        episodes = service.get_episodes_by_project(project_id)

        return SuccessResponse(
            success=True,
            message=f"프로젝트 {project_id}의 에피소드 {len(episodes)}개를 조회했습니다.",
            data=episodes,
        )

    except EpisodeChromaError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"에피소드 목록 조회 중 오류가 발생했습니다: {e!s}",
        )


@router.get("/{episode_id}", response_model=SuccessResponse)
async def get_episode(project_id: str, episode_id: str) -> SuccessResponse:
    """Get single episode by ID"""
    try:
        service = get_episode_service()
        episode = service.get_episode(episode_id)

        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"에피소드 {episode_id}를 찾을 수 없습니다.",
            )

        # Verify episode belongs to the specified project
        if episode["projectId"] != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"프로젝트 {project_id}에서 에피소드 {episode_id}를 찾을 수 없습니다.",
            )

        return SuccessResponse(
            success=True, message="에피소드를 성공적으로 조회했습니다.", data=episode
        )

    except HTTPException:
        raise
    except EpisodeChromaError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"에피소드 조회 중 오류가 발생했습니다: {e!s}",
        )


@router.put("/{episode_id}/script", response_model=SuccessResponse)
async def update_episode_script(
    project_id: str, episode_id: str, request: EpisodeUpdateRequest
) -> SuccessResponse:
    """Update episode script content"""
    try:
        service = get_episode_service()

        # Verify episode exists and belongs to project
        episode = service.get_episode(episode_id)
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"에피소드 {episode_id}를 찾을 수 없습니다.",
            )

        if episode["projectId"] != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"프로젝트 {project_id}에서 에피소드 {episode_id}를 찾을 수 없습니다.",
            )

        # Update script
        script_data = {
            "markdown": request.script.markdown,
            "tokens": request.script.tokens,
        }

        success = service.update_episode_script(
            episode_id=episode_id,
            script=script_data,
            prompt_snapshot=request.promptSnapshot,
        )

        if success:
            return SuccessResponse(
                success=True,
                message="에피소드 스크립트가 성공적으로 업데이트되었습니다.",
                data={"episode_id": episode_id, "updated": True},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="스크립트 업데이트에 실패했습니다.",
            )

    except HTTPException:
        raise
    except EpisodeChromaError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스크립트 업데이트 중 오류가 발생했습니다: {e!s}",
        )


@router.delete("/{episode_id}", response_model=SuccessResponse)
async def delete_episode(project_id: str, episode_id: str) -> SuccessResponse:
    """Delete episode"""
    try:
        service = get_episode_service()

        # Verify episode exists and belongs to project
        episode = service.get_episode(episode_id)
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"에피소드 {episode_id}를 찾을 수 없습니다.",
            )

        if episode["projectId"] != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"프로젝트 {project_id}에서 에피소드 {episode_id}를 찾을 수 없습니다.",
            )

        success = service.delete_episode(episode_id)

        if success:
            return SuccessResponse(
                success=True,
                message=f"에피소드 {episode['number']}가 성공적으로 삭제되었습니다.",
                data={"episode_id": episode_id, "deleted": True},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="에피소드 삭제에 실패했습니다.",
            )

    except HTTPException:
        raise
    except EpisodeChromaError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"에피소드 삭제 중 오류가 발생했습니다: {e!s}",
        )


@router.get("/_next-number", response_model=SuccessResponse)
async def get_next_episode_number(project_id: str) -> SuccessResponse:
    """Get the next episode number for a project"""
    try:
        service = get_episode_service()
        next_number = service.get_next_episode_number(project_id)

        return SuccessResponse(
            success=True,
            message=f"프로젝트 {project_id}의 다음 에피소드 번호입니다.",
            data={"next_number": next_number},
        )

    except EpisodeChromaError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"다음 에피소드 번호 조회 중 오류가 발생했습니다: {e!s}",
        )


@router.post("/_register-project", response_model=SuccessResponse)
async def register_project(project_id: str, project_name: str) -> SuccessResponse:
    """Register a project for episode tracking"""
    try:
        service = get_episode_service()
        success = service.register_project(project_id, project_name)

        if success:
            return SuccessResponse(
                success=True,
                message=f"프로젝트 {project_name}가 성공적으로 등록되었습니다.",
                data={"project_id": project_id, "project_name": project_name},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="프로젝트 등록에 실패했습니다.",
            )

    except EpisodeChromaError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"프로젝트 등록 중 오류가 발생했습니다: {e!s}",
        )


# Health and Stats Endpoints
@router.get("/_stats", response_model=SuccessResponse)
async def get_episode_stats() -> SuccessResponse:
    """Get episode service statistics"""
    try:
        service = get_episode_service()
        stats = service.get_stats()

        return SuccessResponse(
            success=True, message="에피소드 서비스 통계를 조회했습니다.", data=stats
        )

    except Exception as e:
        return SuccessResponse(
            success=False,
            message="통계 조회 중 오류가 발생했습니다.",
            data={"error": str(e)},
        )
