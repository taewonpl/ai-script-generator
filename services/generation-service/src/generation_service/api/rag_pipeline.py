"""
RAG Pipeline API Endpoints
Handles document ingestion, job tracking, and document management for ChromaDB integration
"""

import asyncio
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from generation_service.models.rag_jobs import (
    RAGJobDB, RAGDocumentDB, RAGJobStatus, RAGJobErrorCode,
    RAGIngestRequest, RAGIngestResponse, RAGJobStatusResponse, RAGDocumentsResponse,
    RAG_VALID_TRANSITIONS, RAG_PROGRESS_MAP
)
from generation_service.database import get_db
from generation_service.dependencies import get_current_project
from generation_service.services.rag_processor import RAGProcessor, FileHash
from generation_service.services.metrics import record_rag_metrics
from generation_service.core.errors import APIError

router = APIRouter(prefix="/rag", tags=["RAG Pipeline"])

# In-memory storage for active jobs (production: use Redis)
_active_jobs: Dict[str, RAGJobDB] = {}
_job_locks: Dict[str, asyncio.Lock] = {}

# Rate limiting storage (production: use Redis with TTL)
_ingest_rate_limits: Dict[str, datetime] = {}
INGEST_RATE_LIMIT_SECONDS = 5  # Minimum 5 seconds between ingests per project


