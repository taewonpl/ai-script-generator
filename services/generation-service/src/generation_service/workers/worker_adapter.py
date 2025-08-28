"""
Production-grade durable worker adapter for RAG system
Provides abstraction between FastAPI BackgroundTasks and RQ workers
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
from uuid import uuid4
import logging

import redis
from redis.exceptions import RedisError
from rq import Queue, Worker, Connection
from rq.job import Job as RQJob, JobStatus as RQJobStatus
from rq.exceptions import NoSuchJobError
from sqlalchemy.orm import Session

from generation_service.config_loader import settings
from generation_service.models.rag_jobs import (
    RAGJobDB, RAGDocumentDB, RAGJobStatus, RAGJobErrorCode,
    RAGIngestRequest, RAGIngestResponse
)
from generation_service.database import get_db

logger = logging.getLogger(__name__)

# Configuration flags
USE_DURABLE_WORKER = os.getenv("USE_DURABLE_WORKER", "false").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/5")  # Use DB 5 for RAG
EMBED_VERSION = os.getenv("RAG_EMBED_VERSION", "v1.0")

# Worker configuration
QUEUE_NAME = "rag_processing"
DLQ_NAME = "rag_dlq"
WORKER_TIMEOUT = int(os.getenv("RAG_WORKER_TIMEOUT", "3600"))  # 1 hour
MAX_RETRIES = int(os.getenv("RAG_MAX_RETRIES", "4"))

# Rate limiting and batching
EMBEDDING_BATCH_SIZE = int(os.getenv("RAG_EMBEDDING_BATCH_SIZE", "32"))
EMBEDDING_RATE_LIMIT = int(os.getenv("RAG_EMBEDDING_RATE_LIMIT", "1000"))  # per minute
EMBEDDING_CONCURRENCY = int(os.getenv("RAG_EMBEDDING_CONCURRENCY", "3"))

# Security settings
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_SSL = os.getenv("REDIS_SSL", "false").lower() == "true"
REDIS_SSL_CERT_REQS = os.getenv("REDIS_SSL_CERT_REQS", "required")


class WorkerJobStep(str, Enum):
    """RAG processing steps for worker jobs"""
    QUEUED = "queued"
    UPLOADING = "uploading"
    EXTRACTING = "extracting"
    OCR = "ocr"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    INDEXED = "indexed"
    FAILED = "failed"
    CANCELED = "canceled"


class WorkerErrorType(str, Enum):
    """Worker-specific error types"""
    VALIDATION_ERROR = "validation_error"
    FILE_NOT_FOUND = "file_not_found"
    EXTRACTION_FAILED = "extraction_failed"
    OCR_FAILED = "ocr_failed"
    CHUNKING_FAILED = "chunking_failed"
    EMBEDDING_FAILED = "embedding_failed"
    STORAGE_FAILED = "storage_failed"
    RATE_LIMITED = "rate_limited"
    CANCELED = "canceled"
    TIMEOUT = "timeout"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class WorkerJobPayload:
    """Job payload for RQ workers"""
    ingest_id: str
    project_id: str
    file_id: str
    doc_id: str
    sha256: str
    embed_version: str
    steps: List[str]
    
    # Processing options
    chunk_size: int = 1024
    chunk_overlap: int = 128
    force_ocr: bool = False
    
    # Retry and error handling
    attempt: int = 1
    max_retries: int = MAX_RETRIES
    
    # Metadata
    created_at: str = None
    trace_id: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.trace_id is None:
            self.trace_id = str(uuid4())


@dataclass
class DLQEntry:
    """Dead Letter Queue entry for failed jobs"""
    job_id: str
    payload: Dict[str, Any]
    error_type: WorkerErrorType
    error_message: str
    last_step: str
    attempts: int
    failed_at: str
    trace_id: str
    stack_trace: Optional[str] = None


class WorkerRedisConnection:
    """Redis connection manager with security and failover"""
    
    def __init__(self):
        self._redis = None
        self._connection_params = self._build_connection_params()
    
    def _build_connection_params(self) -> Dict[str, Any]:
        """Build Redis connection parameters with security"""
        params = {
            'decode_responses': True,
            'socket_keepalive': True,
            'socket_keepalive_options': {},
            'retry_on_timeout': True,
            'health_check_interval': 30,
        }
        
        # Parse URL for basic params
        if REDIS_URL.startswith('redis://') or REDIS_URL.startswith('rediss://'):
            params['url'] = REDIS_URL
        
        # Add authentication
        if REDIS_PASSWORD:
            params['password'] = REDIS_PASSWORD
        
        # Add SSL/TLS support
        if REDIS_SSL or REDIS_URL.startswith('rediss://'):
            params['ssl'] = True
            params['ssl_cert_reqs'] = REDIS_SSL_CERT_REQS
        
        return params
    
    @property
    def redis(self) -> redis.Redis:
        """Get Redis connection with lazy initialization"""
        if self._redis is None or not self._test_connection():
            self._redis = redis.Redis(**self._connection_params)
        return self._redis
    
    def _test_connection(self) -> bool:
        """Test Redis connection health"""
        try:
            if self._redis is None:
                return False
            self._redis.ping()
            return True
        except (redis.RedisError, ConnectionError):
            return False
    
    def close(self):
        """Close Redis connection"""
        if self._redis:
            self._redis.close()
            self._redis = None


class WorkerAdapter:
    """Adapter for RAG worker system with durable job processing"""
    
    def __init__(self):
        self.redis_conn = WorkerRedisConnection()
        self._queue = None
        self._dlq = None
    
    @property
    def queue(self) -> Queue:
        """Get RQ queue with lazy initialization"""
        if self._queue is None:
            self._queue = Queue(QUEUE_NAME, connection=self.redis_conn.redis)
        return self._queue
    
    @property
    def dlq(self) -> Queue:
        """Get Dead Letter Queue"""
        if self._dlq is None:
            self._dlq = Queue(DLQ_NAME, connection=self.redis_conn.redis)
        return self._dlq
    
    def enqueue_ingest(
        self,
        ingest_request: RAGIngestRequest,
        file_info: Dict[str, Any],
        ingest_id: str,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Enqueue document ingestion job"""
        
        try:
            # Create job payload
            payload = WorkerJobPayload(
                ingest_id=ingest_id,
                project_id=ingest_request.project_id,
                file_id=ingest_request.file_id,
                doc_id=f"doc-{uuid4()}",
                sha256=file_info['sha256'],
                embed_version=EMBED_VERSION,
                steps=[step.value for step in WorkerJobStep if step not in [WorkerJobStep.FAILED, WorkerJobStep.CANCELED]],
                chunk_size=ingest_request.chunk_size or 1024,
                chunk_overlap=ingest_request.chunk_overlap or 128,
                force_ocr=ingest_request.force_ocr or False,
                max_retries=MAX_RETRIES
            )
            
            # Set job priority and timeout
            job_timeout = WORKER_TIMEOUT
            queue_priority = {"high": 1, "normal": 0, "low": -1}.get(priority, 0)
            
            # Enqueue job with idempotency
            job = self.queue.enqueue(
                'generation_service.workers.rag_worker.process_rag_document',
                asdict(payload),
                job_id=f"rag-{ingest_id}",
                job_timeout=job_timeout,
                retry=None,  # We handle retries manually
                meta={
                    'ingest_id': ingest_id,
                    'project_id': ingest_request.project_id,
                    'embed_version': EMBED_VERSION,
                    'priority': queue_priority,
                    'enqueued_at': datetime.utcnow().isoformat(),
                },
                description=f"RAG processing for {file_info.get('name', 'unknown')}"
            )
            
            logger.info(f"Enqueued RAG job {job.id} for project {ingest_request.project_id}")
            
            return {
                'job_id': job.id,
                'queue_position': len(self.queue),
                'estimated_start_time': self._estimate_start_time(),
                'payload': asdict(payload)
            }
            
        except RedisError as e:
            logger.error(f"Redis error enqueuing job: {e}")
            raise Exception(f"Failed to enqueue job: {e}")
        except Exception as e:
            logger.error(f"Unexpected error enqueuing job: {e}")
            raise Exception(f"Failed to enqueue job: {e}")
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status from RQ"""
        
        try:
            job = RQJob.fetch(job_id, connection=self.redis_conn.redis)
            
            # Map RQ status to our status
            status_mapping = {
                RQJobStatus.QUEUED: WorkerJobStep.QUEUED,
                RQJobStatus.STARTED: WorkerJobStep.UPLOADING,  # Default started status
                RQJobStatus.FINISHED: WorkerJobStep.INDEXED,
                RQJobStatus.FAILED: WorkerJobStep.FAILED,
                RQJobStatus.CANCELED: WorkerJobStep.CANCELED,
                RQJobStatus.DEFERRED: WorkerJobStep.QUEUED,
                RQJobStatus.SCHEDULED: WorkerJobStep.QUEUED,
            }
            
            status = status_mapping.get(job.status, WorkerJobStep.QUEUED)
            
            # Get progress from job meta
            progress_pct = job.meta.get('progress_pct', 0.0)
            current_step = job.meta.get('current_step', status.value)
            
            # Calculate estimated remaining time
            estimated_remaining = None
            if job.started_at and progress_pct > 0 and progress_pct < 100:
                elapsed = (datetime.utcnow() - job.started_at).total_seconds()
                if elapsed > 0:
                    total_estimated = elapsed / (progress_pct / 100)
                    estimated_remaining = int(total_estimated - elapsed)
            
            return {
                'job_id': job.id,
                'status': status.value,
                'progress_pct': progress_pct,
                'current_step': current_step,
                'created_at': job.created_at,
                'started_at': job.started_at,
                'ended_at': job.ended_at,
                'estimated_remaining_seconds': estimated_remaining,
                'result': job.result,
                'exception': str(job.exc_info) if job.exc_info else None,
                'meta': job.meta,
                'retry_count': job.meta.get('retry_count', 0),
                'queue_position': self._get_queue_position(job_id) if status == WorkerJobStep.QUEUED else 0
            }
            
        except NoSuchJobError:
            return {
                'job_id': job_id,
                'status': 'not_found',
                'error': f'Job {job_id} not found'
            }
        except Exception as e:
            logger.error(f"Error getting job status for {job_id}: {e}")
            return {
                'job_id': job_id,
                'status': 'error',
                'error': str(e)
            }
    
    def cancel_job(self, job_id: str, reason: str = "User canceled") -> bool:
        """Cancel a running or queued job"""
        
        try:
            job = RQJob.fetch(job_id, connection=self.redis_conn.redis)
            
            # Set cancellation flag in Redis
            cancel_key = f"cancel:{job_id}"
            self.redis_conn.redis.setex(cancel_key, 3600, json.dumps({  # 1 hour TTL
                'canceled_at': datetime.utcnow().isoformat(),
                'reason': reason,
                'job_id': job_id
            }))
            
            # Cancel the RQ job if queued
            if job.status == RQJobStatus.QUEUED:
                job.cancel()
                logger.info(f"Canceled queued job {job_id}")
                return True
            
            # For running jobs, worker will check cancel flag
            logger.info(f"Set cancel flag for running job {job_id}")
            return True
            
        except NoSuchJobError:
            logger.warning(f"Attempted to cancel non-existent job {job_id}")
            return False
        except Exception as e:
            logger.error(f"Error canceling job {job_id}: {e}")
            return False
    
    def retry_job(
        self,
        job_id: str,
        max_retries: int = None,
        delay_seconds: int = None
    ) -> Dict[str, Any]:
        """Retry a failed job with exponential backoff"""
        
        try:
            # Get original job
            original_job = RQJob.fetch(job_id, connection=self.redis_conn.redis)
            original_payload = original_job.args[0] if original_job.args else {}
            
            # Check retry count
            retry_count = original_job.meta.get('retry_count', 0)
            max_retries = max_retries or original_payload.get('max_retries', MAX_RETRIES)
            
            if retry_count >= max_retries:
                # Send to DLQ
                dlq_entry = DLQEntry(
                    job_id=job_id,
                    payload=original_payload,
                    error_type=WorkerErrorType.UNKNOWN_ERROR,
                    error_message=f"Max retries ({max_retries}) exceeded",
                    last_step=original_job.meta.get('current_step', 'unknown'),
                    attempts=retry_count + 1,
                    failed_at=datetime.utcnow().isoformat(),
                    trace_id=original_payload.get('trace_id', 'unknown'),
                    stack_trace=str(original_job.exc_info) if original_job.exc_info else None
                )
                
                self._send_to_dlq(dlq_entry)
                logger.warning(f"Job {job_id} sent to DLQ after {retry_count} retries")
                
                return {
                    'retry_job_id': None,
                    'sent_to_dlq': True,
                    'dlq_entry': asdict(dlq_entry)
                }
            
            # Calculate delay with exponential backoff: 1s, 5s, 25s, 125s
            if delay_seconds is None:
                delay_seconds = min(5 ** retry_count, 125)
            
            # Update payload for retry
            retry_payload = {
                **original_payload,
                'attempt': retry_count + 1,
                'retry_delay': delay_seconds
            }
            
            # Enqueue retry job
            retry_job_id = f"{job_id}-retry-{retry_count + 1}"
            retry_job = self.queue.enqueue_in(
                delay_seconds,
                'generation_service.workers.rag_worker.process_rag_document',
                retry_payload,
                job_id=retry_job_id,
                job_timeout=WORKER_TIMEOUT,
                meta={
                    **original_job.meta,
                    'retry_count': retry_count + 1,
                    'original_job_id': job_id,
                    'retry_scheduled_at': datetime.utcnow().isoformat(),
                    'retry_delay_seconds': delay_seconds
                },
                description=f"Retry {retry_count + 1} for {original_job.description or job_id}"
            )
            
            logger.info(f"Scheduled retry job {retry_job.id} in {delay_seconds} seconds")
            
            return {
                'retry_job_id': retry_job.id,
                'retry_count': retry_count + 1,
                'delay_seconds': delay_seconds,
                'scheduled_at': datetime.utcnow().isoformat(),
                'sent_to_dlq': False
            }
            
        except NoSuchJobError:
            logger.error(f"Cannot retry non-existent job {job_id}")
            raise Exception(f"Job {job_id} not found")
        except Exception as e:
            logger.error(f"Error retrying job {job_id}: {e}")
            raise Exception(f"Failed to retry job: {e}")
    
    def enqueue_reindex_all(
        self,
        project_id: str,
        new_embed_version: str = None,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """Enqueue reindexing of all documents for a project"""
        
        new_version = new_embed_version or EMBED_VERSION
        reindex_job_id = f"reindex-all-{project_id}-{uuid4()}"
        
        try:
            # Get all indexed documents for project
            with next(get_db()) as db:
                documents = db.query(RAGDocumentDB).filter(
                    RAGDocumentDB.project_id == project_id,
                    RAGDocumentDB.status == RAGJobStatus.INDEXED.value,
                    RAGDocumentDB.embed_version != new_version  # Only reindex if version differs
                ).all()
            
            if not documents:
                return {
                    'reindex_job_id': reindex_job_id,
                    'documents_to_reindex': 0,
                    'message': 'No documents need reindexing'
                }
            
            # Enqueue batch reindex job
            reindex_job = self.queue.enqueue(
                'generation_service.workers.rag_worker.reindex_all_documents',
                {
                    'project_id': project_id,
                    'document_ids': [doc.id for doc in documents],
                    'old_embed_version': documents[0].embed_version,
                    'new_embed_version': new_version,
                    'batch_size': batch_size,
                    'total_documents': len(documents)
                },
                job_id=reindex_job_id,
                job_timeout=WORKER_TIMEOUT * 3,  # Longer timeout for batch jobs
                meta={
                    'project_id': project_id,
                    'operation': 'reindex_all',
                    'embed_version_change': f"{documents[0].embed_version} -> {new_version}",
                    'total_documents': len(documents),
                    'enqueued_at': datetime.utcnow().isoformat()
                },
                description=f"Reindex all documents for project {project_id}"
            )
            
            logger.info(f"Enqueued reindex-all job {reindex_job.id} for {len(documents)} documents")
            
            return {
                'reindex_job_id': reindex_job.id,
                'documents_to_reindex': len(documents),
                'old_embed_version': documents[0].embed_version,
                'new_embed_version': new_version,
                'estimated_duration_minutes': len(documents) * 2 // batch_size  # Rough estimate
            }
            
        except Exception as e:
            logger.error(f"Error enqueuing reindex-all for project {project_id}: {e}")
            raise Exception(f"Failed to enqueue reindex job: {e}")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics"""
        
        try:
            # Queue lengths
            queue_length = len(self.queue)
            dlq_length = len(self.dlq)
            
            # Active workers
            workers = Worker.all(connection=self.redis_conn.redis)
            active_workers = [w for w in workers if w.state == 'busy']
            
            # Failed jobs (last 24 hours)
            failed_jobs = self.queue.failed_job_registry
            recent_failures = [
                job for job in failed_jobs.get_job_ids()
                if (datetime.utcnow() - RQJob.fetch(job, connection=self.redis_conn.redis).created_at).days == 0
            ]
            
            # Embedding rate limiting status
            rate_limit_key = "rag:embedding:rate_limit"
            current_rate = int(self.redis_conn.redis.get(rate_limit_key) or 0)
            
            return {
                'queue_length': queue_length,
                'dlq_length': dlq_length,
                'active_workers': len(active_workers),
                'total_workers': len(workers),
                'failed_jobs_24h': len(recent_failures),
                'embedding_rate_current': current_rate,
                'embedding_rate_limit': EMBEDDING_RATE_LIMIT,
                'embed_version': EMBED_VERSION,
                'worker_timeout': WORKER_TIMEOUT,
                'max_retries': MAX_RETRIES,
                'queue_health': 'healthy' if queue_length < 1000 and len(active_workers) > 0 else 'degraded'
            }
            
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {
                'error': str(e),
                'queue_health': 'unhealthy'
            }
    
    def _estimate_start_time(self) -> Optional[str]:
        """Estimate when a queued job will start processing"""
        try:
            queue_length = len(self.queue)
            active_workers = len([w for w in Worker.all(connection=self.redis_conn.redis) if w.state == 'busy'])
            
            if active_workers == 0:
                return None  # No workers available
            
            # Rough estimate: 5 minutes per job per worker
            estimated_minutes = (queue_length / max(active_workers, 1)) * 5
            estimated_start = datetime.utcnow() + timedelta(minutes=estimated_minutes)
            
            return estimated_start.isoformat()
        except:
            return None
    
    def _get_queue_position(self, job_id: str) -> int:
        """Get position of job in queue"""
        try:
            job_ids = self.queue.job_ids
            if job_id in job_ids:
                return job_ids.index(job_id) + 1
            return 0
        except:
            return 0
    
    def _send_to_dlq(self, dlq_entry: DLQEntry):
        """Send failed job to Dead Letter Queue"""
        try:
            self.dlq.enqueue(
                'generation_service.workers.dlq_handler.process_dlq_entry',
                asdict(dlq_entry),
                job_timeout=300,  # 5 minutes for DLQ processing
                description=f"DLQ entry for failed job {dlq_entry.job_id}"
            )
            
            # Also store in Redis for monitoring
            dlq_key = f"dlq:{dlq_entry.job_id}"
            self.redis_conn.redis.setex(dlq_key, 86400 * 7, json.dumps(asdict(dlq_entry)))  # 7 days TTL
            
            logger.info(f"Sent job {dlq_entry.job_id} to DLQ")
            
        except Exception as e:
            logger.error(f"Error sending job {dlq_entry.job_id} to DLQ: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.redis_conn:
            self.redis_conn.close()


# Global worker adapter instance
_worker_adapter = None


def get_worker_adapter() -> WorkerAdapter:
    """Get global worker adapter instance"""
    global _worker_adapter
    if _worker_adapter is None:
        _worker_adapter = WorkerAdapter()
    return _worker_adapter


def should_use_durable_worker() -> bool:
    """Check if durable worker should be used"""
    return USE_DURABLE_WORKER