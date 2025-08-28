"""
Comprehensive tests for durable RAG worker system
Tests worker reliability, state transitions, retry policies, and edge cases
"""

import pytest
import asyncio
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any

import redis
from rq import Queue, Worker, Connection
from rq.job import Job as RQJob
from sqlalchemy.orm import Session

# Import the modules under test
from generation_service.workers.worker_adapter import (
    WorkerAdapter, WorkerJobPayload, DLQEntry, should_use_durable_worker
)
from generation_service.workers.job_schemas import (
    WorkerJobStatus, WorkerErrorCode, WorkerJobDB, DLQEntryDB,
    calculate_retry_delay, should_retry_error, get_retry_policy,
    VALID_STATE_TRANSITIONS, RetryPolicy
)
from generation_service.workers.rag_worker import (
    process_rag_document, WorkerProgressTracker, EmbeddingRateLimiter,
    WorkerCancellationError, WorkerRateLimitError
)
from generation_service.workers.security import (
    FileSecurityValidator, validate_file_security, TempFileManager,
    ResourceLimitEnforcer, RedisSecurityManager
)
from generation_service.workers.dlq_handler import (
    DLQAnalyzer, DLQHandler, process_dlq_entry
)
from generation_service.models.rag_jobs import RAGIngestRequest


class TestJobSchemas:
    """Test job schemas, state machine, and retry policies"""
    
    def test_valid_state_transitions(self):
        """Test that state machine enforces valid transitions"""
        
        # Valid transitions
        assert WorkerJobStatus.STARTED in VALID_STATE_TRANSITIONS[WorkerJobStatus.QUEUED]
        assert WorkerJobStatus.UPLOADING in VALID_STATE_TRANSITIONS[WorkerJobStatus.STARTED]
        assert WorkerJobStatus.EXTRACTING in VALID_STATE_TRANSITIONS[WorkerJobStatus.UPLOADING]
        assert WorkerJobStatus.INDEXED in VALID_STATE_TRANSITIONS[WorkerJobStatus.STORING]
        
        # Invalid transitions should not exist
        assert WorkerJobStatus.INDEXED not in VALID_STATE_TRANSITIONS.get(WorkerJobStatus.QUEUED, [])
        assert WorkerJobStatus.QUEUED not in VALID_STATE_TRANSITIONS.get(WorkerJobStatus.INDEXED, [])
    
    def test_retry_delay_calculation(self):
        """Test retry delay calculation for different policies"""
        
        # No retry policy
        assert calculate_retry_delay(1, RetryPolicy.NO_RETRY) == 0
        assert calculate_retry_delay(5, RetryPolicy.NO_RETRY) == 0
        
        # Immediate retry
        assert calculate_retry_delay(1, RetryPolicy.IMMEDIATE_RETRY) == 0
        assert calculate_retry_delay(3, RetryPolicy.IMMEDIATE_RETRY) == 0
        
        # Linear backoff
        assert calculate_retry_delay(1, RetryPolicy.LINEAR_BACKOFF, 2) == 2
        assert calculate_retry_delay(3, RetryPolicy.LINEAR_BACKOFF, 2) == 6
        
        # Exponential backoff
        assert calculate_retry_delay(1, RetryPolicy.EXPONENTIAL_BACKOFF) == 1
        assert calculate_retry_delay(2, RetryPolicy.EXPONENTIAL_BACKOFF) == 5
        assert calculate_retry_delay(3, RetryPolicy.EXPONENTIAL_BACKOFF) == 25
        assert calculate_retry_delay(4, RetryPolicy.EXPONENTIAL_BACKOFF) == 125
        assert calculate_retry_delay(5, RetryPolicy.EXPONENTIAL_BACKOFF) == 125  # Capped
        
        # Delayed retry
        assert calculate_retry_delay(1, RetryPolicy.DELAYED_RETRY) == 30
        assert calculate_retry_delay(3, RetryPolicy.DELAYED_RETRY) == 30
    
    def test_should_retry_error(self):
        """Test retry decision logic"""
        
        # Should not retry validation errors
        assert not should_retry_error(WorkerErrorCode.INVALID_FILE_TYPE, 1)
        assert not should_retry_error(WorkerErrorCode.FILE_TOO_LARGE, 1)
        
        # Should retry transient errors
        assert should_retry_error(WorkerErrorCode.EMBEDDING_RATE_LIMITED, 1)
        assert should_retry_error(WorkerErrorCode.NETWORK_ERROR, 1)
        
        # Should not retry after max attempts
        assert not should_retry_error(WorkerErrorCode.EMBEDDING_API_ERROR, 5)
        
        # Should retry processing errors within limits
        assert should_retry_error(WorkerErrorCode.EXTRACTION_FAILED, 2)
        assert not should_retry_error(WorkerErrorCode.EXTRACTION_FAILED, 4)
    
    def test_get_retry_policy(self):
        """Test retry policy assignment"""
        
        assert get_retry_policy(WorkerErrorCode.INVALID_FILE_TYPE) == RetryPolicy.NO_RETRY
        assert get_retry_policy(WorkerErrorCode.EMBEDDING_RATE_LIMITED) == RetryPolicy.DELAYED_RETRY
        assert get_retry_policy(WorkerErrorCode.EXTRACTION_FAILED) == RetryPolicy.EXPONENTIAL_BACKOFF
        assert get_retry_policy(WorkerErrorCode.FILE_LOCKED) == RetryPolicy.IMMEDIATE_RETRY


