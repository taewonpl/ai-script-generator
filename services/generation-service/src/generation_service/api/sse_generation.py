"""
SSE-based Generation API with 5 event types
"""

import asyncio
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from ..models.sse_models import (
    GenerationJobRequest,
    GenerationJobResponse,
    GenerationJobStatus,
)
from ..services.generation_service import GenerationService
from ..services.job_manager import get_job_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# Global service instance
_generation_service_instance = None


def get_generation_service() -> GenerationService:
    """Get generation service instance"""
    global _generation_service_instance
    if _generation_service_instance is None:
        _generation_service_instance = GenerationService()
    return _generation_service_instance


@router.post(
    "/generations",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Script Generation",
    description="Start a new script generation job and return SSE endpoint",
)
async def start_generation(request: GenerationJobRequest, http_request: Request) -> GenerationJobResponse:
    """
    Start a new script generation job

    Returns SSE endpoint URL for real-time updates
    """
    try:
        job_manager = get_job_manager()

        # Create generation job
        job = job_manager.create_job(request)

        # Build URLs
        base_url = str(http_request.base_url).rstrip("/")
        sse_url = f"{base_url}/api/v1/generations/{job.jobId}/events"
        cancel_url = f"{base_url}/api/v1/generations/{job.jobId}"

        # Start generation in background
        asyncio.create_task(execute_generation(job.jobId))

        response = GenerationJobResponse(
            jobId=job.jobId,
            status=job.status,
            sseUrl=sse_url,
            cancelUrl=cancel_url,
            projectId=job.projectId,
            episodeNumber=job.episodeNumber,
            title=job.title,
            estimatedDuration=job.estimatedDuration,
        )

        logger.info(f"Started generation job: {job.jobId}")
        return response

    except Exception as e:
        logger.error(f"Failed to start generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start generation: {e!s}",
        )


@router.get(
    "/generations/{jobId}/events",
    summary="Generation SSE Stream",
    description="Server-Sent Events stream for real-time generation updates with Last-Event-ID support",
)
async def generation_events(jobId: str, request: Request) -> StreamingResponse:
    """
    SSE endpoint for real-time generation updates

    Streams 5 types of events:
    - progress: Generation progress updates
    - preview: Partial script content
    - completed: Final result with complete script
    - failed: Error information
    - heartbeat: Keep-alive events
    """
    try:
        job_manager = get_job_manager()

        # Check if job exists
        job = job_manager.get_job(jobId)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Generation job {jobId} not found",
            )

        # Extract Last-Event-ID header for reconnection support
        last_event_id = request.headers.get("Last-Event-ID")
        logger.info(f"SSE connection for job {jobId}, Last-Event-ID: {last_event_id}")

        # Return SSE stream with Last-Event-ID support
        return StreamingResponse(
            job_manager.generate_sse_events(jobId, last_event_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Last-Event-ID, Cache-Control",
                "Access-Control-Expose-Headers": "Last-Event-ID",
                "X-Accel-Buffering": "no",  # Nginx SSE optimization
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in SSE stream for job {jobId}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to establish SSE stream: {e!s}",
        )


@router.delete(
    "/generations/{jobId}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel Generation",
    description="Cancel a running generation job (idempotent operation)",
)
async def cancel_generation(jobId: str) -> None:
    """
    Cancel a generation job

    This operation is idempotent - calling it multiple times has the same effect.
    Returns 204 even if the job is already finished or doesn't exist.
    """
    try:
        job_manager = get_job_manager()

        # Cancel job (idempotent)
        success = job_manager.cancel_job(jobId)

        if success:
            logger.info(f"Canceled generation job: {jobId}")
        else:
            logger.warning(f"Attempted to cancel non-existent job: {jobId}")

        # Always return 204 for idempotent behavior
        return

    except Exception as e:
        logger.error(f"Error canceling job {jobId}: {e}")
        # Still return 204 to maintain idempotent behavior
        return


@router.get(
    "/generations/{jobId}",
    summary="Get Generation Status",
    description="Get current status and details of a generation job",
)
async def get_generation_status(jobId: str) -> Dict[str, Any]:
    """Get generation job status and details"""
    try:
        job_manager = get_job_manager()
        job = job_manager.get_job(jobId)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Generation job {jobId} not found",
            )

        # Return job details
        return {
            "jobId": job.jobId,
            "status": job.status.value,
            "progress": job.progress,
            "currentStep": job.currentStep,
            "projectId": job.projectId,
            "episodeNumber": job.episodeNumber,
            "title": job.title,
            "wordCount": job.wordCount,
            "tokens": job.tokens,
            "createdAt": job.createdAt.isoformat(),
            "startedAt": job.startedAt.isoformat() if job.startedAt else None,
            "completedAt": job.completedAt.isoformat() if job.completedAt else None,
            "estimatedRemainingTime": job.get_estimated_remaining_time(),
            "errorCode": job.errorCode,
            "errorMessage": job.errorMessage,
            "episodeId": job.episodeId,
            "savedToEpisode": job.savedToEpisode,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status {jobId}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {e!s}",
        )


