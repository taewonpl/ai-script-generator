"""
RAG Job State Machine and Models
Defines the complete RAG processing pipeline states and data models
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

from generation_service.database.connection import Base


class RAGJobStatus(str, Enum):
    """RAG processing job states following complete pipeline"""
    # Main pipeline states
    QUEUED = "queued"           # Job queued for processing
    UPLOADING = "uploading"     # File upload in progress
    EXTRACTING = "extracting"   # Text extraction from document
    OCR = "ocr"                # OCR processing (if extraction fails/incomplete)
    CHUNKING = "chunking"       # Text chunking into segments
    EMBEDDING = "embedding"     # Generating embeddings
    INDEXED = "indexed"         # Successfully indexed in ChromaDB
    
    # Failure states
    FAILED_EXTRACT = "failed_extract"   # Text extraction failed
    FAILED_OCR = "failed_ocr"          # OCR processing failed
    FAILED_EMBED = "failed_embed"       # Embedding generation failed
    FAILED_STORE = "failed_store"       # ChromaDB storage failed
    
    # Control states
    CANCELED = "canceled"       # Job canceled by user or system


class RAGJobErrorCode(str, Enum):
    """Specific error codes for failed RAG jobs"""
    # File/extraction errors
    FILE_TOO_LARGE = "file_too_large"
    FILE_CORRUPTED = "file_corrupted"
    UNSUPPORTED_FORMAT = "unsupported_format"
    NO_TEXT_FOUND = "no_text_found"
    
    # OCR errors
    OCR_ENGINE_FAILED = "ocr_engine_failed"
    OCR_TIMEOUT = "ocr_timeout"
    IMAGE_QUALITY_TOO_LOW = "image_quality_too_low"
    
    # Processing errors
    CHUNKING_FAILED = "chunking_failed"
    EMBEDDING_SERVICE_DOWN = "embedding_service_down"
    EMBEDDING_QUOTA_EXCEEDED = "embedding_quota_exceeded"
    
    # Storage errors
    CHROMADB_CONNECTION_FAILED = "chromadb_connection_failed"
    DUPLICATE_DOCUMENT = "duplicate_document"
    STORAGE_QUOTA_EXCEEDED = "storage_quota_exceeded"
    
    # System errors
    OUT_OF_MEMORY = "out_of_memory"
    TIMEOUT = "timeout"
    UNKNOWN_ERROR = "unknown_error"


# SQLAlchemy Database Models

class RAGJobDB(Base):
    """SQLAlchemy model for RAG jobs"""
    __tablename__ = "rag_jobs"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    document_id = Column(String, nullable=True)
    
    # Status tracking
    status = Column(String, nullable=False, default="queued")
    progress_pct = Column(Float, nullable=False, default=0.0)
    current_step = Column(String, nullable=False, default="queued")
    
    # Metadata as JSON
    metadata = Column(JSON, nullable=False, default=dict)
    
    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Configuration
    chunk_size = Column(Integer, nullable=False, default=1024)
    chunk_overlap = Column(Integer, nullable=False, default=128)
    embed_version = Column(String, nullable=False, default="v1")


class RAGDocumentDB(Base):
    """SQLAlchemy model for RAG documents"""
    __tablename__ = "rag_documents"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    
    # File info
    name = Column(String, nullable=False)
    file_sha256 = Column(String, nullable=False, index=True)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String, nullable=False)
    
    # Processing results
    status = Column(String, nullable=False)
    chunks_count = Column(Integer, nullable=False, default=0)
    embed_version = Column(String, nullable=False)
    
    # Timestamps
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    indexed_at = Column(DateTime, nullable=True)
    
    # Metadata as JSON
    metadata = Column(JSON, nullable=False, default=dict)


# Pydantic Models (for API)

class RAGJobMetadata(BaseModel):
    """Metadata for RAG job execution"""
    file_name: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="MIME type")
    file_sha256: str = Field(..., description="SHA-256 hash for deduplication")
    
    # Processing metadata
    pages_total: Optional[int] = Field(None, description="Total pages (PDF only)")
    pages_processed: Optional[int] = Field(None, description="Successfully processed pages")
    pages_failed: Optional[int] = Field(None, description="Pages that failed processing")
    
    # Extraction results
    text_length: Optional[int] = Field(None, description="Extracted text length")
    chunks_total: Optional[int] = Field(None, description="Total chunks created")
    chunks_indexed: Optional[int] = Field(None, description="Successfully indexed chunks")
    
    # Quality metrics
    ocr_confidence: Optional[float] = Field(None, description="OCR confidence score (0-1)")
    extraction_method: Optional[str] = Field(None, description="text|ocr|hybrid")
    
    # Error details
    error_code: Optional[RAGJobErrorCode] = Field(None, description="Specific error code")
    error_message: Optional[str] = Field(None, description="Human-readable error message")
    retry_count: int = Field(0, description="Number of retry attempts")
    
    # Timing
    started_at: Optional[datetime] = Field(None, description="Processing start time")
    ended_at: Optional[datetime] = Field(None, description="Processing end time")
    
    # Tracing
    request_id: Optional[str] = Field(None, description="Request trace ID")
    trace_id: Optional[str] = Field(None, description="Distributed trace ID")


class RAGJob(BaseModel):
    """Complete RAG processing job model"""
    id: str = Field(..., description="Unique job ID")
    project_id: str = Field(..., description="Associated project ID")
    document_id: Optional[str] = Field(None, description="Document ID (after creation)")
    
    # Status tracking
    status: RAGJobStatus = Field(RAGJobStatus.QUEUED, description="Current job status")
    progress_pct: float = Field(0.0, description="Progress percentage (0-100)")
    current_step: str = Field("queued", description="Human-readable current step")
    
    # Metadata
    metadata: RAGJobMetadata = Field(..., description="Job execution metadata")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Configuration
    chunk_size: int = Field(1024, description="Target chunk size in tokens")
    chunk_overlap: int = Field(128, description="Chunk overlap in tokens")
    embed_version: str = Field("v1", description="Embedding model version")
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }


class RAGDocument(BaseModel):
    """RAG document model (indexed document)"""
    id: str = Field(..., description="Unique document ID")
    project_id: str = Field(..., description="Associated project ID")
    
    # File info
    name: str = Field(..., description="Document name")
    file_sha256: str = Field(..., description="File hash for deduplication")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="MIME type")
    
    # Processing results
    status: RAGJobStatus = Field(..., description="Current document status")
    chunks_count: int = Field(0, description="Number of chunks indexed")
    embed_version: str = Field(..., description="Embedding model version")
    
    # Timestamps
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    indexed_at: Optional[datetime] = Field(None, description="When indexing completed")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }


class RAGIngestRequest(BaseModel):
    """Request to ingest a document into RAG pipeline"""
    project_id: str = Field(..., description="Project ID to associate with document")
    file_id: str = Field(..., description="Uploaded file identifier")
    
    # Optional processing configuration
    chunk_size: Optional[int] = Field(None, description="Custom chunk size (512-2048)")
    chunk_overlap: Optional[int] = Field(None, description="Custom chunk overlap (64-512)")
    force_ocr: Optional[bool] = Field(False, description="Force OCR even if text extraction works")
    
    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "project_id": "proj_123",
                "file_id": "file_abc",
                "chunk_size": 1024,
                "chunk_overlap": 128
            }
        }


class RAGIngestResponse(BaseModel):
    """Response from RAG ingest request"""
    job_id: str = Field(..., description="RAG processing job ID")
    status: RAGJobStatus = Field(..., description="Initial job status")
    progress_pct: float = Field(..., description="Initial progress percentage")
    
    # Deduplication info
    is_duplicate: bool = Field(False, description="Whether this file was already indexed")
    existing_document_id: Optional[str] = Field(None, description="ID of existing document if duplicate")
    
    # Tracing
    request_id: str = Field(..., description="Request trace ID")
    trace_id: str = Field(..., description="Distributed trace ID")


class RAGJobStatusResponse(BaseModel):
    """Response for RAG job status queries"""
    job_id: str = Field(..., description="Job ID")
    status: RAGJobStatus = Field(..., description="Current status")
    progress_pct: float = Field(..., description="Progress percentage (0-100)")
    current_step: str = Field(..., description="Human-readable current step")
    
    # Results (when completed)
    document_id: Optional[str] = Field(None, description="Document ID if successful")
    chunks_indexed: Optional[int] = Field(None, description="Number of chunks indexed")
    
    # Error info (when failed)
    error_code: Optional[RAGJobErrorCode] = Field(None, description="Error code if failed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(0, description="Number of retries attempted")
    
    # Timing
    started_at: Optional[datetime] = Field(None, description="Processing start time")
    ended_at: Optional[datetime] = Field(None, description="Processing end time")
    estimated_remaining_seconds: Optional[int] = Field(None, description="Estimated time remaining")
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }


class RAGDocumentsResponse(BaseModel):
    """Response for RAG documents listing"""
    documents: list[RAGDocument] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    indexed_count: int = Field(..., description="Number of indexed documents")
    processing_count: int = Field(..., description="Number of documents being processed")
    failed_count: int = Field(..., description="Number of failed documents")


# State machine transitions for validation
RAG_VALID_TRANSITIONS = {
    RAGJobStatus.QUEUED: [RAGJobStatus.UPLOADING, RAGJobStatus.CANCELED],
    RAGJobStatus.UPLOADING: [RAGJobStatus.EXTRACTING, RAGJobStatus.FAILED_EXTRACT, RAGJobStatus.CANCELED],
    RAGJobStatus.EXTRACTING: [RAGJobStatus.OCR, RAGJobStatus.CHUNKING, RAGJobStatus.FAILED_EXTRACT, RAGJobStatus.CANCELED],
    RAGJobStatus.OCR: [RAGJobStatus.CHUNKING, RAGJobStatus.FAILED_OCR, RAGJobStatus.CANCELED],
    RAGJobStatus.CHUNKING: [RAGJobStatus.EMBEDDING, RAGJobStatus.FAILED_EMBED, RAGJobStatus.CANCELED],
    RAGJobStatus.EMBEDDING: [RAGJobStatus.INDEXED, RAGJobStatus.FAILED_EMBED, RAGJobStatus.CANCELED],
    RAGJobStatus.INDEXED: [],  # Terminal state
    RAGJobStatus.FAILED_EXTRACT: [RAGJobStatus.EXTRACTING, RAGJobStatus.CANCELED],  # Can retry
    RAGJobStatus.FAILED_OCR: [RAGJobStatus.OCR, RAGJobStatus.CANCELED],  # Can retry
    RAGJobStatus.FAILED_EMBED: [RAGJobStatus.EMBEDDING, RAGJobStatus.CANCELED],  # Can retry
    RAGJobStatus.FAILED_STORE: [RAGJobStatus.EMBEDDING, RAGJobStatus.CANCELED],  # Can retry
    RAGJobStatus.CANCELED: [],  # Terminal state
}

# Progress percentages for each state
RAG_PROGRESS_MAP = {
    RAGJobStatus.QUEUED: 0,
    RAGJobStatus.UPLOADING: 10,
    RAGJobStatus.EXTRACTING: 25,
    RAGJobStatus.OCR: 40,
    RAGJobStatus.CHUNKING: 60,
    RAGJobStatus.EMBEDDING: 80,
    RAGJobStatus.INDEXED: 100,
    # Failed states keep their last progress
    RAGJobStatus.FAILED_EXTRACT: 25,
    RAGJobStatus.FAILED_OCR: 40,
    RAGJobStatus.FAILED_EMBED: 80,
    RAGJobStatus.FAILED_STORE: 90,
    RAGJobStatus.CANCELED: 0,
}