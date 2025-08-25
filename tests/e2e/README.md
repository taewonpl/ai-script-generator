# E2E Test Suite for AI Script Generator v3.0

Comprehensive end-to-end testing framework covering all aspects of the AI Script Generator system.

## Overview

This test suite provides comprehensive coverage of:
- **Core Flow Integration**: Complete project-to-episode workflow testing
- **System Resilience**: Failure scenarios and recovery mechanisms  
- **Monitoring Verification**: Alerting and metrics collection validation
- **Performance Benchmarking**: Load testing and performance measurement
- **Final System Verification**: Service integration and API compliance

## Quick Start

### Prerequisites
```bash
# Ensure all services are running
docker-compose up -d

# Install test dependencies
pip install aiohttp pytest psutil docker
```

### Running All Tests
```bash
# Execute complete test suite
cd tests/e2e
python run_all_tests.py
```

### Running Individual Test Suites
```bash
# Core flow integration tests
python test_core_flow.py

# System resilience tests  
python test_system_resilience.py

# Monitoring verification tests
python test_monitoring_verification.py

# Performance benchmark tests
python test_performance_benchmark.py

# Final system verification tests
python test_final_system_verification.py
```

## Test Suites Detail

### 1. Core Flow Integration Tests (`test_core_flow.py`)
- **Single Project-Episode Flow**: Basic workflow validation
- **Concurrent Episodes**: 15 users × 4 episodes each (60 total)
- **Numbering Integrity**: Sequential episode numbering (1-60)
- **No Gaps/Duplicates**: Zero tolerance validation

**Key Scenarios:**
- Project creation via REST API
- Script generation with SSE monitoring
- Episode storage with automatic numbering
- Concurrent user simulation with proper isolation

### 2. System Resilience Tests (`test_system_resilience.py`)
- **Redis Shutdown**: Idempotency handling during cache unavailability
- **ChromaDB Failure**: Vector database connection retry mechanisms
- **SSE Recovery**: Last-Event-ID based reconnection
- **Server Restart**: State preservation during service interruption

**Failure Simulations:**
- Docker container manipulation for realistic failures
- Network partition simulation
- Graceful degradation verification
- Recovery time measurement

### 3. Monitoring Verification Tests (`test_monitoring_verification.py`)
- **Integrity Violations**: Intentional gap/duplicate creation
- **Alert Triggering**: Monitoring system response validation
- **Metrics Collection**: Prometheus export verification
- **Dashboard Updates**: Real-time monitoring validation

**Monitoring Scenarios:**
- Episode numbering violation detection
- Performance threshold breach alerts
- System health degradation warnings
- Metrics export consistency checks

### 4. Performance Benchmark Tests (`test_performance_benchmark.py`)
- **Response Time Analysis**: P95/P99 percentile measurements
- **Concurrent SSE Limits**: Maximum simultaneous connection testing
- **Memory Efficiency**: Leak detection and usage monitoring
- **Continuous Operation**: Extended runtime simulation

**Performance Metrics:**
- Episode creation: < 2s P95 response time
- SSE connections: 50+ concurrent streams
- Memory stability: No leaks over extended periods
- Throughput: Episodes/second under load

### 5. Final System Verification Tests (`test_final_system_verification.py`)
- **Service Startup**: All services boot sequence validation
- **Health Checks**: Endpoint compliance verification
- **API Documentation**: OpenAPI schema consistency
- **Error Handling**: Complete error scenario coverage

**Verification Areas:**
- Inter-service communication
- API contract compliance
- Error response consistency
- System integration completeness

## Expected Performance Baselines

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Episode Creation P95 | < 2.0s | < 5.0s |
| Concurrent SSE Connections | 50+ | 20+ |
| Memory Usage Growth | < 5% over 1hr | < 20% over 1hr |
| Health Check Response | < 100ms | < 500ms |
| API Documentation Coverage | 100% | 95% |

## Test Environment Requirements

### Services Required
- **Project Service**: `localhost:8001` 
- **Generation Service**: `localhost:8002`
- **Redis**: Cache and session storage
- **ChromaDB**: Vector database
- **Prometheus**: Metrics collection

### Docker Configuration
```yaml
# Ensure these services are in docker-compose.yml
services:
  redis:
    container_name: redis
  chromadb:
    container_name: chromadb
  # ... other services
```

## Interpreting Results

### Success Criteria
- All test suites show "PASSED" status
- No episode numbering gaps or duplicates
- P95 response times within targets
- Zero memory leaks detected
- 100% health check compliance

### Common Failure Scenarios
- **Service Unavailable**: Check docker-compose services
- **Port Conflicts**: Verify services running on expected ports
- **Timeout Issues**: Increase timeout values for slower environments
- **Memory Constraints**: Ensure adequate system resources

## Troubleshooting

### Test Execution Issues
```bash
# Check service availability
curl http://localhost:8001/health
curl http://localhost:8002/health

# Verify Docker services
docker-compose ps

# Check service logs
docker-compose logs project-service
docker-compose logs generation-service
```

### Performance Issues
```bash
# Monitor resource usage during tests
htop
docker stats

# Check for memory leaks
python -m memory_profiler test_performance_benchmark.py
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start services
        run: docker-compose up -d
      - name: Wait for services
        run: sleep 30
      - name: Run E2E tests
        run: |
          cd tests/e2e
          python run_all_tests.py
```

## Reports and Analytics

### Generated Reports
- **JSON Report**: Detailed test results with metrics
- **Executive Summary**: High-level status and recommendations
- **Performance Data**: Response times and resource usage
- **Failure Analysis**: Root cause identification for failed tests

### Metrics Dashboard
Key metrics are exported to Prometheus and can be visualized in Grafana:
- Test execution frequency and success rates
- System performance trends
- Error rate analysis
- Resource utilization patterns

## Contributing

### Adding New Tests
1. Create test file following naming convention: `test_<category>.py`
2. Implement test class with setup/teardown methods
3. Add test scenarios with proper assertions
4. Update `run_all_tests.py` to include new test suite
5. Document expected behavior and success criteria

### Test Development Guidelines
- Use async/await for all I/O operations
- Implement proper cleanup in teardown methods
- Include comprehensive error handling
- Add detailed logging for troubleshooting
- Follow existing code patterns and conventions

## Support

For issues with the E2E test suite:
1. Check service logs: `docker-compose logs [service-name]`
2. Verify test environment setup
3. Review test execution reports
4. Check system resource availability
5. Consult troubleshooting guide above