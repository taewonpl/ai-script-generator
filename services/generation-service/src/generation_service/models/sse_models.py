"""
Server-Sent Events (SSE) models for real-time generation updates
"""

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SSEEventType(str, Enum):
    """SSE event types for generation updates (CLAUDE.md 계약)"""

    PROGRESS = "progress"
    PREVIEW = "preview"
    COMPLETED = "completed"
    ERROR = "error"


class GenerationJobStatus(str, Enum):
    """Generation job status for state machine"""

    QUEUED = "queued"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class StandardSSEEventData(BaseModel):
    """CLAUDE.md 계약에 따른 표준 SSE 이벤트 데이터 구조

    공통 스키마: {id, status, content, eta_ms}
    """

    id: str = Field(..., description="Generation job ID")
    status: SSEEventType = Field(..., description="Event type/status")
    content: Any = Field(..., description="Event-specific content payload")
    eta_ms: Optional[int] = Field(
        None, description="Estimated time remaining in milliseconds"
    )


# Content payload types for each event
class ProgressContent(BaseModel):
    """Progress event content payload"""

    progress_percentage: int = Field(..., ge=0, le=100)
    current_step: str = Field(..., description="Current processing step")
    steps_completed: int = Field(..., ge=0)
    total_steps: int = Field(..., gt=0)


class PreviewContent(BaseModel):
    """Preview event content payload"""

    markdown: str = Field(..., description="Partial script content")
    is_partial: bool = Field(default=True)
    word_count: int = Field(..., ge=0)
    estimated_tokens: Optional[int] = Field(None, ge=0)


class CompletedContent(BaseModel):
    """Completed event content payload"""

    markdown: str = Field(..., description="Final script content")
    total_tokens: int = Field(..., ge=0)
    word_count: int = Field(..., ge=0)
    generation_time_ms: int = Field(..., ge=0)
    quality_score: Optional[float] = Field(None, ge=0, le=1)


class ErrorContent(BaseModel):
    """Error event content payload"""

    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human readable error message")
    retryable: bool = Field(default=False, description="Whether the error is retryable")
    retry_after_ms: Optional[int] = Field(
        None, ge=0, description="Suggested retry delay"
    )


class SSEEvent(BaseModel):
    """CLAUDE.md 계약에 따른 표준 SSE 이벤트 구조"""

    event: SSEEventType = Field(..., description="Event type")
    data: StandardSSEEventData = Field(..., description="Standard event data")

    def format_sse(self, event_id: Optional[str] = None) -> str:
        """Format as Server-Sent Event message"""
        data_json = json.dumps(self.data.model_dump(), ensure_ascii=False)

        sse_message = f"event: {self.event.value}\ndata: {data_json}\n"

        # Add ID field for Last-Event-ID support
        if event_id:
            sse_message = f"id: {event_id}\n{sse_message}"

        return sse_message + "\n"

    @classmethod
    def create_progress(
        cls,
        job_id: str,
        progress_percentage: int,
        current_step: str,
        steps_completed: int,
        total_steps: int,
        eta_ms: Optional[int] = None,
    ) -> "SSEEvent":
        """Create progress event"""
        content = ProgressContent(
            progress_percentage=progress_percentage,
            current_step=current_step,
            steps_completed=steps_completed,
            total_steps=total_steps,
        )
        data = StandardSSEEventData(
            id=job_id,
            status=SSEEventType.PROGRESS,
            content=content.model_dump(),
            eta_ms=eta_ms,
        )
        return cls(event=SSEEventType.PROGRESS, data=data)

    @classmethod
    def create_preview(
        cls,
        job_id: str,
        markdown: str,
        word_count: int,
        is_partial: bool = True,
        estimated_tokens: Optional[int] = None,
        eta_ms: Optional[int] = None,
    ) -> "SSEEvent":
        """Create preview event"""
        content = PreviewContent(
            markdown=markdown,
            is_partial=is_partial,
            word_count=word_count,
            estimated_tokens=estimated_tokens,
        )
        data = StandardSSEEventData(
            id=job_id,
            status=SSEEventType.PREVIEW,
            content=content.model_dump(),
            eta_ms=eta_ms,
        )
        return cls(event=SSEEventType.PREVIEW, data=data)

    @classmethod
    def create_completed(
        cls,
        job_id: str,
        markdown: str,
        total_tokens: int,
        word_count: int,
        generation_time_ms: int,
        quality_score: Optional[float] = None,
    ) -> "SSEEvent":
        """Create completed event"""
        content = CompletedContent(
            markdown=markdown,
            total_tokens=total_tokens,
            word_count=word_count,
            generation_time_ms=generation_time_ms,
            quality_score=quality_score,
        )
        data = StandardSSEEventData(
            id=job_id,
            status=SSEEventType.COMPLETED,
            content=content.model_dump(),
            eta_ms=None,
        )
        return cls(event=SSEEventType.COMPLETED, data=data)

    @classmethod
    def create_error(
        cls,
        job_id: str,
        error_code: str,
        error_message: str,
        retryable: bool = False,
        retry_after_ms: Optional[int] = None,
    ) -> "SSEEvent":
        """Create error event"""
        content = ErrorContent(
            error_code=error_code,
            error_message=error_message,
            retryable=retryable,
            retry_after_ms=retry_after_ms,
        )
        data = StandardSSEEventData(
            id=job_id,
            status=SSEEventType.ERROR,
            content=content.model_dump(),
            eta_ms=None,
        )
        return cls(event=SSEEventType.ERROR, data=data)