@router.post("/ingest", response_model=RAGIngestResponse, status_code=status.HTTP_200_OK)
async def ingest_document(
    request: RAGIngestRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    db: Session = Depends(get_db),
    x_ingest_id: Optional[str] = Header(None, alias="X-Ingest-Id"),
    project = Depends(get_current_project)
):
    """
    Ingest a document into RAG pipeline with idempotency and deduplication
    
    Headers:
    - X-Ingest-Id: Idempotency key (auto-generated if not provided)
    """
    now = datetime.utcnow()
    
    # Generate idempotency key if not provided
    ingest_id = x_ingest_id or f"ingest-{uuid4()}"
    
    # Rate limiting per project
    project_key = request.project_id
    if project_key in _ingest_rate_limits:
        time_diff = (now - _ingest_rate_limits[project_key]).total_seconds()
        if time_diff < INGEST_RATE_LIMIT_SECONDS:
            record_rag_metrics("ingest_rate_limited", {
                "project_id": request.project_id,
                "file_id": request.file_id,
                "ingest_id": ingest_id,
            })
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "RATE_LIMITED",
                    "message": f"Too many ingest requests. Wait {INGEST_RATE_LIMIT_SECONDS - time_diff:.1f} seconds",
                    "retry_after": int(INGEST_RATE_LIMIT_SECONDS - time_diff) + 1,
                },
                headers={"Retry-After": str(int(INGEST_RATE_LIMIT_SECONDS - time_diff) + 1)}
            )
    
    # Check for existing job with same ingest_id (idempotency)
    existing_job = db.query(RAGJobDB).filter(
        RAGJobDB.metadata.op('->>')('request_id') == ingest_id
    ).first()
    
    if existing_job:
        record_rag_metrics("ingest_idempotency_hit", {
            "project_id": request.project_id,
            "job_id": existing_job.id,
            "ingest_id": ingest_id,
        })
        return RAGIngestResponse(
            job_id=existing_job.id,
            status=existing_job.status,
            progress_pct=existing_job.progress_pct,
            is_duplicate=False,
            request_id=ingest_id,
            trace_id=str(uuid4()),
        )
    
    try:
        # Initialize RAG processor
        rag_processor = RAGProcessor()
        
        # Get file info and compute hash for deduplication
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
        existing_doc = db.query(RAGDocumentDB).filter(
            RAGDocumentDB.project_id == request.project_id,
            RAGDocumentDB.file_sha256 == file_info.sha256
        ).first()
        
        if existing_doc and existing_doc.status == RAGJobStatus.INDEXED:
            record_rag_metrics("ingest_duplicate_detected", {
                "project_id": request.project_id,
                "file_id": request.file_id,
                "existing_doc_id": existing_doc.id,
                "file_sha256": file_info.sha256,
            })
            return RAGIngestResponse(
                job_id=f"dup-{existing_doc.id}",
                status=RAGJobStatus.INDEXED,
                progress_pct=100.0,
                is_duplicate=True,
                existing_document_id=existing_doc.id,
                request_id=ingest_id,
                trace_id=str(uuid4()),
            )
        
        # Create new RAG job
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
        
        # Store in memory for processing
        _active_jobs[job_id] = job
        _job_locks[job_id] = asyncio.Lock()
        
        # Save to database
        db.add(job)
        db.commit()
        
        # Update rate limiting
        _ingest_rate_limits[project_key] = now
        
        # Start background processing
        background_tasks.add_task(
            process_rag_job,
            job_id,
            request.file_id,
            request.force_ocr or False,
            db
        )
        
        record_rag_metrics("ingest_started", {
            "project_id": request.project_id,
            "job_id": job_id,
            "file_id": request.file_id,
            "file_size": file_info.size,
            "file_type": file_info.content_type,
            "ingest_id": ingest_id,
        })
        
        return RAGIngestResponse(
            job_id=job_id,
            status=RAGJobStatus.QUEUED,
            progress_pct=0.0,
            is_duplicate=False,
            request_id=ingest_id,
            trace_id=trace_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        record_rag_metrics("ingest_failed", {
            "project_id": request.project_id,
            "file_id": request.file_id,
            "error": str(e),
            "ingest_id": ingest_id,
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INGEST_FAILED",
                "message": "Failed to start document ingestion",
                "error": str(e),
            }
        )


@router.get("/jobs/{job_id}", response_model=RAGJobStatusResponse)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    project = Depends(get_current_project)
):
    """Get status of a RAG processing job"""
    
    # Check in-memory active jobs first
    if job_id in _active_jobs:
        job = _active_jobs[job_id]
    else:
        # Check database
        job = db.query(RAGJobDB).filter(RAGJobDB.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "JOB_NOT_FOUND",
                    "message": f"Job {job_id} not found",
                }
            )
    
    # Verify project access
    if job.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACCESS_DENIED",
                "message": "Access to this job is denied",
            }
        )
    
    # Calculate estimated remaining time
    estimated_remaining = None
    if job.metadata.get("started_at") and job.progress_pct > 0 and job.progress_pct < 100:
        started_at = datetime.fromisoformat(job.metadata["started_at"])
        elapsed_seconds = (datetime.utcnow() - started_at).total_seconds()
        if elapsed_seconds > 0:
            estimated_total = elapsed_seconds / (job.progress_pct / 100)
            estimated_remaining = int(estimated_total - elapsed_seconds)
    
    return RAGJobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress_pct=job.progress_pct,
        current_step=job.current_step,
        document_id=job.document_id,
        chunks_indexed=job.metadata.get("chunks_indexed"),
        error_code=job.metadata.get("error_code"),
        error_message=job.metadata.get("error_message"),
        retry_count=job.metadata.get("retry_count", 0),
        started_at=datetime.fromisoformat(job.metadata["started_at"]) if job.metadata.get("started_at") else None,
        ended_at=datetime.fromisoformat(job.metadata["ended_at"]) if job.metadata.get("ended_at") else None,
        estimated_remaining_seconds=estimated_remaining,
    )


