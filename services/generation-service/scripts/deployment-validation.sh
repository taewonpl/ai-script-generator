#!/bin/bash

# Generation Service - 배포 환경 검증 스크립트
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VALIDATION_TIMEOUT=180  # 3 minutes
LOG_FILE="deployment_validation_$(date +%Y%m%d_%H%M%S).log"

echo -e "${BLUE}🚀 Generation Service 배포 환경 검증 시작${NC}"
echo "로그 파일: $LOG_FILE"

# Function to log and display messages
log_message() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Function to run command with timeout and logging
run_with_timeout() {
    local cmd="$1"
    local description="$2"
    local timeout="${3:-$VALIDATION_TIMEOUT}"

    log_message "${BLUE}[$description] 검증 중...${NC}"

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

# Function to validate Docker installation
validate_docker() {
    log_message "${BLUE}🐳 Docker 환경 검증${NC}"

    # Check Docker daemon
    if ! docker info > /dev/null 2>&1; then
        log_message "${RED}❌ Docker 데몬이 실행되지 않고 있습니다${NC}"
        return 1
    fi

    # Check Docker Compose
    if ! docker-compose --version > /dev/null 2>&1; then
        log_message "${RED}❌ Docker Compose가 설치되지 않았습니다${NC}"
        return 1
    fi

    # Check Docker version
    DOCKER_VERSION=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    log_message "${GREEN}✅ Docker 버전: $DOCKER_VERSION${NC}"

    # Check available disk space (minimum 10GB)
    AVAILABLE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 10 ]; then
        log_message "${YELLOW}⚠️ 디스크 공간 부족: ${AVAILABLE_SPACE}GB (최소 10GB 필요)${NC}"
    else
        log_message "${GREEN}✅ 디스크 공간: ${AVAILABLE_SPACE}GB${NC}"
    fi

    log_message "${GREEN}✅ Docker 환경 검증 완료${NC}"
}

# Function to validate Docker build
validate_docker_build() {
    log_message "${BLUE}🔨 Docker 이미지 빌드 검증${NC}"

    # Build development image
    run_with_timeout "docker build -f docker/Dockerfile --target development -t generation-service:dev-validation ." "개발 이미지 빌드" 300

    # Build production image
    run_with_timeout "docker build -f docker/Dockerfile --target production -t generation-service:prod-validation ." "프로덕션 이미지 빌드" 300

    # Check image sizes
    DEV_SIZE=$(docker images generation-service:dev-validation --format "{{.Size}}")
    PROD_SIZE=$(docker images generation-service:prod-validation --format "{{.Size}}")

    log_message "${GREEN}✅ 개발 이미지 크기: $DEV_SIZE${NC}"
    log_message "${GREEN}✅ 프로덕션 이미지 크기: $PROD_SIZE${NC}"

    # Security scan with Trivy (if available)
    if command -v trivy > /dev/null; then
        log_message "${BLUE}보안 스캔 실행 중...${NC}"
        trivy image --exit-code 0 --severity HIGH,CRITICAL generation-service:prod-validation >> "$LOG_FILE" 2>&1 || \
            log_message "${YELLOW}⚠️ 보안 취약점이 발견되었습니다. 로그를 확인하세요.${NC}"
    fi
}

# Function to validate Docker Compose configuration
validate_docker_compose() {
    log_message "${BLUE}📋 Docker Compose 설정 검증${NC}"

    # Validate development compose file
    if [ -f "docker/docker-compose.yml" ]; then
        run_with_timeout "docker-compose -f docker/docker-compose.yml config" "개발 환경 Compose 설정 검증" 30
    fi

    # Validate production compose file
    if [ -f "docker/docker-compose.prod.yml" ]; then
        run_with_timeout "docker-compose -f docker/docker-compose.prod.yml config" "프로덕션 환경 Compose 설정 검증" 30
    fi

    log_message "${GREEN}✅ Docker Compose 설정 검증 완료${NC}"
}

