# Generation Service Docker Deployment

This directory contains Docker containerization and deployment configurations for the Generation Service.

## Overview

The Docker setup provides:
- **Multi-stage builds** for optimized production images
- **Development and production environments** with docker-compose
- **Complete monitoring stack** (Prometheus, Grafana, Loki)
- **Performance optimization** and health checking
- **Security best practices** and non-root execution

## Files Structure

```
docker/
├── Dockerfile                 # Multi-stage build configuration
├── docker-compose.yml         # Development environment
├── docker-compose.prod.yml    # Production environment
├── entrypoint.sh             # Container initialization script
├── health-check.sh           # Health check script
├── redis.conf                # Redis development config
├── redis-prod.conf           # Redis production config
├── prometheus.yml            # Prometheus development config
├── prometheus-prod.yml       # Prometheus production config
├── nginx/
│   └── nginx.conf            # Nginx reverse proxy config
├── .env.example              # Environment variables template
└── README.md                 # This file
```

## Quick Start

### Development Environment

1. **Copy environment file:**
   ```bash
   cp docker/.env.example docker/.env
   # Edit docker/.env with your configuration
   ```

2. **Start development stack:**
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

3. **Access services:**
   - Generation Service: http://localhost:8000
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (admin/admin)
   - Redis: localhost:6379

### Production Environment

1. **Set up environment variables:**
   ```bash
   export REDIS_PASSWORD="your_secure_password"  # pragma: allowlist secret
   export GRAFANA_ADMIN_PASSWORD="your_grafana_password"  # pragma: allowlist secret
   export GRAFANA_SECRET_KEY="your_grafana_secret"  # pragma: allowlist secret
   ```

2. **Deploy production stack:**
   ```bash
   docker-compose -f docker/docker-compose.prod.yml up -d
   ```

3. **Access services:**
   - Generation Service: https://localhost (via Nginx)
   - Monitoring stack: Internal only

## Build Stages

The Dockerfile uses multi-stage builds:

### 1. Builder Stage
- Installs build dependencies
- Compiles Python packages
- Prepares application source

### 2. Production Stage
- Minimal runtime environment
- Non-root user execution
- Optimized for size and security

### 3. Development Stage
- Additional development tools
- Hot-reload support
- Extended debugging capabilities

## Environment Configuration

### Required Environment Variables

```bash
# Application
ENVIRONMENT=production|development|testing
DEBUG=true|false
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=secure_password

# Monitoring
ENABLE_MONITORING=true
ENABLE_CACHING=true
ENABLE_PERFORMANCE_OPTIMIZATION=true
```

### Performance Settings

```bash
MAX_WORKERS=4
WORKER_CONNECTIONS=1000
KEEP_ALIVE=2
```

### Health Check Settings

```bash
HEALTH_CHECK_HOST=localhost
HEALTH_CHECK_PORT=8000
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_ENDPOINT=/api/monitoring/health
HEALTH_CHECK_MAX_RETRIES=3
```

## Docker Commands

### Build Commands

```bash
# Build development image
docker build -f docker/Dockerfile --target development -t generation-service:dev .

# Build production image
docker build -f docker/Dockerfile --target production -t generation-service:prod .

# Build with build args
docker build --build-arg ENVIRONMENT=production -t generation-service:latest .
```

### Runtime Commands

```bash
# Run development container
docker run -p 8000:8000 -e ENVIRONMENT=development generation-service:dev

# Run production container
docker run -p 8000:8000 -e ENVIRONMENT=production generation-service:prod

# Run with volume mounts for development
docker run -p 8000:8000 -v $(pwd)/src:/app/src:ro generation-service:dev
```

### Debugging Commands

```bash
# Execute shell in running container
docker exec -it generation-service-dev /bin/bash

# View logs
docker logs -f generation-service-dev

# Check health
docker exec generation-service-dev /health-check.sh quick
```

## Health Checks

The health check system performs multiple validations:

### HTTP Health Check
- Tests API endpoint availability
- Validates response time
- Configurable retry logic

### Process Health Check
- Verifies Python/uvicorn processes
- Checks process resource usage

### System Health Check
- Disk space validation
- Memory usage monitoring
- Application-specific checks

### Running Health Checks

```bash
# Quick health check
docker exec container_name /health-check.sh quick

# Comprehensive health check
docker exec container_name /health-check.sh comprehensive
```

## Monitoring Stack

### Prometheus Configuration
- Service discovery for Generation Service
- Custom metrics collection
- Alert rule definitions
- Recording rules for performance

### Grafana Dashboards
- System metrics visualization
- Application performance monitoring
- Error rate and latency tracking
- Resource utilization graphs

### Log Aggregation (Production)
- Loki for log aggregation
- Promtail for log shipping
- Structured logging support

## Security Considerations

### Container Security
- Non-root user execution
- Minimal base image (Python slim)
- No unnecessary packages
- Read-only root filesystem where possible

### Network Security
- Isolated Docker networks
- Rate limiting via Nginx
- SSL/TLS termination
- Internal service communication

### Secret Management
- Environment variable based secrets
- Docker secrets support
- No secrets in images or logs

## Performance Optimization

### Image Optimization
- Multi-stage builds reduce size
- Layer caching optimization
- Minimal runtime dependencies

### Runtime Optimization
- Resource limits and reservations
- Horizontal scaling support
- Load balancing via Nginx
- Connection pooling

### Monitoring Performance
- Prometheus metrics collection
- Grafana visualization
- Performance target validation
- Real-time alerting

## Troubleshooting

### Common Issues

1. **Container fails to start:**
   ```bash
   docker logs container_name
   # Check entrypoint script logs
   ```

2. **Health checks failing:**
   ```bash
   docker exec container_name /health-check.sh comprehensive
   # Review health check output
   ```

3. **Performance issues:**
   ```bash
   # Check resource usage
   docker stats
   
   # Review application metrics
   curl http://localhost:8000/api/monitoring/metrics
   ```

4. **Redis connection issues:**
   ```bash
   # Test Redis connectivity
   docker exec container_name redis-cli -h redis ping
   ```

### Debug Mode

Enable debug mode for verbose logging:

```bash
docker run -e DEBUG=true -e LOG_LEVEL=DEBUG generation-service:dev
```

### Performance Testing

```bash
# Run load tests against containerized service
docker exec generation-service-dev python -m pytest tests/performance/ -v
```

## Production Deployment Checklist

- [ ] Environment variables configured
- [ ] SSL certificates in place
- [ ] Redis password set
- [ ] Grafana admin password set
- [ ] Resource limits configured
- [ ] Health checks working
- [ ] Monitoring stack operational
- [ ] Log aggregation configured
- [ ] Backup strategy in place
- [ ] Security scan completed

## Maintenance

### Updates
- Rebuild images for security updates
- Update base image versions
- Review and update dependencies

### Monitoring
- Monitor resource usage trends
- Review application metrics
- Set up alerting for critical issues

### Backup
- Redis data persistence
- Prometheus data retention
- Grafana dashboard exports
- Application logs archival

## Support

For issues related to Docker deployment:
1. Check container logs: `docker logs container_name`
2. Run health checks: `docker exec container_name /health-check.sh`
3. Review monitoring dashboards
4. Check system resources with `docker stats`