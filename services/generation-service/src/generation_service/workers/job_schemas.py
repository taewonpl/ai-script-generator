"""
Enhanced job schemas and models for durable RAG worker system
Includes state machine, retry policies, and DLQ handling
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator
import json

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class WorkerJobStatus(str, Enum):
    """Enhanced job status for worker system"""
    # Queue states
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    DEFERRED = "deferred"
    
    # Processing states
    STARTED = "started"
    UPLOADING = "uploading"
    EXTRACTING = "extracting"
    OCR = "ocr"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    
    # Final states
    INDEXED = "indexed"
    CANCELED = "canceled"
    
    # Failure states
    FAILED_VALIDATION = "failed_validation"
    FAILED_UPLOAD = "failed_upload"
    FAILED_EXTRACT = "failed_extract"
    FAILED_OCR = "failed_ocr"
    FAILED_CHUNK = "failed_chunk"
    FAILED_EMBED = "failed_embed"
    FAILED_STORE = "failed_store"
    FAILED_TIMEOUT = "failed_timeout"
    FAILED_CANCELED = "failed_canceled"
    
    # DLQ state
    DEAD_LETTER = "dead_letter"


class WorkerErrorCode(str, Enum):
    """Detailed error codes for troubleshooting"""
    # Validation errors
    INVALID_FILE_TYPE = "invalid_file_type"
    FILE_TOO_LARGE = "file_too_large"
    INVALID_PROJECT = "invalid_project"
    DUPLICATE_INGEST = "duplicate_ingest"
    
    # File errors
    FILE_NOT_FOUND = "file_not_found"
    FILE_CORRUPTED = "file_corrupted"
    FILE_LOCKED = "file_locked"
    STORAGE_UNAVAILABLE = "storage_unavailable"
    
    # Processing errors
    EXTRACTION_FAILED = "extraction_failed"
    OCR_ENGINE_ERROR = "ocr_engine_error"
    OCR_CONFIDENCE_LOW = "ocr_confidence_low"
    CHUNKING_ERROR = "chunking_error"
    
    # Embedding errors
    EMBEDDING_API_ERROR = "embedding_api_error"
    EMBEDDING_RATE_LIMITED = "embedding_rate_limited"
    EMBEDDING_QUOTA_EXCEEDED = "embedding_quota_exceeded"
    EMBEDDING_MODEL_UNAVAILABLE = "embedding_model_unavailable"
    
    # Storage errors
    CHROMA_CONNECTION_ERROR = "chroma_connection_error"
    CHROMA_WRITE_ERROR = "chroma_write_error"
    INDEX_CORRUPTION = "index_corruption"
    
    # System errors
    WORKER_TIMEOUT = "worker_timeout"
    MEMORY_EXHAUSTED = "memory_exhausted"
    DISK_FULL = "disk_full"
    NETWORK_ERROR = "network_error"
    
    # Cancellation
    USER_CANCELED = "user_canceled"
    SYSTEM_CANCELED = "system_canceled"
    
    UNKNOWN_ERROR = "unknown_error"


class RetryPolicy(str, Enum):
    """Retry policies for different error types"""
    NO_RETRY = "no_retry"           # Don't retry (validation errors)
    LINEAR_BACKOFF = "linear"       # Linear: 1s, 2s, 3s, 4s
    EXPONENTIAL_BACKOFF = "exp"     # Exponential: 1s, 5s, 25s, 125s
    IMMEDIATE_RETRY = "immediate"   # Retry immediately (transient errors)
    DELAYED_RETRY = "delayed"       # Fixed 30s delay


# State machine transitions
VALID_STATE_TRANSITIONS = {
    WorkerJobStatus.QUEUED: [
        WorkerJobStatus.STARTED, WorkerJobStatus.SCHEDULED, WorkerJobStatus.CANCELED
    ],
    WorkerJobStatus.SCHEDULED: [
        WorkerJobStatus.QUEUED, WorkerJobStatus.STARTED, WorkerJobStatus.CANCELED
    ],
    WorkerJobStatus.DEFERRED: [
        WorkerJobStatus.QUEUED, WorkerJobStatus.CANCELED
    ],
    WorkerJobStatus.STARTED: [
        WorkerJobStatus.UPLOADING, WorkerJobStatus.FAILED_VALIDATION, WorkerJobStatus.CANCELED
    ],
    WorkerJobStatus.UPLOADING: [
        WorkerJobStatus.EXTRACTING, WorkerJobStatus.FAILED_UPLOAD, WorkerJobStatus.CANCELED
    ],
    WorkerJobStatus.EXTRACTING: [
        WorkerJobStatus.OCR, WorkerJobStatus.CHUNKING, WorkerJobStatus.FAILED_EXTRACT, WorkerJobStatus.CANCELED
    ],
    WorkerJobStatus.OCR: [
        WorkerJobStatus.CHUNKING, WorkerJobStatus.FAILED_OCR, WorkerJobStatus.CANCELED
    ],
    WorkerJobStatus.CHUNKING: [
        WorkerJobStatus.EMBEDDING, WorkerJobStatus.FAILED_CHUNK, WorkerJobStatus.CANCELED
    ],
    WorkerJobStatus.EMBEDDING: [
        WorkerJobStatus.STORING, WorkerJobStatus.FAILED_EMBED, WorkerJobStatus.CANCELED
    ],
    WorkerJobStatus.STORING: [
        WorkerJobStatus.INDEXED, WorkerJobStatus.FAILED_STORE, WorkerJobStatus.CANCELED
    ],
    # Final states have no transitions
    WorkerJobStatus.INDEXED: [],
    WorkerJobStatus.CANCELED: [],
    WorkerJobStatus.DEAD_LETTER: [],
    # Failed states can only go to DLQ or be retried (back to QUEUED)
    **{status: [WorkerJobStatus.QUEUED, WorkerJobStatus.DEAD_LETTER] 
       for status in WorkerJobStatus if status.value.startswith('failed_')}
}

# Progress percentage mapping
PROGRESS_PERCENTAGE_MAP = {
    WorkerJobStatus.QUEUED: 0.0,
    WorkerJobStatus.SCHEDULED: 0.0,
    WorkerJobStatus.DEFERRED: 0.0,
    WorkerJobStatus.STARTED: 5.0,
    WorkerJobStatus.UPLOADING: 10.0,
    WorkerJobStatus.EXTRACTING: 25.0,
    WorkerJobStatus.OCR: 40.0,
    WorkerJobStatus.CHUNKING: 55.0,
    WorkerJobStatus.EMBEDDING: 75.0,
    WorkerJobStatus.STORING: 90.0,
    WorkerJobStatus.INDEXED: 100.0,
    WorkerJobStatus.CANCELED: 0.0,
    WorkerJobStatus.DEAD_LETTER: 0.0,
    # Failed states keep last progress
}

# Error code to retry policy mapping
ERROR_RETRY_POLICIES = {
    # No retry for validation errors
    WorkerErrorCode.INVALID_FILE_TYPE: RetryPolicy.NO_RETRY,
    WorkerErrorCode.FILE_TOO_LARGE: RetryPolicy.NO_RETRY,
    WorkerErrorCode.INVALID_PROJECT: RetryPolicy.NO_RETRY,
    WorkerErrorCode.DUPLICATE_INGEST: RetryPolicy.NO_RETRY,
    
    # Immediate retry for transient file errors
    WorkerErrorCode.FILE_LOCKED: RetryPolicy.IMMEDIATE_RETRY,
    WorkerErrorCode.STORAGE_UNAVAILABLE: RetryPolicy.LINEAR_BACKOFF,
    
    # Exponential backoff for processing errors
    WorkerErrorCode.EXTRACTION_FAILED: RetryPolicy.EXPONENTIAL_BACKOFF,
    WorkerErrorCode.OCR_ENGINE_ERROR: RetryPolicy.EXPONENTIAL_BACKOFF,
    WorkerErrorCode.CHUNKING_ERROR: RetryPolicy.LINEAR_BACKOFF,
    
    # Delayed retry for rate limiting
    WorkerErrorCode.EMBEDDING_RATE_LIMITED: RetryPolicy.DELAYED_RETRY,
    WorkerErrorCode.EMBEDDING_API_ERROR: RetryPolicy.EXPONENTIAL_BACKOFF,
    
    # Linear backoff for storage errors
    WorkerErrorCode.CHROMA_CONNECTION_ERROR: RetryPolicy.LINEAR_BACKOFF,
    WorkerErrorCode.CHROMA_WRITE_ERROR: RetryPolicy.LINEAR_BACKOFF,
    
    # No retry for system limits
    WorkerErrorCode.WORKER_TIMEOUT: RetryPolicy.NO_RETRY,
    WorkerErrorCode.MEMORY_EXHAUSTED: RetryPolicy.NO_RETRY,
    WorkerErrorCode.DISK_FULL: RetryPolicy.NO_RETRY,
    
    # No retry for cancellation
    WorkerErrorCode.USER_CANCELED: RetryPolicy.NO_RETRY,
    WorkerErrorCode.SYSTEM_CANCELED: RetryPolicy.NO_RETRY,
}

# Maximum retry counts by error type
MAX_RETRIES_BY_ERROR = {
    RetryPolicy.NO_RETRY: 0,
    RetryPolicy.IMMEDIATE_RETRY: 3,
    RetryPolicy.LINEAR_BACKOFF: 4,
    RetryPolicy.EXPONENTIAL_BACKOFF: 4,
    RetryPolicy.DELAYED_RETRY: 3,
}


@dataclass
class JobMetrics:
    """Metrics collected during job processing"""
    # Timing metrics
    queue_wait_time_seconds: float = 0.0
    processing_time_seconds: float = 0.0
    upload_time_seconds: float = 0.0
    extraction_time_seconds: float = 0.0
    ocr_time_seconds: float = 0.0
    chunking_time_seconds: float = 0.0
    embedding_time_seconds: float = 0.0
    storage_time_seconds: float = 0.0
    
    # Content metrics
    file_size_bytes: int = 0
    extracted_text_length: int = 0
    chunks_created: int = 0
    chunks_embedded: int = 0
    chunks_stored: int = 0
    
    # Quality metrics
    ocr_confidence_score: float = 0.0
    extraction_method: str = ""
    embedding_model: str = ""
    avg_chunk_size: int = 0
    
    # Cost metrics
    embedding_tokens_used: int = 0
    estimated_cost_usd: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'timing': {
                'queue_wait_time_seconds': self.queue_wait_time_seconds,
                'processing_time_seconds': self.processing_time_seconds,
                'upload_time_seconds': self.upload_time_seconds,
                'extraction_time_seconds': self.extraction_time_seconds,
                'ocr_time_seconds': self.ocr_time_seconds,
                'chunking_time_seconds': self.chunking_time_seconds,
                'embedding_time_seconds': self.embedding_time_seconds,
                'storage_time_seconds': self.storage_time_seconds,
            },
            'content': {
                'file_size_bytes': self.file_size_bytes,
                'extracted_text_length': self.extracted_text_length,
                'chunks_created': self.chunks_created,
                'chunks_embedded': self.chunks_embedded,
                'chunks_stored': self.chunks_stored,
            },
            'quality': {
                'ocr_confidence_score': self.ocr_confidence_score,
                'extraction_method': self.extraction_method,
                'embedding_model': self.embedding_model,
                'avg_chunk_size': self.avg_chunk_size,
            },
            'cost': {
                'embedding_tokens_used': self.embedding_tokens_used,
                'estimated_cost_usd': self.estimated_cost_usd,
            }
        }


class WorkerJobDB(Base):
    """Database model for worker jobs with enhanced tracking"""
    __tablename__ = 'worker_jobs'
    
    # Primary identifiers
    id = Column(String(128), primary_key=True)  # RQ job ID
    ingest_id = Column(String(128), unique=True, nullable=False, index=True)
    project_id = Column(String(64), nullable=False, index=True)
    document_id = Column(String(128), nullable=True, index=True)
    
    # Job state
    status = Column(String(32), nullable=False, default=WorkerJobStatus.QUEUED.value, index=True)
    current_step = Column(String(32), nullable=False, default="queued")
    progress_pct = Column(Float, default=0.0)
    
    # File information
    file_id = Column(String(128), nullable=False)
    file_sha256 = Column(String(64), nullable=False, index=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String(100), nullable=True)
    
    # Processing configuration
    embed_version = Column(String(16), nullable=False, index=True)
    chunk_size = Column(Integer, default=1024)
    chunk_overlap = Column(Integer, default=128)
    force_ocr = Column(Boolean, default=False)
    
    # Retry and error handling
    attempt = Column(Integer, default=1)
    max_retries = Column(Integer, default=4)
    retry_policy = Column(String(32), nullable=True)
    
    # Error information
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    stack_trace = Column(Text, nullable=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Job metadata and metrics
    metadata = Column(JSON, default=dict)
    metrics = Column(JSON, nullable=True)
    
    # Trace information
    trace_id = Column(String(64), nullable=False, index=True)
    parent_job_id = Column(String(128), nullable=True)  # For retry chains
    
    # Cancellation
    canceled_at = Column(DateTime, nullable=True)
    cancel_reason = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<WorkerJob {self.id} ({self.status})>"


class DLQEntryDB(Base):
    """Database model for Dead Letter Queue entries"""
    __tablename__ = 'dlq_entries'
    
    # Primary key
    id = Column(String(128), primary_key=True)  # DLQ entry ID
    
    # Original job information
    original_job_id = Column(String(128), nullable=False, index=True)
    ingest_id = Column(String(128), nullable=False, index=True)
    project_id = Column(String(64), nullable=False, index=True)
    
    # Failure information
    error_type = Column(String(64), nullable=False, index=True)
    error_code = Column(String(64), nullable=False)
    error_message = Column(Text, nullable=False)
    last_step = Column(String(32), nullable=False)
    
    # Retry history
    attempts = Column(Integer, nullable=False)
    failed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    first_attempt_at = Column(DateTime, nullable=True)
    
    # Debug information
    trace_id = Column(String(64), nullable=False, index=True)
    stack_trace = Column(Text, nullable=True)
    job_payload = Column(JSON, nullable=True)
    final_metadata = Column(JSON, nullable=True)
    
    # Resolution
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(String(128), nullable=True)  # User/system that resolved
    
    def __repr__(self):
        return f"<DLQEntry {self.id} ({self.error_type})>"


# Pydantic models for API
class JobStatusResponse(BaseModel):
    """Response model for job status queries"""
    job_id: str
    ingest_id: str
    status: WorkerJobStatus
    progress_pct: float
    current_step: str
    
    # Timing
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    estimated_remaining_seconds: Optional[int] = None
    
    # Results
    document_id: Optional[str] = None
    chunks_indexed: Optional[int] = None
    
    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Queue information
    queue_position: Optional[int] = None
    
    class Config:
        use_enum_values = True


class DLQListResponse(BaseModel):
    """Response for listing DLQ entries"""
    entries: List[Dict[str, Any]]
    total: int
    resolved_count: int
    error_type_counts: Dict[str, int]
    
    class Config:
        use_enum_values = True


class ReindexRequest(BaseModel):
    """Request model for reindexing operations"""
    project_id: str
    new_embed_version: Optional[str] = None
    batch_size: int = Field(default=10, ge=1, le=100)
    force_reindex: bool = False  # Reindex even if version matches
    
    @validator('project_id')
    def validate_project_id(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Invalid project_id')
        return v


class ReindexResponse(BaseModel):
    """Response model for reindex operations"""
    reindex_job_id: str
    documents_to_reindex: int
    old_embed_version: Optional[str] = None
    new_embed_version: str
    estimated_duration_minutes: int
    batch_size: int
    
    class Config:
        use_enum_values = True


class QueueStatsResponse(BaseModel):
    """Response model for queue statistics"""
    # Queue metrics
    queue_length: int
    dlq_length: int
    processing_jobs: int
    
    # Worker metrics
    active_workers: int
    total_workers: int
    worker_utilization: float
    
    # Performance metrics
    avg_processing_time_minutes: float
    jobs_completed_24h: int
    jobs_failed_24h: int
    success_rate_24h: float
    
    # Rate limiting
    embedding_rate_current: int
    embedding_rate_limit: int
    embedding_quota_remaining: int
    
    # Version information
    embed_version: str
    outdated_documents: int
    
    # Health status
    queue_health: str  # 'healthy', 'degraded', 'unhealthy'
    worker_health: str
    storage_health: str
    
    class Config:
        use_enum_values = True


def calculate_retry_delay(
    retry_count: int, 
    policy: RetryPolicy,
    base_delay: int = 1
) -> int:
    """Calculate retry delay based on policy"""
    
    if policy == RetryPolicy.NO_RETRY:
        return 0
    elif policy == RetryPolicy.IMMEDIATE_RETRY:
        return 0
    elif policy == RetryPolicy.LINEAR_BACKOFF:
        return base_delay * retry_count
    elif policy == RetryPolicy.EXPONENTIAL_BACKOFF:
        return min(base_delay * (5 ** (retry_count - 1)), 125)  # Cap at 125 seconds
    elif policy == RetryPolicy.DELAYED_RETRY:
        return 30  # Fixed 30 second delay
    else:
        return base_delay


def should_retry_error(error_code: WorkerErrorCode, retry_count: int) -> bool:
    """Determine if an error should be retried"""
    
    policy = ERROR_RETRY_POLICIES.get(error_code, RetryPolicy.EXPONENTIAL_BACKOFF)
    max_retries = MAX_RETRIES_BY_ERROR.get(policy, 4)
    
    return retry_count < max_retries and policy != RetryPolicy.NO_RETRY


def get_retry_policy(error_code: WorkerErrorCode) -> RetryPolicy:
    """Get retry policy for an error code"""
    return ERROR_RETRY_POLICIES.get(error_code, RetryPolicy.EXPONENTIAL_BACKOFF)