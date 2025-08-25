#!/bin/bash

# Generation Service - 종합 테스트 실행 스크립트
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TEST_TIMEOUT=300  # 5 minutes
COVERAGE_THRESHOLD=85
LOG_FILE="test_results_$(date +%Y%m%d_%H%M%S).log"

echo -e "${BLUE}🚀 Generation Service 종합 테스트 시작${NC}"
echo "로그 파일: $LOG_FILE"

# Function to log and display messages
log_message() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Function to run command with timeout and logging
run_with_timeout() {
    local cmd="$1"
    local description="$2"
    local timeout="${3:-$TEST_TIMEOUT}"

    log_message "${BLUE}[$description] 시작...${NC}"

    if timeout "$timeout" bash -c "$cmd" >> "$LOG_FILE" 2>&1; then
        log_message "${GREEN}✅ [$description] 성공${NC}"
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            log_message "${RED}❌ [$description] 타임아웃 (${timeout}초)${NC}"
        else
            log_message "${RED}❌ [$description] 실패 (exit code: $exit_code)${NC}"
        fi
        return $exit_code
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log_message "${BLUE}📋 사전 요구사항 확인${NC}"

    # Check Python
    if ! python3 --version > /dev/null 2>&1; then
        log_message "${RED}❌ Python 3가 설치되지 않았습니다${NC}"
        exit 1
    fi

    # Check pip
    if ! pip --version > /dev/null 2>&1; then
        log_message "${RED}❌ pip가 설치되지 않았습니다${NC}"
        exit 1
    fi

    # Check Docker
    if ! docker --version > /dev/null 2>&1; then
        log_message "${YELLOW}⚠️ Docker가 설치되지 않았습니다 (일부 테스트 제외)${NC}"
        DOCKER_AVAILABLE=false
    else
        DOCKER_AVAILABLE=true
    fi

    # Check pytest
    if ! python3 -c "import pytest" 2>/dev/null; then
        log_message "${YELLOW}⚠️ pytest 설치 중...${NC}"
        pip install pytest pytest-asyncio pytest-cov
    fi

    log_message "${GREEN}✅ 사전 요구사항 확인 완료${NC}"
}

# Function to setup test environment
setup_test_environment() {
    log_message "${BLUE}🔧 테스트 환경 설정${NC}"

    # Install dependencies
    if [ -f "requirements-dev.txt" ]; then
        run_with_timeout "pip install -r requirements-dev.txt" "개발 의존성 설치" 120
    fi

    if [ -f "requirements.txt" ]; then
        run_with_timeout "pip install -r requirements.txt" "프로덕션 의존성 설치" 120
    fi

    # Install package in development mode
    if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
        run_with_timeout "pip install -e ." "패키지 설치" 60
    fi

    # Set environment variables
    export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
    export ENVIRONMENT=testing
    export DEBUG=true
    export LOG_LEVEL=DEBUG

    log_message "${GREEN}✅ 테스트 환경 설정 완료${NC}"
}

# Function to start test services
start_test_services() {
    log_message "${BLUE}🔄 테스트 서비스 시작${NC}"

    if [ "$DOCKER_AVAILABLE" = true ]; then
        # Start Redis for testing
        if ! docker ps | grep test-redis > /dev/null; then
            log_message "${BLUE}Redis 테스트 컨테이너 시작...${NC}"
            docker run -d --name test-redis -p 6380:6379 redis:7-alpine > /dev/null 2>&1 || true
            sleep 2
        fi

        # Check Redis connectivity
        if docker exec test-redis redis-cli ping > /dev/null 2>&1; then
            export REDIS_HOST=localhost
            export REDIS_PORT=6380
            log_message "${GREEN}✅ Redis 테스트 서비스 준비 완료${NC}"
        else
            log_message "${YELLOW}⚠️ Redis 테스트 서비스를 사용할 수 없습니다${NC}"
        fi
    else
        log_message "${YELLOW}⚠️ Docker를 사용할 수 없어 외부 서비스 테스트를 건너뜁니다${NC}"
    fi
}

