# AI Script Generator v3.0 - Docker Deployment Guide

## 🚀 Quick Start

### Development Environment
```bash
# Clone and setup
git clone <repository-url>
cd ai-script-generator-v3

# Copy environment file
cp .env.production .env
# Edit .env with your API keys and configurations

# Start development stack
docker-compose up --build
```

### Production Environment
```bash
# Use production configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## 📋 Services Overview

| Service | Port | Description | Health Check |
|---------|------|-------------|--------------|
| Project Service | 8001 | Project/Episode Management | `/api/v1/health` |
| Generation Service | 8000 | AI Script Generation | `/api/v1/health` |
| PostgreSQL | 5432 | Primary Database | Internal |
| Redis | 6379 | Cache & Sessions | Internal |
| ChromaDB | 8004 | Vector Database for RAG | `/api/v1/heartbeat` |

## 🔧 Configuration

### Environment Variables

#### Required Variables
```bash
# AI Provider Keys (at least one required)
OPENAI_API_KEY=your-openai-api-key  # pragma: allowlist secret
ANTHROPIC_API_KEY=your-anthropic-api-key  # pragma: allowlist secret

# Database Security
DATABASE_PASSWORD=secure-database-password  # pragma: allowlist secret
REDIS_PASSWORD=secure-redis-password  # pragma: allowlist secret
SECRET_KEY=your-32-character-secret-key  # pragma: allowlist secret
```

#### Optional Variables
```bash
# Database Configuration
DATABASE_NAME=ai_script_generator_v3
DATABASE_USER=postgres
DATABASE_POOL_SIZE=10

# Service Scaling
PROJECT_WORKERS=2
GENERATION_WORKERS=2
MAX_CONCURRENT_GENERATIONS=10

# Feature Flags
DEBUG=false
LOG_LEVEL=info
ENABLE_METRICS=true
```

### Core Module Integration

The Core Module is automatically installed in both services:
- **Project Service**: Shared schemas, exceptions, utilities
- **Generation Service**: Consistent DTOs and error handling
- **Volume Mount**: `/app/shared/core` (read-only in production)

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐
│  Project Service │    │Generation Service│
│     (8001)      │    │     (8000)      │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
        ┌────────────▼────────────┐
        │      PostgreSQL        │
        │       (5432)           │
        └────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │        Redis           │
        │       (6379)           │
        └────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │      ChromaDB          │
        │       (8004)           │
        └────────────────────────┘
```

### Inter-Service Communication
- **Project ↔ Generation**: Direct HTTP calls via Docker network
- **Data Persistence**: PostgreSQL for structured data
- **Caching**: Redis for sessions and temporary data  
- **Vector Search**: ChromaDB for RAG functionality

## 🔨 Build Process

### 1. Core Module Installation
```dockerfile
# Automatic installation in each service
COPY ../../shared/core /app/shared/core
RUN pip install -e /app/shared/core
```

### 2. Service Dependencies
```dockerfile
# SQLAlchemy 2.0.25 unified across services
# FastAPI, Pydantic, and AI provider libraries
# Health check utilities
```

### 3. Security Features
- Non-root user execution
- Minimal base images (Python 3.11-slim)
- Health checks for all services
- Secrets management via environment variables

## 📊 Monitoring & Health Checks

### Service Health Endpoints
```bash
# Project Service
curl http://localhost:8001/api/v1/health

# Generation Service  
curl http://localhost:8000/api/v1/health

# ChromaDB
curl http://localhost:8004/api/v1/heartbeat
```

### Container Health Status
```bash
# Check all service health
docker-compose ps

# View service logs
docker-compose logs project-service
docker-compose logs generation-service

# Monitor resource usage
docker stats
```

## 🗄️ Data Persistence

### Volumes Configuration
```yaml
volumes:
  postgres_data:     # Database files
  redis_data:        # Cache persistence  
  chroma_data:       # Vector database
  project_data:      # Project service data
  generation_data:   # Generation artifacts
```

### Backup Strategy
```bash
# Database backup
docker-compose exec postgres pg_dump -U postgres ai_script_generator_v3 > backup.sql

# Volume backup
docker run --rm -v ai-script-generator-v3_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

## 🚀 Deployment Scenarios

### Development
```bash
# Start with hot reload
docker-compose up --build

# Features:
# - Source code mounting
# - Debug mode enabled
# - Exposed database ports
# - Real-time logs
```

### Staging
```bash
# Production-like with monitoring
docker-compose -f docker-compose.yml up --build

# Features:
# - Production images
# - Health checks enabled
# - Resource monitoring
# - Persistent volumes
```

### Production
```bash
# Full production stack
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Features:
# - Multiple replicas
# - Resource limits
# - Security hardening
# - Nginx reverse proxy
# - Log aggregation
```

## 🔒 Security Considerations

### Environment Security
- ✅ All sensitive data in environment variables
- ✅ No hardcoded API keys or passwords
- ✅ Production secrets management required

### Network Security
- ✅ Isolated Docker network
- ✅ No exposed internal ports in production
- ✅ Service-to-service communication via internal DNS

### Container Security
- ✅ Non-root user execution
- ✅ Minimal attack surface
- ✅ Regular security updates
- ✅ Health monitoring

## 🛠️ Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
docker-compose logs service-name

# Common causes:
# - Missing API keys
# - Database connection failed
# - Port conflicts
# - Core Module import errors
```

#### Database Connection Issues
```bash
# Verify database is running
docker-compose ps postgres

# Check connection from service
docker-compose exec project-service python -c "from project_service.database import test_connection; test_connection()"
```

#### Core Module Issues
```bash
# Verify Core Module installation
docker-compose exec project-service python -c "import ai_script_core; print('Core Module OK')"

# Rebuild with Core Module
docker-compose build --no-cache project-service
```

### Performance Tuning

#### Database Optimization
```bash
# Increase connection pool
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Enable query optimization
POSTGRES_SHARED_BUFFERS=512MB
POSTGRES_EFFECTIVE_CACHE_SIZE=2GB
```

#### Service Scaling
```bash
# Scale services
docker-compose up -d --scale generation-service=3 --scale project-service=2

# Monitor resource usage
docker stats
```

## 📈 Monitoring & Observability

### Metrics Collection
- Health check endpoints
- Docker container metrics
- Application performance monitoring
- Database connection pooling stats

### Log Aggregation
- Structured JSON logging
- Centralized log collection with Fluentd
- Log rotation and retention policies

## 🤝 Development Workflow

### Local Development
1. Start development stack: `docker-compose up`
2. Edit code - changes auto-reload
3. Run tests in containers
4. Debug via container logs

### Testing
```bash
# Run service tests
docker-compose exec project-service pytest
docker-compose exec generation-service pytest

# Integration tests
docker-compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit
```

### Deployment Pipeline
1. Build and test locally
2. Push to staging environment
3. Run integration tests
4. Deploy to production with blue-green strategy

---

**Ready for production deployment! 🚀**