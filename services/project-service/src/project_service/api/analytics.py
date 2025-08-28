"""
Analytics API endpoints with K-anonymity protection
Provides aggregated behavior analysis data for AI improvement
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text, func
from sqlalchemy.exc import SQLAlchemyError

from ..database import get_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])

# K-anonymity threshold - only return aggregates with >= k observations
K_ANONYMITY_THRESHOLD = 5


class AnalyticsPatternResponse(BaseModel):
    """Response model for behavior pattern analysis"""
    project_id: str
    time_window: str
    total_events: int
    unique_users: int  # Anonymized count
    
    # Pattern metrics (aggregated)
    regeneration_patterns: Dict[str, int]
    satisfaction_metrics: Dict[str, float]
    usage_frequency: Dict[str, int]
    
    # Privacy metadata
    k_anonymity_compliant: bool
    aggregation_level: str
    data_retention_days: int


class EventMetricsResponse(BaseModel):
    """Response model for event type metrics"""
    event_type: str
    count: int
    average_latency_ms: Optional[float]
    success_rate: float
    user_satisfaction_score: Optional[float]
    time_period: str


class AnalyticsStatsResponse(BaseModel):
    """Response model for general analytics statistics"""
    total_sessions: int
    total_events: int
    active_projects: int
    data_quality_score: float
    k_anonymity_compliance_rate: float
    last_updated: str


@router.get(
    "/analytics/patterns",
    response_model=AnalyticsPatternResponse,
    summary="Get behavior patterns with K-anonymity protection",
    description="Returns aggregated behavior patterns only if K-anonymity threshold is met"
)
async def get_behavior_patterns(
    project_id: str = Query(..., description="Project UUID to analyze"),
    time_window: str = Query("7d", description="Time window: 1d, 7d, 30d, 90d"),
    request: Request = None
) -> AnalyticsPatternResponse:
    """
    Get aggregated behavior patterns with privacy protection
    
    - Only returns data if >= K users contribute to each bucket
    - All user identifiers are anonymized
    - Text content is never included in responses
    """
    request_id = str(uuid4())
    trace_id = getattr(request.state if request else None, 'trace_id', str(uuid4()))
    
    log_context = {
        "project_id": project_id,
        "time_window": time_window,
        "request_id": request_id,
        "trace_id": trace_id,
    }
    
    logger.info("Analytics patterns request received", extra=log_context)
    
    # Parse time window
    time_mapping = {
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }
    
    if time_window not in time_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_TIME_WINDOW", "message": "Invalid time window specified"}
        )
    
    time_delta = time_mapping[time_window]
    cutoff_time = datetime.utcnow() - time_delta
    
    try:
        with get_session() as db:
            # Check if we have the feedback/analytics table structure
            check_table_query = text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND (name='episode_commits' OR name='behavior_events')
            """)
            result = db.execute(check_table_query)
            tables = [row[0] for row in result]
            
            if not tables:
                logger.warning("No analytics tables found", extra=log_context)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "NO_DATA", "message": "No analytics data available"}
                )
            
            # Create behavior events table if not exists (hardened schema)
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
                    
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute(create_behavior_table_query)
            
            # Get unique user count for K-anonymity check
            user_count_query = text("""
                SELECT COUNT(DISTINCT actor_id_hash) as unique_users
                FROM behavior_events 
                WHERE project_id = :project_id 
                AND datetime(ts_server) >= datetime(:cutoff_time)
                AND actor_id_hash IS NOT NULL
            """)
            result = db.execute(user_count_query, {
                "project_id": project_id,
                "cutoff_time": cutoff_time.isoformat()
            })
            unique_users = result.scalar() or 0
            
            # Apply K-anonymity protection
            if unique_users < K_ANONYMITY_THRESHOLD:
                logger.info("K-anonymity threshold not met", extra={
                    **log_context, 
                    "unique_users": unique_users,
                    "threshold": K_ANONYMITY_THRESHOLD
                })
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "INSUFFICIENT_DATA", 
                        "message": f"Insufficient data for privacy-compliant analysis (need >= {K_ANONYMITY_THRESHOLD} users)"
                    }
                )
            
            # Get total events
            total_events_query = text("""
                SELECT COUNT(*) as total_events
                FROM behavior_events 
                WHERE project_id = :project_id 
                AND datetime(ts_server) >= datetime(:cutoff_time)
            """)
            result = db.execute(total_events_query, {
                "project_id": project_id,
                "cutoff_time": cutoff_time.isoformat()
            })
            total_events = result.scalar() or 0
            
            # Get regeneration patterns (aggregated)
            regen_patterns_query = text("""
                SELECT event_type, COUNT(*) as count
                FROM behavior_events 
                WHERE project_id = :project_id 
                AND datetime(ts_server) >= datetime(:cutoff_time)
                AND event_type IN ('regen_again', 'regen_different')
                GROUP BY event_type
                HAVING COUNT(DISTINCT actor_id_hash) >= :k_threshold
            """)
            result = db.execute(regen_patterns_query, {
                "project_id": project_id,
                "cutoff_time": cutoff_time.isoformat(),
                "k_threshold": K_ANONYMITY_THRESHOLD
            })
            regeneration_patterns = {row[0]: row[1] for row in result}
            
            # Get satisfaction metrics (aggregated)
            satisfaction_query = text("""
                SELECT 
                    CASE 
                        WHEN event_type IN ('accept_partial', 'commit_positive') THEN 'positive'
                        WHEN event_type IN ('reject_partial', 'regen_again') THEN 'negative'
                        ELSE 'neutral'
                    END as sentiment,
                    COUNT(*) * 1.0 / (SELECT COUNT(*) FROM behavior_events 
                                      WHERE project_id = :project_id 
                                      AND datetime(ts_server) >= datetime(:cutoff_time)) as ratio
                FROM behavior_events 
                WHERE project_id = :project_id 
                AND datetime(ts_server) >= datetime(:cutoff_time)
                GROUP BY sentiment
                HAVING COUNT(DISTINCT actor_id_hash) >= :k_threshold
            """)
            result = db.execute(satisfaction_query, {
                "project_id": project_id,
                "cutoff_time": cutoff_time.isoformat(),
                "k_threshold": K_ANONYMITY_THRESHOLD
            })
            satisfaction_metrics = {row[0]: float(row[1]) for row in result}
            
            # Get usage frequency (aggregated by hour buckets)
            usage_frequency_query = text("""
                SELECT 
                    strftime('%H', ts_server) as hour_bucket,
                    COUNT(*) as event_count
                FROM behavior_events 
                WHERE project_id = :project_id 
                AND datetime(ts_server) >= datetime(:cutoff_time)
                GROUP BY hour_bucket
                HAVING COUNT(DISTINCT actor_id_hash) >= :k_threshold
                ORDER BY hour_bucket
            """)
            result = db.execute(usage_frequency_query, {
                "project_id": project_id,
                "cutoff_time": cutoff_time.isoformat(),
                "k_threshold": K_ANONYMITY_THRESHOLD
            })
            usage_frequency = {f"hour_{row[0]}": row[1] for row in result}
            
            response = AnalyticsPatternResponse(
                project_id=project_id,
                time_window=time_window,
                total_events=total_events,
                unique_users=unique_users,
                regeneration_patterns=regeneration_patterns,
                satisfaction_metrics=satisfaction_metrics,
                usage_frequency=usage_frequency,
                k_anonymity_compliant=True,
                aggregation_level="project",
                data_retention_days=180
            )
            
            logger.info("Analytics patterns response generated", extra={
                **log_context,
                "total_events": total_events,
                "unique_users": unique_users,
                "k_anonymity_compliant": True
            })
            
            return response
            
    except SQLAlchemyError as e:
        logger.error("Database error in analytics query", extra={
            **log_context, 
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "DATABASE_ERROR", "message": "Failed to retrieve analytics data"}
        )
    
    except Exception as e:
        logger.error("Unexpected error in analytics query", extra={
            **log_context, 
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        )


@router.get(
    "/analytics/events",
    response_model=List[EventMetricsResponse],
    summary="Get event type metrics",
    description="Returns aggregated metrics for different event types"
)
async def get_event_metrics(
    project_id: Optional[str] = Query(None, description="Optional project filter"),
    time_window: str = Query("7d", description="Time window: 1d, 7d, 30d"),
    request: Request = None
) -> List[EventMetricsResponse]:
    """Get aggregated metrics for event types with K-anonymity protection"""
    
    request_id = str(uuid4())
    
    # Parse time window
    time_mapping = {
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    
    if time_window not in time_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_TIME_WINDOW", "message": "Invalid time window"}
        )
    
    time_delta = time_mapping[time_window]
    cutoff_time = datetime.utcnow() - time_delta
    
    try:
        with get_session() as db:
            base_query = """
                SELECT 
                    event_type,
                    COUNT(*) as count,
                    AVG(CAST(json_extract(behavior_context, '$.time_spent') AS REAL) * 1000) as avg_latency_ms,
                    COUNT(DISTINCT actor_id_hash) as unique_users,
                    CASE 
                        WHEN event_type IN ('accept_partial', 'commit_positive') THEN 0.8
                        WHEN event_type IN ('reject_partial', 'regen_again') THEN 0.3
                        ELSE 0.6
                    END as satisfaction_score
                FROM behavior_events 
                WHERE datetime(ts_server) >= datetime(:cutoff_time)
            """
            
            params = {"cutoff_time": cutoff_time.isoformat()}
            
            if project_id:
                base_query += " AND project_id = :project_id"
                params["project_id"] = project_id
            
            base_query += """
                GROUP BY event_type
                HAVING COUNT(DISTINCT actor_id_hash) >= :k_threshold
                ORDER BY count DESC
            """
            params["k_threshold"] = K_ANONYMITY_THRESHOLD
            
            result = db.execute(text(base_query), params)
            
            metrics = []
            for row in result:
                metrics.append(EventMetricsResponse(
                    event_type=row[0],
                    count=row[1],
                    average_latency_ms=row[2],
                    success_rate=1.0,  # Simplified - actual calculation would be more complex
                    user_satisfaction_score=row[4],
                    time_period=time_window
                ))
            
            logger.info("Event metrics generated", extra={
                "request_id": request_id,
                "project_id": project_id,
                "time_window": time_window,
                "metrics_count": len(metrics)
            })
            
            return metrics
            
    except Exception as e:
        logger.error("Error generating event metrics", extra={
            "request_id": request_id,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "METRICS_ERROR", "message": "Failed to generate event metrics"}
        )


@router.get(
    "/analytics/stats",
    response_model=AnalyticsStatsResponse,
    summary="Get general analytics statistics",
    description="Returns high-level analytics statistics"
)
async def get_analytics_stats(request: Request = None) -> AnalyticsStatsResponse:
    """Get general analytics statistics"""
    
    request_id = str(uuid4())
    
    try:
        with get_session() as db:
            # Get total sessions (unique session_id)
            sessions_query = text("""
                SELECT COUNT(DISTINCT session_id) as total_sessions
                FROM behavior_events
                WHERE datetime(ts_server) >= datetime('now', '-30 days')
            """)
            result = db.execute(sessions_query)
            total_sessions = result.scalar() or 0
            
            # Get total events
            events_query = text("""
                SELECT COUNT(*) as total_events
                FROM behavior_events
                WHERE datetime(ts_server) >= datetime('now', '-30 days')
            """)
            result = db.execute(events_query)
            total_events = result.scalar() or 0
            
            # Get active projects
            projects_query = text("""
                SELECT COUNT(DISTINCT project_id) as active_projects
                FROM behavior_events
                WHERE datetime(ts_server) >= datetime('now', '-30 days')
            """)
            result = db.execute(projects_query)
            active_projects = result.scalar() or 0
            
            # Calculate data quality score (simplified)
            quality_score = min(1.0, total_events / 1000.0) if total_events > 0 else 0.0
            
            # Calculate K-anonymity compliance rate
            compliance_query = text("""
                SELECT 
                    COUNT(*) as total_buckets,
                    SUM(CASE WHEN user_count >= :k_threshold THEN 1 ELSE 0 END) as compliant_buckets
                FROM (
                    SELECT event_type, COUNT(DISTINCT actor_id_hash) as user_count
                    FROM behavior_events
                    WHERE datetime(ts_server) >= datetime('now', '-30 days')
                    GROUP BY event_type
                ) as bucket_stats
            """)
            result = db.execute(compliance_query, {"k_threshold": K_ANONYMITY_THRESHOLD})
            bucket_stats = result.fetchone()
            
            if bucket_stats and bucket_stats[0] > 0:
                compliance_rate = bucket_stats[1] / bucket_stats[0]
            else:
                compliance_rate = 0.0
            
            response = AnalyticsStatsResponse(
                total_sessions=total_sessions,
                total_events=total_events,
                active_projects=active_projects,
                data_quality_score=quality_score,
                k_anonymity_compliance_rate=compliance_rate,
                last_updated=datetime.utcnow().isoformat() + "Z"
            )
            
            logger.info("Analytics stats generated", extra={
                "request_id": request_id,
                "total_sessions": total_sessions,
                "total_events": total_events,
                "compliance_rate": compliance_rate
            })
            
            return response
            
    except Exception as e:
        logger.error("Error generating analytics stats", extra={
            "request_id": request_id,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "STATS_ERROR", "message": "Failed to generate analytics statistics"}
        )