@router.get("/documents", response_model=RAGDocumentsResponse)
async def list_documents(
    project_id: str,
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    project = Depends(get_current_project)
):
    """List RAG documents for a project"""
    
    if project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACCESS_DENIED",
                "message": "Access to this project is denied",
            }
        )
    
    # Build query
    query = db.query(RAGDocumentDB).filter(RAGDocumentDB.project_id == project_id)
    
    if status_filter:
        query = query.filter(RAGDocumentDB.status == status_filter)
    
    # Get counts
    total = query.count()
    indexed_count = db.query(RAGDocumentDB).filter(
        RAGDocumentDB.project_id == project_id,
        RAGDocumentDB.status == RAGJobStatus.INDEXED.value
    ).count()
    
    processing_count = db.query(RAGDocumentDB).filter(
        RAGDocumentDB.project_id == project_id,
        RAGDocumentDB.status.in_([
            RAGJobStatus.QUEUED.value,
            RAGJobStatus.UPLOADING.value,
            RAGJobStatus.EXTRACTING.value,
            RAGJobStatus.OCR.value,
            RAGJobStatus.CHUNKING.value,
            RAGJobStatus.EMBEDDING.value,
        ])
    ).count()
    
    failed_count = db.query(RAGDocumentDB).filter(
        RAGDocumentDB.project_id == project_id,
        RAGDocumentDB.status.in_([
            RAGJobStatus.FAILED_EXTRACT.value,
            RAGJobStatus.FAILED_OCR.value,
            RAGJobStatus.FAILED_EMBED.value,
            RAGJobStatus.FAILED_STORE.value,
        ])
    ).count()
    
    # Get documents with pagination
    documents = query.offset(offset).limit(limit).all()
    
    return RAGDocumentsResponse(
        documents=documents,
        total=total,
        indexed_count=indexed_count,
        processing_count=processing_count,
        failed_count=failed_count,
    )


@router.post("/retry/{document_id}", status_code=status.HTTP_200_OK)
async def retry_document_processing(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    project = Depends(get_current_project)
):
    """Retry processing a failed document"""
    
    document = db.query(RAGDocument).filter(RAGDocument.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DOCUMENT_NOT_FOUND",
                "message": f"Document {document_id} not found",
            }
        )
    
    if document.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACCESS_DENIED",
                "message": "Access to this document is denied",
            }
        )
    
    # Check if document is in a retryable state
    retryable_states = [
        RAGJobStatus.FAILED_EXTRACT,
        RAGJobStatus.FAILED_OCR,
        RAGJobStatus.FAILED_EMBED,
        RAGJobStatus.FAILED_STORE,
        RAGJobStatus.CANCELED,
    ]
    
    if document.status not in retryable_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NOT_RETRYABLE",
                "message": f"Document in status {document.status} cannot be retried",
                "current_status": document.status,
            }
        )
    
    # Create new job for retry
    job_id = f"rag-retry-{uuid4()}"
    retry_job = RAGJob(
        id=job_id,
        project_id=document.project_id,
        document_id=document.id,
        status=RAGJobStatus.QUEUED,
        progress_pct=0.0,
        current_step="queued",
        metadata={
            **document.metadata,
            "retry_count": document.metadata.get("retry_count", 0) + 1,
            "original_document_id": document.id,
            "trace_id": str(uuid4()),
            "started_at": datetime.utcnow().isoformat(),
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    _active_jobs[job_id] = retry_job
    _job_locks[job_id] = asyncio.Lock()
    
    db.add(retry_job)
    db.commit()
    
    # Start background retry processing
    background_tasks.add_task(
        process_rag_job,
        job_id,
        document.metadata.get("file_id"),
        False,  # Don't force OCR on retry
        db
    )
    
    record_rag_metrics("document_retry_started", {
        "document_id": document_id,
        "job_id": job_id,
        "project_id": document.project_id,
        "retry_count": retry_job.metadata["retry_count"],
    })
    
    return {"job_id": job_id, "status": "retry_started"}


@router.delete("/documents/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    project = Depends(get_current_project)
):
    """Delete a RAG document and its chunks from ChromaDB"""
    
    document = db.query(RAGDocument).filter(RAGDocument.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DOCUMENT_NOT_FOUND", 
                "message": f"Document {document_id} not found",
            }
        )
    
    if document.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACCESS_DENIED",
                "message": "Access to this document is denied",
            }
        )
    
    try:
        # Delete from ChromaDB
        rag_processor = RAGProcessor()
        await rag_processor.delete_document_chunks(document_id)
        
        # Delete from database
        db.delete(document)
        db.commit()
        
        record_rag_metrics("document_deleted", {
            "document_id": document_id,
            "project_id": document.project_id,
            "chunks_count": document.chunks_count,
        })
        
        return {"status": "deleted", "document_id": document_id}
        
    except Exception as e:
        record_rag_metrics("document_delete_failed", {
            "document_id": document_id,
            "project_id": document.project_id,
            "error": str(e),
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "DELETE_FAILED",
                "message": "Failed to delete document",
                "error": str(e),
            }
        )


