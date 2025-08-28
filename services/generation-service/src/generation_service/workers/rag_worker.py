"""
Durable RAG worker implementation with cancellation, rate limiting, and state management
"""

import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import asyncio
import logging
from contextlib import asynccontextmanager

import redis
from rq import get_current_job
from rq.exceptions import WorkerLostError
from sqlalchemy.orm import Session

from generation_service.database import get_db
from generation_service.services.rag_processor import RAGProcessor, FileInfo
from generation_service.models.rag_jobs import RAGDocumentDB, RAGJobStatus
from generation_service.workers.job_schemas import (
    WorkerJobDB, DLQEntryDB, WorkerJobStatus, WorkerErrorCode,
    JobMetrics, calculate_retry_delay, should_retry_error, get_retry_policy,
    VALID_STATE_TRANSITIONS, PROGRESS_PERCENTAGE_MAP
)
from generation_service.workers.worker_adapter import WorkerRedisConnection

logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/5")
EMBED_VERSION = os.getenv("RAG_EMBED_VERSION", "v1.0")
MAX_FILE_SIZE_MB = int(os.getenv("RAG_MAX_FILE_SIZE_MB", "30"))
MAX_PAGES = int(os.getenv("RAG_MAX_PAGES", "500"))
CHUNK_TIMEOUT_SECONDS = int(os.getenv("RAG_CHUNK_TIMEOUT", "300"))

# Rate limiting for embeddings
EMBEDDING_RATE_LIMIT_KEY = "rag:embedding:rate_limit"
EMBEDDING_RATE_WINDOW = 60  # 1 minute window
EMBEDDING_MAX_PER_WINDOW = int(os.getenv("RAG_EMBEDDING_RATE_LIMIT", "1000"))

# Batch processing
EMBEDDING_BATCH_SIZE = int(os.getenv("RAG_EMBEDDING_BATCH_SIZE", "32"))
EMBEDDING_CONCURRENCY_LIMIT = int(os.getenv("RAG_EMBEDDING_CONCURRENCY", "3"))


class WorkerCancellationError(Exception):
    """Raised when worker job is canceled"""
    pass


class WorkerRateLimitError(Exception):
    """Raised when rate limit is exceeded"""
    pass


class WorkerProgressTracker:
    """Tracks and reports job progress with cancellation checking"""
    
    def __init__(self, job_id: str, redis_conn: redis.Redis):
        self.job_id = job_id
        self.redis = redis_conn
        self.current_status = WorkerJobStatus.STARTED
        self.progress_pct = 0.0
        self.last_check = time.time()
        
        # Get RQ job for metadata updates
        self.rq_job = get_current_job()
    
    def check_cancellation(self):
        """Check if job has been canceled"""
        cancel_key = f"cancel:{self.job_id}"
        cancel_data = self.redis.get(cancel_key)
        
        if cancel_data:
            cancel_info = json.loads(cancel_data)
            logger.info(f"Job {self.job_id} canceled: {cancel_info.get('reason', 'Unknown reason')}")
            raise WorkerCancellationError(f"Job canceled: {cancel_info.get('reason', 'User request')}")
    
    def update_progress(
        self, 
        status: WorkerJobStatus, 
        progress_pct: Optional[float] = None,
        step_info: Optional[str] = None
    ):
        """Update job progress with cancellation check"""
        
        # Check for cancellation every 5 seconds
        now = time.time()
        if now - self.last_check > 5.0:
            self.check_cancellation()
            self.last_check = now
        
        # Validate state transition
        if status not in VALID_STATE_TRANSITIONS.get(self.current_status, []):
            logger.warning(f"Invalid state transition from {self.current_status} to {status}")
            return
        
        self.current_status = status
        
        # Use default progress if not provided
        if progress_pct is None:
            progress_pct = PROGRESS_PERCENTAGE_MAP.get(status, self.progress_pct)
        
        self.progress_pct = progress_pct
        
        # Update RQ job metadata
        if self.rq_job:
            self.rq_job.meta.update({
                'current_step': status.value,
                'progress_pct': progress_pct,
                'step_info': step_info,
                'updated_at': datetime.utcnow().isoformat(),
            })
            self.rq_job.save_meta()
        
        logger.info(f"Job {self.job_id} progress: {status.value} ({progress_pct:.1f}%)")


