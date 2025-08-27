# Production-ready Dockerfile for Project Service
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd -r project && useradd -r -g project project

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
COPY services/project-service/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY services/project-service/src/ ./src/

# Create data directories
RUN mkdir -p /app/data \
    && chmod -R 755 /app/data

# Set ownership
RUN chown -R project:project /app

# Switch to non-root user
USER project

# Set environment variables
ENV PYTHONPATH=/app/src:/app \
    PROJECT_SERVICE_PORT=8001 \
    PROJECT_SERVICE_HOST=0.0.0.0

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "project_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