async def process_rag_job(job_id: str, file_id: str, force_ocr: bool, db: Session):
    """Background task to process RAG job through the pipeline"""
    
    if job_id not in _active_jobs or job_id not in _job_locks:
        return
    
    async with _job_locks[job_id]:
        job = _active_jobs[job_id]
        rag_processor = RAGProcessor()
        
        try:
            # Update job status through pipeline stages
            await update_job_status(job, RAGJobStatus.UPLOADING, "Uploading file", db)
            
            # Process through pipeline
            result = await rag_processor.process_document(
                file_id=file_id,
                job_id=job_id,
                project_id=job.project_id,
                chunk_size=job.chunk_size,
                chunk_overlap=job.chunk_overlap,
                force_ocr=force_ocr,
                progress_callback=lambda status, pct, step: asyncio.create_task(
                    update_job_status(job, status, step, db, pct)
                )
            )
            
            if result.success:
                # Create document record
                document = RAGDocument(
                    id=result.document_id,
                    project_id=job.project_id,
                    name=job.metadata["file_name"],
                    file_sha256=job.metadata["file_sha256"],
                    file_size=job.metadata["file_size"],
                    file_type=job.metadata["file_type"],
                    status=RAGJobStatus.INDEXED,
                    chunks_count=result.chunks_indexed,
                    embed_version=job.embed_version,
                    uploaded_at=datetime.fromisoformat(job.metadata["started_at"]),
                    indexed_at=datetime.utcnow(),
                    metadata={
                        **job.metadata,
                        "processing_time_seconds": result.processing_time_seconds,
                        "extraction_method": result.extraction_method,
                        "ocr_confidence": result.ocr_confidence,
                    }
                )
                
                db.add(document)
                job.document_id = result.document_id
                await update_job_status(job, RAGJobStatus.INDEXED, "Completed", db, 100.0)
                
            else:
                # Handle failure
                await update_job_status(
                    job, 
                    result.error_status or RAGJobStatus.FAILED_EXTRACT,
                    result.error_message or "Processing failed",
                    db,
                    job.progress_pct,  # Keep last progress
                    result.error_code
                )
            
            db.commit()
            
        except Exception as e:
            await update_job_status(
                job,
                RAGJobStatus.FAILED_EXTRACT,
                f"Processing error: {str(e)}",
                db,
                job.progress_pct,
                RAGJobErrorCode.UNKNOWN_ERROR
            )
            db.commit()
        
        finally:
            # Clean up active job after completion or failure
            if job_id in _active_jobs:
                del _active_jobs[job_id]
            if job_id in _job_locks:
                del _job_locks[job_id]


async def update_job_status(
    job: RAGJob,
    status: RAGJobStatus,
    step: str,
    db: Session,
    progress_pct: Optional[float] = None,
    error_code: Optional[RAGJobErrorCode] = None
):
    """Update job status with validation"""
    
    # Validate state transition
    if status not in RAG_VALID_TRANSITIONS.get(job.status, []):
        return  # Invalid transition, ignore
    
    job.status = status
    job.current_step = step
    job.progress_pct = progress_pct or RAG_PROGRESS_MAP.get(status, job.progress_pct)
    job.updated_at = datetime.utcnow()
    
    if error_code:
        job.metadata["error_code"] = error_code
        job.metadata["error_message"] = step
    
    if status in [RAGJobStatus.INDEXED, RAGJobStatus.CANCELED] or status.startswith("failed_"):
        job.metadata["ended_at"] = datetime.utcnow().isoformat()
    
    # Update in database
    db.merge(job)
    
    record_rag_metrics("job_status_updated", {
        "job_id": job.id,
        "project_id": job.project_id,
        "status": status,
        "progress_pct": job.progress_pct,
        "step": step,
    })