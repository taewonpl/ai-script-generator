# ChromaDB Episodes API Documentation

## Overview

The ChromaDB Episodes API provides automatic episode number assignment and script storage using ChromaDB as the backend. This implementation replaces the previous SQLite-based approach with a vector database solution that enables better content search and retrieval.

## Features

- ✅ **Automatic Episode Numbering**: Episodes are assigned sequential numbers (1, 2, 3...) automatically by the server
- ✅ **Concurrency Safe**: Uses threading locks and retry logic to handle concurrent episode creation
- ✅ **Project Tracking**: Maintains episode counts and metadata per project
- ✅ **Script Storage**: Stores full episode scripts with token counting
- ✅ **Vector Search Ready**: ChromaDB backend enables future semantic search capabilities

## ChromaDB Schema

### Episodes Collection
```json
{
  "id": "episode_id (UUID)",
  "metadata": {
    "project_id": "string",
    "number": "number (1, 2, 3...)",
    "title": "string ('{ProjectName} - Ep. {N}' if auto-generated)",
    "created_at": "timestamp",
    "tokens": "number",
    "prompt_snapshot": "string"
  },
  "document": "script_markdown (full episode text)"
}
```

### Projects Collection
```json
{
  "id": "project_id",
  "metadata": {
    "name": "string",
    "episode_count": "number",
    "created_at": "timestamp",
    "updated_at": "timestamp"
  },
  "document": "Project: {project_name}"
}
```

## API Endpoints

### POST /projects/{project_id}/episodes

Create a new episode with automatic number assignment.

**Request Body:**
```json
{
  "title": "Episode Title (optional)",
  "script": {
    "markdown": "# Episode Script\n\nScript content...",
    "tokens": 150
  },
  "promptSnapshot": "Prompt used for generation"
}
```

**Response:**
```json
{
  "success": true,
  "message": "에피소드 1가 성공적으로 생성되었습니다.",
  "data": {
    "id": "episode-uuid",
    "projectId": "project-123",
    "number": 1,
    "title": "ProjectName - Ep. 1",
    "script": {
      "markdown": "# Episode Script...",
      "tokens": 150
    },
    "promptSnapshot": "Prompt used...",
    "createdAt": "2024-01-01T00:00:00Z"
  }
}
```

### GET /projects/{project_id}/episodes

Get all episodes for a project, sorted by episode number.

**Response:**
```json
{
  "success": true,
  "message": "프로젝트 project-123의 에피소드 3개를 조회했습니다.",
  "data": [
    {
      "id": "episode-uuid-1",
      "projectId": "project-123",
      "number": 1,
      "title": "Episode 1",
      "script": { /* script data */ },
      "promptSnapshot": "...",
      "createdAt": "2024-01-01T00:00:00Z"
    },
    // ... more episodes
  ]
}
```

### GET /projects/{project_id}/episodes/{episode_id}

Get a single episode by ID.

### PUT /projects/{project_id}/episodes/{episode_id}/script

Update episode script content.

**Request Body:**
```json
{
  "script": {
    "markdown": "Updated script content",
    "tokens": 200
  },
  "promptSnapshot": "Updated prompt (optional)"
}
```

### DELETE /projects/{project_id}/episodes/{episode_id}

Delete an episode.

### GET /projects/{project_id}/episodes/_next-number

Get the next episode number for a project.

**Response:**
```json
{
  "success": true,
  "message": "프로젝트 project-123의 다음 에피소드 번호입니다.",
  "data": {
    "next_number": 4
  }
}
```

### POST /projects/{project_id}/episodes/_register-project

Register a project for episode tracking.

**Query Parameters:**
- `project_name`: Name of the project

### GET /projects/{project_id}/episodes/_stats

Get service statistics.

## Automatic Number Assignment Logic

1. **Thread-Safe Assignment**: Uses threading locks to prevent race conditions
2. **Retry Logic**: Retries up to 3 times with exponential backoff for concurrency handling
3. **MAX + 1 Calculation**: Finds the maximum existing episode number and adds 1
4. **First Episode**: Projects with no episodes start at number 1

## Title Generation

If no title is provided, episodes are automatically titled as:
```
{ProjectName} - Ep. {EpisodeNumber}
```

Example: "My Drama - Ep. 1", "My Drama - Ep. 2"

## Token Counting

- Automatic token estimation using `tiktoken` library (GPT-4 encoding)
- Fallback to character-based estimation (1 token ≈ 4 characters)
- Tokens are updated when script content is modified

## Installation & Setup

1. **Install Dependencies:**
```bash
pip install chromadb tiktoken numpy
```

2. **Environment Variables:**
```bash
export CHROMA_DB_PATH="./data/chroma"  # Optional, defaults to ./data/chroma
```

3. **Start Service:**
```bash
cd services/project-service
PYTHONPATH=src python3 -m uvicorn project_service.main:app --reload --port 8001
```

## Testing

Run the integration tests:

```bash
# Test ChromaDB service directly
python3 test_chroma_episodes.py

# Test API endpoints (requires running service)
python3 test_api_integration.py
```

## Migration from SQLite

The new ChromaDB implementation can run alongside the existing SQLite-based episodes service. To migrate:

1. The main.py already imports the new `episodes_chroma` router
2. Existing data can be migrated by reading from SQLite and creating episodes via the new API
3. The old `episodes.py` router can be removed once migration is complete

## Performance Considerations

- **ChromaDB Storage**: Persistent storage in `./data/chroma` directory
- **Memory Usage**: ChromaDB loads collections into memory for fast access
- **Concurrency**: Thread-safe operations with minimal locking overhead
- **Scalability**: ChromaDB handles thousands of episodes efficiently

## Future Enhancements

- **Semantic Search**: Use ChromaDB's vector search for content-based episode discovery
- **Script Similarity**: Find similar episodes based on content
- **Advanced Metadata**: Add genre, character, and plot point metadata
- **Bulk Operations**: Batch episode creation and updates