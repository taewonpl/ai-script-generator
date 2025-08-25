# SQLite + ChromaDB Storage Configuration

## Overview

Generation Service uses a simplified storage architecture with SQLite for structured data and ChromaDB for vector storage.

## Storage Architecture

### SQLite Database
- **Purpose**: Stores structured data, configurations, and metadata
- **Location**: Auto-configured based on environment
- **Driver**: `sqlite+aiosqlite` for async support

### ChromaDB Vector Store
- **Purpose**: Vector embeddings and semantic search
- **Location**: Configurable via `CHROMA_PERSIST_DIRECTORY`
- **Collection**: Configurable via `CHROMA_COLLECTION_NAME`

## Environment-Specific Configuration

| Environment | SQLite Path | ChromaDB Path | Description |
|-------------|-------------|---------------|-------------|
| **Development** | `./data/app.db` | `./data/chroma` | Local files for development |
| **Test** | `:memory:` | `:memory:` | In-memory for testing |
| **Production** | `/app/data/app.db` | `/app/data/chroma` | Persistent data in containers |

## Configuration Variables

### Required Environment Variables
```bash
# Data paths
DATA_ROOT_PATH=/app/data
CHROMA_PERSIST_DIRECTORY=/app/data/chroma
CHROMA_COLLECTION_NAME=script_knowledge

# Optional database path override
SQLITE_DATABASE_PATH=/app/data/app.db
```

### Auto-Configuration Logic

The service automatically determines storage paths based on environment:

1. **Development Environment**:
   - SQLite: `${DATA_ROOT_PATH}/app.db`
   - ChromaDB: `${DATA_ROOT_PATH}/chroma`

2. **Test Environment**:
   - SQLite: In-memory (`:memory:`)
   - ChromaDB: Temporary directory

3. **Production Environment**:
   - Must explicitly set `DATA_ROOT_PATH`
   - Persistent volumes recommended

## Best Practices

### Development Setup
```bash
# .env file
DATA_ROOT_PATH=./data
CHROMA_PERSIST_DIRECTORY=./data/chroma
CHROMA_COLLECTION_NAME=script_knowledge
```

### Production Setup
```bash
# Production environment
DATA_ROOT_PATH=/app/data
CHROMA_PERSIST_DIRECTORY=/app/data/chroma
CHROMA_COLLECTION_NAME=script_knowledge
```

### Docker Volume Configuration
```yaml
volumes:
  - generation-data:/app/data
```

## Migration Notes

- No complex database migrations needed
- SQLite schema handled by SQLAlchemy
- ChromaDB collections created automatically
- Simple backup: copy data directory
- Restore: place data directory and restart service

## Benefits

1. **Simplicity**: No external database dependencies
2. **Performance**: Local file access for both storage types
3. **Development**: Zero-configuration local setup
4. **Deployment**: Self-contained with data volumes
5. **Backup**: Simple file-based backup strategy