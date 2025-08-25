#!/bin/bash

# Generation Service health check script
set -e

# Configuration
HOST=${HEALTH_CHECK_HOST:-localhost}
PORT=${HEALTH_CHECK_PORT:-8000}
TIMEOUT=${HEALTH_CHECK_TIMEOUT:-10}
ENDPOINT=${HEALTH_CHECK_ENDPOINT:-/api/v1/health}
MAX_RETRIES=${HEALTH_CHECK_MAX_RETRIES:-3}

# Function to log messages
log() {
    echo "[HEALTH] $(date +'%Y-%m-%d %H:%M:%S') $1"
}

# Function to check HTTP endpoint
check_http_endpoint() {
    local url="http://${HOST}:${PORT}${ENDPOINT}"
    local attempt=1

    while [ $attempt -le $MAX_RETRIES ]; do
        log "Health check attempt $attempt/$MAX_RETRIES: $url"

        # Use curl for health check
        if curl -f -s -m "$TIMEOUT" "$url" >/dev/null 2>&1; then
            log "✓ HTTP health check passed"
            return 0
        fi

        log "✗ HTTP health check failed (attempt $attempt)"
        attempt=$((attempt + 1))

        if [ $attempt -le $MAX_RETRIES ]; then
            sleep 2
        fi
    done

    log "✗ HTTP health check failed after $MAX_RETRIES attempts"
    return 1
}

# Function to check process health
check_process_health() {
    log "Checking process health..."

    # Check if Python process is running
    if ! pgrep -f "python.*uvicorn" >/dev/null 2>&1; then
        log "✗ No Python/uvicorn process found"
        return 1
    fi

    log "✓ Process health check passed"
    return 0
}

# Function to check disk space
check_disk_space() {
    log "Checking disk space..."

    # Check available disk space (require at least 100MB)
    local available_mb=$(df /app | awk 'NR==2 {print int($4/1024)}')
    local required_mb=100

    if [ "$available_mb" -lt "$required_mb" ]; then
        log "✗ Insufficient disk space: ${available_mb}MB available, ${required_mb}MB required"
        return 1
    fi

    log "✓ Disk space check passed: ${available_mb}MB available"
    return 0
}

# Function to check memory usage
check_memory_usage() {
    log "Checking memory usage..."

    # Check if memory usage is reasonable (under 90%)
    if command -v free >/dev/null 2>&1; then
        local mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
        local max_usage=90

        if [ "$mem_usage" -gt "$max_usage" ]; then
            log "⚠ High memory usage: ${mem_usage}%"
            # Don't fail for high memory usage, just warn
        else
            log "✓ Memory usage check passed: ${mem_usage}%"
        fi
    else
        log "ℹ Memory check skipped (free command not available)"
    fi

    return 0
}

# Function to check application-specific health
check_application_health() {
    log "Checking application-specific health..."

    # Check if log directory is writable
    if [ ! -w "/app/logs" ]; then
        log "✗ Log directory not writable"
        return 1
    fi

    # Check if cache directory exists and is writable
    if [ ! -w "/app/cache" ]; then
        log "✗ Cache directory not writable"
        return 1
    fi

    log "✓ Application health check passed"
    return 0
}

# Function to perform comprehensive health check
comprehensive_health_check() {
    log "=== Starting comprehensive health check ==="

    local checks_passed=0
    local total_checks=5

    # Process health check
    if check_process_health; then
        checks_passed=$((checks_passed + 1))
    fi

    # HTTP endpoint health check
    if check_http_endpoint; then
        checks_passed=$((checks_passed + 1))
    fi

    # Disk space check
    if check_disk_space; then
        checks_passed=$((checks_passed + 1))
    fi

    # Memory usage check
    if check_memory_usage; then
        checks_passed=$((checks_passed + 1))
    fi

    # Application-specific health check
    if check_application_health; then
        checks_passed=$((checks_passed + 1))
    fi

    log "=== Health check summary: $checks_passed/$total_checks checks passed ==="

    # Require at least 4 out of 5 checks to pass
    if [ $checks_passed -ge 4 ]; then
        log "✓ Overall health check: HEALTHY"
        return 0
    else
        log "✗ Overall health check: UNHEALTHY"
        return 1
    fi
}

# Function to perform quick health check
quick_health_check() {
    log "Performing quick health check..."

    # Just check if the service responds
    if check_http_endpoint; then
        log "✓ Quick health check: HEALTHY"
        return 0
    else
        log "✗ Quick health check: UNHEALTHY"
        return 1
    fi
}

# Main execution
main() {
    local check_type=${1:-comprehensive}

    case $check_type in
        "quick")
            quick_health_check
            ;;
        "comprehensive"|*)
            comprehensive_health_check
            ;;
    esac
}

# Execute health check
main "$@"
