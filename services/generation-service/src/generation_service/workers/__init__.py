"""
Durable RAG Worker System

A production-grade worker system for RAG document processing with:
- Redis Queue (RQ) based job processing
- Automatic retry with exponential backoff
- Dead Letter Queue (DLQ) for failed jobs
- Job cancellation and rollback
- Comprehensive monitoring and alerting
- Security validation and resource limits
- Multi-tab conflict resolution
- Embedding version management

## Quick Start

1. Install dependencies:
   ```bash
   pip install redis rq python-magic psutil cryptography
   ```

2. Set environment variables:
   ```bash
   export USE_DURABLE_WORKER=true
   export REDIS_URL=redis://localhost:6379/5
   export RAG_EMBED_VERSION=v1.0
   ```

3. Start RQ workers:
   ```bash
   rq worker rag_processing --url redis://localhost:6379/5
   ```

4. Monitor with RQ Dashboard:
   ```bash
   rq-dashboard --redis-url redis://localhost:6379/5
   ```

## Configuration

Environment variables for production deployment:

### Core Configuration
- `USE_DURABLE_WORKER`: Enable durable worker system (default: false)
- `REDIS_URL`: Redis connection URL (default: redis://localhost:6379/5)
- `RAG_EMBED_VERSION`: Current embedding model version (default: v1.0)

### Worker Configuration
- `RAG_WORKER_TIMEOUT`: Job timeout in seconds (default: 3600)
- `RAG_MAX_RETRIES`: Maximum retry attempts (default: 4)
- `RAG_EMBEDDING_BATCH_SIZE`: Embedding batch size (default: 32)
- `RAG_EMBEDDING_RATE_LIMIT`: Embeddings per minute (default: 1000)
- `RAG_EMBEDDING_CONCURRENCY`: Concurrent embedding requests (default: 3)

### Security Configuration
- `RAG_MAX_FILE_SIZE_MB`: Maximum file size (default: 30)
- `RAG_MAX_PAGES_PDF`: Maximum PDF pages (default: 500)
- `RAG_ALLOWED_FILE_TYPES`: Allowed extensions (default: pdf,txt,md,doc,docx)
- `REDIS_PASSWORD`: Redis authentication password
- `REDIS_SSL`: Enable Redis SSL/TLS (default: false)
- `RAG_REDIS_ENCRYPTION_KEY`: Key for Redis data encryption

### Resource Limits
- `RAG_MAX_MEMORY_MB`: Memory limit per worker (default: 512)
- `RAG_MAX_CPU_TIME`: CPU time limit per job (default: 300)
- `RAG_MAX_OPEN_FILES`: Open file descriptor limit (default: 50)
- `RAG_TEMP_FILE_TTL_HOURS`: Temp file cleanup TTL (default: 2)

### DLQ Configuration
- `DLQ_RETENTION_DAYS`: DLQ entry retention (default: 30)
- `DLQ_AUTO_RESOLVE_AFTER_DAYS`: Auto-resolve old entries (default: 7)
- `DLQ_ALERT_THRESHOLD`: Alert when DLQ exceeds size (default: 10)
- `ENABLE_DLQ_ALERTS`: Enable DLQ alerting (default: true)

## Production Deployment

### Redis Security Setup
```bash
# Enable SSL/TLS
export REDIS_SSL=true
export REDIS_SSL_CERT_REQS=required

# Enable authentication
export REDIS_PASSWORD=your-secure-password
export REDIS_ACL_USERNAME=rag_worker

# Enable data encryption
export RAG_REDIS_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### Worker Process Management
```bash
# Use supervisord or systemd for production
[program:rag-worker]
command=/path/to/venv/bin/rq worker rag_processing --url redis://localhost:6379/5
directory=/path/to/app
autostart=true
autorestart=true
user=rag-worker
numprocs=4
process_name=rag-worker-%(process_num)02d
```

### Monitoring Setup
```yaml
# docker-compose.yml for monitoring stack
version: '3.8'
services:
  rq-dashboard:
    image: eoranged/rq-dashboard:latest
    ports:
      - "9181:9181"
    environment:
      - RQ_DASHBOARD_REDIS_URL=redis://redis:6379/5
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

## API Usage

### Basic Document Ingestion
```python
import requests

# Ingest document
response = requests.post('/rag/ingest', json={
    'project_id': 'my-project',
    'file_id': 'document-123',
    'chunk_size': 1024,
    'chunk_overlap': 128
}, headers={
    'X-Ingest-Id': 'unique-ingest-id',
    'X-Priority': 'high'  # high|normal|low
})

job_info = response.json()
job_id = job_info['job_id']

# Monitor job progress
response = requests.get(f'/rag/jobs/{job_id}')
status = response.json()
print(f"Progress: {status['progress_pct']}%")
```

### Job Management
```python
# Cancel running job
requests.post(f'/rag/jobs/{job_id}/cancel', params={
    'reason': 'User requested cancellation'
})

# Retry failed job
requests.post(f'/rag/jobs/{job_id}/retry', params={
    'max_retries': 3,
    'delay_seconds': 60
})

# Reindex all documents
requests.post('/rag/reindex-all', json={
    'project_id': 'my-project',
    'new_embed_version': 'v2.0',
    'batch_size': 10
})
```

### Monitoring and Health
```python
# Get queue statistics
response = requests.get('/rag/queue/stats')
stats = response.json()
print(f"Queue length: {stats['queue_length']}")
print(f"Active workers: {stats['active_workers']}")
print(f"Success rate: {stats['success_rate_24h']}%")

# Get DLQ entries
response = requests.get('/rag/dlq', params={
    'limit': 50,
    'error_type_filter': 'embedding_api_error'
})
dlq_entries = response.json()
```

## Error Handling and Recovery

### Automatic Retry Policies
- **No Retry**: Validation errors (invalid file type, too large)
- **Immediate Retry**: Transient errors (file locked)
- **Linear Backoff**: Storage errors (1s, 2s, 3s, 4s)
- **Exponential Backoff**: Processing errors (1s, 5s, 25s, 125s)
- **Delayed Retry**: Rate limiting (30s fixed delay)

### Dead Letter Queue (DLQ)
Failed jobs are automatically sent to DLQ after exceeding retry limits:
- **Error Analysis**: Automatic categorization and severity assessment
- **Trend Detection**: Pattern recognition across failures
- **Alert Generation**: Notifications for critical errors or spikes
- **Manual Resolution**: Tools for investigating and resolving issues

### Job Cancellation
Jobs can be canceled at any processing stage:
- **Graceful Shutdown**: Workers check cancellation flags regularly
- **Resource Cleanup**: Automatic cleanup of temp files and connections
- **Rollback Support**: 60-second rollback window for completed operations

## Security Features

### File Validation
- **MIME Type Verification**: libmagic-based content detection
- **Size Limits**: Configurable maximum file sizes
- **Content Scanning**: Suspicious pattern detection
- **PDF Security**: JavaScript and action detection

### Redis Security
- **SSL/TLS Encryption**: End-to-end encrypted connections
- **Authentication**: Password and ACL-based access control
- **Data Encryption**: Optional Fernet encryption for sensitive data
- **Connection Pooling**: Secure connection management

### Resource Protection
- **Memory Limits**: Per-worker memory usage monitoring
- **CPU Time Limits**: Maximum processing time enforcement  
- **File Descriptor Limits**: Open file handle monitoring
- **Temp File Cleanup**: Secure deletion with overwrite

## Troubleshooting

### Common Issues

1. **Jobs stuck in queue**
   ```bash
   # Check worker status
   rq info --url redis://localhost:6379/5
   
   # Start more workers
   rq worker rag_processing --url redis://localhost:6379/5
   ```

2. **High memory usage**
   ```bash
   # Check resource limits
   export RAG_MAX_MEMORY_MB=256
   export RAG_EMBEDDING_BATCH_SIZE=16
   ```

3. **Rate limiting issues**
   ```bash
   # Adjust rate limits
   export RAG_EMBEDDING_RATE_LIMIT=500
   export RAG_EMBEDDING_CONCURRENCY=2
   ```

4. **DLQ accumulation**
   ```bash
   # Check DLQ status
   curl http://localhost:8002/rag/dlq | jq
   
   # Clean up old entries
   python -c "from workers.dlq_handler import cleanup_dlq_entries; cleanup_dlq_entries()"
   ```

### Health Checks
```python
# Worker system health check
def check_rag_worker_health():
    try:
        response = requests.get('/rag/queue/stats', timeout=5)
        stats = response.json()
        
        if stats['queue_health'] != 'healthy':
            return False, f"Queue unhealthy: {stats['queue_health']}"
        
        if stats['active_workers'] == 0:
            return False, "No active workers"
            
        return True, "Workers healthy"
        
    except Exception as e:
        return False, f"Health check failed: {e}"
```

For detailed implementation examples, see the test files and API documentation.
"""

