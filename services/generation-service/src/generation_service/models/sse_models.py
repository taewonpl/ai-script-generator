"""
Server-Sent Events (SSE) models for real-time generation updates
"""

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SSEEventType(str, Enum):
    """SSE event types for generation updates"""

    PROGRESS = "progress"
    PREVIEW = "preview"
    COMPLETED = "completed"
    FAILED = "failed"
    HEARTBEAT = "heartbeat"


class GenerationJobStatus(str, Enum):
    """Generation job status for state machine"""

    QUEUED = "queued"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ProgressEventData(BaseModel):
    """Progress event data structure"""

    type: str = SSEEventType.PROGRESS
    jobId: str = Field(..., description="Generation job ID")
    value: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    currentStep: str = Field(..., description="Current step description in Korean")
    estimatedTime: int | None = Field(
        None, description="Estimated remaining time in seconds"
    )
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class PreviewEventData(BaseModel):
    """Preview event data structure"""

    type: str = SSEEventType.PREVIEW
    jobId: str = Field(..., description="Generation job ID")
    markdown: str = Field(..., description="Partial script content in markdown")
    isPartial: bool = Field(True, description="Whether this is partial content")
    wordCount: int | None = Field(None, description="Current word count")
    estimatedTokens: int | None = Field(None, description="Estimated token count")


class CompletedEventData(BaseModel):
    """Completed event data structure"""

    type: str = SSEEventType.COMPLETED
    jobId: str = Field(..., description="Generation job ID")
    result: dict[str, Any] = Field(..., description="Final generation result")

    @classmethod
    def create_result(
        cls, job_id: str, markdown: str, tokens: int, **kwargs: Any
    ) -> "CompletedEventData":
        """Create completed event with result data"""
        result = {"markdown": markdown, "tokens": tokens, **kwargs}
        return cls(jobId=job_id, result=result)


class FailedEventData(BaseModel):
    """Failed event data structure"""

    type: str = SSEEventType.FAILED
    jobId: str = Field(..., description="Generation job ID")
    error: dict[str, Any] = Field(..., description="Error information")

    @classmethod
    def create_error(
        cls,
        job_id: str,
        code: str,
        message: str,
        retryable: bool = False,
        **kwargs: Any,
    ) -> "FailedEventData":
        """Create failed event with error data"""
        error = {"code": code, "message": message, "retryable": retryable, **kwargs}
        return cls(jobId=job_id, error=error)


class HeartbeatEventData(BaseModel):
    """Heartbeat event data structure"""

    type: str = SSEEventType.HEARTBEAT
    timestamp: str = Field(..., description="Current timestamp in ISO format")
    jobId: str | None = Field(None, description="Optional job ID")

    @classmethod
    def create_now(cls, job_id: str | None = None) -> "HeartbeatEventData":
        """Create heartbeat event with current timestamp"""
        return cls(timestamp=datetime.now(timezone.utc).isoformat(), jobId=job_id)


class SSEEvent(BaseModel):
    """Base SSE event structure"""

    event: SSEEventType = Field(..., description="Event type")
    data: (
        ProgressEventData
        | PreviewEventData
        | CompletedEventData
        | FailedEventData
        | HeartbeatEventData
    ) = Field(..., description="Event data")

    def format_sse(self, event_id: str | None = None) -> str:
        """Format as SSE message with optional ID field"""
        data_json = json.dumps(self.data.model_dump(), ensure_ascii=False)

        sse_message = f"event: {self.event.value}\ndata: {data_json}\n"

        # Add ID field for Last-Event-ID support
        if event_id:
            sse_message = f"id: {event_id}\n{sse_message}"

        return sse_message + "\n"