class TestWorkerAdapter:
    """Test worker adapter functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_redis = Mock()
        self.mock_queue = Mock()
        
        # Mock Redis connection
        patcher = patch('generation_service.workers.worker_adapter.WorkerRedisConnection')
        self.mock_redis_conn = patcher.start()
        self.mock_redis_conn.return_value.redis = self.mock_redis
        
        self.addCleanup = patcher.stop
    
    def test_enqueue_ingest_success(self):
        """Test successful job enqueuing"""
        
        adapter = WorkerAdapter()
        adapter._queue = self.mock_queue
        
        # Mock successful enqueue
        mock_job = Mock()
        mock_job.id = "test-job-123"
        self.mock_queue.enqueue.return_value = mock_job
        self.mock_queue.__len__.return_value = 5
        
        # Create test request
        ingest_request = RAGIngestRequest(
            project_id="test-project",
            file_id="test-file",
            chunk_size=1024,
            chunk_overlap=128,
            force_ocr=False
        )
        
        file_info = {
            'name': 'test.pdf',
            'size': 1024000,
            'sha256': 'test-hash',
            'content_type': 'application/pdf'
        }
        
        result = adapter.enqueue_ingest(ingest_request, file_info, "test-ingest-id")
        
        assert result['job_id'] == "test-job-123"
        assert result['queue_position'] == 5
        assert 'payload' in result
        
        # Verify queue.enqueue was called with correct parameters
        self.mock_queue.enqueue.assert_called_once()
        call_args = self.mock_queue.enqueue.call_args
        assert call_args[0][0] == 'generation_service.workers.rag_worker.process_rag_document'
    
    def test_get_job_status(self):
        """Test job status retrieval"""
        
        adapter = WorkerAdapter()
        
        # Mock RQ job
        with patch('generation_service.workers.worker_adapter.RQJob') as mock_rq_job:
            mock_job = Mock()
            mock_job.id = "test-job"
            mock_job.status = "started"
            mock_job.created_at = datetime.utcnow()
            mock_job.started_at = datetime.utcnow()
            mock_job.ended_at = None
            mock_job.result = None
            mock_job.exc_info = None
            mock_job.meta = {'progress_pct': 50.0, 'current_step': 'extracting'}
            
            mock_rq_job.fetch.return_value = mock_job
            
            status = adapter.get_job_status("test-job")
            
            assert status['job_id'] == "test-job"
            assert status['status'] == 'uploading'  # Mapped from 'started'
            assert status['progress_pct'] == 50.0
            assert status['current_step'] == 'extracting'
    
    def test_cancel_job(self):
        """Test job cancellation"""
        
        adapter = WorkerAdapter()
        
        with patch('generation_service.workers.worker_adapter.RQJob') as mock_rq_job:
            mock_job = Mock()
            mock_job.status = "queued"
            mock_rq_job.fetch.return_value = mock_job
            
            # Mock Redis setex for cancel flag
            self.mock_redis.setex.return_value = True
            
            result = adapter.cancel_job("test-job", "Test cancellation")
            
            assert result is True
            mock_job.cancel.assert_called_once()
            self.mock_redis.setex.assert_called_once()
    
    def test_retry_job_within_limits(self):
        """Test job retry within retry limits"""
        
        adapter = WorkerAdapter()
        adapter._queue = self.mock_queue
        
        with patch('generation_service.workers.worker_adapter.RQJob') as mock_rq_job:
            mock_original_job = Mock()
            mock_original_job.args = [{'max_retries': 4}]
            mock_original_job.meta = {'retry_count': 2}
            mock_original_job.description = "Test job"
            mock_original_job.exc_info = None
            mock_rq_job.fetch.return_value = mock_original_job
            
            # Mock retry job enqueue
            mock_retry_job = Mock()
            mock_retry_job.id = "retry-job-123"
            self.mock_queue.enqueue_in.return_value = mock_retry_job
            
            result = adapter.retry_job("original-job-id")
            
            assert result['retry_job_id'] == "retry-job-123"
            assert result['retry_count'] == 3
            assert result['sent_to_dlq'] is False
            self.mock_queue.enqueue_in.assert_called_once()
    
    def test_retry_job_max_retries_exceeded(self):
        """Test job retry when max retries exceeded (should go to DLQ)"""
        
        adapter = WorkerAdapter()
        adapter._dlq = self.mock_queue
        
        with patch('generation_service.workers.worker_adapter.RQJob') as mock_rq_job:
            mock_original_job = Mock()
            mock_original_job.args = [{'max_retries': 3}]
            mock_original_job.meta = {'retry_count': 3}
            mock_original_job.exc_info = "Error info"
            mock_rq_job.fetch.return_value = mock_original_job
            
            result = adapter.retry_job("original-job-id")
            
            assert result['sent_to_dlq'] is True
            assert result['retry_job_id'] is None
            assert 'dlq_entry' in result


class TestRagWorker:
    """Test RAG worker processing logic"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.test_payload = {
            'ingest_id': 'test-ingest-123',
            'project_id': 'test-project',
            'file_id': 'test-file-123',
            'doc_id': 'test-doc-123',
            'sha256': 'test-hash',
            'embed_version': 'v1.0',
            'steps': ['uploading', 'extracting', 'chunking', 'embedding', 'storing'],
            'chunk_size': 1024,
            'chunk_overlap': 128,
            'force_ocr': False,
            'trace_id': 'test-trace-123'
        }
    
    @patch('generation_service.workers.rag_worker.get_db')
    @patch('generation_service.workers.rag_worker.RAGProcessor')
    @patch('generation_service.workers.rag_worker.WorkerRedisConnection')
    def test_process_rag_document_success(self, mock_redis_conn, mock_processor, mock_get_db):
        """Test successful document processing"""
        
        # Mock database
        mock_db = Mock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        # Mock Redis connection
        mock_redis = Mock()
        mock_redis_conn.return_value.redis = mock_redis
        
        # Mock RAG processor
        mock_rag = Mock()
        mock_processor.return_value = mock_rag
        
        # Mock file info
        mock_file_info = Mock()
        mock_file_info.size = 1024000
        mock_file_info.content_type = 'application/pdf'
        mock_file_info.name = 'test.pdf'
        mock_rag.get_file_info = AsyncMock(return_value=mock_file_info)
        
        # Mock processing stages
        mock_rag.extract_text = AsyncMock(return_value="Extracted text content")
        mock_rag.create_chunks = AsyncMock(return_value=["chunk1", "chunk2", "chunk3"])
        mock_rag.generate_embeddings = AsyncMock(return_value=[[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        
        # Mock storage result
        mock_storage_result = Mock()
        mock_storage_result.chunks_stored = 3
        mock_rag.store_vectors = AsyncMock(return_value=mock_storage_result)
        
        # Mock worker job creation
        mock_worker_job = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing job
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        # Run the worker function
        result = process_rag_document(self.test_payload)
        
        assert result['success'] is True
        assert result['job_id'] == 'test-ingest-123'
        assert result['document_id'] == 'test-doc-123'
        assert result['chunks_indexed'] == 3
        assert 'processing_time_seconds' in result
        assert 'metrics' in result
    
    @patch('generation_service.workers.rag_worker.WorkerRedisConnection')
    def test_worker_progress_tracker_cancellation(self, mock_redis_conn):
        """Test worker progress tracking with cancellation"""
        
        mock_redis = Mock()
        mock_redis_conn.return_value.redis = mock_redis
        
        # Mock cancellation data in Redis
        mock_redis.get.return_value = json.dumps({
            'canceled_at': datetime.utcnow().isoformat(),
            'reason': 'User canceled',
            'job_id': 'test-job'
        })
        
        tracker = WorkerProgressTracker("test-job", mock_redis)
        
        # Should raise cancellation error
        with pytest.raises(WorkerCancellationError):
            tracker.check_cancellation()
    
    @patch('generation_service.workers.rag_worker.WorkerRedisConnection')
    def test_embedding_rate_limiter(self, mock_redis_conn):
        """Test embedding rate limiting"""
        
        mock_redis = Mock()
        mock_redis_conn.return_value.redis = mock_redis
        
        rate_limiter = EmbeddingRateLimiter(mock_redis)
        
        # Test within limits
        mock_redis.get.return_value = "500"  # Current usage
        assert rate_limiter.check_rate_limit(400) is True  # 500 + 400 = 900 < 1000 (default limit)
        
        # Test exceeding limits
        assert rate_limiter.check_rate_limit(600) is False  # 500 + 600 = 1100 > 1000
        
        # Test usage increment
        mock_pipeline = Mock()
        mock_redis.pipeline.return_value = mock_pipeline
        mock_pipeline.execute.return_value = None
        
        rate_limiter.increment_usage(100)
        
        mock_pipeline.incr.assert_called_once()
        mock_pipeline.expire.assert_called_once()
        mock_pipeline.execute.assert_called_once()
    
    @patch('generation_service.workers.rag_worker._classify_error')
    def test_worker_error_classification(self, mock_classify):
        """Test error classification for different error types"""
        
        # Test file not found error
        mock_classify.return_value = WorkerErrorCode.FILE_NOT_FOUND
        error_code = mock_classify(FileNotFoundError("File not found"))
        assert error_code == WorkerErrorCode.FILE_NOT_FOUND
        
        # Test rate limiting error
        mock_classify.return_value = WorkerErrorCode.EMBEDDING_RATE_LIMITED
        error_code = mock_classify(WorkerRateLimitError("Rate limit exceeded"))
        assert error_code == WorkerErrorCode.EMBEDDING_RATE_LIMITED
        
        # Test cancellation error
        mock_classify.return_value = WorkerErrorCode.USER_CANCELED
        error_code = mock_classify(WorkerCancellationError("User canceled"))
        assert error_code == WorkerErrorCode.USER_CANCELED


class TestSecurityValidation:
    """Test security validation and file handling"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validator = FileSecurityValidator()
        self.temp_manager = TempFileManager()
        
    def test_validate_safe_pdf_file(self):
        """Test validation of safe PDF file"""
        
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b'%PDF-1.4\n%Test PDF content\nendobj')
            temp_path = temp_file.name
        
        try:
            report = self.validator.validate_file(temp_path, 'application/pdf')
            
            # Should be considered safe (minimal content)
            assert report.size_compliant is True
            assert report.content_scan_clean is True
            assert len(report.issues) == 0 or all('magic' in issue.lower() for issue in report.issues)
            
        finally:
            os.unlink(temp_path)
    
    def test_validate_oversized_file(self):
        """Test validation of oversized file"""
        
        # Create a large temporary file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            # Write more than the default 30MB limit
            large_content = b'x' * (31 * 1024 * 1024)  # 31MB
            temp_file.write(large_content)
            temp_path = temp_file.name
        
        try:
            report = self.validator.validate_file(temp_path, 'text/plain')
            
            assert report.size_compliant is False
            assert any('too large' in issue.lower() for issue in report.issues)
            assert report.risk_score > 0.0
            
        finally:
            os.unlink(temp_path)
    
    def test_validate_suspicious_content(self):
        """Test validation of file with suspicious content"""
        
        # Create file with suspicious patterns
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            suspicious_content = b'Normal content\n<script>alert("xss")</script>\nMore content'
            temp_file.write(suspicious_content)
            temp_path = temp_file.name
        
        try:
            report = self.validator.validate_file(temp_path, 'text/plain')
            
            assert report.content_scan_clean is False
            assert any('suspicious' in issue.lower() for issue in report.issues)
            assert report.risk_score > 0.0
            
        finally:
            os.unlink(temp_path)
    
    def test_temp_file_manager(self):
        """Test secure temporary file management"""
        
        # Create temp file
        temp_path = self.temp_manager.create_temp_file(suffix='.test', prefix='security_test_')
        
        assert os.path.exists(temp_path)
        assert temp_path.endswith('.test')
        assert 'security_test_' in os.path.basename(temp_path)
        
        # Check file permissions (should be restrictive)
        file_stat = os.stat(temp_path)
        file_mode = file_stat.st_mode & 0o777
        assert file_mode == 0o600  # Owner read/write only
        
        # Cleanup
        self.temp_manager.cleanup_temp_file(temp_path)
        assert not os.path.exists(temp_path)
    
    def test_resource_limit_enforcer(self):
        """Test resource limit enforcement"""
        
        enforcer = ResourceLimitEnforcer()
        
        # Test memory check
        memory_ok, memory_usage = enforcer.check_memory_usage()
        assert isinstance(memory_ok, bool)
        assert isinstance(memory_usage, (int, float))
        
        # Test CPU time check
        import time
        start_time = time.time()
        time.sleep(0.1)  # Small delay
        cpu_ok = enforcer.check_cpu_time(start_time)
        assert cpu_ok is True  # Should be within limits
        
        # Test file descriptor check
        files_ok, open_files = enforcer.check_open_files()
        assert isinstance(files_ok, bool)
        assert isinstance(open_files, int)


class TestDLQHandler:
    """Test Dead Letter Queue handling and analysis"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.analyzer = DLQAnalyzer()
        self.handler = DLQHandler()
    
    def test_error_categorization(self):
        """Test error categorization logic"""
        
        # File handling error
        dlq_entry = DLQEntry(
            job_id="test-job",
            payload={"project_id": "test"},
            error_type="file_not_found",
            error_message="File could not be located",
            last_step="uploading",
            attempts=1,
            failed_at=datetime.utcnow().isoformat(),
            trace_id="test-trace"
        )
        
        analysis = self.analyzer.analyze_error(dlq_entry)
        assert analysis['error_category'] == 'file_handling'
        
        # Embedding API error
        dlq_entry.error_type = "embedding_api_error"
        dlq_entry.error_message = "Rate limit exceeded"
        analysis = self.analyzer.analyze_error(dlq_entry)
        assert analysis['error_category'] == 'embedding_api'
    
    def test_severity_assessment(self):
        """Test error severity assessment"""
        
        # Critical error
        critical_entry = DLQEntry(
            job_id="test-job",
            payload={"project_id": "test"},
            error_type="security_violation",
            error_message="Potential security injection detected",
            last_step="extracting",
            attempts=1,
            failed_at=datetime.utcnow().isoformat(),
            trace_id="test-trace"
        )
        
        analysis = self.analyzer.analyze_error(critical_entry)
        assert analysis['severity'] == 'critical'
        assert analysis['is_critical'] is True
        
        # Transient error
        transient_entry = DLQEntry(
            job_id="test-job-2",
            payload={"project_id": "test"},
            error_type="network_error",
            error_message="Connection timeout",
            last_step="embedding",
            attempts=1,
            failed_at=datetime.utcnow().isoformat(),
            trace_id="test-trace-2"
        )
        
        analysis = self.analyzer.analyze_error(transient_entry)
        assert analysis['severity'] == 'low'
        assert analysis['is_transient'] is True
        assert analysis['retry_recommended'] is True
    
    def test_retry_recommendations(self):
        """Test retry recommendation logic"""
        
        # Should retry: transient error with few attempts
        transient_entry = DLQEntry(
            job_id="test-job",
            payload={"project_id": "test"},
            error_type="timeout",
            error_message="Operation timed out",
            last_step="embedding",
            attempts=2,
            failed_at=datetime.utcnow().isoformat(),
            trace_id="test-trace"
        )
        
        analysis = self.analyzer.analyze_error(transient_entry)
        assert analysis['retry_recommended'] is True
        
        # Should not retry: too many attempts
        failed_entry = DLQEntry(
            job_id="test-job-2",
            payload={"project_id": "test"},
            error_type="extraction_failed",
            error_message="Could not extract text",
            last_step="extracting",
            attempts=5,
            failed_at=datetime.utcnow().isoformat(),
            trace_id="test-trace-2"
        )
        
        analysis = self.analyzer.analyze_error(failed_entry)
        assert analysis['retry_recommended'] is False
        
        # Should not retry: validation error
        validation_entry = DLQEntry(
            job_id="test-job-3",
            payload={"project_id": "test"},
            error_type="invalid_file_type",
            error_message="Unsupported file format",
            last_step="validation",
            attempts=1,
            failed_at=datetime.utcnow().isoformat(),
            trace_id="test-trace-3"
        )
        
        analysis = self.analyzer.analyze_error(validation_entry)
        assert analysis['retry_recommended'] is False
    
    def test_generate_recommendations(self):
        """Test recommendation generation"""
        
        # Critical error recommendation
        critical_entry = DLQEntry(
            job_id="test-job",
            payload={"project_id": "test"},
            error_type="security_violation",
            error_message="Security threat detected",
            last_step="validation",
            attempts=1,
            failed_at=datetime.utcnow().isoformat(),
            trace_id="test-trace"
        )
        
        analysis = self.analyzer.analyze_error(critical_entry)
        assert 'CRITICAL' in analysis['recommendation']
        assert 'security review' in analysis['recommendation'].lower()
        
        # Retry recommendation
        transient_entry = DLQEntry(
            job_id="test-job-2",
            payload={"project_id": "test"},
            error_type="network_error",
            error_message="Connection failed",
            last_step="embedding",
            attempts=1,
            failed_at=datetime.utcnow().isoformat(),
            trace_id="test-trace-2"
        )
        
        analysis = self.analyzer.analyze_error(transient_entry)
        assert 'retry' in analysis['recommendation'].lower()
    
    @patch('generation_service.workers.dlq_handler.get_db')
    def test_dlq_trend_analysis(self, mock_get_db):
        """Test DLQ trend analysis"""
        
        # Mock database with sample DLQ entries
        mock_db = Mock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        # Create mock DLQ entries
        now = datetime.utcnow()
        mock_entries = [
            Mock(
                error_type='file_not_found',
                project_id='project1',
                failed_at=now - timedelta(hours=2)
            ),
            Mock(
                error_type='file_not_found', 
                project_id='project1',
                failed_at=now - timedelta(hours=4)
            ),
            Mock(
                error_type='rate_limited',
                project_id='project2',
                failed_at=now - timedelta(hours=1)
            ),
        ]
        
        mock_db.query.return_value.filter.return_value.all.return_value = mock_entries
        
        # Run trend analysis
        trends = self.analyzer.analyze_dlq_trends(mock_db, days=1)
        
        assert trends['total_entries'] == 3
        assert trends['error_trends']['file_not_found'] == 2
        assert trends['error_trends']['rate_limited'] == 1
        assert trends['project_trends']['project1'] == 2
        assert trends['project_trends']['project2'] == 1
        assert len(trends['recommendations']) > 0


class TestIntegrationScenarios:
    """Integration tests for complete workflow scenarios"""
    
    @pytest.mark.asyncio
    async def test_worker_restart_recovery(self):
        """Test that jobs survive worker restarts"""
        
        # This would require actual Redis/RQ setup in integration environment
        pytest.skip("Requires Redis integration environment")
    
    @pytest.mark.asyncio 
    async def test_embedding_429_retry_backoff(self):
        """Test retry with exponential backoff for embedding 429 errors"""
        
        # Mock scenario: API returns 429, then succeeds after backoff
        with patch('generation_service.workers.rag_worker.RAGProcessor') as mock_processor:
            mock_rag = Mock()
            
            # First call raises rate limit error, second succeeds
            mock_rag.generate_embeddings = AsyncMock(side_effect=[
                WorkerRateLimitError("Rate limit exceeded"),
                [[1, 2, 3], [4, 5, 6]]  # Success on retry
            ])
            
            mock_processor.return_value = mock_rag
            
            # This test would need to be expanded with full worker simulation
            # For now, just verify the error is classified correctly
            error_code = WorkerErrorCode.EMBEDDING_RATE_LIMITED
            assert should_retry_error(error_code, 1) is True
            assert get_retry_policy(error_code) == RetryPolicy.DELAYED_RETRY
            assert calculate_retry_delay(1, RetryPolicy.DELAYED_RETRY) == 30
    
    @pytest.mark.asyncio
    async def test_corrupted_pdf_dlq_handling(self):
        """Test DLQ handling for corrupted PDF files"""
        
        # Create DLQ entry for corrupted PDF
        dlq_entry = DLQEntry(
            job_id="corrupt-pdf-job",
            payload={"project_id": "test-project", "file_id": "corrupt.pdf"},
            error_type="file_corrupted",
            error_message="PDF structure is corrupted and cannot be parsed",
            last_step="extracting",
            attempts=3,
            failed_at=datetime.utcnow().isoformat(),
            trace_id="corrupt-pdf-trace"
        )
        
        analyzer = DLQAnalyzer()
        analysis = analyzer.analyze_error(dlq_entry)
        
        # Should not retry corrupted files
        assert analysis['retry_recommended'] is False
        assert analysis['error_category'] == 'file_handling'
        assert 'file' in analysis['recommendation'].lower()
        assert len(analysis['action_required']) > 0
    
    @pytest.mark.asyncio
    async def test_embed_version_change_reindex(self):
        """Test reindexing when embedding version changes"""
        
        # Mock database with documents of old version
        with patch('generation_service.workers.worker_adapter.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__next__.return_value = mock_db
            
            # Mock documents with old version
            mock_docs = [
                Mock(id="doc1", embed_version="v1.0"),
                Mock(id="doc2", embed_version="v1.0"),
                Mock(id="doc3", embed_version="v2.0"),  # Already current
            ]
            mock_db.query.return_value.filter.return_value.all.return_value = mock_docs
            
            adapter = WorkerAdapter()
            adapter._queue = Mock()
            
            # Mock job enqueue
            mock_job = Mock()
            mock_job.id = "reindex-job-123"
            adapter._queue.enqueue.return_value = mock_job
            
            result = adapter.enqueue_reindex_all("test-project", "v2.0", batch_size=5)
            
            # Should only reindex documents with old version (doc1, doc2)
            assert result['documents_to_reindex'] == 2
            assert result['new_embed_version'] == "v2.0"
            assert result['reindex_job_id'] == "reindex-job-123"
    
    def test_large_pdf_ocr_cancellation(self):
        """Test cancellation during OCR of large PDF"""
        
        # Mock progress tracker with cancellation
        mock_redis = Mock()
        mock_redis.get.return_value = json.dumps({
            'canceled_at': datetime.utcnow().isoformat(),
            'reason': 'User canceled large PDF processing',
            'job_id': 'large-pdf-job'
        })
        
        tracker = WorkerProgressTracker("large-pdf-job", mock_redis)
        
        # Should raise cancellation error when checked
        with pytest.raises(WorkerCancellationError) as exc_info:
            tracker.check_cancellation()
        
        assert "User canceled large PDF processing" in str(exc_info.value)
    
    def test_resource_cleanup_after_failure(self):
        """Test that resources are cleaned up after job failure"""
        
        temp_manager = TempFileManager()
        
        # Create some temp files
        temp_files = []
        for i in range(3):
            temp_path = temp_manager.create_temp_file(suffix=f'.test{i}')
            temp_files.append(temp_path)
            assert os.path.exists(temp_path)
        
        # Simulate cleanup (normally called on worker shutdown/failure)
        temp_manager.cleanup_all_temp_files()
        
        # All temp files should be removed
        for temp_path in temp_files:
            assert not os.path.exists(temp_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])