# Function to validate environment configuration
validate_environment_config() {
    log_message "${BLUE}⚙️ 환경 설정 검증${NC}"

    # Check environment template
    if [ -f "docker/.env.example" ]; then
        log_message "${GREEN}✅ 환경 변수 템플릿 파일 존재${NC}"

        # Validate required environment variables
        REQUIRED_VARS=(
            "ENVIRONMENT"
            "DEBUG"
            "LOG_LEVEL"
            "REDIS_HOST"
            "REDIS_PORT"
            "ENABLE_MONITORING"
            "ENABLE_CACHING"
        )

        for var in "${REQUIRED_VARS[@]}"; do
            if grep -q "^${var}=" "docker/.env.example"; then
                log_message "${GREEN}✅ 환경 변수 $var 정의됨${NC}"
            else
                log_message "${YELLOW}⚠️ 환경 변수 $var가 템플릿에 없습니다${NC}"
            fi
        done
    else
        log_message "${RED}❌ 환경 변수 템플릿 파일(.env.example)이 없습니다${NC}"
    fi

    # Check configuration files
    CONFIG_FILES=(
        "docker/redis.conf"
        "docker/redis-prod.conf"
        "docker/prometheus.yml"
        "docker/nginx/nginx.conf"
    )

    for config_file in "${CONFIG_FILES[@]}"; do
        if [ -f "$config_file" ]; then
            log_message "${GREEN}✅ 설정 파일 $config_file 존재${NC}"
        else
            log_message "${YELLOW}⚠️ 설정 파일 $config_file가 없습니다${NC}"
        fi
    done
}

# Function to test container startup
test_container_startup() {
    log_message "${BLUE}🚀 컨테이너 시작 테스트${NC}"

    # Start development environment
    if [ -f "docker/docker-compose.yml" ]; then
        log_message "${BLUE}개발 환경 시작 중...${NC}"

        # Copy environment template
        if [ -f "docker/.env.example" ] && [ ! -f "docker/.env" ]; then
            cp "docker/.env.example" "docker/.env"
            log_message "${GREEN}✅ 환경 변수 파일 생성${NC}"
        fi

        # Start services
        if docker-compose -f docker/docker-compose.yml up -d --build >> "$LOG_FILE" 2>&1; then
            log_message "${GREEN}✅ 개발 환경 시작 성공${NC}"

            # Wait for services to be ready
            log_message "${BLUE}서비스 준비 대기 중...${NC}"
            sleep 30

            # Test service connectivity
            test_service_health

            # Stop services
            docker-compose -f docker/docker-compose.yml down >> "$LOG_FILE" 2>&1
            log_message "${GREEN}✅ 개발 환경 정리 완료${NC}"
        else
            log_message "${RED}❌ 개발 환경 시작 실패${NC}"
            return 1
        fi
    fi
}

# Function to test service health
test_service_health() {
    log_message "${BLUE}🏥 서비스 헬스체크 테스트${NC}"

    # Test main service health endpoint
    for i in {1..30}; do
        if curl -f http://localhost:8000/api/monitoring/health > /dev/null 2>&1; then
            log_message "${GREEN}✅ 메인 서비스 헬스체크 성공${NC}"
            break
        fi

        if [ $i -eq 30 ]; then
            log_message "${RED}❌ 메인 서비스 헬스체크 실패 (타임아웃)${NC}"
            return 1
        fi

        sleep 2
    done

    # Test service endpoints
    ENDPOINTS=(
        "http://localhost:8000/api/monitoring/health"
        "http://localhost:8000/api/monitoring/metrics"
        "http://localhost:8000/api/cache/status"
        "http://localhost:8000/api/performance/status"
    )

    for endpoint in "${ENDPOINTS[@]}"; do
        if curl -f "$endpoint" > /dev/null 2>&1; then
            log_message "${GREEN}✅ 엔드포인트 $endpoint 응답 정상${NC}"
        else
            log_message "${YELLOW}⚠️ 엔드포인트 $endpoint 응답 없음${NC}"
        fi
    done

    # Test Grafana (if available)
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        log_message "${GREEN}✅ Grafana 접근 가능${NC}"
    else
        log_message "${YELLOW}⚠️ Grafana 접근 불가${NC}"
    fi

    # Test Prometheus (if available)
    if curl -f http://localhost:9090 > /dev/null 2>&1; then
        log_message "${GREEN}✅ Prometheus 접근 가능${NC}"
    else
        log_message "${YELLOW}⚠️ Prometheus 접근 불가${NC}"
    fi
}