# Function to run unit tests
run_unit_tests() {
    log_message "${BLUE}🧪 단위 테스트 실행${NC}"

    if [ -d "tests/unit" ]; then
        run_with_timeout "python -m pytest tests/unit/ -v --tb=short --cov=src/generation_service --cov-report=xml --cov-report=html --cov-report=term" "단위 테스트"

        # Check coverage
        if command -v coverage > /dev/null; then
            COVERAGE=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
            if [ ! -z "$COVERAGE" ] && [ "$COVERAGE" -lt "$COVERAGE_THRESHOLD" ]; then
                log_message "${YELLOW}⚠️ 코드 커버리지가 목표치보다 낮습니다: ${COVERAGE}% (목표: ${COVERAGE_THRESHOLD}%)${NC}"
            else
                log_message "${GREEN}✅ 코드 커버리지: ${COVERAGE}%${NC}"
            fi
        fi
    else
        log_message "${YELLOW}⚠️ 단위 테스트 디렉토리가 없습니다${NC}"
    fi
}

# Function to run integration tests
run_integration_tests() {
    log_message "${BLUE}🔗 통합 테스트 실행${NC}"

    if [ -d "tests/integration" ]; then
        run_with_timeout "python -m pytest tests/integration/ -v --tb=short" "통합 테스트"
    else
        log_message "${YELLOW}⚠️ 통합 테스트 디렉토리가 없습니다${NC}"
    fi
}

# Function to run API endpoint tests
run_api_tests() {
    log_message "${BLUE}🌐 API 엔드포인트 테스트 실행${NC}"

    if [ -f "tests/test_api_endpoints.py" ]; then
        # Start service for API testing
        if [ "$DOCKER_AVAILABLE" = true ]; then
            log_message "${BLUE}테스트용 서비스 시작...${NC}"

            # Build and start service
            if run_with_timeout "docker build -f docker/Dockerfile --target development -t generation-service:test ." "Docker 이미지 빌드" 180; then
                docker run -d --name generation-service-test \
                    --network host \
                    -e ENVIRONMENT=testing \
                    -e REDIS_HOST=localhost \
                    -e REDIS_PORT=6380 \
                    generation-service:test > /dev/null 2>&1 || true

                # Wait for service to be ready
                log_message "${BLUE}서비스 시작 대기...${NC}"
                for i in {1..30}; do
                    if curl -f http://localhost:8000/api/monitoring/health > /dev/null 2>&1; then
                        log_message "${GREEN}✅ 서비스 준비 완료${NC}"
                        break
                    fi
                    sleep 2
                done

                # Run API tests
                run_with_timeout "python -m pytest tests/test_api_endpoints.py -v --tb=short" "API 테스트"

                # Stop test service
                docker stop generation-service-test > /dev/null 2>&1 || true
                docker rm generation-service-test > /dev/null 2>&1 || true
            else
                log_message "${YELLOW}⚠️ Docker 빌드에 실패하여 API 테스트를 건너뜁니다${NC}"
            fi
        else
            log_message "${YELLOW}⚠️ Docker를 사용할 수 없어 API 테스트를 건너뜁니다${NC}"
        fi
    else
        log_message "${YELLOW}⚠️ API 테스트 파일이 없습니다${NC}"
    fi
}

# Function to run performance tests
run_performance_tests() {
    log_message "${BLUE}⚡ 성능 테스트 실행${NC}"

    if [ -d "tests/performance" ]; then
        run_with_timeout "python -m pytest tests/performance/ -v --tb=short" "성능 테스트" 600  # 10 minutes for performance tests
    else
        log_message "${YELLOW}⚠️ 성능 테스트 디렉토리가 없습니다${NC}"
    fi
}

