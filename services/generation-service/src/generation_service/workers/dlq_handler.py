"""
Dead Letter Queue handler for failed RAG processing jobs
Handles error analysis, alerting, and manual intervention
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

from sqlalchemy.orm import Session
from rq import get_current_job

from generation_service.database import get_db
from generation_service.workers.job_schemas import (
    DLQEntryDB, WorkerErrorCode, WorkerJobDB, DLQEntry
)
from generation_service.workers.worker_adapter import WorkerRedisConnection
from generation_service.core.monitoring import send_alert, AlertSeverity, AlertChannel

logger = logging.getLogger(__name__)

# DLQ configuration
DLQ_RETENTION_DAYS = int(os.getenv("DLQ_RETENTION_DAYS", "30"))
DLQ_AUTO_RESOLVE_AFTER_DAYS = int(os.getenv("DLQ_AUTO_RESOLVE_AFTER_DAYS", "7"))
DLQ_ALERT_THRESHOLD = int(os.getenv("DLQ_ALERT_THRESHOLD", "10"))  # Alert when DLQ size exceeds this
ENABLE_DLQ_ALERTS = os.getenv("ENABLE_DLQ_ALERTS", "true").lower() == "true"

# Error analysis patterns
CRITICAL_ERROR_PATTERNS = [
    'corruption',
    'security',
    'authentication',
    'authorization',
    'injection',
    'overflow'
]

TRANSIENT_ERROR_PATTERNS = [
    'timeout',
    'connection',
    'network',
    'rate limit',
    'service unavailable',
    'temporary'
]


class DLQAnalyzer:
    """Analyzes DLQ entries for patterns and recommendations"""
    
    def __init__(self):
        self.error_patterns = self._load_error_patterns()
    
    def analyze_error(self, dlq_entry: DLQEntry) -> Dict[str, Any]:
        """Analyze a DLQ entry and provide recommendations"""
        
        analysis = {
            'error_category': self._categorize_error(dlq_entry),
            'severity': self._assess_severity(dlq_entry),
            'is_transient': self._is_transient_error(dlq_entry),
            'is_critical': self._is_critical_error(dlq_entry),
            'retry_recommended': self._should_retry(dlq_entry),
            'action_required': self._get_required_actions(dlq_entry),
            'similar_errors_count': 0,  # Will be filled by caller
            'recommendation': '',
        }
        
        # Generate recommendation
        analysis['recommendation'] = self._generate_recommendation(dlq_entry, analysis)
        
        return analysis
    
    def analyze_dlq_trends(self, db: Session, days: int = 7) -> Dict[str, Any]:
        """Analyze DLQ trends over time"""
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Get all DLQ entries in time window
        entries = db.query(DLQEntryDB).filter(
            DLQEntryDB.failed_at >= cutoff
        ).all()
        
        if not entries:
            return {
                'total_entries': 0,
                'error_trends': {},
                'project_trends': {},
                'time_trends': {},
                'recommendations': []
            }
        
        # Analyze by error type
        error_counts = {}
        for entry in entries:
            error_counts[entry.error_type] = error_counts.get(entry.error_type, 0) + 1
        
        # Analyze by project
        project_counts = {}
        for entry in entries:
            project_counts[entry.project_id] = project_counts.get(entry.project_id, 0) + 1
        
        # Analyze by time (daily)
        time_trends = {}
        for entry in entries:
            day_key = entry.failed_at.strftime('%Y-%m-%d')
            time_trends[day_key] = time_trends.get(day_key, 0) + 1
        
        # Generate trend-based recommendations
        recommendations = self._generate_trend_recommendations(
            error_counts, project_counts, time_trends
        )
        
        return {
            'total_entries': len(entries),
            'error_trends': error_counts,
            'project_trends': project_counts,
            'time_trends': time_trends,
            'recommendations': recommendations,
            'analysis_period_days': days,
            'critical_errors': sum(1 for e in entries if self._is_critical_error_type(e.error_type)),
            'transient_errors': sum(1 for e in entries if self._is_transient_error_type(e.error_type)),
        }
    
    def _categorize_error(self, dlq_entry: DLQEntry) -> str:
        """Categorize error type"""
        
        error_msg = dlq_entry.error_message.lower()
        error_type = dlq_entry.error_type.lower()
        
        if any(pattern in error_msg or pattern in error_type for pattern in ['file', 'upload', 'storage']):
            return 'file_handling'
        elif any(pattern in error_msg or pattern in error_type for pattern in ['extract', 'parse', 'ocr']):
            return 'content_extraction'
        elif any(pattern in error_msg or pattern in error_type for pattern in ['embed', 'api', 'rate']):
            return 'embedding_api'
        elif any(pattern in error_msg or pattern in error_type for pattern in ['chroma', 'vector', 'index']):
            return 'vector_storage'
        elif any(pattern in error_msg or pattern in error_type for pattern in ['timeout', 'memory', 'resource']):
            return 'system_resource'
        else:
            return 'unknown'
    
    def _assess_severity(self, dlq_entry: DLQEntry) -> str:
        """Assess error severity"""
        
        if self._is_critical_error(dlq_entry):
            return 'critical'
        elif dlq_entry.attempts >= 3:
            return 'high'
        elif self._is_transient_error(dlq_entry):
            return 'low'
        else:
            return 'medium'
    
    def _is_transient_error(self, dlq_entry: DLQEntry) -> bool:
        """Check if error is likely transient"""
        
        error_text = f"{dlq_entry.error_type} {dlq_entry.error_message}".lower()
        return any(pattern in error_text for pattern in TRANSIENT_ERROR_PATTERNS)
    
    def _is_critical_error(self, dlq_entry: DLQEntry) -> bool:
        """Check if error is critical"""
        
        error_text = f"{dlq_entry.error_type} {dlq_entry.error_message}".lower()
        return any(pattern in error_text for pattern in CRITICAL_ERROR_PATTERNS)
    
    def _is_critical_error_type(self, error_type: str) -> bool:
        """Check if error type is critical"""
        
        critical_types = [
            'security_violation',
            'data_corruption',
            'authentication_error',
            'authorization_error'
        ]
        return error_type.lower() in critical_types
    
    def _is_transient_error_type(self, error_type: str) -> bool:
        """Check if error type is transient"""
        
        transient_types = [
            'timeout',
            'network_error',
            'rate_limited',
            'service_unavailable'
        ]
        return error_type.lower() in transient_types
    
    def _should_retry(self, dlq_entry: DLQEntry) -> bool:
        """Determine if error should be retried"""
        
        # Don't retry if too many attempts already
        if dlq_entry.attempts >= 5:
            return False
        
        # Don't retry critical errors
        if self._is_critical_error(dlq_entry):
            return False
        
        # Retry transient errors
        if self._is_transient_error(dlq_entry):
            return True
        
        # Don't retry validation errors
        validation_errors = ['validation_error', 'invalid_file_type', 'file_too_large']
        if dlq_entry.error_type in validation_errors:
            return False
        
        # Default: retry if attempts < 3
        return dlq_entry.attempts < 3
    
    def _get_required_actions(self, dlq_entry: DLQEntry) -> List[str]:
        """Get list of required manual actions"""
        
        actions = []
        
        if self._is_critical_error(dlq_entry):
            actions.append('security_review')
        
        if 'file_not_found' in dlq_entry.error_type:
            actions.append('verify_file_exists')
        
        if 'invalid_file_type' in dlq_entry.error_type:
            actions.append('check_file_format')
        
        if 'rate_limited' in dlq_entry.error_type:
            actions.append('check_api_quota')
        
        if 'chroma' in dlq_entry.error_message.lower():
            actions.append('check_vector_db_health')
        
        if dlq_entry.attempts >= 3:
            actions.append('manual_investigation')
        
        return actions
    
    def _generate_recommendation(self, dlq_entry: DLQEntry, analysis: Dict[str, Any]) -> str:
        """Generate human-readable recommendation"""
        
        if analysis['is_critical']:
            return f"CRITICAL: {dlq_entry.error_type} requires immediate attention. Security review needed."
        
        elif analysis['retry_recommended']:
            return f"Transient error. Retry job after addressing: {', '.join(analysis['action_required'])}"
        
        elif analysis['error_category'] == 'file_handling':
            return "File handling issue. Verify file exists and is accessible."
        
        elif analysis['error_category'] == 'content_extraction':
            return "Content extraction failed. Check file format and integrity."
        
        elif analysis['error_category'] == 'embedding_api':
            return "Embedding API issue. Check API quota, rate limits, and service status."
        
        elif analysis['error_category'] == 'vector_storage':
            return "Vector database issue. Check ChromaDB health and connectivity."
        
        elif analysis['error_category'] == 'system_resource':
            return "System resource issue. Check memory, CPU, and disk usage."
        
        else:
            return f"Unknown error pattern. Manual investigation required for {dlq_entry.error_type}."
    
    def _generate_trend_recommendations(
        self,
        error_counts: Dict[str, int],
        project_counts: Dict[str, int],
        time_trends: Dict[str, int]
    ) -> List[str]:
        """Generate recommendations based on trends"""
        
        recommendations = []
        
        # Check for dominant error types
        if error_counts:
            most_common_error = max(error_counts.items(), key=lambda x: x[1])
            if most_common_error[1] > 5:
                recommendations.append(
                    f"Address recurring {most_common_error[0]} errors ({most_common_error[1]} occurrences)"
                )
        
        # Check for project-specific issues
        if project_counts:
            problematic_projects = [(p, c) for p, c in project_counts.items() if c > 3]
            for project, count in problematic_projects:
                recommendations.append(
                    f"Project {project} has {count} failures - investigate project-specific issues"
                )
        
        # Check for time-based patterns
        if len(time_trends) > 1:
            daily_counts = list(time_trends.values())
            if max(daily_counts) > 2 * (sum(daily_counts) / len(daily_counts)):
                recommendations.append("Spike in failures detected - check for system issues during peak times")
        
        return recommendations
    
    def _load_error_patterns(self) -> Dict[str, List[str]]:
        """Load error patterns for classification"""
        
        # This could be loaded from a config file in production
        return {
            'file_errors': ['file_not_found', 'file_corrupted', 'invalid_file_type'],
            'api_errors': ['embedding_api_error', 'rate_limited', 'quota_exceeded'],
            'system_errors': ['timeout', 'memory_exhausted', 'disk_full'],
            'security_errors': ['authentication_error', 'authorization_error'],
        }


class DLQHandler:
    """Handles DLQ entry processing and management"""
    
    def __init__(self):
        self.analyzer = DLQAnalyzer()
        self.redis_conn = WorkerRedisConnection()
    
    def process_dlq_entry(self, dlq_entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a DLQ entry (RQ worker function)"""
        
        try:
            # Convert to DLQEntry object
            dlq_entry = DLQEntry(**dlq_entry_data)
            
            # Store in database
            with next(get_db()) as db:
                db_entry = self._create_dlq_db_entry(db, dlq_entry)
                
                # Analyze the error
                analysis = self.analyzer.analyze_error(dlq_entry)
                
                # Count similar errors
                similar_count = db.query(DLQEntryDB).filter(
                    DLQEntryDB.error_type == dlq_entry.error_type,
                    DLQEntryDB.failed_at >= datetime.utcnow() - timedelta(hours=24),
                    DLQEntryDB.resolved_at.is_(None)
                ).count()
                
                analysis['similar_errors_count'] = similar_count
                
                # Update database entry with analysis
                db_entry.final_metadata = {
                    'analysis': analysis,
                    'processed_at': datetime.utcnow().isoformat(),
                    'similar_errors_24h': similar_count
                }
                db.commit()
                
                # Send alert if needed
                if ENABLE_DLQ_ALERTS:
                    self._send_dlq_alert_if_needed(dlq_entry, analysis, similar_count)
                
                logger.info(f"Processed DLQ entry {dlq_entry.job_id}: {analysis['error_category']} ({analysis['severity']})")
                
                return {
                    'success': True,
                    'dlq_entry_id': db_entry.id,
                    'analysis': analysis,
                    'action_required': analysis.get('action_required', [])
                }
        
        except Exception as e:
            logger.error(f"Failed to process DLQ entry: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_old_dlq_entries(self) -> Dict[str, Any]:
        """Cleanup old DLQ entries (scheduled job)"""
        
        cutoff_resolved = datetime.utcnow() - timedelta(days=DLQ_RETENTION_DAYS)
        cutoff_auto_resolve = datetime.utcnow() - timedelta(days=DLQ_AUTO_RESOLVE_AFTER_DAYS)
        
        try:
            with next(get_db()) as db:
                # Delete old resolved entries
                deleted_resolved = db.query(DLQEntryDB).filter(
                    DLQEntryDB.resolved_at.isnot(None),
                    DLQEntryDB.resolved_at < cutoff_resolved
                ).delete()
                
                # Auto-resolve very old unresolved entries
                auto_resolved = db.query(DLQEntryDB).filter(
                    DLQEntryDB.resolved_at.is_(None),
                    DLQEntryDB.failed_at < cutoff_auto_resolve
                ).update({
                    'resolved_at': datetime.utcnow(),
                    'resolution_notes': f'Auto-resolved after {DLQ_AUTO_RESOLVE_AFTER_DAYS} days',
                    'resolved_by': 'system'
                })
                
                db.commit()
                
                logger.info(f"DLQ cleanup: deleted {deleted_resolved} old entries, auto-resolved {auto_resolved} entries")
                
                return {
                    'success': True,
                    'deleted_resolved': deleted_resolved,
                    'auto_resolved': auto_resolved
                }
        
        except Exception as e:
            logger.error(f"DLQ cleanup failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_dlq_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive DLQ report"""
        
        try:
            with next(get_db()) as db:
                # Get trend analysis
                trends = self.analyzer.analyze_dlq_trends(db, days)
                
                # Get current DLQ size
                current_dlq_size = db.query(DLQEntryDB).filter(
                    DLQEntryDB.resolved_at.is_(None)
                ).count()
                
                # Get top errors
                top_errors = db.query(
                    DLQEntryDB.error_type,
                    DLQEntryDB.error_code,
                    db.func.count(DLQEntryDB.id).label('count')
                ).filter(
                    DLQEntryDB.failed_at >= datetime.utcnow() - timedelta(days=days),
                    DLQEntryDB.resolved_at.is_(None)
                ).group_by(
                    DLQEntryDB.error_type,
                    DLQEntryDB.error_code
                ).order_by(
                    db.func.count(DLQEntryDB.id).desc()
                ).limit(10).all()
                
                # Get projects with most failures
                failing_projects = db.query(
                    DLQEntryDB.project_id,
                    db.func.count(DLQEntryDB.id).label('count')
                ).filter(
                    DLQEntryDB.failed_at >= datetime.utcnow() - timedelta(days=days)
                ).group_by(
                    DLQEntryDB.project_id
                ).order_by(
                    db.func.count(DLQEntryDB.id).desc()
                ).limit(5).all()
                
                report = {
                    'report_generated_at': datetime.utcnow().isoformat(),
                    'analysis_period_days': days,
                    'current_dlq_size': current_dlq_size,
                    'trends': trends,
                    'top_errors': [
                        {'error_type': err[0], 'error_code': err[1], 'count': err[2]}
                        for err in top_errors
                    ],
                    'failing_projects': [
                        {'project_id': proj[0], 'failure_count': proj[1]}
                        for proj in failing_projects
                    ],
                    'alert_threshold_exceeded': current_dlq_size > DLQ_ALERT_THRESHOLD,
                    'recommendations': trends.get('recommendations', []),
                }
                
                return report
        
        except Exception as e:
            logger.error(f"Failed to generate DLQ report: {e}")
            return {
                'error': str(e),
                'report_generated_at': datetime.utcnow().isoformat()
            }
    
    def _create_dlq_db_entry(self, db: Session, dlq_entry: DLQEntry) -> DLQEntryDB:
        """Create database entry for DLQ item"""
        
        db_entry = DLQEntryDB(
            id=dlq_entry.job_id + "_dlq",
            original_job_id=dlq_entry.job_id,
            ingest_id=dlq_entry.job_id,  # Might need to extract from payload
            project_id=dlq_entry.payload.get('project_id', 'unknown'),
            error_type=dlq_entry.error_type.value,
            error_code=dlq_entry.error_message[:64],  # Truncate for DB
            error_message=dlq_entry.error_message,
            last_step=dlq_entry.last_step,
            attempts=dlq_entry.attempts,
            failed_at=datetime.fromisoformat(dlq_entry.failed_at),
            trace_id=dlq_entry.trace_id,
            stack_trace=dlq_entry.stack_trace,
            job_payload=dlq_entry.payload,
        )
        
        db.add(db_entry)
        return db_entry
    
    def _send_dlq_alert_if_needed(
        self, 
        dlq_entry: DLQEntry, 
        analysis: Dict[str, Any], 
        similar_count: int
    ):
        """Send alert if DLQ entry meets alert criteria"""
        
        should_alert = False
        alert_severity = AlertSeverity.INFO
        alert_reason = ""
        
        # Alert on critical errors
        if analysis['is_critical']:
            should_alert = True
            alert_severity = AlertSeverity.CRITICAL
            alert_reason = f"Critical error: {dlq_entry.error_type}"
        
        # Alert on repeated errors
        elif similar_count >= 5:
            should_alert = True
            alert_severity = AlertSeverity.WARNING
            alert_reason = f"Repeated error: {similar_count} occurrences of {dlq_entry.error_type}"
        
        # Alert if DLQ is getting full
        with next(get_db()) as db:
            current_dlq_size = db.query(DLQEntryDB).filter(
                DLQEntryDB.resolved_at.is_(None)
            ).count()
            
            if current_dlq_size >= DLQ_ALERT_THRESHOLD:
                should_alert = True
                alert_severity = AlertSeverity.WARNING
                alert_reason = f"DLQ size exceeded threshold: {current_dlq_size} entries"
        
        if should_alert:
            alert_message = f"RAG DLQ Alert: {alert_reason}\n\nJob: {dlq_entry.job_id}\nProject: {dlq_entry.payload.get('project_id')}\nError: {dlq_entry.error_message}\nRecommendation: {analysis.get('recommendation', 'Manual investigation required')}"
            
            send_alert(
                title=f"RAG DLQ Alert: {dlq_entry.error_type}",
                message=alert_message,
                severity=alert_severity,
                channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
                metadata={
                    'job_id': dlq_entry.job_id,
                    'error_type': dlq_entry.error_type,
                    'project_id': dlq_entry.payload.get('project_id'),
                    'similar_count': similar_count,
                    'analysis': analysis
                }
            )


# Global DLQ handler instance
_dlq_handler = DLQHandler()


def process_dlq_entry(dlq_entry_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process DLQ entry (RQ worker function)"""
    return _dlq_handler.process_dlq_entry(dlq_entry_data)


def cleanup_dlq_entries() -> Dict[str, Any]:
    """Cleanup old DLQ entries (scheduled function)"""
    return _dlq_handler.cleanup_old_dlq_entries()


def generate_dlq_report(days: int = 7) -> Dict[str, Any]:
    """Generate DLQ report (scheduled function)"""
    return _dlq_handler.generate_dlq_report(days)