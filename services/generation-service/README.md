# AI Script Generator v3.0 - Generation Service

FastAPI-based microservice for AI-powered script generation with Core Module integration.

## Overview

The Generation Service is responsible for creating scripts using AI models based on project requirements and user inputs. It provides RESTful APIs for script generation, status tracking, and template management. **Fully integrated with the shared Core Module** for consistent DTOs, exception handling, and utilities across the microservices architecture.

## Features

- **Multi-AI Provider Support**: OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet, Local Llama models
- **Core Module Integration**: Shared schemas, exceptions, and utilities for consistency
- **Script Generation**: AI-powered script creation with multiple model support
- **Real-time Status**: Track generation progress and results
- **Template System**: Pre-defined script templates for different genres
- **Async Processing**: Non-blocking generation with status updates
- **Database Integration**: PostgreSQL for persistent storage
- **Health Monitoring**: Built-in health checks and metrics
- **Graceful Fallback**: Works with or without Core Module availability

## Tech Stack

- **Framework**: FastAPI 0.104+
- **Core Integration**: AI Script Core Module (shared DTOs, exceptions, utilities)
- **Database**: PostgreSQL with SQLAlchemy
- **AI Integration**: OpenAI, Anthropic, Local APIs with provider factory pattern
- **Async**: Python asyncio with async/await
- **Validation**: Pydantic v2 models with Core schema integration
- **Documentation**: Auto-generated OpenAPI/Swagger
- **Containerization**: Docker with multi-stage builds

## Core Module Integration

The Generation Service leverages the shared Core Module for:

### 📄 **Shared Schemas**
- `GenerationRequestDTO` - Standardized generation requests
- `GenerationResponseDTO` - Consistent response format
- `AIModelConfigDTO` - AI model configurations
- `ProjectDTO`, `EpisodeDTO` - Project management integration

### ⚠️ **Exception Handling**
- `BaseServiceException` - Standardized error handling
- `GenerationServiceError` - Service-specific errors
- `ValidationException` - Input validation errors
- `NotFoundError` - Resource not found errors

### 🛠️ **Utilities**
- `get_service_logger()` - Consistent logging
- `generate_uuid()`, `generate_prefixed_id()` - ID generation
- `utc_now()` - Timezone-aware timestamps
- `safe_json_loads()`, `safe_json_dumps()` - Safe JSON handling

## Installation

### Prerequisites
- Python 3.9+ (Python 3.10+ recommended for full Core Module support)
- PostgreSQL 12+
- AI API Keys (OpenAI, Anthropic - optional)

1. **Clone and Navigate**
   ```bash
   cd services/generation-service
   ```

2. **Install Dependencies**
   ```bash
   # Install Core Module first (recommended)
   pip install -e ../../shared/core
   
   # Install Generation Service dependencies
   pip install -r requirements.txt
   # or with development dependencies
   pip install -e ".[dev,ai]"
   ```

3. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Database Setup**
   ```bash
   # Ensure PostgreSQL is running
   createdb generation_db
   ```

### Core Module Compatibility

- **Python 3.10+**: Full Core Module integration with all features
- **Python 3.9**: Graceful fallback mode with reduced functionality
- **Without Core Module**: Standalone mode with basic features

The service automatically detects Core Module availability and adapts accordingly.

## Docker Deployment

### Quick Start with Docker

```bash
# Build and run with Docker Compose (Development)
docker compose -f docker/docker-compose.yml up --build

# Production deployment  
docker compose -f docker/docker-compose.prod.yml up --build
```

### Manual Docker Build

```bash
# Production build
docker build -t generation-service:latest .

# Development build with hot reload
docker build -t generation-service:dev --target development .

# Run container
docker run -d \
  --name generation-service \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -e DATA_ROOT_PATH=/app/data \
  -e CHROMA_PERSIST_DIRECTORY=/app/data/chroma \
  generation-service:latest
```

### Multi-stage Build Features

- **Builder Stage**: Optimized dependency installation
- **Production Stage**: Minimal runtime image with security
- **Development Stage**: Hot reload support for development

### Data Paths

All data is unified under `/app/data/`:
- ChromaDB: `/app/data/chroma`
- Vector Data: `/app/data/vectors` 
- Logs: `/app/data/logs`
- Cache: `/app/data/cache`

## Configuration

Key environment variables:

- `PORT`: Service port (default: 8000)
- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: OpenAI API key for GPT models
- `ANTHROPIC_API_KEY`: Anthropic API key for Claude models
- `PROJECT_SERVICE_URL`: Project service endpoint

## Running the Service

### Development
```bash
python -m uvicorn generation_service.main:app --reload --port 8000
```

### Production
```bash
python -m uvicorn generation_service.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Check
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health with dependencies

### Generation
- `POST /api/v1/generate` - Create new generation request
- `GET /api/v1/generate/{id}` - Get generation status
- `DELETE /api/v1/generate/{id}` - Cancel generation

### Templates
- `GET /api/v1/templates` - List available templates

### Documentation
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc documentation

## Usage Example

```python
import httpx

# Create generation request
async with httpx.AsyncClient() as client:
    response = await client.post("http://localhost:8000/api/v1/generate", json={
        "project_id": "proj_123",
        "script_type": "drama",
        "title": "My Script",
        "description": "A compelling drama about...",
        "length_target": 2000
    })
    
    generation = response.json()
    generation_id = generation["generation_id"]
    
    # Check status
    status_response = await client.get(f"http://localhost:8000/api/v1/generate/{generation_id}")
    print(status_response.json())
```

## Development

### Code Quality
```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
flake8 src/ tests/
mypy src/

# Test
pytest
```

### Project Structure
```
src/generation_service/
├── __init__.py
├── main.py                 # FastAPI application
├── config.py              # Configuration settings
├── api/                    # API endpoints
│   ├── health.py          # Health check routes
│   └── generate.py        # Generation routes
├── models/                 # Pydantic models
│   └── generation.py      # Generation request/response models
├── database/               # Database components
│   └── connection.py      # Database connection management
└── services/               # Business logic
    └── generation_service.py # Core generation logic
```

## Integration

This service integrates with:
- **Project Service**: Validates projects and episodes
- **Core Module**: Shared DTOs and utilities
- **AI Services**: OpenAI, Anthropic APIs for generation

## Monitoring

The service provides:
- Health check endpoints for container orchestration
- Detailed dependency status reporting
- Generation metrics and statistics
- Error tracking and logging

## License

Part of AI Script Generator v3.0 project.