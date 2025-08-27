# Production-ready Dockerfile for Generation Service
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd -r generation && useradd -r -g generation generation

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Core Module
COPY shared/core /app/shared/core
WORKDIR /app/shared/core
RUN pip install -e .
WORKDIR /app

# Copy requirements and install Python dependencies
COPY services/generation-service/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY services/generation-service/src/ ./src/
COPY services/generation-service/main.py ./

# Create default scripts
RUN echo '#!/bin/bash\nexec "$@"' > /entrypoint.sh
RUN echo '#!/bin/bash\ncurl -f http://localhost:8002/health || exit 1' > /health-check.sh

# Make scripts executable
RUN chmod +x /entrypoint.sh /health-check.sh

# Create data directories
RUN mkdir -p /app/data/chroma \
    && mkdir -p /app/data/vectors \
    && mkdir -p /app/data/logs \
    && mkdir -p /app/data/cache \
    && chmod -R 755 /app/data

# Set ownership
RUN chown -R generation:generation /app

# Switch to non-root user
USER generation

# Set environment variables
ENV DATA_ROOT_PATH=/app/data \
    CHROMA_DB_PATH=/app/data/chroma \
    VECTOR_DATA_PATH=/app/data/vectors \
    LOG_DATA_PATH=/app/data/logs \
    CACHE_DATA_PATH=/app/data/cache \
    PYTHONPATH=/app/src:/app

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /health-check.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command - directly use uvicorn
CMD ["uvicorn", "generation_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