class EmbeddingRateLimiter:
    """Rate limiter for embedding API calls"""
    
    def __init__(self, redis_conn: redis.Redis):
        self.redis = redis_conn
    
    def check_rate_limit(self, tokens_needed: int) -> bool:
        """Check if embedding request is within rate limits"""
        
        current_count = int(self.redis.get(EMBEDDING_RATE_LIMIT_KEY) or 0)
        
        if current_count + tokens_needed > EMBEDDING_MAX_PER_WINDOW:
            logger.warning(f"Embedding rate limit exceeded: {current_count + tokens_needed} > {EMBEDDING_MAX_PER_WINDOW}")
            return False
        
        return True
    
    def increment_usage(self, tokens_used: int):
        """Increment embedding token usage"""
        
        pipe = self.redis.pipeline()
        pipe.incr(EMBEDDING_RATE_LIMIT_KEY, tokens_used)
        pipe.expire(EMBEDDING_RATE_LIMIT_KEY, EMBEDDING_RATE_WINDOW)
        pipe.execute()
    
    def get_current_usage(self) -> Dict[str, int]:
        """Get current rate limit usage"""
        
        current = int(self.redis.get(EMBEDDING_RATE_LIMIT_KEY) or 0)
        return {
            'current_usage': current,
            'limit': EMBEDDING_MAX_PER_WINDOW,
            'remaining': max(0, EMBEDDING_MAX_PER_WINDOW - current),
            'window_seconds': EMBEDDING_RATE_WINDOW
        }