@router.get(
    "/generations/active",
    summary="List Active Generations",
    description="Get list of currently active generation jobs",
)
async def list_active_generations() -> Dict[str, Any]:
    """List all active generation jobs"""
    try:
        job_manager = get_job_manager()
        active_jobs = job_manager.get_active_jobs()

        jobs_data = []
        for job in active_jobs:
            jobs_data.append(
                {
                    "jobId": job.jobId,
                    "status": job.status.value,
                    "progress": job.progress,
                    "currentStep": job.currentStep,
                    "projectId": job.projectId,
                    "title": job.title,
                    "createdAt": job.createdAt.isoformat(),
                    "estimatedRemainingTime": job.get_estimated_remaining_time(),
                }
            )

        return {"active_jobs": jobs_data, "total_active": len(jobs_data)}

    except Exception as e:
        logger.error(f"Error listing active jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list active jobs: {e!s}",
        )


@router.get(
    "/generations/_stats",
    summary="Generation Statistics",
    description="Get generation service statistics",
)
async def get_generation_stats() -> Dict[str, Any]:
    """Get generation service statistics"""
    try:
        job_manager = get_job_manager()
        stats = job_manager.get_job_stats()

        return {
            "job_statistics": stats,
            "service_status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
        }

    except Exception as e:
        logger.error(f"Error getting generation stats: {e}")
        return {
            "job_statistics": {},
            "service_status": "error",
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time(),
        }


async def execute_generation(job_id: str) -> None:
    """
    Execute the actual generation process

    This simulates the generation workflow with progress updates
    """
    try:
        job_manager = get_job_manager()
        generation_service = get_generation_service()

        job = job_manager.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found during execution")
            return

        # Start streaming
        if not job_manager.start_job_streaming(job_id):
            logger.error(f"Failed to start streaming for job {job_id}")
            return

        # Generation steps with progress updates
        steps = [
            (10, "프롬프트 분석 중", "# Script Generation\n\nAnalyzing prompt..."),
            (
                25,
                "캐릭터 설정 생성 중",
                "# Characters\n\n**Main Character**: Analyzing personality...",
            ),
            (
                40,
                "플롯 구조 설계 중",
                "## Plot Structure\n\nAct 1: Setup\n- Opening scene...",
            ),
            (
                60,
                "대화 생성 중",
                "### Scene 1\n\n**Character A**: Hello, I've been waiting...",
            ),
            (
                75,
                "스토리 흐름 다듬기",
                "The tension builds as our protagonist faces...",
            ),
            (
                90,
                "최종 검토 중",
                "# Final Script\n\nFADE IN:\n\nEXT. PARK - DAY\n\nA bustling city park...",
            ),
            (100, "완료", None),
        ]

        for progress, step, content in steps:
            # Check if job was canceled
            current_job = job_manager.get_job(job_id)
            if not current_job or current_job.status == GenerationJobStatus.CANCELED:
                logger.info(f"Job {job_id} was canceled during execution")
                return

            # Update progress
            job_manager.update_job_progress(job_id, progress, step, content or "")

            # Simulate processing time
            await asyncio.sleep(2.0)

        # Generate final content
        final_script = generate_final_script(job)

        # Complete the job
        job_manager.complete_job(
            job_id,
            final_script,
            tokens=len(final_script.split()) * 4,  # Rough token estimate
            model_used="gpt-4",
        )

        # Try to save to Episode (if ChromaDB integration is available)
        await try_save_to_episode(job_id)

        logger.info(f"Successfully completed generation job: {job_id}")

    except Exception as e:
        logger.error(f"Generation execution failed for job {job_id}: {e}")
        job_manager.fail_job(job_id, "GENERATION_ERROR", str(e))