from .worker_adapter import (
    WorkerAdapter, 
    get_worker_adapter, 
    should_use_durable_worker,
    WorkerJobPayload,
    DLQEntry
)

from .job_schemas import (
    WorkerJobStatus,
    WorkerErrorCode, 
    WorkerJobDB,
    DLQEntryDB,
    JobStatusResponse,
    ReindexRequest,
    ReindexResponse,
    QueueStatsResponse
)

from .rag_worker import (
    process_rag_document,
    reindex_all_documents
)

from .security import (
    validate_file_security,
    create_secure_temp_file,
    cleanup_temp_file,
    check_resource_limits
)

from .dlq_handler import (
    process_dlq_entry,
    cleanup_dlq_entries,
    generate_dlq_report
)

__all__ = [
    # Worker adapter
    'WorkerAdapter',
    'get_worker_adapter', 
    'should_use_durable_worker',
    'WorkerJobPayload',
    'DLQEntry',
    
    # Job schemas
    'WorkerJobStatus',
    'WorkerErrorCode',
    'WorkerJobDB', 
    'DLQEntryDB',
    'JobStatusResponse',
    'ReindexRequest',
    'ReindexResponse', 
    'QueueStatsResponse',
    
    # Worker functions
    'process_rag_document',
    'reindex_all_documents',
    
    # Security functions
    'validate_file_security',
    'create_secure_temp_file',
    'cleanup_temp_file',
    'check_resource_limits',
    
    # DLQ functions
    'process_dlq_entry',
    'cleanup_dlq_entries', 
    'generate_dlq_report',
]