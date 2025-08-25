# Multi-stage build optimized Dockerfile for Generation Service
# Stage 1: Build dependencies and prepare application
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt ./
COPY pyproject.toml setup.py ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ ./src/
COPY tests/ ./tests/
COPY *.py ./
COPY *.md ./

# Install the application in development mode
RUN pip install -e .

# Stage 2: Production runtime
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd -r generation && useradd -r -g generation generation

# Set working directory
WORKDIR /app

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application
COPY --from=builder /app/src/ ./src/
COPY --from=builder /app/*.py ./

# Copy Docker scripts
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/health-check.sh /health-check.sh

# Make scripts executable
RUN chmod +x /entrypoint.sh /health-check.sh

# Create required directories
RUN mkdir -p /app/logs /app/data /app/cache

# Set ownership
RUN chown -R generation:generation /app

# Switch to non-root user
USER generation

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /health-check.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["uvicorn", "generation_service.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 3: Development runtime (optional)
FROM production as development

# Switch back to root for development tools
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    git \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Copy test files
COPY --from=builder /app/tests/ ./tests/

# Install development Python packages
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov black isort flake8

# Switch back to generation user
USER generation

# Development command
CMD ["uvicorn", "generation_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