def process_rag_document(job_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main worker function to process RAG documents
    Handles the full pipeline: upload → extract → ocr → chunk → embed → store
    """
    
    # Initialize components
    redis_conn = WorkerRedisConnection().redis
    job_id = job_payload['ingest_id']
    progress_tracker = WorkerProgressTracker(job_id, redis_conn)
    rate_limiter = EmbeddingRateLimiter(redis_conn)
    metrics = JobMetrics()
    
    start_time = time.time()
    logger.info(f"Starting RAG processing for job {job_id}")
    
    try:
        # Initialize database session
        with next(get_db()) as db:
            # Create or update worker job record
            worker_job = _create_or_update_worker_job(db, job_payload, WorkerJobStatus.STARTED)
            
            # Validate job payload
            _validate_job_payload(job_payload)
            progress_tracker.update_progress(WorkerJobStatus.UPLOADING, 10.0)
            
            # Initialize RAG processor
            rag_processor = RAGProcessor()
            
            # Stage 1: File Upload and Validation
            file_info = await _process_file_upload(
                rag_processor, job_payload, progress_tracker, metrics
            )
            
            # Stage 2: Content Extraction
            extracted_content = await _process_content_extraction(
                rag_processor, job_payload, file_info, progress_tracker, metrics
            )
            
            # Stage 3: OCR (if needed)
            if job_payload.get('force_ocr', False) or _needs_ocr(extracted_content):
                extracted_content = await _process_ocr(
                    rag_processor, job_payload, file_info, progress_tracker, metrics
                )
            
            # Stage 4: Text Chunking
            chunks = await _process_chunking(
                rag_processor, job_payload, extracted_content, progress_tracker, metrics
            )
            
            # Stage 5: Embedding Generation (with rate limiting)
            embeddings = await _process_embeddings(
                rag_processor, job_payload, chunks, rate_limiter, progress_tracker, metrics
            )
            
            # Stage 6: Vector Storage
            document_id = await _process_storage(
                rag_processor, job_payload, chunks, embeddings, progress_tracker, metrics
            )
            
            # Final: Mark as completed
            progress_tracker.update_progress(WorkerJobStatus.INDEXED, 100.0)
            
            # Calculate final metrics
            metrics.processing_time_seconds = time.time() - start_time
            
            # Update database records
            _finalize_successful_job(db, worker_job, document_id, metrics)
            
            logger.info(f"Successfully processed job {job_id} in {metrics.processing_time_seconds:.2f}s")
            
            return {
                'success': True,
                'job_id': job_id,
                'document_id': document_id,
                'chunks_indexed': metrics.chunks_stored,
                'processing_time_seconds': metrics.processing_time_seconds,
                'metrics': metrics.to_dict()
            }
    
    except WorkerCancellationError as e:
        logger.info(f"Job {job_id} was canceled: {e}")
        
        with next(get_db()) as db:
            _handle_job_cancellation(db, job_id, str(e), metrics)
        
        return {
            'success': False,
            'job_id': job_id,
            'error': 'canceled',
            'message': str(e)
        }
    
    except Exception as e:
        logger.error(f"Job {job_id} failed with error: {e}", exc_info=True)
        
        # Determine error type and retry policy
        error_code = _classify_error(e)
        
        with next(get_db()) as db:
            should_retry = _handle_job_failure(
                db, job_id, error_code, str(e), job_payload, metrics
            )
        
        return {
            'success': False,
            'job_id': job_id,
            'error_code': error_code.value,
            'error_message': str(e),
            'should_retry': should_retry,
            'metrics': metrics.to_dict()
        }


async def _process_file_upload(
    rag_processor: RAGProcessor,
    job_payload: Dict[str, Any],
    progress_tracker: WorkerProgressTracker,
    metrics: JobMetrics
) -> FileInfo:
    """Process file upload stage"""
    
    upload_start = time.time()
    
    try:
        file_id = job_payload['file_id']
        file_info = await rag_processor.get_file_info(file_id)
        
        if not file_info:
            raise ValueError(f"File {file_id} not found")
        
        # Validate file size
        if file_info.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValueError(f"File too large: {file_info.size / (1024*1024):.1f}MB > {MAX_FILE_SIZE_MB}MB")
        
        # Validate file type
        if not _is_supported_file_type(file_info.content_type):
            raise ValueError(f"Unsupported file type: {file_info.content_type}")
        
        metrics.file_size_bytes = file_info.size
        metrics.upload_time_seconds = time.time() - upload_start
        
        progress_tracker.update_progress(
            WorkerJobStatus.EXTRACTING, 
            25.0, 
            f"Uploaded {file_info.name} ({file_info.size / 1024:.1f}KB)"
        )
        
        return file_info
        
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise


async def _process_content_extraction(
    rag_processor: RAGProcessor,
    job_payload: Dict[str, Any],
    file_info: FileInfo,
    progress_tracker: WorkerProgressTracker,
    metrics: JobMetrics
) -> str:
    """Process content extraction stage"""
    
    extraction_start = time.time()
    
    try:
        # Check cancellation
        progress_tracker.check_cancellation()
        
        # Extract text content
        extracted_content = await rag_processor.extract_text(file_info.file_id)
        
        if not extracted_content or len(extracted_content.strip()) < 10:
            raise ValueError("No text content could be extracted from file")
        
        metrics.extracted_text_length = len(extracted_content)
        metrics.extraction_time_seconds = time.time() - extraction_start
        metrics.extraction_method = _get_extraction_method(file_info.content_type)
        
        progress_tracker.update_progress(
            WorkerJobStatus.OCR if _needs_ocr(extracted_content) else WorkerJobStatus.CHUNKING,
            40.0,
            f"Extracted {len(extracted_content)} characters"
        )
        
        return extracted_content
        
    except Exception as e:
        logger.error(f"Content extraction failed: {e}")
        raise


async def _process_ocr(
    rag_processor: RAGProcessor,
    job_payload: Dict[str, Any],
    file_info: FileInfo,
    progress_tracker: WorkerProgressTracker,
    metrics: JobMetrics
) -> str:
    """Process OCR stage"""
    
    ocr_start = time.time()
    
    try:
        progress_tracker.check_cancellation()
        
        # Perform OCR
        ocr_result = await rag_processor.perform_ocr(file_info.file_id)
        
        if not ocr_result or len(ocr_result.text.strip()) < 10:
            raise ValueError("OCR failed to extract readable text")
        
        # Check OCR confidence
        if ocr_result.confidence < 0.7:
            logger.warning(f"Low OCR confidence: {ocr_result.confidence:.2f}")
        
        metrics.ocr_time_seconds = time.time() - ocr_start
        metrics.ocr_confidence_score = ocr_result.confidence
        metrics.extracted_text_length = len(ocr_result.text)
        
        progress_tracker.update_progress(
            WorkerJobStatus.CHUNKING,
            55.0,
            f"OCR completed (confidence: {ocr_result.confidence:.1%})"
        )
        
        return ocr_result.text
        
    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        raise


async def _process_chunking(
    rag_processor: RAGProcessor,
    job_payload: Dict[str, Any],
    content: str,
    progress_tracker: WorkerProgressTracker,
    metrics: JobMetrics
) -> List[str]:
    """Process text chunking stage"""
    
    chunking_start = time.time()
    
    try:
        progress_tracker.check_cancellation()
        
        chunk_size = job_payload.get('chunk_size', 1024)
        chunk_overlap = job_payload.get('chunk_overlap', 128)
        
        # Create text chunks
        chunks = await rag_processor.create_chunks(
            content, 
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            timeout_seconds=CHUNK_TIMEOUT_SECONDS
        )
        
        if not chunks:
            raise ValueError("Failed to create text chunks")
        
        metrics.chunks_created = len(chunks)
        metrics.chunking_time_seconds = time.time() - chunking_start
        metrics.avg_chunk_size = sum(len(chunk) for chunk in chunks) // len(chunks)
        
        progress_tracker.update_progress(
            WorkerJobStatus.EMBEDDING,
            75.0,
            f"Created {len(chunks)} chunks (avg size: {metrics.avg_chunk_size})"
        )
        
        return chunks
        
    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        raise


async def _process_embeddings(
    rag_processor: RAGProcessor,
    job_payload: Dict[str, Any],
    chunks: List[str],
    rate_limiter: EmbeddingRateLimiter,
    progress_tracker: WorkerProgressTracker,
    metrics: JobMetrics
) -> List[List[float]]:
    """Process embedding generation with rate limiting and batching"""
    
    embedding_start = time.time()
    embeddings = []
    total_tokens = 0
    
    try:
        # Estimate token count (rough approximation)
        estimated_tokens = sum(len(chunk.split()) * 1.3 for chunk in chunks)  # 1.3x word count
        
        # Check rate limits
        if not rate_limiter.check_rate_limit(int(estimated_tokens)):
            usage = rate_limiter.get_current_usage()
            raise WorkerRateLimitError(
                f"Embedding rate limit exceeded. Current: {usage['current_usage']}, "
                f"Needed: {estimated_tokens}, Limit: {usage['limit']}"
            )
        
        # Process in batches to manage memory and API limits
        batch_size = min(EMBEDDING_BATCH_SIZE, len(chunks))
        
        for i in range(0, len(chunks), batch_size):
            # Check cancellation before each batch
            progress_tracker.check_cancellation()
            
            batch_chunks = chunks[i:i + batch_size]
            
            # Generate embeddings for batch
            batch_embeddings = await rag_processor.generate_embeddings(batch_chunks)
            embeddings.extend(batch_embeddings)
            
            # Update rate limiter
            batch_tokens = sum(len(chunk.split()) * 1.3 for chunk in batch_chunks)
            rate_limiter.increment_usage(int(batch_tokens))
            total_tokens += batch_tokens
            
            # Update progress
            progress_pct = 75.0 + (i + len(batch_chunks)) / len(chunks) * 15.0
            progress_tracker.update_progress(
                WorkerJobStatus.EMBEDDING,
                progress_pct,
                f"Embedded {i + len(batch_chunks)}/{len(chunks)} chunks"
            )
            
            # Small delay between batches to be nice to API
            if i + batch_size < len(chunks):
                await asyncio.sleep(0.1)
        
        metrics.chunks_embedded = len(embeddings)
        metrics.embedding_time_seconds = time.time() - embedding_start
        metrics.embedding_tokens_used = int(total_tokens)
        metrics.estimated_cost_usd = total_tokens * 0.00001  # Rough estimate for OpenAI
        metrics.embedding_model = "text-embedding-ada-002"  # Could be configurable
        
        progress_tracker.update_progress(
            WorkerJobStatus.STORING,
            90.0,
            f"Generated {len(embeddings)} embeddings ({total_tokens:.0f} tokens)"
        )
        
        return embeddings
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise


async def _process_storage(
    rag_processor: RAGProcessor,
    job_payload: Dict[str, Any],
    chunks: List[str],
    embeddings: List[List[float]],
    progress_tracker: WorkerProgressTracker,
    metrics: JobMetrics
) -> str:
    """Process vector storage stage"""
    
    storage_start = time.time()
    
    try:
        progress_tracker.check_cancellation()
        
        # Generate document ID
        document_id = job_payload['doc_id']
        project_id = job_payload['project_id']
        
        # Store in vector database (ChromaDB)
        storage_result = await rag_processor.store_vectors(
            document_id=document_id,
            project_id=project_id,
            chunks=chunks,
            embeddings=embeddings,
            metadata={
                'embed_version': job_payload['embed_version'],
                'chunk_size': job_payload.get('chunk_size', 1024),
                'chunk_overlap': job_payload.get('chunk_overlap', 128),
                'file_sha256': job_payload['sha256'],
                'processing_date': datetime.utcnow().isoformat(),
            }
        )
        
        metrics.chunks_stored = storage_result.chunks_stored
        metrics.storage_time_seconds = time.time() - storage_start
        
        progress_tracker.update_progress(
            WorkerJobStatus.INDEXED,
            100.0,
            f"Stored {storage_result.chunks_stored} vectors"
        )
        
        return document_id
        
    except Exception as e:
        logger.error(f"Vector storage failed: {e}")
        raise


def _create_or_update_worker_job(
    db: Session,
    job_payload: Dict[str, Any],
    status: WorkerJobStatus
) -> WorkerJobDB:
    """Create or update worker job record"""
    
    job = db.query(WorkerJobDB).filter(
        WorkerJobDB.ingest_id == job_payload['ingest_id']
    ).first()
    
    if not job:
        job = WorkerJobDB(
            id=f"worker-{job_payload['ingest_id']}",
            ingest_id=job_payload['ingest_id'],
            project_id=job_payload['project_id'],
            file_id=job_payload['file_id'],
            file_sha256=job_payload['sha256'],
            embed_version=job_payload['embed_version'],
            chunk_size=job_payload.get('chunk_size', 1024),
            chunk_overlap=job_payload.get('chunk_overlap', 128),
            force_ocr=job_payload.get('force_ocr', False),
            attempt=job_payload.get('attempt', 1),
            trace_id=job_payload['trace_id'],
            status=status.value,
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow() if status != WorkerJobStatus.QUEUED else None
        )
        db.add(job)
    else:
        job.status = status.value
        job.attempt = job_payload.get('attempt', job.attempt)
        job.started_at = datetime.utcnow() if status != WorkerJobStatus.QUEUED else job.started_at
        job.updated_at = datetime.utcnow()
    
    db.commit()
    return job


def _validate_job_payload(job_payload: Dict[str, Any]):
    """Validate job payload"""
    required_fields = ['ingest_id', 'project_id', 'file_id', 'sha256', 'embed_version']
    
    for field in required_fields:
        if field not in job_payload:
            raise ValueError(f"Missing required field: {field}")
    
    if not job_payload['project_id']:
        raise ValueError("Invalid project_id")
    
    if not job_payload['file_id']:
        raise ValueError("Invalid file_id")


def _is_supported_file_type(content_type: str) -> bool:
    """Check if file type is supported"""
    supported_types = [
        'application/pdf',
        'text/plain',
        'text/markdown',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    return content_type in supported_types


def _needs_ocr(content: str) -> bool:
    """Determine if OCR is needed based on extracted content"""
    if not content or len(content.strip()) < 50:
        return True
    
    # Check for garbled text patterns that indicate OCR might help
    garbled_patterns = ['����', '???', '□□□', 'ǂǂǂ']
    return any(pattern in content for pattern in garbled_patterns)


def _get_extraction_method(content_type: str) -> str:
    """Get extraction method name for content type"""
    method_map = {
        'application/pdf': 'pdf_extraction',
        'text/plain': 'text_direct',
        'text/markdown': 'markdown_parsing',
        'application/msword': 'doc_extraction',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx_extraction'
    }
    return method_map.get(content_type, 'unknown')


def _classify_error(error: Exception) -> WorkerErrorCode:
    """Classify error into appropriate error code"""
    
    error_str = str(error).lower()
    
    # Validation errors
    if 'file not found' in error_str:
        return WorkerErrorCode.FILE_NOT_FOUND
    if 'file too large' in error_str or 'unsupported file type' in error_str:
        return WorkerErrorCode.INVALID_FILE_TYPE
    if 'invalid project' in error_str:
        return WorkerErrorCode.INVALID_PROJECT
    
    # Processing errors
    if 'extraction failed' in error_str or 'no text content' in error_str:
        return WorkerErrorCode.EXTRACTION_FAILED
    if 'ocr failed' in error_str:
        return WorkerErrorCode.OCR_ENGINE_ERROR
    if 'chunking failed' in error_str:
        return WorkerErrorCode.CHUNKING_ERROR
    
    # Embedding errors
    if 'rate limit' in error_str:
        return WorkerErrorCode.EMBEDDING_RATE_LIMITED
    if 'embedding' in error_str:
        return WorkerErrorCode.EMBEDDING_API_ERROR
    
    # Storage errors
    if 'chroma' in error_str or 'vector' in error_str:
        return WorkerErrorCode.CHROMA_CONNECTION_ERROR
    
    # Cancellation
    if isinstance(error, WorkerCancellationError):
        return WorkerErrorCode.USER_CANCELED
    
    # Rate limiting
    if isinstance(error, WorkerRateLimitError):
        return WorkerErrorCode.EMBEDDING_RATE_LIMITED
    
    return WorkerErrorCode.UNKNOWN_ERROR


def _handle_job_failure(
    db: Session,
    job_id: str,
    error_code: WorkerErrorCode,
    error_message: str,
    job_payload: Dict[str, Any],
    metrics: JobMetrics
) -> bool:
    """Handle job failure and determine if retry is needed"""
    
    # Update worker job record
    job = db.query(WorkerJobDB).filter(
        WorkerJobDB.ingest_id == job_payload['ingest_id']
    ).first()
    
    if job:
        job.status = f"failed_{error_code.value}"
        job.error_code = error_code.value
        job.error_message = error_message
        job.ended_at = datetime.utcnow()
        job.metrics = metrics.to_dict()
        
        # Determine retry policy
        retry_policy = get_retry_policy(error_code)
        should_retry = should_retry_error(error_code, job.attempt)
        
        if should_retry:
            # Calculate retry delay
            delay = calculate_retry_delay(job.attempt, retry_policy)
            job.retry_policy = retry_policy.value
            logger.info(f"Job {job_id} will be retried in {delay} seconds (attempt {job.attempt + 1})")
        else:
            logger.warning(f"Job {job_id} will not be retried (error: {error_code.value})")
        
        db.commit()
        return should_retry
    
    return False


def _handle_job_cancellation(
    db: Session,
    job_id: str,
    reason: str,
    metrics: JobMetrics
):
    """Handle job cancellation"""
    
    job = db.query(WorkerJobDB).filter(
        WorkerJobDB.id == job_id
    ).first()
    
    if job:
        job.status = WorkerJobStatus.CANCELED.value
        job.canceled_at = datetime.utcnow()
        job.cancel_reason = reason
        job.ended_at = datetime.utcnow()
        job.metrics = metrics.to_dict()
        db.commit()


def _finalize_successful_job(
    db: Session,
    worker_job: WorkerJobDB,
    document_id: str,
    metrics: JobMetrics
):
    """Finalize successful job processing"""
    
    # Update worker job
    worker_job.status = WorkerJobStatus.INDEXED.value
    worker_job.document_id = document_id
    worker_job.ended_at = datetime.utcnow()
    worker_job.metrics = metrics.to_dict()
    
    # Create/update document record
    document = RAGDocumentDB(
        id=document_id,
        project_id=worker_job.project_id,
        name=worker_job.file_name,
        file_sha256=worker_job.file_sha256,
        file_size=worker_job.file_size,
        file_type=worker_job.file_type,
        status=RAGJobStatus.INDEXED.value,
        chunks_count=metrics.chunks_stored,
        embed_version=worker_job.embed_version,
        uploaded_at=worker_job.created_at,
        indexed_at=datetime.utcnow(),
        metadata={
            'processing_metrics': metrics.to_dict(),
            'worker_job_id': worker_job.id,
            'trace_id': worker_job.trace_id
        }
    )
    
    db.merge(document)  # Use merge in case document already exists
    db.commit()


# Reindex all documents function
def reindex_all_documents(reindex_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reindex all documents for a project with new embedding version
    """
    
    project_id = reindex_payload['project_id']
    document_ids = reindex_payload['document_ids']
    old_version = reindex_payload['old_embed_version']
    new_version = reindex_payload['new_embed_version']
    batch_size = reindex_payload.get('batch_size', 10)
    
    logger.info(f"Starting reindex for project {project_id}: {len(document_ids)} documents")
    
    processed = 0
    failed = 0
    
    try:
        with next(get_db()) as db:
            # Process documents in batches
            for i in range(0, len(document_ids), batch_size):
                batch_ids = document_ids[i:i + batch_size]
                
                for doc_id in batch_ids:
                    try:
                        # Get document info
                        doc = db.query(RAGDocumentDB).filter(RAGDocumentDB.id == doc_id).first()
                        if not doc:
                            logger.warning(f"Document {doc_id} not found for reindex")
                            continue
                        
                        # Create reindex job payload
                        reindex_job_payload = {
                            'ingest_id': f"reindex-{doc_id}-{new_version}",
                            'project_id': project_id,
                            'file_id': doc.metadata.get('file_id', doc_id),  # Might need to be stored
                            'doc_id': doc_id,
                            'sha256': doc.file_sha256,
                            'embed_version': new_version,
                            'chunk_size': doc.metadata.get('chunk_size', 1024),
                            'chunk_overlap': doc.metadata.get('chunk_overlap', 128),
                            'force_ocr': False,
                            'trace_id': f"reindex-{doc_id}",
                            'created_at': datetime.utcnow().isoformat(),
                            'attempt': 1,
                        }
                        
                        # Process the document
                        result = process_rag_document(reindex_job_payload)
                        
                        if result['success']:
                            processed += 1
                            logger.info(f"Reindexed document {doc_id} ({processed}/{len(document_ids)})")
                        else:
                            failed += 1
                            logger.error(f"Failed to reindex document {doc_id}: {result.get('error_message')}")
                    
                    except Exception as e:
                        failed += 1
                        logger.error(f"Error reindexing document {doc_id}: {e}", exc_info=True)
                
                # Progress update for RQ job
                rq_job = get_current_job()
                if rq_job:
                    progress_pct = min(100.0, (i + len(batch_ids)) / len(document_ids) * 100)
                    rq_job.meta.update({
                        'progress_pct': progress_pct,
                        'processed': processed,
                        'failed': failed,
                        'current_step': f'reindexing_batch_{i // batch_size + 1}'
                    })
                    rq_job.save_meta()
        
        logger.info(f"Reindex completed for project {project_id}: {processed} success, {failed} failed")
        
        return {
            'success': True,
            'project_id': project_id,
            'processed': processed,
            'failed': failed,
            'old_embed_version': old_version,
            'new_embed_version': new_version
        }
    
    except Exception as e:
        logger.error(f"Reindex failed for project {project_id}: {e}", exc_info=True)
        return {
            'success': False,
            'project_id': project_id,
            'error': str(e),
            'processed': processed,
            'failed': failed
        }