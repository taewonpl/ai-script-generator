# SSE Generation Service Implementation

## Overview

The SSE (Server-Sent Events) Generation Service provides real-time script generation with 5 types of events. It implements a complete state machine (queued → streaming → completed/failed/canceled) and integrates with the ChromaDB Episode API for automatic episode creation.

## Features

✅ **5 Event Types**: progress, preview, completed, failed, heartbeat  
✅ **State Machine**: queued → streaming → completed|failed|canceled  
✅ **Idempotent Cancellation**: DELETE requests are safe to repeat  
✅ **ChromaDB Integration**: Automatic episode creation with auto-assigned numbers  
✅ **Real-time Progress**: Live updates with estimated completion times  
✅ **Connection Management**: Automatic cleanup and heartbeat monitoring  

## API Endpoints

### POST /api/v1/generations

Start a new script generation job.

**Request Body:**
```json
{
  "projectId": "project-123",
  "episodeNumber": 1,
  "title": "Episode Title",
  "description": "Script description/prompt",
  "scriptType": "drama",
  "model": "gpt-4",
  "temperature": 0.7,
  "lengthTarget": 1000
}
```

**Response (201 Created):**
```json
{
  "jobId": "job_abc123def456",
  "status": "queued",
  "sseUrl": "http://localhost:8000/api/v1/generations/job_abc123def456/events",
  "cancelUrl": "http://localhost:8000/api/v1/generations/job_abc123def456",
  "projectId": "project-123",
  "episodeNumber": 1,
  "title": "Episode Title",
  "estimatedDuration": 120
}
```

### GET /api/v1/generations/{jobId}/events

**SSE Stream Endpoint** - Returns Server-Sent Events stream.

**Headers:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

**Event Types:**

#### 1. Progress Event
```
event: progress
data: {"type":"progress","jobId":"job_123","value":25,"currentStep":"프롬프트 분석 중","estimatedTime":120}
```

#### 2. Preview Event
```
event: preview
data: {"type":"preview","jobId":"job_123","markdown":"# My Drama - Ep. 1\\n\\nFADE IN:","isPartial":true,"wordCount":50,"estimatedTokens":200}
```

#### 3. Completed Event
```
event: completed
data: {"type":"completed","jobId":"job_123","result":{"markdown":"완성된 대본...","tokens":1250,"wordCount":312,"modelUsed":"gpt-4","episodeId":"episode-uuid","savedToEpisode":true}}
```

#### 4. Failed Event
```
event: failed
data: {"type":"failed","jobId":"job_123","error":{"code":"TOKEN_LIMIT_EXCEEDED","message":"토큰 한도 초과","retryable":false}}
```

#### 5. Heartbeat Event
```
event: heartbeat
data: {"type":"heartbeat","timestamp":"2025-08-22T10:30:25Z","jobId":"job_123"}
```

### DELETE /api/v1/generations/{jobId}

Cancel a generation job (idempotent operation).

