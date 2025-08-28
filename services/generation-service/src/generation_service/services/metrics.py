"""
Metrics collection for RAG operations
Provides comprehensive telemetry and monitoring for the RAG pipeline
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)


@dataclass
class RAGMetrics:
    """RAG operation metrics storage"""
    
    # Job metrics
    jobs_created: int = 0
    jobs_completed: int = 0
    jobs_failed: int = 0
    jobs_cancelled: int = 0
    
    # Processing metrics
    total_documents_processed: int = 0
    total_chunks_created: int = 0
    total_processing_time_seconds: float = 0.0
    
    # Error tracking
    extraction_failures: int = 0
    ocr_failures: int = 0
    embedding_failures: int = 0
    storage_failures: int = 0
    
    # Performance metrics
    avg_processing_time_seconds: float = 0.0
    avg_chunks_per_document: float = 0.0
    avg_file_size_mb: float = 0.0
    
    # Rate limiting
    rate_limit_hits: int = 0
    duplicate_detections: int = 0
    
    # ChromaDB metrics
    chromadb_operations: int = 0
    chromadb_errors: int = 0
    
    # Recent operations for trend analysis
    recent_operations: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    # Last reset timestamp
    last_reset: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class RAGMetricsCollector:
    """Collects and aggregates RAG operation metrics"""
    
    def __init__(self):
        self.metrics = RAGMetrics()
        self._operation_times: Dict[str, List[float]] = defaultdict(list)
        self._file_sizes: List[float] = []
        self._document_chunks: List[int] = []
    
    def record_job_created(self, data: Dict[str, Any]):
        """Record new job creation"""
        self.metrics.jobs_created += 1
        self._record_operation("job_created", data)
    
    def record_job_completed(self, data: Dict[str, Any]):
        """Record job completion"""
        self.metrics.jobs_completed += 1
        
        # Update processing metrics
        if "processing_time_seconds" in data:
            processing_time = data["processing_time_seconds"]
            self.metrics.total_processing_time_seconds += processing_time
            self._operation_times["processing"].append(processing_time)
        
        if "chunks_indexed" in data:
            chunks = data["chunks_indexed"]
            self.metrics.total_chunks_created += chunks
            self._document_chunks.append(chunks)
        
        if "file_size" in data:
            file_size_mb = data["file_size"] / (1024 * 1024)
            self._file_sizes.append(file_size_mb)
        
        self.metrics.total_documents_processed += 1
        self._update_averages()
        self._record_operation("job_completed", data)
    
    def record_job_failed(self, data: Dict[str, Any]):
        """Record job failure"""
        self.metrics.jobs_failed += 1
        
        # Track specific failure types
        error_code = data.get("error_code", "")
        if "extract" in error_code.lower():
            self.metrics.extraction_failures += 1
        elif "ocr" in error_code.lower():
            self.metrics.ocr_failures += 1
        elif "embed" in error_code.lower():
            self.metrics.embedding_failures += 1
        elif "store" in error_code.lower():
            self.metrics.storage_failures += 1
        
        self._record_operation("job_failed", data)
    
    def record_job_cancelled(self, data: Dict[str, Any]):
        """Record job cancellation"""
        self.metrics.jobs_cancelled += 1
        self._record_operation("job_cancelled", data)
    
    def record_rate_limit_hit(self, data: Dict[str, Any]):
        """Record rate limiting event"""
        self.metrics.rate_limit_hits += 1
        self._record_operation("rate_limit_hit", data)
    
    def record_duplicate_detection(self, data: Dict[str, Any]):
        """Record duplicate file detection"""
        self.metrics.duplicate_detections += 1
        self._record_operation("duplicate_detection", data)
    
    def record_chromadb_operation(self, data: Dict[str, Any]):
        """Record ChromaDB operation"""
        self.metrics.chromadb_operations += 1
        if data.get("success", True):
            self._record_operation("chromadb_success", data)
        else:
            self.metrics.chromadb_errors += 1
            self._record_operation("chromadb_error", data)
    
    def _record_operation(self, operation: str, data: Dict[str, Any]):
        """Record operation in recent history"""
        operation_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "data": data
        }
        self.metrics.recent_operations.append(operation_record)
    
    def _update_averages(self):
        """Update calculated averages"""
        if self.metrics.total_documents_processed > 0:
            self.metrics.avg_processing_time_seconds = (
                self.metrics.total_processing_time_seconds / self.metrics.total_documents_processed
            )
        
        if self._document_chunks:
            self.metrics.avg_chunks_per_document = sum(self._document_chunks) / len(self._document_chunks)
        
        if self._file_sizes:
            self.metrics.avg_file_size_mb = sum(self._file_sizes) / len(self._file_sizes)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        return {
            "job_stats": {
                "created": self.metrics.jobs_created,
                "completed": self.metrics.jobs_completed,
                "failed": self.metrics.jobs_failed,
                "cancelled": self.metrics.jobs_cancelled,
                "success_rate": (
                    self.metrics.jobs_completed / max(self.metrics.jobs_created, 1) * 100
                ),
            },
            "processing_stats": {
                "total_documents": self.metrics.total_documents_processed,
                "total_chunks": self.metrics.total_chunks_created,
                "total_processing_time_hours": self.metrics.total_processing_time_seconds / 3600,
                "avg_processing_time_seconds": self.metrics.avg_processing_time_seconds,
                "avg_chunks_per_document": self.metrics.avg_chunks_per_document,
                "avg_file_size_mb": self.metrics.avg_file_size_mb,
            },
            "error_stats": {
                "extraction_failures": self.metrics.extraction_failures,
                "ocr_failures": self.metrics.ocr_failures,
                "embedding_failures": self.metrics.embedding_failures,
                "storage_failures": self.metrics.storage_failures,
                "total_failures": self.metrics.jobs_failed,
            },
            "operational_stats": {
                "rate_limit_hits": self.metrics.rate_limit_hits,
                "duplicate_detections": self.metrics.duplicate_detections,
                "chromadb_operations": self.metrics.chromadb_operations,
                "chromadb_errors": self.metrics.chromadb_errors,
                "chromadb_success_rate": (
                    (self.metrics.chromadb_operations - self.metrics.chromadb_errors) /
                    max(self.metrics.chromadb_operations, 1) * 100
                ),
            },
            "recent_activity": list(self.metrics.recent_operations)[-10:],  # Last 10 operations
            "last_reset": self.metrics.last_reset,
            "collection_timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        metrics_lines = [
            "# HELP rag_jobs_total Total number of RAG jobs by status",
            "# TYPE rag_jobs_total counter",
            f"rag_jobs_total{{status=\"created\"}} {self.metrics.jobs_created}",
            f"rag_jobs_total{{status=\"completed\"}} {self.metrics.jobs_completed}",
            f"rag_jobs_total{{status=\"failed\"}} {self.metrics.jobs_failed}",
            f"rag_jobs_total{{status=\"cancelled\"}} {self.metrics.jobs_cancelled}",
            "",
            "# HELP rag_documents_processed_total Total documents processed",
            "# TYPE rag_documents_processed_total counter",
            f"rag_documents_processed_total {self.metrics.total_documents_processed}",
            "",
            "# HELP rag_chunks_created_total Total chunks created",
            "# TYPE rag_chunks_created_total counter",
            f"rag_chunks_created_total {self.metrics.total_chunks_created}",
            "",
            "# HELP rag_processing_time_seconds_total Total processing time",
            "# TYPE rag_processing_time_seconds_total counter",
            f"rag_processing_time_seconds_total {self.metrics.total_processing_time_seconds}",
            "",
            "# HELP rag_avg_processing_time_seconds Average processing time per document",
            "# TYPE rag_avg_processing_time_seconds gauge",
            f"rag_avg_processing_time_seconds {self.metrics.avg_processing_time_seconds}",
            "",
            "# HELP rag_errors_total Total errors by type",
            "# TYPE rag_errors_total counter",
            f"rag_errors_total{{type=\"extraction\"}} {self.metrics.extraction_failures}",
            f"rag_errors_total{{type=\"ocr\"}} {self.metrics.ocr_failures}",
            f"rag_errors_total{{type=\"embedding\"}} {self.metrics.embedding_failures}",
            f"rag_errors_total{{type=\"storage\"}} {self.metrics.storage_failures}",
            "",
            "# HELP rag_rate_limit_hits_total Total rate limit hits",
            "# TYPE rag_rate_limit_hits_total counter",
            f"rag_rate_limit_hits_total {self.metrics.rate_limit_hits}",
            "",
            "# HELP rag_duplicate_detections_total Total duplicate file detections",
            "# TYPE rag_duplicate_detections_total counter",
            f"rag_duplicate_detections_total {self.metrics.duplicate_detections}",
            "",
            "# HELP rag_chromadb_operations_total Total ChromaDB operations",
            "# TYPE rag_chromadb_operations_total counter",
            f"rag_chromadb_operations_total {self.metrics.chromadb_operations}",
            "",
            "# HELP rag_chromadb_errors_total Total ChromaDB errors",
            "# TYPE rag_chromadb_errors_total counter",
            f"rag_chromadb_errors_total {self.metrics.chromadb_errors}",
        ]
        
        return "\n".join(metrics_lines)
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = RAGMetrics()
        self._operation_times.clear()
        self._file_sizes.clear()
        self._document_chunks.clear()
        logger.info("RAG metrics reset")


# Global metrics collector instance
_metrics_collector: Optional[RAGMetricsCollector] = None


def get_metrics_collector() -> RAGMetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = RAGMetricsCollector()
    return _metrics_collector


def record_rag_metrics(event: str, data: Dict[str, Any]):
    """Record RAG operation metrics"""
    collector = get_metrics_collector()
    timestamp = datetime.utcnow().isoformat()
    
    # Add timestamp to data
    data_with_timestamp = {**data, "timestamp": timestamp}
    
    # Route to appropriate metric recording method
    if event == "ingest_started":
        collector.record_job_created(data_with_timestamp)
    elif event == "job_completed":
        collector.record_job_completed(data_with_timestamp)
    elif event == "job_failed":
        collector.record_job_failed(data_with_timestamp)
    elif event == "job_cancelled":
        collector.record_job_cancelled(data_with_timestamp)
    elif event == "ingest_rate_limited":
        collector.record_rate_limit_hit(data_with_timestamp)
    elif event == "ingest_duplicate_detected":
        collector.record_duplicate_detection(data_with_timestamp)
    elif event.startswith("chromadb_"):
        collector.record_chromadb_operation({
            **data_with_timestamp,
            "success": "error" not in event
        })
    else:
        # Generic operation recording
        collector._record_operation(event, data_with_timestamp)
    
    # Log in development
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"📊 RAG Metrics: {event}", extra=data_with_timestamp)


def get_rag_metrics_summary() -> Dict[str, Any]:
    """Get comprehensive RAG metrics summary"""
    return get_metrics_collector().get_metrics_summary()


def get_rag_prometheus_metrics() -> str:
    """Get RAG metrics in Prometheus format"""
    return get_metrics_collector().get_prometheus_metrics()


def reset_rag_metrics():
    """Reset RAG metrics"""
    get_metrics_collector().reset_metrics()


# Performance tracking decorator
def track_rag_operation(operation_name: str):
    """Decorator to track RAG operation performance"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                record_rag_metrics(f"{operation_name}_success", {
                    "duration_seconds": duration,
                    "operation": operation_name,
                })
                return result
            except Exception as e:
                duration = time.time() - start_time
                record_rag_metrics(f"{operation_name}_failed", {
                    "duration_seconds": duration,
                    "operation": operation_name,
                    "error": str(e),
                })
                raise
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                record_rag_metrics(f"{operation_name}_success", {
                    "duration_seconds": duration,
                    "operation": operation_name,
                })
                return result
            except Exception as e:
                duration = time.time() - start_time
                record_rag_metrics(f"{operation_name}_failed", {
                    "duration_seconds": duration,
                    "operation": operation_name,
                    "error": str(e),
                })
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator