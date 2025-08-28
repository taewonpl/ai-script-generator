"""
SSE (Server-Sent Events) Schemas for AI Script Generator v3.0

Frontend와 일관성을 유지하기 위한 SSE 이벤트 타입 정의입니다.
TypeScript와 정확히 매치되는 구조를 제공합니다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Union

from pydantic import Field

from .base import BaseSchema

# =============================================================================
# SSE Event Base Types
# =============================================================================


class BaseSSEEvent(BaseSchema):
    """SSE 이벤트 기본 구조"""

    type: str = Field(..., description="이벤트 타입")
    job_id: str = Field(..., description="작업 ID", alias="jobId")


class ProgressEventData(BaseSSEEvent):
    """진행률 이벤트 데이터"""

    type: Literal["progress"] = Field(default="progress", description="이벤트 타입")
    value: float = Field(..., ge=0.0, le=100.0, description="진행률 (0-100)")
    current_step: str = Field(
        ..., description="현재 단계 (한국어 설명)", alias="currentStep"
    )
    estimated_time: int | None = Field(
        None, description="예상 남은 시간(초)", alias="estimatedTime"
    )
    metadata: dict[str, Any] | None = Field(None, description="추가 메타데이터")


class PreviewEventData(BaseSSEEvent):
    """미리보기 이벤트 데이터"""

    type: Literal["preview"] = Field(default="preview", description="이벤트 타입")
    markdown: str = Field(..., description="부분 스크립트 내용")
    is_partial: bool = Field(True, description="부분 내용 여부", alias="isPartial")
    word_count: int | None = Field(None, description="단어 수", alias="wordCount")
    estimated_tokens: int | None = Field(
        None, description="예상 토큰 수", alias="estimatedTokens"
    )


class CompletedEventData(BaseSSEEvent):
    """완료 이벤트 데이터"""

    type: Literal["completed"] = Field(default="completed", description="이벤트 타입")
    result: CompletionResult = Field(..., description="완료 결과")


class CompletionResult(BaseSchema):
    """완료 결과 데이터"""

    markdown: str = Field(..., description="완성된 스크립트")
    tokens: int = Field(..., description="사용된 토큰 수")
    word_count: int | None = Field(None, description="단어 수", alias="wordCount")
    model_used: str | None = Field(None, description="사용된 모델", alias="modelUsed")
    episode_id: str | None = Field(
        None, description="ChromaDB 에피소드 ID", alias="episodeId"
    )
    saved_to_episode: bool | None = Field(
        None, description="에피소드 저장 여부", alias="savedToEpisode"
    )


class FailedEventData(BaseSSEEvent):
    """실패 이벤트 데이터"""

    type: Literal["failed"] = Field(default="failed", description="이벤트 타입")
    error: SSEErrorInfo = Field(..., description="오류 정보")


class SSEErrorInfo(BaseSchema):
    """SSE 오류 정보"""

    code: str = Field(..., description="오류 코드")
    message: str = Field(..., description="오류 메시지")
    retryable: bool = Field(..., description="재시도 가능 여부")
    details: dict[str, Any] | None = Field(None, description="오류 세부사항")


class HeartbeatEventData(BaseSSEEvent):
    """하트비트 이벤트 데이터"""

    type: Literal["heartbeat"] = Field(default="heartbeat", description="이벤트 타입")
    timestamp: datetime = Field(default_factory=datetime.now, description="타임스탬프")
    server_info: dict[str, Any] | None = Field(
        None, description="서버 정보", alias="serverInfo"
    )


# =============================================================================
# Generation Job Management Types
# =============================================================================


class GenerationJobStatus(BaseSchema):
    """생성 작업 상태"""

    queued: Literal["queued"] = "queued"
    streaming: Literal["streaming"] = "streaming"
    completed: Literal["completed"] = "completed"
    failed: Literal["failed"] = "failed"
    canceled: Literal["canceled"] = "canceled"


class GenerationJobRequest(BaseSchema):
    """생성 작업 요청"""

    project_id: str = Field(..., description="프로젝트 ID", alias="projectId")
    episode_number: int | None = Field(
        None, description="에피소드 번호", alias="episodeNumber"
    )
    title: str | None = Field(None, description="제목")
    description: str = Field(
        ..., min_length=10, max_length=2000, description="스크립트 설명"
    )
    script_type: Literal["drama", "comedy", "documentary"] = Field(
        default="drama", description="스크립트 타입", alias="scriptType"
    )
    length_target: int = Field(
        default=1000, ge=100, le=50000, description="목표 길이", alias="lengthTarget"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="창의도")


class GenerationJobResponse(BaseSchema):
    """생성 작업 응답"""

    job_id: str = Field(..., description="작업 ID", alias="jobId")
    status: str = Field(..., description="초기 상태")
    sse_url: str = Field(..., description="SSE 스트림 URL", alias="sseUrl")
    estimated_duration: int | None = Field(
        None, description="예상 소요 시간(초)", alias="estimatedDuration"
    )


class GenerationJobDetails(BaseSchema):
    """생성 작업 상세 정보"""

    job_id: str = Field(..., description="작업 ID", alias="jobId")
    project_id: str = Field(..., description="프로젝트 ID", alias="projectId")
    status: str = Field(..., description="현재 상태")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="진행률")
    created_at: datetime = Field(..., description="생성 시간", alias="createdAt")
    started_at: datetime | None = Field(
        None, description="시작 시간", alias="startedAt"
    )
    completed_at: datetime | None = Field(
        None, description="완료 시간", alias="completedAt"
    )
    error_message: str | None = Field(
        None, description="오류 메시지", alias="errorMessage"
    )


# =============================================================================
# API Response Types
# =============================================================================


class GenerationStartResponse(BaseSchema):
    """생성 시작 API 응답"""

    success: bool = Field(..., description="성공 여부")
    data: GenerationJobResponse | None = Field(None, description="응답 데이터")
    error: dict[str, Any] | None = Field(None, description="오류 정보")


class GenerationStatusResponse(BaseSchema):
    """생성 상태 API 응답"""

    success: bool = Field(..., description="성공 여부")
    data: GenerationJobDetails | None = Field(None, description="작업 상세 정보")
    error: dict[str, Any] | None = Field(None, description="오류 정보")


class GenerationListResponse(BaseSchema):
    """활성 생성 목록 API 응답"""

    success: bool = Field(..., description="성공 여부")
    data: dict[str, Any] | None = Field(None, description="활성 작업 목록")
    error: dict[str, Any] | None = Field(None, description="오류 정보")


class GenerationStatsResponse(BaseSchema):
    """생성 통계 API 응답"""

    success: bool = Field(..., description="성공 여부")
    data: dict[str, Any] | None = Field(None, description="생성 통계")
    error: dict[str, Any] | None = Field(None, description="오류 정보")


# =============================================================================
# Connection and State Management Types
# =============================================================================


class SSEConnectionState(BaseSchema):
    """SSE 연결 상태"""

    closed: Literal["closed"] = "closed"
    connecting: Literal["connecting"] = "connecting"
    connected: Literal["connected"] = "connected"
    error: Literal["error"] = "error"


class SSEConnectionStatus(BaseSchema):
    """SSE 연결 상태 정보"""

    state: str = Field(..., description="연결 상태")
    retry_count: int = Field(default=0, description="재시도 횟수", alias="retryCount")
    max_retries: int = Field(
        default=5, description="최대 재시도 횟수", alias="maxRetries"
    )
    next_retry_in: int | None = Field(
        None, description="다음 재시도까지 시간(초)", alias="nextRetryIn"
    )
    error: str | None = Field(None, description="오류 메시지")
    last_heartbeat: datetime | None = Field(
        None, description="마지막 하트비트", alias="lastHeartbeat"
    )


# =============================================================================
# Union Types for Event Handling
# =============================================================================

SSEEventData = Union[
    ProgressEventData,
    PreviewEventData,
    CompletedEventData,
    FailedEventData,
    HeartbeatEventData,
]

# Update forward references
CompletedEventData.model_rebuild()