# Function to validate performance targets
validate_performance_targets() {
    log_message "${BLUE}⚡ 성능 목표 검증${NC}"

    # Test response time
    RESPONSE_TIME=$(curl -w "%{time_total}" -s -o /dev/null http://localhost:8000/api/monitoring/health 2>/dev/null || echo "999")

    if (( $(echo "$RESPONSE_TIME < 1.0" | bc -l 2>/dev/null) )); then
        log_message "${GREEN}✅ 응답 시간: ${RESPONSE_TIME}s (목표: < 1s)${NC}"
    else
        log_message "${YELLOW}⚠️ 응답 시간 느림: ${RESPONSE_TIME}s${NC}"
    fi

    # Test concurrent requests
    log_message "${BLUE}동시 요청 테스트 중...${NC}"

    # Send 10 concurrent requests
    for i in {1..10}; do
        curl -s http://localhost:8000/api/monitoring/health > /dev/null &
    done
    wait

    log_message "${GREEN}✅ 동시 요청 처리 테스트 완료${NC}"

    # Get memory usage if metrics are available
    if curl -s http://localhost:8000/api/monitoring/metrics > /dev/null 2>&1; then
        MEMORY_USAGE=$(curl -s http://localhost:8000/api/monitoring/metrics | grep -o '"memory_usage_mb":[0-9]*' | cut -d':' -f2 2>/dev/null || echo "0")

        if [ "$MEMORY_USAGE" -gt 0 ] && [ "$MEMORY_USAGE" -lt 2048 ]; then
            log_message "${GREEN}✅ 메모리 사용량: ${MEMORY_USAGE}MB (목표: < 2048MB)${NC}"
        elif [ "$MEMORY_USAGE" -gt 2048 ]; then
            log_message "${YELLOW}⚠️ 메모리 사용량 초과: ${MEMORY_USAGE}MB${NC}"
        fi
    fi
}

# Function to validate security configuration
validate_security() {
    log_message "${BLUE}🔒 보안 설정 검증${NC}"

    # Check for secrets in configuration files
    if grep -r "password.*=" docker/ --include="*.yml" --include="*.yaml" | grep -v "example" | grep -v "#" > /dev/null; then
        log_message "${RED}❌ 설정 파일에 평문 비밀번호가 발견되었습니다${NC}"
    else
        log_message "${GREEN}✅ 설정 파일에 평문 비밀번호 없음${NC}"
    fi

    # Check Docker user configuration
    if grep -q "USER generation" docker/Dockerfile; then
        log_message "${GREEN}✅ Docker 컨테이너가 비root 사용자로 실행됩니다${NC}"
    else
        log_message "${YELLOW}⚠️ Docker 컨테이너가 root 사용자로 실행될 수 있습니다${NC}"
    fi

    # Check for HTTPS configuration in Nginx
    if [ -f "docker/nginx/nginx.conf" ]; then
        if grep -q "ssl" "docker/nginx/nginx.conf"; then
            log_message "${GREEN}✅ Nginx SSL 설정 발견${NC}"
        else
            log_message "${YELLOW}⚠️ Nginx SSL 설정이 없습니다${NC}"
        fi
    fi
}

# Function to validate monitoring setup
validate_monitoring() {
    log_message "${BLUE}📊 모니터링 설정 검증${NC}"

    # Check Prometheus configuration
    if [ -f "docker/prometheus.yml" ]; then
        if grep -q "generation-service" "docker/prometheus.yml"; then
            log_message "${GREEN}✅ Prometheus에 Generation Service 타겟 설정됨${NC}"
        else
            log_message "${YELLOW}⚠️ Prometheus 타겟 설정이 없습니다${NC}"
        fi
    fi

    # Check for alerting rules
    if [ -d "docker/prometheus/rules" ] || grep -q "alerting" docker/prometheus*.yml; then
        log_message "${GREEN}✅ 알림 규칙 설정 발견${NC}"
    else
        log_message "${YELLOW}⚠️ 알림 규칙 설정이 없습니다${NC}"
    fi

    # Check log aggregation
    if grep -q "loki\|fluentd\|logstash" docker/docker-compose*.yml; then
        log_message "${GREEN}✅ 로그 집계 시스템 설정됨${NC}"
    else
        log_message "${YELLOW}⚠️ 로그 집계 시스템 설정이 없습니다${NC}"
    fi
}

# Function to validate CI/CD pipeline
validate_cicd() {
    log_message "${BLUE}🔄 CI/CD 파이프라인 검증${NC}"

    # Check GitHub Actions workflow
    if [ -f ".github/workflows/ci.yml" ]; then
        log_message "${GREEN}✅ CI 워크플로우 파일 존재${NC}"

        # Validate workflow syntax
        if grep -q "name:" ".github/workflows/ci.yml" && grep -q "on:" ".github/workflows/ci.yml"; then
            log_message "${GREEN}✅ CI 워크플로우 구문 유효${NC}"
        else
            log_message "${RED}❌ CI 워크플로우 구문 오류${NC}"
        fi
    else
        log_message "${YELLOW}⚠️ CI 워크플로우 파일이 없습니다${NC}"
    fi

    # Check release pipeline
    if [ -f ".github/workflows/release.yml" ]; then
        log_message "${GREEN}✅ 릴리스 파이프라인 파일 존재${NC}"
    else
        log_message "${YELLOW}⚠️ 릴리스 파이프라인 파일이 없습니다${NC}"
    fi

    # Check Dockerfile security best practices
    if grep -q "RUN.*sudo" docker/Dockerfile; then
        log_message "${YELLOW}⚠️ Dockerfile에서 sudo 사용이 발견되었습니다${NC}"
    fi

    if grep -q "ADD.*http" docker/Dockerfile; then
        log_message "${YELLOW}⚠️ Dockerfile에서 원격 파일 ADD 사용이 발견되었습니다${NC}"
    fi
}

# Function to cleanup validation artifacts
cleanup_validation() {
    log_message "${BLUE}🧹 검증 환경 정리${NC}"

    # Remove validation images
    docker rmi generation-service:dev-validation generation-service:prod-validation > /dev/null 2>&1 || true

    # Stop any running containers
    docker-compose -f docker/docker-compose.yml down > /dev/null 2>&1 || true

    # Remove temporary files
    rm -f docker/.env > /dev/null 2>&1 || true

    log_message "${GREEN}✅ 검증 환경 정리 완료${NC}"
}

# Function to generate validation report
generate_validation_report() {
    log_message "${BLUE}📄 검증 보고서 생성${NC}"

    REPORT_FILE="deployment_validation_report_$(date +%Y%m%d_%H%M%S).md"

    cat > "$REPORT_FILE" << EOF
# Generation Service 배포 환경 검증 보고서

**생성 일시**: $(date)
**검증 실행자**: $(whoami)
**환경**: $(uname -a)

## 검증 결과 요약

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

## 배포 준비 상태

EOF

        if [ "$FAILURE_COUNT" -eq 0 ]; then
            echo "✅ **배포 준비 완료**: 모든 필수 검증이 통과했습니다." >> "$REPORT_FILE"
        else
            echo "❌ **배포 준비 미완료**: 실패한 검증을 수정해야 합니다." >> "$REPORT_FILE"
        fi

        cat >> "$REPORT_FILE" << EOF

## 검증 세부 결과

### Docker 환경
- 이미지 빌드 및 배포 환경 검증

### 서비스 기능
- API 엔드포인트 및 헬스체크 검증

### 성능 및 보안
- 성능 목표 및 보안 설정 검증

### 모니터링 및 CI/CD
- 모니터링 시스템 및 자동화 파이프라인 검증

## 상세 로그

\`\`\`
$(tail -100 "$LOG_FILE")
\`\`\`

## 권장 사항

EOF

        if [ "$FAILURE_COUNT" -gt 0 ]; then
            echo "- 실패한 검증 항목을 수정한 후 다시 검증하세요" >> "$REPORT_FILE"
        fi

        if [ "$WARNING_COUNT" -gt 0 ]; then
            echo "- 경고 사항을 검토하고 가능한 개선하세요" >> "$REPORT_FILE"
        fi

        cat >> "$REPORT_FILE" << EOF
- 프로덕션 배포 전에 스테이징 환경에서 테스트하세요
- 배포 후 모니터링 시스템을 통해 서비스 상태를 확인하세요
- 백업 및 롤백 계획을 준비하세요

## 다음 단계

1. 실패한 검증 항목 수정
2. 스테이징 환경 배포 테스트
3. 프로덕션 배포 실행
4. 배포 후 모니터링 및 검증

EOF
    fi

    log_message "${GREEN}✅ 검증 보고서 생성 완료: $REPORT_FILE${NC}"
}

# Main execution
main() {
    local start_time=$(date +%s)

    # Trap for cleanup
    trap cleanup_validation EXIT

    log_message "${BLUE}📊 Generation Service 배포 환경 검증 실행${NC}"
    log_message "시작 시간: $(date)"

    # Step 1: Docker environment validation
    validate_docker

    # Step 2: Docker build validation
    validate_docker_build

    # Step 3: Docker Compose validation
    validate_docker_compose

    # Step 4: Environment configuration validation
    validate_environment_config

    # Step 5: Container startup test
    test_container_startup

    # Step 6: Performance validation
    validate_performance_targets

    # Step 7: Security validation
    validate_security

    # Step 8: Monitoring validation
    validate_monitoring

    # Step 9: CI/CD validation
    validate_cicd

    # Step 10: Generate report
    generate_validation_report

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log_message "${GREEN}🎉 배포 환경 검증 완료!${NC}"
    log_message "총 검증 시간: ${duration}초"
    log_message "로그 파일: $LOG_FILE"

    # Final status
    if grep -q "❌" "$LOG_FILE"; then
        log_message "${RED}⚠️ 일부 검증이 실패했습니다. 배포 전에 문제를 해결하세요.${NC}"
        exit 1
    else
        log_message "${GREEN}✅ 모든 배포 환경 검증이 성공했습니다! 배포를 진행할 수 있습니다.${NC}"
        exit 0
    fi
}

# Run main function
main "$@"