class GenerationJob(BaseModel):
    """Generation job tracking model"""

    jobId: str = Field(..., description="Unique job ID")
    projectId: str = Field(..., description="Project ID")
    episodeNumber: int | None = Field(None, description="Episode number if specified")

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
    finalContent: str | None = Field(None, description="Final completed content")

    # Metadata
    tokens: int = Field(default=0, description="Token count")
    wordCount: int = Field(default=0, description="Word count")
    modelUsed: str | None = Field(None, description="AI model used")

    # Timing
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    startedAt: datetime | None = Field(None, description="When streaming started")
    completedAt: datetime | None = Field(None, description="When completed")
    estimatedDuration: int | None = Field(
        None, description="Estimated duration in seconds"
    )

    # Error handling
    errorCode: str | None = Field(None, description="Error code if failed")
    errorMessage: str | None = Field(None, description="Error message if failed")
    retryCount: int = Field(default=0, description="Number of retry attempts")

    # Episode integration
    episodeId: str | None = Field(None, description="Created episode ID")
    savedToEpisode: bool = Field(default=False, description="Whether saved to episode")

    # Event tracking for Last-Event-ID support
    eventSequence: int = Field(
        default=0, description="Event sequence number for Last-Event-ID"
    )
    lastEventId: str | None = Field(None, description="Last event ID sent to client")

    def to_progress_event(self) -> SSEEvent:
        """Convert to progress SSE event"""
        data = ProgressEventData(
            jobId=self.jobId,
            value=self.progress,
            currentStep=self.currentStep,
            estimatedTime=self.get_estimated_remaining_time(),
            metadata=None,
        )
        return SSEEvent(event=SSEEventType.PROGRESS, data=data)

    def to_preview_event(self) -> SSEEvent:
        """Convert to preview SSE event"""
        data = PreviewEventData(
            jobId=self.jobId,
            markdown=self.currentContent,
            isPartial=self.status != GenerationJobStatus.COMPLETED,
            wordCount=self.wordCount,
            estimatedTokens=self.tokens,
        )
        return SSEEvent(event=SSEEventType.PREVIEW, data=data)

    def to_completed_event(self) -> SSEEvent:
        """Convert to completed SSE event"""
        data = CompletedEventData.create_result(
            job_id=self.jobId,
            markdown=self.finalContent or self.currentContent,
            tokens=self.tokens,
            wordCount=self.wordCount,
            modelUsed=self.modelUsed,
            episodeId=self.episodeId,
            savedToEpisode=self.savedToEpisode,
        )
        return SSEEvent(event=SSEEventType.COMPLETED, data=data)

    def to_failed_event(self) -> SSEEvent:
        """Convert to failed SSE event"""
        data = FailedEventData.create_error(
            job_id=self.jobId,
            code=self.errorCode or "GENERATION_ERROR",
            message=self.errorMessage or "Generation failed",
            retryable=self.retryCount < 3,
        )
        return SSEEvent(event=SSEEventType.FAILED, data=data)

    def get_estimated_remaining_time(self) -> int | None:
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
        self, final_content: str, tokens: int = 0, model_used: str | None = None
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
    episodeNumber: int | None = Field(
        None, description="Episode number (auto-assigned if not provided)"
    )
    title: str | None = Field(
        None, description="Script title (auto-generated if not provided)"
    )
    description: str = Field(..., description="Script description/prompt")
    scriptType: str = Field(default="drama", description="Type of script")
    model: str | None = Field(None, description="Preferred AI model")
    temperature: float | None = Field(0.7, description="Generation creativity")
    lengthTarget: int | None = Field(None, description="Target length in words")


class GenerationJobResponse(BaseModel):
    """Response when creating a generation job"""

    jobId: str = Field(..., description="Unique job ID")
    status: GenerationJobStatus = Field(..., description="Initial job status")
    sseUrl: str = Field(..., description="SSE endpoint URL")
    cancelUrl: str = Field(..., description="Cancellation endpoint URL")

    # Job details
    projectId: str
    episodeNumber: int | None = None
    title: str
    estimatedDuration: int | None = Field(
        None, description="Estimated duration in seconds"
    )