**Response:** 204 No Content (always, even if job doesn't exist)

### GET /api/v1/generations/{jobId}

Get current job status and details.

**Response:**
```json
{
  "jobId": "job_123",
  "status": "streaming",
  "progress": 45,
  "currentStep": "대화 생성 중",
  "projectId": "project-123",
  "episodeNumber": 1,
  "title": "Episode Title",
  "wordCount": 150,
  "tokens": 600,
  "createdAt": "2025-08-22T10:00:00Z",
  "startedAt": "2025-08-22T10:00:05Z",
  "completedAt": null,
  "estimatedRemainingTime": 75,
  "errorCode": null,
  "errorMessage": null,
  "episodeId": null,
  "savedToEpisode": false
}
```

### GET /api/v1/generations/active

List all currently active generation jobs.

### GET /api/v1/generations/_stats

Get service statistics including job counts and connection metrics.

## State Machine

```
┌─────────┐    start_job_streaming()    ┌───────────┐
│ QUEUED  │──────────────────────────→  │ STREAMING │
└─────────┘                             └───────────┘
     │                                        │
     │                                        ├─── complete_job() ──→ ┌───────────┐
     │                                        │                       │ COMPLETED │
     │                                        │                       └───────────┘
     │                                        │
     │                                        ├─── fail_job() ───────→ ┌─────────┐
     │                                        │                       │ FAILED  │
     │                                        │                       └─────────┘
     │                                        │
     └─── cancel_job() ──────────────────────┼─── cancel_job() ─────→ ┌──────────┐
                                              │                       │ CANCELED │
                                              │                       └──────────┘
```

## Job Manager

The `JobManager` class handles:

- **Job Creation**: Unique job IDs and initial state
- **Progress Tracking**: Real-time updates and progress calculation
- **SSE Event Generation**: Streaming events to connected clients
- **Connection Management**: Tracking active SSE connections
- **Background Tasks**: Heartbeat and cleanup processes
- **Concurrency Safety**: Thread-safe operations

### Key Features:

1. **Automatic Cleanup**: Removes completed jobs after 1 hour
2. **Heartbeat Monitoring**: Sends heartbeat events every 30 seconds
3. **Connection Counting**: Tracks active SSE connections per job
4. **Estimated Times**: Calculates remaining time based on progress
5. **Idempotent Operations**: Safe to call cancellation multiple times

## ChromaDB Integration

When a generation completes successfully, the system automatically:

1. **Creates Episode**: Calls ChromaDB Episode API with auto-number assignment
2. **Updates Job**: Sets `episodeId` and `savedToEpisode` flag
3. **Handles Errors**: Gracefully handles episode creation failures

**Episode Creation Request:**
```json
{
  "title": "Generated Episode Title",
  "script": {
    "markdown": "# Complete script content...",
    "tokens": 1250
  },
  "promptSnapshot": "Original generation prompt"
}
```

**Episode Response:**
```json
{
  "id": "episode-uuid",
  "projectId": "project-123",
  "number": 1,  // Auto-assigned
  "title": "Generated Episode Title",
  "createdAt": "2025-08-22T10:30:00Z"
}
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| `JOB_NOT_FOUND` | Job ID doesn't exist | No |
| `JOB_CANCELED` | Job was canceled | No |
| `GENERATION_ERROR` | General generation failure | Yes |
| `TOKEN_LIMIT_EXCEEDED` | AI model token limit reached | No |
| `MODEL_UNAVAILABLE` | Requested AI model not available | Yes |
| `TIMEOUT_ERROR` | Generation took too long | Yes |
| `SSE_ERROR` | SSE stream connection issue | Yes |

## Frontend Integration

### JavaScript EventSource

```javascript
const eventSource = new EventSource('/api/v1/generations/job_123/events');

eventSource.addEventListener('progress', (event) => {
    const data = JSON.parse(event.data);
    updateProgress(data.value, data.currentStep);
});

eventSource.addEventListener('preview', (event) => {
    const data = JSON.parse(event.data);
    updateContent(data.markdown);
});

eventSource.addEventListener('completed', (event) => {
    const data = JSON.parse(event.data);
    showFinalResult(data.result);
    eventSource.close();
});

eventSource.addEventListener('failed', (event) => {
    const data = JSON.parse(event.data);
    showError(data.error);
    eventSource.close();
});
```

### React Hook Example

```typescript
import { useEffect, useState } from 'react';

interface GenerationState {
  status: string;
  progress: number;
  content: string;
  error: string | null;
}

export function useGeneration(jobId: string) {
  const [state, setState] = useState<GenerationState>({
    status: 'connecting',
    progress: 0,
    content: '',
    error: null
  });

  useEffect(() => {
    const eventSource = new EventSource(`/api/v1/generations/${jobId}/events`);
    
    eventSource.addEventListener('progress', (event) => {
      const data = JSON.parse(event.data);
      setState(prev => ({ ...prev, progress: data.value }));
    });
    
    eventSource.addEventListener('completed', (event) => {
      const data = JSON.parse(event.data);
      setState(prev => ({ 
        ...prev, 
        status: 'completed', 
        content: data.result.markdown 
      }));
    });
    
    return () => eventSource.close();
  }, [jobId]);

  return state;
}
```

## Testing

### Integration Test

```bash
cd services/generation-service
python test_sse_integration.py
```

### Web Interface Test

Open `sse_test.html` in a browser and test the complete SSE flow with a visual interface.

### Manual Testing with curl

```bash
# Start generation
curl -X POST http://localhost:8000/api/v1/generations \
  -H "Content-Type: application/json" \
  -d '{
    "projectId": "test-project",
    "title": "Test Script",
    "description": "Test description",
    "scriptType": "drama"
  }'

# Connect to SSE stream
curl -N http://localhost:8000/api/v1/generations/job_123/events

# Cancel generation
curl -X DELETE http://localhost:8000/api/v1/generations/job_123
```

## Performance Considerations

- **Memory Usage**: Jobs are cleaned up automatically after completion
- **Connection Limits**: Each job tracks active SSE connections
- **Background Tasks**: Minimal overhead for heartbeat and cleanup
- **Event Frequency**: Progress updates every 500ms, heartbeat every 30s
- **Graceful Shutdown**: Proper cleanup of resources and connections

## Security Considerations

- **CORS Headers**: Configured for cross-origin SSE connections
- **Job Isolation**: Each job has unique ID and isolated state
- **Input Validation**: All request parameters are validated
- **Error Handling**: No sensitive information in error messages
- **Resource Limits**: Automatic cleanup prevents memory leaks

## Future Enhancements

- **Authentication**: Add JWT-based job ownership verification
- **Rate Limiting**: Implement per-user generation limits
- **Webhooks**: Optional HTTP callbacks for job completion
- **Resume Capability**: Support for pausing/resuming long generations
- **Batch Operations**: Multiple script generation in parallel
- **Advanced Routing**: Custom workflow paths for different script types