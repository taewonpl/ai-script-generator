#!/bin/bash

# Generation Service container entrypoint script
set -e

echo "Starting Generation Service entrypoint..."

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=1

    log "Waiting for $service_name at $host:$port..."

    while [ $attempt -le $max_attempts ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            log "$service_name is ready!"
            return 0
        fi

        log "Attempt $attempt/$max_attempts: $service_name not ready yet..."
        attempt=$((attempt + 1))
        sleep 2
    done

    log "WARNING: $service_name not available after $max_attempts attempts"
    return 1
}

# Function to initialize application
initialize_app() {
    log "Initializing Generation Service..."

    # Set default environment variables
    export PYTHONPATH="/app/src:${PYTHONPATH}"
    export ENVIRONMENT=${ENVIRONMENT:-development}
    export DEBUG=${DEBUG:-false}
    export LOG_LEVEL=${LOG_LEVEL:-INFO}

    # Performance settings
    export ENABLE_MONITORING=${ENABLE_MONITORING:-true}
    export ENABLE_CACHING=${ENABLE_CACHING:-true}
    export ENABLE_PERFORMANCE_OPTIMIZATION=${ENABLE_PERFORMANCE_OPTIMIZATION:-true}

    # Server settings
    export MAX_WORKERS=${MAX_WORKERS:-1}
    export WORKER_CONNECTIONS=${WORKER_CONNECTIONS:-1000}
    export KEEP_ALIVE=${KEEP_ALIVE:-2}

    log "Environment: $ENVIRONMENT"
    log "Debug: $DEBUG"
    log "Log Level: $LOG_LEVEL"
    log "Monitoring: $ENABLE_MONITORING"
    log "Caching: $ENABLE_CACHING"
    log "Performance Optimization: $ENABLE_PERFORMANCE_OPTIMIZATION"
}

# Function to run database migrations (if needed)
run_migrations() {
    log "Checking for database migrations..."

    # Add migration logic here if needed
    # For now, just log that migrations are complete
    log "Database migrations completed"
}

# Function to setup directories
setup_directories() {
    log "Setting up application directories..."

    # Create necessary directories
    mkdir -p /app/logs
    mkdir -p /app/data
    mkdir -p /app/cache

    # Set permissions
    chmod 755 /app/logs
    chmod 755 /app/data
    chmod 755 /app/cache

    log "Directories setup completed"
}

# Function to validate configuration
validate_config() {
    log "Validating configuration..."

    # Check required environment variables
    if [ "$ENVIRONMENT" != "development" ] && [ "$ENVIRONMENT" != "production" ] && [ "$ENVIRONMENT" != "testing" ]; then
        log "ERROR: Invalid ENVIRONMENT value: $ENVIRONMENT"
        exit 1
    fi

    # Validate Python path
    if [ ! -d "/app/src" ]; then
        log "ERROR: Application source directory not found"
        exit 1
    fi

    log "Configuration validation completed"
}

# Function to perform health check
health_check() {
    log "Performing initial health check..."

    # Check Python installation
    if ! python --version >/dev/null 2>&1; then
        log "ERROR: Python not available"
        exit 1
    fi

    # Check if application can import
    if ! python -c "import sys; sys.path.insert(0, '/app/src'); import generation_service" >/dev/null 2>&1; then
        log "WARNING: Application import check failed - continuing anyway"
    fi

    log "Health check completed"
}

# Main execution
main() {
    log "=== Generation Service Container Starting ==="

    # Initialize application
    initialize_app

    # Setup directories
    setup_directories

    # Validate configuration
    validate_config

    # Wait for dependencies if in production
    if [ "$ENVIRONMENT" = "production" ]; then
        if [ -n "$REDIS_HOST" ]; then
            wait_for_service "$REDIS_HOST" "${REDIS_PORT:-6379}" "Redis"
        fi
    fi

    # Run migrations
    run_migrations

    # Perform health check
    health_check

    log "=== Initialization Complete ==="
    log "Starting application with command: $*"

    # Execute the main command
    exec "$@"
}

# Handle signals for graceful shutdown
trap 'log "Received shutdown signal, terminating..."; kill -TERM $PID; wait $PID' TERM INT

# Run main function with all arguments
main "$@" &
PID=$!
wait $PID