class GenerationJob(BaseModel):
    """Generation job tracking model"""

    jobId: str = Field(..., description="Unique job ID")
    projectId: str = Field(..., description="Project ID")
    episodeNumber: Optional[int] = Field(
        None, description="Episode number if specified"
    )

    # Job configuration
    title: str = Field(..., description="Script title")
    description: str = Field(..., description="Script description")
    scriptType: str = Field(..., description="Type of script")
    promptSnapshot: str = Field("", description="Original prompt")

    # Status and progress
    status: GenerationJobStatus = Field(
        default=GenerationJobStatus.QUEUED, description="Current status"
    )
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    currentStep: str = Field(default="대기 중", description="Current step description")

    # Content
    currentContent: str = Field("", description="Current generated content")
    finalContent: Optional[str] = Field(None, description="Final completed content")

    # Metadata
    tokens: int = Field(default=0, description="Token count")
    wordCount: int = Field(default=0, description="Word count")
    modelUsed: Optional[str] = Field(None, description="AI model used")

    # Timing
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    startedAt: Optional[datetime] = Field(None, description="When streaming started")
    completedAt: Optional[datetime] = Field(None, description="When completed")
    estimatedDuration: Optional[int] = Field(
        None, description="Estimated duration in seconds"
    )

    # Error handling
    errorCode: Optional[str] = Field(None, description="Error code if failed")
    errorMessage: Optional[str] = Field(None, description="Error message if failed")
    retryCount: int = Field(default=0, description="Number of retry attempts")

    # Episode integration
    episodeId: Optional[str] = Field(None, description="Created episode ID")
    savedToEpisode: bool = Field(default=False, description="Whether saved to episode")

    # Event tracking for Last-Event-ID support
    eventSequence: int = Field(
        default=0, description="Event sequence number for Last-Event-ID"
    )
    lastEventId: Optional[str] = Field(None, description="Last event ID sent to client")

    def to_progress_event(self) -> SSEEvent:
        """Convert to progress SSE event"""
        return SSEEvent.create_progress(
            job_id=self.jobId,
            progress_percentage=self.progress,
            current_step=self.currentStep,
            steps_completed=min(self.progress, 100) // 10,  # Rough estimate
            total_steps=10,  # Rough estimate
            eta_ms=(
                self.get_estimated_remaining_time() * 1000
                if self.get_estimated_remaining_time()
                else None
            ),
        )

    def to_preview_event(self) -> SSEEvent:
        """Convert to preview SSE event"""
        return SSEEvent.create_preview(
            job_id=self.jobId,
            markdown=self.currentContent,
            word_count=self.wordCount,
            is_partial=self.status != GenerationJobStatus.COMPLETED,
            estimated_tokens=self.tokens if self.tokens > 0 else None,
            eta_ms=(
                self.get_estimated_remaining_time() * 1000
                if self.get_estimated_remaining_time()
                else None
            ),
        )

    def to_completed_event(self) -> SSEEvent:
        """Convert to completed SSE event"""
        generation_time = 0
        if self.startedAt and self.completedAt:
            generation_time = int(
                (self.completedAt - self.startedAt).total_seconds() * 1000
            )

        return SSEEvent.create_completed(
            job_id=self.jobId,
            markdown=self.finalContent or self.currentContent,
            total_tokens=self.tokens,
            word_count=self.wordCount,
            generation_time_ms=generation_time,
        )

    def to_failed_event(self) -> SSEEvent:
        """Convert to failed SSE event"""
        return SSEEvent.create_error(
            job_id=self.jobId,
            error_code=self.errorCode or "GENERATION_ERROR",
            error_message=self.errorMessage or "Generation failed",
            retryable=self.retryCount < 3,
        )

    def get_estimated_remaining_time(self) -> Optional[int]:
        """Calculate estimated remaining time in seconds"""
        if not self.startedAt or self.progress <= 0:
            return self.estimatedDuration

        elapsed = (datetime.now(timezone.utc) - self.startedAt).total_seconds()
        if self.progress >= 100:
            return 0

        estimated_total = elapsed * (100 / self.progress)
        remaining = max(0, estimated_total - elapsed)
        return int(remaining)

    def update_progress(self, progress: int, step: str, content: str = "") -> None:
        """Update job progress"""
        self.progress = max(0, min(100, progress))
        self.currentStep = step
        if content:
            self.currentContent = content
            self.wordCount = len(content.split())

        if not self.startedAt and progress > 0:
            self.startedAt = datetime.now(timezone.utc)

        # Increment event sequence for Last-Event-ID
        self.eventSequence += 1
        self.lastEventId = f"{self.jobId}_{self.eventSequence}"

    def complete(
        self, final_content: str, tokens: int = 0, model_used: Optional[str] = None
    ) -> None:
        """Mark job as completed"""
        self.status = GenerationJobStatus.COMPLETED
        self.progress = 100
        self.currentStep = "완료"
        self.finalContent = final_content
        self.currentContent = final_content
        self.tokens = tokens or len(final_content.split()) * 4  # Rough token estimate
        self.wordCount = len(final_content.split())
        self.completedAt = datetime.now(timezone.utc)
        if model_used:
            self.modelUsed = model_used

    def fail(self, error_code: str, error_message: str) -> None:
        """Mark job as failed"""
        self.status = GenerationJobStatus.FAILED
        self.currentStep = "실패"
        self.errorCode = error_code
        self.errorMessage = error_message
        self.completedAt = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """Mark job as canceled"""
        self.status = GenerationJobStatus.CANCELED
        self.currentStep = "취소됨"
        self.completedAt = datetime.now(timezone.utc)

    def is_active(self) -> bool:
        """Check if job is still active"""
        return self.status in [
            GenerationJobStatus.QUEUED,
            GenerationJobStatus.STREAMING,
        ]

    def is_finished(self) -> bool:
        """Check if job is finished"""
        return self.status in [
            GenerationJobStatus.COMPLETED,
            GenerationJobStatus.FAILED,
            GenerationJobStatus.CANCELED,
        ]


class GenerationJobRequest(BaseModel):
    """Request to create a new generation job"""

    projectId: str = Field(..., description="Project ID")
    episodeNumber: Optional[int] = Field(
        None, description="Episode number (auto-assigned if not provided)"
    )
    title: Optional[str] = Field(
        None, description="Script title (auto-generated if not provided)"
    )
    description: str = Field(..., description="Script description/prompt")
    scriptType: str = Field(default="drama", description="Type of script")
    model: Optional[str] = Field(None, description="Preferred AI model")
    temperature: Optional[float] = Field(0.7, description="Generation creativity")
    lengthTarget: Optional[int] = Field(None, description="Target length in words")


class GenerationJobResponse(BaseModel):
    """Response when creating a generation job"""

    jobId: str = Field(..., description="Unique job ID")
    status: GenerationJobStatus = Field(..., description="Initial job status")
    sseUrl: str = Field(..., description="SSE endpoint URL")
    cancelUrl: str = Field(..., description="Cancellation endpoint URL")

    # Job details
    projectId: str
    episodeNumber: Optional[int] = None
    title: str
    estimatedDuration: Optional[int] = Field(
        None, description="Estimated duration in seconds"
    )
