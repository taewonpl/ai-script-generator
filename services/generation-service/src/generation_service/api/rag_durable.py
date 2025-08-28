"""
Durable RAG API endpoints with worker system integration
Provides production-grade document ingestion, monitoring, and management
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from generation_service.database import get_db
from generation_service.dependencies import get_current_project
from generation_service.services.rag_processor import RAGProcessor
from generation_service.models.rag_jobs import RAGIngestRequest, RAGIngestResponse
from generation_service.workers.worker_adapter import (
    get_worker_adapter, should_use_durable_worker, WorkerAdapter
)
from generation_service.workers.job_schemas import (
    WorkerJobDB, DLQEntryDB, WorkerJobStatus, WorkerErrorCode,
    JobStatusResponse, DLQListResponse, ReindexRequest, ReindexResponse,
    QueueStatsResponse
)
from generation_service.core.errors import APIError

router = APIRouter(prefix="/rag", tags=["RAG Durable"])

# Environment configuration
EMBED_VERSION = os.getenv("RAG_EMBED_VERSION", "v1.0")
MAX_CONCURRENT_JOBS = int(os.getenv("RAG_MAX_CONCURRENT_JOBS", "50"))

# Rate limiting
_project_rate_limits: Dict[str, datetime] = {}
PROJECT_RATE_LIMIT_SECONDS = 3  # Minimum 3 seconds between ingests per project


@router.post("/ingest", response_model=RAGIngestResponse, status_code=status.HTTP_200_OK)
async def ingest_document_durable(
    request: RAGIngestRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    db: Session = Depends(get_db),
    x_ingest_id: Optional[str] = Header(None, alias="X-Ingest-Id"),
    x_priority: Optional[str] = Header("normal", alias="X-Priority"),
    project = Depends(get_current_project)
):
    """
    Ingest a document using durable worker system or fallback to BackgroundTasks
    
    Headers:
    - X-Ingest-Id: Idempotency key (auto-generated if not provided)
    - X-Priority: Job priority (high|normal|low, default: normal)
    """
    
    now = datetime.utcnow()
    ingest_id = x_ingest_id or f"ingest-{uuid4()}"
    priority = x_priority or "normal"
    
    # Rate limiting per project
    if request.project_id in _project_rate_limits:
        time_diff = (now - _project_rate_limits[request.project_id]).total_seconds()
        if time_diff < PROJECT_RATE_LIMIT_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "RATE_LIMITED",
                    "message": f"Too many ingest requests. Wait {PROJECT_RATE_LIMIT_SECONDS - time_diff:.1f} seconds",
                    "retry_after": int(PROJECT_RATE_LIMIT_SECONDS - time_diff) + 1,
                },
                headers={"Retry-After": str(int(PROJECT_RATE_LIMIT_SECONDS - time_diff) + 1)}
            )
    
    try:
        # Check for existing job with same ingest_id (idempotency)
        if should_use_durable_worker():
            existing_job = db.query(WorkerJobDB).filter(
                WorkerJobDB.ingest_id == ingest_id
            ).first()
        else:
            # Fallback: use existing BackgroundTasks logic
            return await _fallback_to_background_tasks(
                request, background_tasks, db, ingest_id, project
            )
        
        if existing_job:
            return RAGIngestResponse(
                job_id=existing_job.id,
                status=existing_job.status,
                progress_pct=existing_job.progress_pct,
                is_duplicate=False,
                request_id=ingest_id,
                trace_id=existing_job.trace_id,
            )
        
        # Get file info for validation and deduplication
        rag_processor = RAGProcessor()
        file_info = await rag_processor.get_file_info(request.file_id)
        
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "FILE_NOT_FOUND",
                    "message": f"File {request.file_id} not found",
                    "file_id": request.file_id,
                }
            )
        
        # Check for duplicate documents by file hash
        existing_doc = db.query(WorkerJobDB).filter(
            WorkerJobDB.project_id == request.project_id,
            WorkerJobDB.file_sha256 == file_info.sha256,
            WorkerJobDB.status == WorkerJobStatus.INDEXED.value,
            WorkerJobDB.embed_version == EMBED_VERSION  # Only consider current version
        ).first()
        
        if existing_doc:
            return RAGIngestResponse(
                job_id=f"dup-{existing_doc.id}",
                status=WorkerJobStatus.INDEXED.value,
                progress_pct=100.0,
                is_duplicate=True,
                existing_document_id=existing_doc.document_id,
                request_id=ingest_id,
                trace_id=existing_doc.trace_id,
            )
        
        # Enqueue with durable worker
        worker_adapter = get_worker_adapter()
        enqueue_result = worker_adapter.enqueue_ingest(
            request, 
            file_info.__dict__, 
            ingest_id, 
            priority
        )
        
        # Update rate limiting
        _project_rate_limits[request.project_id] = now
        
        return RAGIngestResponse(
            job_id=enqueue_result['job_id'],
            status=WorkerJobStatus.QUEUED.value,
            progress_pct=0.0,
            is_duplicate=False,
            request_id=ingest_id,
            trace_id=enqueue_result['payload']['trace_id'],
            estimated_start_time=enqueue_result.get('estimated_start_time'),
            queue_position=enqueue_result.get('queue_position'),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INGEST_FAILED",
                "message": "Failed to start document ingestion",
                "error": str(e),
            }
        )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status_durable(
    job_id: str,
    db: Session = Depends(get_db),
    project = Depends(get_current_project)
):
    """Get detailed job status from worker system"""
    
    if should_use_durable_worker():
        worker_adapter = get_worker_adapter()
        job_status = worker_adapter.get_job_status(job_id)
        
        if job_status.get('status') == 'not_found':
            # Check database for completed/failed jobs
            db_job = db.query(WorkerJobDB).filter(WorkerJobDB.id == job_id).first()
            if not db_job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found"}
                )
            
            # Verify project access
            if db_job.project_id != project.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "ACCESS_DENIED", "message": "Access to this job is denied"}
                )
            
            return JobStatusResponse(
                job_id=db_job.id,
                ingest_id=db_job.ingest_id,
                status=WorkerJobStatus(db_job.status),
                progress_pct=db_job.progress_pct,
                current_step=db_job.current_step,
                created_at=db_job.created_at,
                started_at=db_job.started_at,
                ended_at=db_job.ended_at,
                document_id=db_job.document_id,
                chunks_indexed=db_job.metrics.get('content', {}).get('chunks_stored') if db_job.metrics else None,
                error_code=db_job.error_code,
                error_message=db_job.error_message,
                retry_count=db_job.attempt - 1,
            )
        
        return JobStatusResponse(
            job_id=job_status['job_id'],
            ingest_id=job_status.get('meta', {}).get('ingest_id', job_id),
            status=WorkerJobStatus(job_status['status']),
            progress_pct=job_status.get('progress_pct', 0.0),
            current_step=job_status.get('current_step', 'unknown'),
            created_at=job_status.get('created_at'),
            started_at=job_status.get('started_at'),
            ended_at=job_status.get('ended_at'),
            estimated_remaining_seconds=job_status.get('estimated_remaining_seconds'),
            retry_count=job_status.get('retry_count', 0),
            queue_position=job_status.get('queue_position'),
            error_message=job_status.get('exception'),
        )
    
    else:
        # Fallback to original implementation
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Worker system not available, check USE_DURABLE_WORKER setting"}
        )


@router.post("/jobs/{job_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_job(
    job_id: str,
    reason: Optional[str] = Query("User requested cancellation"),
    db: Session = Depends(get_db),
    project = Depends(get_current_project)
):
    """Cancel a running or queued job"""
    
    if not should_use_durable_worker():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Job cancellation requires durable worker system"}
        )
    
    # Verify job exists and user has access
    job = db.query(WorkerJobDB).filter(WorkerJobDB.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found"}
        )
    
    if job.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCESS_DENIED", "message": "Access to this job is denied"}
        )
    
    # Check if job can be canceled
    cancelable_states = [
        WorkerJobStatus.QUEUED.value,
        WorkerJobStatus.STARTED.value,
        WorkerJobStatus.UPLOADING.value,
        WorkerJobStatus.EXTRACTING.value,
        WorkerJobStatus.OCR.value,
        WorkerJobStatus.CHUNKING.value,
        WorkerJobStatus.EMBEDDING.value,
        WorkerJobStatus.STORING.value,
    ]
    
    if job.status not in cancelable_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NOT_CANCELABLE",
                "message": f"Job in status {job.status} cannot be canceled",
                "current_status": job.status,
            }
        )
    
    # Cancel the job
    worker_adapter = get_worker_adapter()
    canceled = worker_adapter.cancel_job(job_id, reason)
    
    if canceled:
        # Update database record
        job.canceled_at = datetime.utcnow()
        job.cancel_reason = reason
        job.status = WorkerJobStatus.CANCELED.value
        db.commit()
        
        return {"job_id": job_id, "status": "canceled", "reason": reason}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to cancel job"}
        )


@router.post("/jobs/{job_id}/retry", status_code=status.HTTP_200_OK)
async def retry_job(
    job_id: str,
    max_retries: Optional[int] = Query(None, ge=1, le=10),
    delay_seconds: Optional[int] = Query(None, ge=0, le=300),
    db: Session = Depends(get_db),
    project = Depends(get_current_project)
):
    """Retry a failed job"""
    
    if not should_use_durable_worker():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Job retry requires durable worker system"}
        )
    
    # Verify job exists and user has access
    job = db.query(WorkerJobDB).filter(WorkerJobDB.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found"}
        )
    
    if job.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCESS_DENIED", "message": "Access to this job is denied"}
        )
    
    # Check if job can be retried
    retryable_states = [
        WorkerJobStatus.FAILED_VALIDATION.value,
        WorkerJobStatus.FAILED_UPLOAD.value,
        WorkerJobStatus.FAILED_EXTRACT.value,
        WorkerJobStatus.FAILED_OCR.value,
        WorkerJobStatus.FAILED_CHUNK.value,
        WorkerJobStatus.FAILED_EMBED.value,
        WorkerJobStatus.FAILED_STORE.value,
        WorkerJobStatus.CANCELED.value,
    ]
    
    if job.status not in retryable_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NOT_RETRYABLE",
                "message": f"Job in status {job.status} cannot be retried",
                "current_status": job.status,
            }
        )
    
    # Retry the job
    worker_adapter = get_worker_adapter()
    try:
        retry_result = worker_adapter.retry_job(job_id, max_retries, delay_seconds)
        return retry_result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Failed to retry job: {str(e)}"}
        )


@router.post("/reindex-all", response_model=ReindexResponse)
async def reindex_all_documents(
    request: ReindexRequest,
    db: Session = Depends(get_db),
    project = Depends(get_current_project)
):
    """Reindex all documents in a project with new embedding version"""
    
    if not should_use_durable_worker():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Reindexing requires durable worker system"}
        )
    
    # Verify project access
    if request.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCESS_DENIED", "message": "Access to this project is denied"}
        )
    
    try:
        worker_adapter = get_worker_adapter()
        new_embed_version = request.new_embed_version or f"v{datetime.now().strftime('%Y%m%d')}"
        
        reindex_result = worker_adapter.enqueue_reindex_all(
            request.project_id,
            new_embed_version,
            request.batch_size
        )
        
        return ReindexResponse(
            reindex_job_id=reindex_result['reindex_job_id'],
            documents_to_reindex=reindex_result['documents_to_reindex'],
            old_embed_version=reindex_result.get('old_embed_version'),
            new_embed_version=reindex_result['new_embed_version'],
            estimated_duration_minutes=reindex_result.get('estimated_duration_minutes', 0),
            batch_size=request.batch_size,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Failed to start reindexing: {str(e)}"}
        )


@router.get("/projects/{project_id}/documents", response_model=Dict[str, Any])
async def list_project_documents(
    project_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None),
    embed_version_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    project = Depends(get_current_project)
):
    """List documents for a project with advanced filtering"""
    
    if project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCESS_DENIED", "message": "Access to this project is denied"}
        )
    
    # Build query
    query = db.query(WorkerJobDB).filter(WorkerJobDB.project_id == project_id)
    
    if status_filter:
        query = query.filter(WorkerJobDB.status == status_filter)
    
    if embed_version_filter:
        query = query.filter(WorkerJobDB.embed_version == embed_version_filter)
    
    # Get counts by status
    status_counts = {}
    status_query = db.query(
        WorkerJobDB.status, 
        func.count(WorkerJobDB.id).label('count')
    ).filter(
        WorkerJobDB.project_id == project_id
    ).group_by(WorkerJobDB.status)
    
    for status, count in status_query:
        status_counts[status] = count
    
    # Get embed version counts
    version_counts = {}
    version_query = db.query(
        WorkerJobDB.embed_version,
        func.count(WorkerJobDB.id).label('count')
    ).filter(
        WorkerJobDB.project_id == project_id,
        WorkerJobDB.status == WorkerJobStatus.INDEXED.value
    ).group_by(WorkerJobDB.embed_version)
    
    for version, count in version_query:
        version_counts[version] = count
    
    # Get total count
    total = query.count()
    
    # Get documents with pagination
    documents = query.order_by(desc(WorkerJobDB.created_at)).offset(offset).limit(limit).all()
    
    # Convert to dict format
    document_list = []
    for doc in documents:
        document_list.append({
            'id': doc.id,
            'document_id': doc.document_id,
            'ingest_id': doc.ingest_id,
            'file_name': doc.file_name,
            'file_size': doc.file_size,
            'file_type': doc.file_type,
            'status': doc.status,
            'embed_version': doc.embed_version,
            'chunks_count': doc.metrics.get('content', {}).get('chunks_stored') if doc.metrics else 0,
            'created_at': doc.created_at.isoformat() if doc.created_at else None,
            'indexed_at': doc.ended_at.isoformat() if doc.ended_at and doc.status == WorkerJobStatus.INDEXED.value else None,
            'processing_time_seconds': doc.metrics.get('timing', {}).get('processing_time_seconds') if doc.metrics else None,
            'error_code': doc.error_code,
            'error_message': doc.error_message,
        })
    
    return {
        'documents': document_list,
        'total': total,
        'status_counts': status_counts,
        'version_counts': version_counts,
        'current_embed_version': EMBED_VERSION,
        'outdated_documents': version_counts.get(EMBED_VERSION, 0) < sum(version_counts.values()),
    }


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_statistics(
    db: Session = Depends(get_db)
):
    """Get comprehensive queue and worker statistics"""
    
    if not should_use_durable_worker():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Queue statistics require durable worker system"}
        )
    
    try:
        worker_adapter = get_worker_adapter()
        queue_stats = worker_adapter.get_queue_stats()
        
        # Get additional stats from database
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        
        # Job counts
        total_jobs_24h = db.query(func.count(WorkerJobDB.id)).filter(
            WorkerJobDB.created_at >= day_ago
        ).scalar()
        
        completed_jobs_24h = db.query(func.count(WorkerJobDB.id)).filter(
            WorkerJobDB.created_at >= day_ago,
            WorkerJobDB.status == WorkerJobStatus.INDEXED.value
        ).scalar()
        
        failed_jobs_24h = db.query(func.count(WorkerJobDB.id)).filter(
            WorkerJobDB.created_at >= day_ago,
            WorkerJobDB.status.like('failed_%')
        ).scalar()
        
        # Processing time stats
        avg_processing_time = db.query(
            func.avg(func.json_extract(WorkerJobDB.metrics, '$.timing.processing_time_seconds'))
        ).filter(
            WorkerJobDB.created_at >= day_ago,
            WorkerJobDB.status == WorkerJobStatus.INDEXED.value,
            WorkerJobDB.metrics.isnot(None)
        ).scalar()
        
        # Embedding quota estimation
        total_tokens_24h = db.query(
            func.sum(func.json_extract(WorkerJobDB.metrics, '$.cost.embedding_tokens_used'))
        ).filter(
            WorkerJobDB.created_at >= day_ago,
            WorkerJobDB.status == WorkerJobStatus.INDEXED.value,
            WorkerJobDB.metrics.isnot(None)
        ).scalar()
        
        # Outdated documents count
        outdated_count = db.query(func.count(WorkerJobDB.id)).filter(
            WorkerJobDB.status == WorkerJobStatus.INDEXED.value,
            WorkerJobDB.embed_version != EMBED_VERSION
        ).scalar()
        
        # Calculate rates and health
        success_rate = (completed_jobs_24h / max(total_jobs_24h, 1)) * 100
        worker_utilization = (queue_stats['active_workers'] / max(queue_stats['total_workers'], 1)) * 100
        
        # Determine health status
        queue_health = 'healthy'
        if queue_stats['queue_length'] > 100 or queue_stats['active_workers'] == 0:
            queue_health = 'degraded'
        if queue_stats['queue_length'] > 500 or success_rate < 80:
            queue_health = 'unhealthy'
        
        worker_health = 'healthy'
        if worker_utilization > 90:
            worker_health = 'degraded'
        if queue_stats['total_workers'] == 0:
            worker_health = 'unhealthy'
        
        storage_health = 'healthy'  # Could add ChromaDB health checks
        
        return QueueStatsResponse(
            # Queue metrics
            queue_length=queue_stats['queue_length'],
            dlq_length=queue_stats['dlq_length'],
            processing_jobs=queue_stats['active_workers'],  # Approximation
            
            # Worker metrics
            active_workers=queue_stats['active_workers'],
            total_workers=queue_stats['total_workers'],
            worker_utilization=worker_utilization,
            
            # Performance metrics
            avg_processing_time_minutes=(avg_processing_time or 0) / 60,
            jobs_completed_24h=completed_jobs_24h,
            jobs_failed_24h=failed_jobs_24h,
            success_rate_24h=success_rate,
            
            # Rate limiting
            embedding_rate_current=queue_stats['embedding_rate_current'],
            embedding_rate_limit=queue_stats['embedding_rate_limit'],
            embedding_quota_remaining=max(0, 100000 - (total_tokens_24h or 0)),  # Example quota
            
            # Version information
            embed_version=EMBED_VERSION,
            outdated_documents=outdated_count,
            
            # Health status
            queue_health=queue_health,
            worker_health=worker_health,
            storage_health=storage_health,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Failed to get queue stats: {str(e)}"}
        )


@router.get("/dlq", response_model=DLQListResponse)
async def list_dlq_entries(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    error_type_filter: Optional[str] = Query(None),
    resolved_filter: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """List Dead Letter Queue entries for debugging failed jobs"""
    
    # Build query
    query = db.query(DLQEntryDB)
    
    if error_type_filter:
        query = query.filter(DLQEntryDB.error_type == error_type_filter)
    
    if resolved_filter is not None:
        if resolved_filter:
            query = query.filter(DLQEntryDB.resolved_at.isnot(None))
        else:
            query = query.filter(DLQEntryDB.resolved_at.is_(None))
    
    # Get counts
    total = query.count()
    resolved_count = db.query(func.count(DLQEntryDB.id)).filter(
        DLQEntryDB.resolved_at.isnot(None)
    ).scalar()
    
    # Get error type counts
    error_type_counts = {}
    error_query = db.query(
        DLQEntryDB.error_type,
        func.count(DLQEntryDB.id).label('count')
    ).group_by(DLQEntryDB.error_type)
    
    for error_type, count in error_query:
        error_type_counts[error_type] = count
    
    # Get entries with pagination
    entries = query.order_by(desc(DLQEntryDB.failed_at)).offset(offset).limit(limit).all()
    
    # Convert to dict format
    entry_list = []
    for entry in entries:
        entry_list.append({
            'id': entry.id,
            'original_job_id': entry.original_job_id,
            'ingest_id': entry.ingest_id,
            'project_id': entry.project_id,
            'error_type': entry.error_type,
            'error_code': entry.error_code,
            'error_message': entry.error_message,
            'last_step': entry.last_step,
            'attempts': entry.attempts,
            'failed_at': entry.failed_at.isoformat(),
            'first_attempt_at': entry.first_attempt_at.isoformat() if entry.first_attempt_at else None,
            'resolved_at': entry.resolved_at.isoformat() if entry.resolved_at else None,
            'resolution_notes': entry.resolution_notes,
            'trace_id': entry.trace_id,
        })
    
    return DLQListResponse(
        entries=entry_list,
        total=total,
        resolved_count=resolved_count,
        error_type_counts=error_type_counts,
    )


async def _fallback_to_background_tasks(
    request: RAGIngestRequest,
    background_tasks: BackgroundTasks,
    db: Session,
    ingest_id: str,
    project
) -> RAGIngestResponse:
    """Fallback to original BackgroundTasks implementation"""
    
    # Import original implementation
    from generation_service.api.rag_pipeline import process_rag_job, RAGJobDB, RAGJobStatus
    
    now = datetime.utcnow()
    rag_processor = RAGProcessor()
    
    # Get file info
    file_info = await rag_processor.get_file_info(request.file_id)
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "FILE_NOT_FOUND", "message": f"File {request.file_id} not found"}
        )
    
    # Create job using original schema
    job_id = f"rag-{uuid4()}"
    trace_id = str(uuid4())
    
    job = RAGJobDB(
        id=job_id,
        project_id=request.project_id,
        status=RAGJobStatus.QUEUED.value,
        progress_pct=0.0,
        current_step="queued",
        metadata={
            "file_name": file_info.name,
            "file_size": file_info.size,
            "file_type": file_info.content_type,
            "file_sha256": file_info.sha256,
            "request_id": ingest_id,
            "trace_id": trace_id,
            "started_at": now.isoformat(),
        },
        chunk_size=request.chunk_size or 1024,
        chunk_overlap=request.chunk_overlap or 128,
        created_at=now,
        updated_at=now,
    )
    
    db.add(job)
    db.commit()
    
    # Start background processing
    background_tasks.add_task(
        process_rag_job,
        job_id,
        request.file_id,
        request.force_ocr or False,
        db
    )
    
    return RAGIngestResponse(
        job_id=job_id,
        status=RAGJobStatus.QUEUED.value,
        progress_pct=0.0,
        is_duplicate=False,
        request_id=ingest_id,
        trace_id=trace_id,
    )