# Function to run error scenario tests
run_error_scenario_tests() {
    log_message "${BLUE}🚨 에러 시나리오 테스트 실행${NC}"

    if [ -f "tests/test_error_scenarios.py" ]; then
        run_with_timeout "python -m pytest tests/test_error_scenarios.py -v --tb=short" "에러 시나리오 테스트"
    else
        log_message "${YELLOW}⚠️ 에러 시나리오 테스트 파일이 없습니다${NC}"
    fi
}

# Function to run monitoring tests
run_monitoring_tests() {
    log_message "${BLUE}📊 모니터링 테스트 실행${NC}"

    if [ -f "tests/test_monitoring.py" ]; then
        run_with_timeout "python -m pytest tests/test_monitoring.py -v --tb=short" "모니터링 테스트"
    else
        log_message "${YELLOW}⚠️ 모니터링 테스트 파일이 없습니다${NC}"
    fi
}

# Function to run code quality checks
run_code_quality_checks() {
    log_message "${BLUE}🔍 코드 품질 검사${NC}"

    # Install tools if needed
    pip install black isort flake8 mypy bandit safety > /dev/null 2>&1 || true

    # Black formatting check
    if command -v black > /dev/null; then
        if black --check --diff src/ tests/ > /dev/null 2>&1; then
            log_message "${GREEN}✅ 코드 포맷팅 (Black)${NC}"
        else
            log_message "${YELLOW}⚠️ 코드 포맷팅 문제 발견 (Black)${NC}"
        fi
    fi

    # Import sorting check
    if command -v isort > /dev/null; then
        if isort --check-only --diff src/ tests/ > /dev/null 2>&1; then
            log_message "${GREEN}✅ Import 정렬 (isort)${NC}"
        else
            log_message "${YELLOW}⚠️ Import 정렬 문제 발견 (isort)${NC}"
        fi
    fi

    # Linting
    if command -v flake8 > /dev/null; then
        if flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503 > /dev/null 2>&1; then
            log_message "${GREEN}✅ 린팅 (flake8)${NC}"
        else
            log_message "${YELLOW}⚠️ 린팅 문제 발견 (flake8)${NC}"
        fi
    fi

    # Type checking
    if command -v mypy > /dev/null; then
        if mypy src/ --ignore-missing-imports > /dev/null 2>&1; then
            log_message "${GREEN}✅ 타입 체킹 (mypy)${NC}"
        else
            log_message "${YELLOW}⚠️ 타입 체킹 문제 발견 (mypy)${NC}"
        fi
    fi

    # Security scan
    if command -v bandit > /dev/null; then
        if bandit -r src/ -q > /dev/null 2>&1; then
            log_message "${GREEN}✅ 보안 검사 (bandit)${NC}"
        else
            log_message "${YELLOW}⚠️ 보안 문제 발견 (bandit)${NC}"
        fi
    fi

    # Dependency vulnerability scan
    if command -v safety > /dev/null; then
        if safety check > /dev/null 2>&1; then
            log_message "${GREEN}✅ 의존성 보안 검사 (safety)${NC}"
        else
            log_message "${YELLOW}⚠️ 취약한 의존성 발견 (safety)${NC}"
        fi
    fi
}

# Function to run Docker tests
run_docker_tests() {
    log_message "${BLUE}🐳 Docker 빌드 테스트${NC}"

    if [ "$DOCKER_AVAILABLE" = true ]; then
        # Test multi-stage builds
        run_with_timeout "docker build -f docker/Dockerfile --target development -t generation-service:dev-test ." "개발 이미지 빌드" 300
        run_with_timeout "docker build -f docker/Dockerfile --target production -t generation-service:prod-test ." "프로덕션 이미지 빌드" 300

        # Test docker-compose
        if [ -f "docker/docker-compose.yml" ]; then
            run_with_timeout "docker-compose -f docker/docker-compose.yml config" "Docker Compose 설정 검증" 30
        fi

        # Cleanup test images
        docker rmi generation-service:dev-test generation-service:prod-test > /dev/null 2>&1 || true
    else
        log_message "${YELLOW}⚠️ Docker를 사용할 수 없어 Docker 테스트를 건너뜁니다${NC}"
    fi
}

