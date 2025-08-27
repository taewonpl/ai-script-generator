#!/bin/bash

# AI Script Generator v3.0 - Docker Stack Test Script
# Tests the full stack deployment and validates all services

set -e

echo "🚀 AI Script Generator v3.0 - Docker Stack Test"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
echo "🔍 Checking Docker daemon..."
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker daemon is not running. Please start Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker daemon is running${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Copying from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env file with your actual API keys before running in production${NC}"
fi

# Validate docker-compose configuration
echo "🔍 Validating docker-compose configuration..."
if docker compose config --quiet; then
    echo -e "${GREEN}✅ Docker Compose configuration is valid${NC}"
else
    echo -e "${RED}❌ Docker Compose configuration has errors${NC}"
    exit 1
fi

# Function to check service health
check_service_health() {
    local service_name=$1
    local health_url=$2
    local max_attempts=30
    local attempt=1
    
    echo "🔍 Checking $service_name health..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_url" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is healthy${NC}"
            return 0
        fi
        
        echo "⏳ Attempt $attempt/$max_attempts - waiting for $service_name..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}❌ $service_name health check failed after $max_attempts attempts${NC}"
    return 1
}

# Function to show service logs on error
show_logs() {
    local service=$1
    echo -e "${YELLOW}📋 Last 20 lines of $service logs:${NC}"
    docker compose logs --tail=20 "$service" || echo "Could not retrieve logs for $service"
}

# Build and start services
echo "🏗️  Building and starting services..."
if docker compose up -d --build; then
    echo -e "${GREEN}✅ Services started successfully${NC}"
else
    echo -e "${RED}❌ Failed to start services${NC}"
    docker compose logs
    exit 1
fi

# Wait a moment for services to initialize
echo "⏳ Waiting for services to initialize..."
sleep 10

# Check individual service health
echo "🔍 Performing health checks..."

# Check PostgreSQL
echo "🔍 Checking PostgreSQL..."
if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
else
    echo -e "${RED}❌ PostgreSQL is not ready${NC}"
    show_logs postgres
fi

# Check Redis
echo "🔍 Checking Redis..."
if docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is ready${NC}"
else
    echo -e "${RED}❌ Redis is not ready${NC}"
    show_logs redis
fi

# Check ChromaDB
echo "🔍 Checking ChromaDB..."
if check_service_health "ChromaDB" "http://localhost:8004/api/v1/heartbeat"; then
    echo -e "${GREEN}✅ ChromaDB is ready${NC}"
else
    echo -e "${RED}❌ ChromaDB health check failed${NC}"
    show_logs chromadb
fi

# Check Project Service
if check_service_health "Project Service" "http://localhost:8001/api/v1/health"; then
    echo -e "${GREEN}✅ Project Service is ready${NC}"
else
    echo -e "${RED}❌ Project Service health check failed${NC}"
    show_logs project-service
fi

# Check Generation Service
if check_service_health "Generation Service" "http://localhost:8002/api/v1/health"; then
    echo -e "${GREEN}✅ Generation Service is ready${NC}"
else
    echo -e "${RED}❌ Generation Service health check failed${NC}"
    show_logs generation-service
fi

# Check Frontend
if check_service_health "Frontend" "http://localhost:3000"; then
    echo -e "${GREEN}✅ Frontend is ready${NC}"
else
    echo -e "${RED}❌ Frontend health check failed${NC}"
    show_logs frontend
fi

echo ""
echo "🎉 Docker Stack Test Complete!"
echo "================================"
echo "Services running on:"
echo "  • Frontend:           http://localhost:3000"
echo "  • Project Service:    http://localhost:8001"
echo "  • Generation Service: http://localhost:8002"
echo "  • ChromaDB:          http://localhost:8004"
echo "  • PostgreSQL:        localhost:5432"
echo "  • Redis:             localhost:6379"
echo ""
echo "API Documentation:"
echo "  • Project Service:    http://localhost:8001/docs"
echo "  • Generation Service: http://localhost:8002/docs"
echo ""
echo "To stop the stack: docker compose down"
echo "To view logs: docker compose logs [service-name]"