def generate_final_script(job: Any) -> str:
    """Generate the final script content"""
    return f"""# {job.title}

## 기본 정보
- **프로젝트**: {job.projectId}
- **에피소드**: {job.episodeNumber or 1}
- **장르**: {job.scriptType}

## 시놉시스
{job.description}

---

# 대본

FADE IN:

EXT. 도시 공원 - 낮

푸른 잔디와 벚꽃이 만개한 아름다운 도시 공원. 사람들이 여유롭게 산책하고 있다.

주인공 민수(20대 후반, 성실한 직장인)가 벤치에 앉아 스마트폰을 보고 있다.

**민수**
(혼잣말로)
오늘은 꼭 용기를 내보자.

갑자기 공이 민수의 발치로 굴러온다. 어린 소녀(7살)가 뛰어온다.

**소녀**
아저씨, 공 좀 주세요!

민수가 공을 집어 소녀에게 건넨다.

**민수**
(미소지으며)
여기 있어.

**소녀**
고마워요! 아저씨는 왜 혼자 앉아 있어요?

민수가 잠시 망설인다.

**민수**
음... 중요한 사람을 기다리고 있단다.

**소녀**
그럼 꽃을 선물해보세요! 우리 엄마는 꽃을 받으면 정말 좋아해요.

소녀가 근처 꽃밭을 가리킨다.

**민수**
(깨달으며)
그래, 좋은 생각이야.

CUT TO:

EXT. 꽃가게 앞 - 낮

민수가 꽃가게 앞에서 꽃다발을 고르고 있다.

**꽃가게 아주머니**
첫 고백인가봐요?

**민수**
(부끄러워하며)
네... 맞아요.

**꽃가게 아주머니**
그럼 이 장미들이 좋을 것 같아요. 진심이 전해질 거예요.

민수가 아름다운 장미 꽃다발을 받는다.

CUT TO:

EXT. 카페 앞 - 낮

민수가 꽃다발을 들고 카페 앞에서 기다린다. 드디어 수연(20대 후반, 밝고 활발한 성격)이 나타난다.

**수연**
민수야! 미안해, 늦었지?

**민수**
(떨리는 목소리로)
아니야... 수연아, 이거...

민수가 꽃다발을 수연에게 내민다.

**수연**
(놀라며)
와, 이게 뭐야? 무슨 일이야?

**민수**
수연아... 나는... 너를...

잠시 침묵. 주변이 조용해진다.

**민수**
(용기를 내며)
너를 정말 좋아해. 오랫동안 말하고 싶었어.

수연의 얼굴에 미소가 번진다.

**수연**
바보야... 나도 그랬는데.

둘이 서로를 바라보며 미소짓는다. 벚꽃잎이 바람에 날린다.

FADE OUT.

**끝**

---

## 제작 노트
- 총 소요 시간: 15분 분량
- 촬영 장소: 도시 공원, 꽃가게, 카페
- 주요 테마: 용기, 첫사랑, 성장

*본 대본은 AI에 의해 생성되었으며, 실제 제작 시 수정이 필요할 수 있습니다.*"""


async def try_save_to_episode(job_id: str) -> None:
    """Try to save completed script to Episode using ChromaDB API"""
    try:
        import httpx

        job_manager = get_job_manager()
        job = job_manager.get_job(job_id)

        if not job or not job.finalContent:
            return

        # Try to create episode in project-service
        episode_data = {
            "title": job.title,
            "script": {"markdown": job.finalContent, "tokens": job.tokens},
            "promptSnapshot": job.promptSnapshot,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"http://localhost:8001/api/v1/projects/{job.projectId}/episodes/",
                json=episode_data,
            )

            if response.status_code == 201:
                data = response.json()
                episode = data.get("data", {})

                # Update job with episode info
                job.episodeId = episode.get("id")
                job.savedToEpisode = True
                job.episodeNumber = episode.get("number")

                logger.info(f"Saved job {job_id} to episode {job.episodeId}")
            else:
                logger.warning(
                    f"Failed to save job {job_id} to episode: {response.status_code}"
                )

    except Exception as e:
        logger.warning(f"Could not save job {job_id} to episode: {e}")
        # Don't fail the generation if episode save fails
