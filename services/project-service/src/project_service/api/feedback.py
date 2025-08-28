"""
Feedback API endpoints for collecting positive feedback and commits
Handles idempotent commit operations with data integrity, snapshots, and validation
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ..database import get_session
from ..models.episode import Episode
from ..models.project import Project
from ..repositories.episode import EpisodeRepository
from ..repositories.project import ProjectRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])

# In-memory rate limiting and idempotency cache (production: use Redis)
_commit_timestamps: Dict[str, datetime] = {}
_commit_hashes: Dict[str, str] = {}  # episode_key -> last_commit_body_hash
_idempotency_cache: Dict[str, Dict[str, Any]] = {}  # commit_id -> commit_data
COMMIT_RATE_LIMIT_SECONDS = 3
IDEMPOTENCY_TTL_HOURS = 48  # Extended TTL for idempotency


class FeedbackRequest(BaseModel):
    """Request model for feedback submission with schema hardening"""
    
    # Schema hardening fields
    schema_version: str = Field(..., description="Event schema version")
    event_id: str = Field(..., description="UUID for idempotency")
    seq: int = Field(..., description="Monotonic sequence per session")
    
    # Event details
    event: str = Field(..., description="Event type")
    project_id: str = Field(..., description="Project UUID")
    episode_id: str = Field(..., description="Episode UUID")
    commit_id: str = Field(..., description="Legacy commit ID")
    
    # Timestamps
    ts_client: str = Field(..., description="Client timestamp (ISO8601)")
    ts_client_hr: float = Field(..., description="Client high-resolution timestamp (performance.now)")
    
    # Session and scope tracking
    session_id: str = Field(..., description="Session identifier")
    page_id: str = Field(..., description="Page load identifier")
    editor_scope_id: str = Field(..., description="Editor scope identifier")
    
    # Reserved tracking fields
    actor_id_hash: Optional[str] = Field(None, description="Anonymized user identifier")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    trace_id: Optional[str] = Field(None, description="Trace correlation ID")
    ua_hash: Optional[str] = Field(None, description="User agent hash")
    ip_anonymized: Optional[str] = Field(None, description="Anonymized IP")
    tz_offset: int = Field(..., description="Timezone offset in minutes")
    
    # Legacy compatibility
    client_ts: str = Field(..., description="Legacy client timestamp")
    
    # Extended behavior data
    behavior_context: Optional[Dict[str, Any]] = Field(None, description="Behavior context data")
    content_data: Optional[Dict[str, Any]] = Field(None, description="Additional content data")
    
    # Legacy content fields (for compatibility)
    body_content: Optional[str] = Field(None, description="Episode body content for hash validation")
    body_hash: Optional[str] = Field(None, description="SHA-256 hash of body content")
    content_length: Optional[int] = Field(None, description="Content length for validation")


class FeedbackResponse(BaseModel):
    """Response model for feedback submission with integrity info"""
    stored: bool = Field(..., description="True if stored, False if duplicate commit_id or no changes")
    commit_id: str = Field(..., description="The commit ID that was processed")
    timestamp: str = Field(..., description="Server timestamp (ISO string)")
    request_id: str = Field(..., description="Request trace ID")
    trace_id: str = Field(..., description="Trace ID for logging")
    body_hash: Optional[str] = Field(None, description="Server-computed body hash")
    no_change_detected: bool = Field(False, description="True if content unchanged from last commit")
    snapshot_saved: bool = Field(False, description="True if server snapshot was saved")


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit positive feedback/commit",
    description="Submit positive feedback for an episode with idempotent commit handling",
)
async def submit_feedback(
    request: FeedbackRequest,
    http_request: Request,
) -> FeedbackResponse:
    """
    Submit positive feedback for an episode with idempotent handling.
    
    - Validates project membership and episode existence
    - Enforces rate limiting (3 second intervals per episode)
    - Handles duplicate commit_id gracefully (returns stored: false)
    - Records structured logs with trace IDs
    """
    request_id = str(uuid4())
    trace_id = getattr(http_request.state, 'trace_id', str(uuid4()))
    server_timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Structured logging context
    log_context = {
        "event": request.event,
        "project_id": request.project_id,
        "episode_id": request.episode_id,
        "commit_id": request.commit_id,
        "request_id": request_id,
        "trace_id": trace_id,
        "client_ts": request.client_ts,
        "server_ts": server_timestamp,
    }
    
    logger.info("Feedback submission received", extra=log_context)
    
    # Validate event type (expanded for behavior events)
    allowed_events = {
        "commit_positive", "accept_partial", "reject_partial", 
        "regen_again", "regen_different", "edit_manual"
    }
    
    if request.event not in allowed_events:
        logger.warning("Invalid event type", extra={**log_context, "error": "unsupported_event"})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNSUPPORTED_EVENT", "message": f"Event '{request.event}' is not supported"}
        )
    
    # TEXT-FREE VALIDATION: Ensure no text content in behavior data
    if request.behavior_context or request.content_data:
        forbidden_keys = ['text', 'body', 'content', 'script', 'message', 'comment', 'description']
        
        def check_text_content(obj, path=""):
            if not isinstance(obj, dict):
                return
            for key, value in obj.items():
                full_path = f"{path}.{key}" if path else key
                if any(forbidden in key.lower() for forbidden in forbidden_keys):
                    if isinstance(value, str) and len(value) > 10:
                        logger.warning("Text content detected in event", extra={
                            **log_context, 
                            "error": "forbidden_text_content",
                            "field_path": full_path
                        })
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"code": "FORBIDDEN_TEXT_CONTENT", "message": "Text content not allowed in behavior data"}
                        )
                elif isinstance(value, dict):
                    check_text_content(value, full_path)
        
        if request.behavior_context:
            check_text_content(request.behavior_context, "behavior_context")
        if request.content_data:
            check_text_content(request.content_data, "content_data")
    
    # Rate limiting check
    episode_key = f"{request.project_id}:{request.episode_id}"
    now = datetime.utcnow()
    
    if episode_key in _commit_timestamps:
        last_commit = _commit_timestamps[episode_key]
        time_diff = (now - last_commit).total_seconds()
        
        if time_diff < COMMIT_RATE_LIMIT_SECONDS:
            remaining = COMMIT_RATE_LIMIT_SECONDS - time_diff
            logger.warning("Rate limit exceeded", extra={
                **log_context, 
                "error": "rate_limited",
                "remaining_seconds": remaining
            })
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "RATE_LIMITED",
                    "message": f"Please wait {remaining:.1f} seconds before committing again",
                    "retry_after": int(remaining) + 1
                },
                headers={"Retry-After": str(int(remaining) + 1)}
            )
    
    try:
        with get_session() as db:
            project_repo = ProjectRepository(db)
            episode_repo = EpisodeRepository(db)
            
            # Validate project exists
            project = project_repo.get(request.project_id)
            if not project:
                logger.warning("Project not found", extra={**log_context, "error": "project_not_found"})
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "PROJECT_NOT_FOUND", "message": "Project does not exist"}
                )
            
            # Validate episode exists and belongs to project
            episode = episode_repo.get(request.episode_id)
            if not episode:
                logger.warning("Episode not found", extra={**log_context, "error": "episode_not_found"})
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "EPISODE_NOT_FOUND", "message": "Episode does not exist"}
                )
            
            if episode.project_id != request.project_id:
                logger.warning("Episode-project mismatch", extra={
                    **log_context, 
                    "error": "project_mismatch",
                    "actual_project_id": episode.project_id
                })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "PROJECT_MISMATCH", "message": "Episode does not belong to specified project"}
                )
            
            # Server-side body hash computation and validation
            server_body_hash = None
            if request.body_content:
                server_body_hash = hashlib.sha256(request.body_content.encode('utf-8')).hexdigest()
                
                # Validate client-provided hash if present
                if request.body_hash and request.body_hash != server_body_hash:
                    logger.warning("Hash mismatch detected", extra={
                        **log_context, 
                        "error": "hash_mismatch",
                        "client_hash": request.body_hash,
                        "server_hash": server_body_hash
                    })
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"code": "HASH_MISMATCH", "message": "Body content hash validation failed"}
                    )
                
                # Validate content length if present
                if request.content_length and len(request.body_content) != request.content_length:
                    logger.warning("Content length mismatch", extra={
                        **log_context, 
                        "error": "length_mismatch",
                        "expected": request.content_length,
                        "actual": len(request.body_content)
                    })
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"code": "LENGTH_MISMATCH", "message": "Content length validation failed"}
                    )
            
            # Check if commit_id already exists (idempotency - extended to 48 hours)
            existing_commit_query = text("""
                SELECT commit_id, created_at FROM episode_commits 
                WHERE commit_id = :commit_id
            """)
            result = db.execute(existing_commit_query, {"commit_id": request.commit_id})
            existing_commit = result.fetchone()
            
            if existing_commit:
                # Clean up old idempotency records beyond 48 hours TTL
                cleanup_query = text("""
                    DELETE FROM episode_commits 
                    WHERE created_at < datetime('now', '-48 hours')
                """)
                db.execute(cleanup_query)
                
                logger.info("Duplicate commit detected (idempotency)", extra={**log_context, "stored": False})
                return FeedbackResponse(
                    stored=False,
                    commit_id=request.commit_id,
                    timestamp=server_timestamp,
                    request_id=request_id,
                    trace_id=trace_id,
                    body_hash=server_body_hash
                )
            
            # No-change detection: compare with last commit hash for this episode
            no_change_detected = False
            last_commit_hash = _commit_hashes.get(episode_key)
            
            if server_body_hash and last_commit_hash and server_body_hash == last_commit_hash:
                no_change_detected = True
                logger.info("No change detected since last commit", extra={
                    **log_context, 
                    "stored": False,
                    "no_change": True,
                    "previous_hash": last_commit_hash
                })
                return FeedbackResponse(
                    stored=False,
                    commit_id=request.commit_id,
                    timestamp=server_timestamp,
                    request_id=request_id,
                    trace_id=trace_id,
                    body_hash=server_body_hash,
                    no_change_detected=True
                )
            
            # Create commits table with enhanced schema for snapshots and integrity
            create_table_query = text("""
                CREATE TABLE IF NOT EXISTS episode_commits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    commit_id TEXT UNIQUE NOT NULL,
                    project_id TEXT NOT NULL,
                    episode_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    client_timestamp TEXT NOT NULL,
                    server_timestamp TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    body_hash TEXT,
                    body_content TEXT,
                    content_length INTEGER,
                    snapshot_saved BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute(create_table_query)
            
            # Create behavior events table with hardened schema
            create_behavior_table_query = text("""
                CREATE TABLE IF NOT EXISTS behavior_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    schema_version TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    
                    event_type TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    episode_id TEXT NOT NULL,
                    
                    ts_client TEXT NOT NULL,
                    ts_client_hr REAL NOT NULL,
                    ts_server TEXT DEFAULT (datetime('now')),
                    
                    session_id TEXT NOT NULL,
                    page_id TEXT NOT NULL,
                    editor_scope_id TEXT NOT NULL,
                    
                    actor_id_hash TEXT,
                    request_id TEXT,
                    trace_id TEXT,
                    ua_hash TEXT,
                    tz_offset INTEGER,
                    
                    behavior_context TEXT, -- JSON blob
                    content_data TEXT,     -- JSON blob (text-free)
                    
                    -- Legacy compatibility
                    commit_id TEXT,
                    client_timestamp TEXT,
                    
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute(create_table_query)
            db.execute(create_behavior_table_query)
            
            # Insert into behavior_events table (new hardened schema)
            import json
            
            insert_behavior_query = text("""
                INSERT INTO behavior_events 
                (event_id, schema_version, seq, event_type, project_id, episode_id,
                 ts_client, ts_client_hr, session_id, page_id, editor_scope_id,
                 actor_id_hash, request_id, trace_id, ua_hash, tz_offset,
                 behavior_context, content_data, commit_id, client_timestamp)
                VALUES (:event_id, :schema_version, :seq, :event_type, :project_id, :episode_id,
                        :ts_client, :ts_client_hr, :session_id, :page_id, :editor_scope_id,
                        :actor_id_hash, :request_id, :trace_id, :ua_hash, :tz_offset,
                        :behavior_context, :content_data, :commit_id, :client_timestamp)
            """)
            
            db.execute(insert_behavior_query, {
                "event_id": request.event_id,
                "schema_version": request.schema_version,
                "seq": request.seq,
                "event_type": request.event,
                "project_id": request.project_id,
                "episode_id": request.episode_id,
                "ts_client": request.ts_client,
                "ts_client_hr": request.ts_client_hr,
                "session_id": request.session_id,
                "page_id": request.page_id,
                "editor_scope_id": request.editor_scope_id,
                "actor_id_hash": request.actor_id_hash,
                "request_id": request.request_id or request_id,
                "trace_id": request.trace_id or trace_id,
                "ua_hash": request.ua_hash,
                "tz_offset": request.tz_offset,
                "behavior_context": json.dumps(request.behavior_context) if request.behavior_context else None,
                "content_data": json.dumps(request.content_data) if request.content_data else None,
                "commit_id": request.commit_id,
                "client_timestamp": request.client_ts,
            })
            
            # Atomic commit with snapshot saving
            snapshot_saved = False
            
            # Insert commit record with snapshot in single transaction
            insert_commit_query = text("""
                INSERT INTO episode_commits 
                (commit_id, project_id, episode_id, event_type, client_timestamp, 
                 server_timestamp, request_id, trace_id, body_hash, body_content, 
                 content_length, snapshot_saved)
                VALUES (:commit_id, :project_id, :episode_id, :event_type, 
                        :client_timestamp, :server_timestamp, :request_id, :trace_id,
                        :body_hash, :body_content, :content_length, :snapshot_saved)
            """)
            
            # Save snapshot if content is provided
            if request.body_content:
                snapshot_saved = True
            
            db.execute(insert_commit_query, {
                "commit_id": request.commit_id,
                "project_id": request.project_id,
                "episode_id": request.episode_id,
                "event_type": request.event,
                "client_timestamp": request.client_ts,
                "server_timestamp": server_timestamp,
                "request_id": request_id,
                "trace_id": trace_id,
                "body_hash": server_body_hash,
                "body_content": request.body_content,
                "content_length": len(request.body_content) if request.body_content else None,
                "snapshot_saved": snapshot_saved
            })
            
            # Commit transaction atomically
            db.commit()
            
            # Update tracking caches after successful commit
            _commit_timestamps[episode_key] = now
            if server_body_hash:
                _commit_hashes[episode_key] = server_body_hash
            
            logger.info("Commit and snapshot stored successfully", extra={
                **log_context, 
                "stored": True,
                "snapshot_saved": snapshot_saved,
                "body_hash": server_body_hash
            })
            
            return FeedbackResponse(
                stored=True,
                commit_id=request.commit_id,
                timestamp=server_timestamp,
                request_id=request_id,
                trace_id=trace_id,
                body_hash=server_body_hash,
                no_change_detected=False,
                snapshot_saved=snapshot_saved
            )
            
    except IntegrityError as e:
        # Handle race condition where commit_id was inserted between check and insert
        if "UNIQUE constraint failed" in str(e) and "commit_id" in str(e):
            logger.info("Race condition: duplicate commit", extra={**log_context, "stored": False})
            return FeedbackResponse(
                stored=False,
                commit_id=request.commit_id,
                timestamp=server_timestamp,
                request_id=request_id,
                trace_id=trace_id,
                body_hash=server_body_hash
            )
        else:
            logger.error("Database integrity error", extra={**log_context, "error": str(e)})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"code": "DATABASE_ERROR", "message": "Failed to store commit"}
            )
    
    except Exception as e:
        logger.error("Unexpected error in feedback submission", extra={
            **log_context, 
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        )


@router.get(
    "/episodes/{episode_id}/commits",
    summary="Get commit history for episode",
    description="Retrieve all commits for a specific episode with snapshot data"
)
async def get_episode_commits(
    episode_id: str,
    include_snapshots: bool = False
) -> Dict[str, Any]:
    """Get commit history for an episode with optional snapshot content"""
    try:
        with get_session() as db:
            # Query with optional snapshot content based on parameter
            fields = [
                "commit_id", "event_type", "client_timestamp", "server_timestamp", 
                "request_id", "trace_id", "body_hash", "content_length", 
                "snapshot_saved", "created_at"
            ]
            
            if include_snapshots:
                fields.insert(-1, "body_content")
            
            query = text(f"""
                SELECT {', '.join(fields)}
                FROM episode_commits 
                WHERE episode_id = :episode_id 
                ORDER BY created_at DESC
                LIMIT 50
            """)
            result = db.execute(query, {"episode_id": episode_id})
            
            commits = []
            for row in result:
                commit_data = {
                    "commit_id": row[0],
                    "event_type": row[1],
                    "client_timestamp": row[2],
                    "server_timestamp": row[3],
                    "request_id": row[4],
                    "trace_id": row[5],
                    "body_hash": row[6],
                    "content_length": row[7],
                    "snapshot_saved": bool(row[8]),
                    "created_at": row[9].isoformat() if row[9] else None
                }
                
                if include_snapshots and len(row) > 10:
                    commit_data["body_content"] = row[9]  # body_content is at index 9 when included
                    commit_data["created_at"] = row[10].isoformat() if row[10] else None
                
                commits.append(commit_data)
            
            return {
                "episode_id": episode_id,
                "commits": commits,
                "total": len(commits),
                "includes_snapshots": include_snapshots
            }
            
    except Exception as e:
        logger.error(f"Error fetching commits for episode {episode_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "FETCH_ERROR", "message": "Failed to fetch commit history"}
        )