# Function to cleanup test services
cleanup_test_services() {
    log_message "${BLUE}🧹 테스트 서비스 정리${NC}"

    if [ "$DOCKER_AVAILABLE" = true ]; then
        # Stop and remove test containers
        docker stop test-redis > /dev/null 2>&1 || true
        docker rm test-redis > /dev/null 2>&1 || true
        docker stop generation-service-test > /dev/null 2>&1 || true
        docker rm generation-service-test > /dev/null 2>&1 || true

        # Clean up test images
        docker rmi generation-service:test > /dev/null 2>&1 || true
    fi
}

# Function to generate test report
generate_test_report() {
    log_message "${BLUE}📄 테스트 보고서 생성${NC}"

    REPORT_FILE="test_report_$(date +%Y%m%d_%H%M%S).md"

    cat > "$REPORT_FILE" << EOF
# Generation Service 테스트 보고서

**생성 일시**: $(date)
**테스트 실행자**: $(whoami)
**환경**: $(uname -a)

## 테스트 결과 요약

EOF

    # Analyze log file for results
    if [ -f "$LOG_FILE" ]; then
        SUCCESS_COUNT=$(grep -c "✅" "$LOG_FILE" || echo "0")
        FAILURE_COUNT=$(grep -c "❌" "$LOG_FILE" || echo "0")
        WARNING_COUNT=$(grep -c "⚠️" "$LOG_FILE" || echo "0")

        cat >> "$REPORT_FILE" << EOF
- **성공**: $SUCCESS_COUNT
- **실패**: $FAILURE_COUNT
- **경고**: $WARNING_COUNT

## 상세 결과

\`\`\`
$(tail -50 "$LOG_FILE")
\`\`\`

## 권장 사항

EOF

        if [ "$FAILURE_COUNT" -gt 0 ]; then
            echo "- 실패한 테스트를 검토하고 수정하세요" >> "$REPORT_FILE"
        fi

        if [ "$WARNING_COUNT" -gt 0 ]; then
            echo "- 경고 사항을 검토하고 개선하세요" >> "$REPORT_FILE"
        fi

        if [ "$FAILURE_COUNT" -eq 0 ] && [ "$WARNING_COUNT" -eq 0 ]; then
            echo "- 모든 테스트가 성공적으로 완료되었습니다!" >> "$REPORT_FILE"
        fi
    fi

    log_message "${GREEN}✅ 테스트 보고서 생성 완료: $REPORT_FILE${NC}"
}

# Main execution
main() {
    local start_time=$(date +%s)

    # Trap for cleanup
    trap cleanup_test_services EXIT

    log_message "${BLUE}📊 Generation Service 종합 테스트 실행${NC}"
    log_message "시작 시간: $(date)"

    # Step 1: Prerequisites
    check_prerequisites

    # Step 2: Setup
    setup_test_environment

    # Step 3: Start services
    start_test_services

    # Step 4: Run tests
    run_unit_tests
    run_integration_tests
    run_api_tests
    run_performance_tests
    run_error_scenario_tests
    run_monitoring_tests

    # Step 5: Code quality
    run_code_quality_checks

    # Step 6: Docker tests
    run_docker_tests

    # Step 7: Generate report
    generate_test_report

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log_message "${GREEN}🎉 테스트 실행 완료!${NC}"
    log_message "총 실행 시간: ${duration}초"
    log_message "로그 파일: $LOG_FILE"

    # Final status
    if grep -q "❌" "$LOG_FILE"; then
        log_message "${RED}⚠️ 일부 테스트가 실패했습니다. 로그를 확인하세요.${NC}"
        exit 1
    else
        log_message "${GREEN}✅ 모든 테스트가 성공적으로 완료되었습니다!${NC}"
        exit 0
    fi
}

# Run main function
main "$@"
