# 관찰가능성 가이드 (Observability Guide)

> **AI Script Generator v3.0 모니터링, 로깅, 메트릭 수집 가이드**

## 📊 개요 (Overview)

AI Script Generator v3.0은 포괄적인 관찰가능성(Observability) 기능을 제공합니다:
- **헬스체크**: 서비스 상태 모니터링
- **메트릭**: Prometheus 호환 메트릭 수집
- **구조화된 로깅**: JSON 형식의 중앙화된 로그
- **보안 모니터링**: 요청 패턴 및 보안 이벤트 추적

## 🏥 헬스체크 엔드포인트 (Health Check Endpoints)

### 기본 헬스체크
모든 서비스에서 기본 헬스체크를 제공합니다:

```bash
# Project Service
curl http://localhost:8001/api/v1/health

# Generation Service  
curl http://localhost:8002/api/v1/health
```

**응답 예시:**
```json
{
  "service": "Generation Service",
  "version": "3.0.0", 
  "status": "healthy",
  "timestamp": "2025-08-27T00:20:00.000Z",
  "port": 8002
}
```

### 상세 헬스체크 (Generation Service)
종속성 상태를 포함한 상세 헬스체크:

```bash
curl http://localhost:8002/api/v1/health/detailed
```

**응답 예시:**
```json
{
  "service": "Generation Service",
  "status": "healthy",
  "dependencies": {
    "database": {"status": "healthy"},
    "project_service": {"status": "healthy", "url": "http://project-service:8001"}
  },
  "ai_providers": {
    "openai": {"configured": true, "api_key_masked": "<YOUR_TOKEN_HERE>"}, <!-- pragma: allowlist secret -->
    "anthropic": {"configured": true, "api_key_masked": "<YOUR_TOKEN_HERE>"} <!-- pragma: allowlist secret -->
  },
  "storage": {
    "redis": {"status": "healthy", "ping_successful": true},
    "chroma": {"status": "healthy", "path_writable": true},
    "filesystem": {"overall_status": "healthy"}
  }
}
```

## 📈 메트릭 엔드포인트 (Metrics Endpoints)

### Prometheus 메트릭
Prometheus가 스크래핑할 수 있는 표준 형식:

```bash
# Project Service
curl http://localhost:8001/api/v1/metrics

# Generation Service
curl http://localhost:8002/api/v1/metrics
```

**메트릭 종류:**

#### Project Service
- `project_service_uptime_seconds`: 서비스 가동 시간
- `project_service_requests_total`: 총 요청 수
- `project_service_requests_duration_seconds`: 요청 처리 시간 합계
- `project_service_projects_total`: 데이터베이스의 총 프로젝트 수
- `project_service_episodes_total`: 데이터베이스의 총 에피소드 수

#### Generation Service  
- `generation_service_uptime_seconds`: 서비스 가동 시간
- `generation_service_requests_total`: 총 요청 수
- `generation_service_requests_duration_seconds`: 요청 처리 시간 합계
- `generation_service_jobs_active`: 현재 활성 작업 수
- `generation_service_jobs_completed_total`: 완료된 작업 총 수
- `generation_service_jobs_failed_total`: 실패한 작업 총 수
- `generation_service_sse_connections_active`: 활성 SSE 연결 수

### JSON 메트릭
JSON 형식으로도 메트릭을 제공합니다:

```bash
curl http://localhost:8002/api/v1/metrics/json
```

## 🎯 Kubernetes 스타일 프로브

### Readiness Probe
서비스가 트래픽을 받을 준비가 되었는지 확인:

```bash
curl http://localhost:8001/api/v1/readyz
curl http://localhost:8002/api/v1/readyz
```

**성공 응답 (200):**
```json
{
  "status": "ready",
  "timestamp": "2025-08-27T00:20:00.000Z",
  "checks": {
    "database": true,
    "service_healthy": true
  },
  "service": "project-service",
  "version": "1.0.0"
}
```

### Liveness Probe  
서비스가 살아있고 재시작이 필요하지 않은지 확인:

```bash
curl http://localhost:8001/api/v1/livez
curl http://localhost:8002/api/v1/livez
```

**응답 (200):**
```json
{
  "status": "alive",
  "timestamp": "2025-08-27T00:20:00.000Z", 
  "service": "project-service",
  "version": "1.0.0"
}
```

## 📝 구조화된 로깅 (Structured Logging)

### 로그 형식
모든 서비스는 JSON 형식의 구조화된 로그를 생성합니다:

```json
{
  "timestamp": "2025-08-27T00:20:00.123456",
  "level": "INFO",
  "logger": "generation-service.main",
  "message": "API routers registered",
  "service": {
    "name": "ai-script-generator",
    "version": "3.0.0"
  },
  "process": {
    "pid": 12345,
    "thread_id": 140123456789,
    "thread_name": "MainThread"
  },
  "location": {
    "file": "main.py",
    "function": "startup_event", 
    "line": 97,
    "module": "main"
  }
}
```

### 보안 로깅
보안 관련 이벤트는 자동으로 로그에 기록됩니다:

- 잘못된 API 키 시도
- 속도 제한 위반
- 악성 요청 패턴 감지
- 인증 실패

**보안 로그 예시:**
```json
{
  "timestamp": "2025-08-27T00:20:00.123456",
  "level": "WARNING", 
  "logger": "generation-service.middleware.security",
  "message": "Invalid API key attempt from 192.168.1.100: sk-test1...",
  "security": {
    "event_type": "authentication_failure",
    "client_ip": "192.168.1.100",
    "user_agent": "curl/7.68.0",
    "api_key_prefix": "<SET_IN_ENV>" <!-- pragma: allowlist secret -->
  }
}
```

## 🔍 모니터링 설정

### Prometheus 구성
`prometheus.yml` 설정 예시:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ai-script-generator-project'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: '/api/v1/metrics'
    scrape_interval: 10s
    
  - job_name: 'ai-script-generator-generation' 
    static_configs:
      - targets: ['localhost:8002']
    metrics_path: '/api/v1/metrics'
    scrape_interval: 10s
```

### Grafana 대시보드
권장 메트릭 시각화:

#### 서비스 개요
- 서비스 가동 시간
- 요청 처리량 (RPS)
- 평균 응답 시간
- 오류율

#### Generation Service 특화
- 활성 작업 수
- 작업 완료율
- SSE 연결 수
- AI 모델 응답 시간

#### Project Service 특화  
- 데이터베이스 연결 상태
- 프로젝트/에피소드 생성률
- ChromaDB 성능

### Alerting 규칙
Prometheus Alertmanager 규칙 예시:

```yaml
groups:
- name: ai-script-generator.rules
  rules:
  - alert: ServiceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "AI Script Generator service is down"
      
  - alert: HighErrorRate
    expr: rate(generation_service_jobs_failed_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate in generation service"
      
  - alert: SSEConnectionsHigh
    expr: generation_service_sse_connections_active > 100
    for: 5m
    labels:
      severity: info
    annotations:
      summary: "High number of SSE connections"
```

## 🚨 트러블슈팅

### 일반적인 문제

#### 헬스체크 실패
```bash
# 상세 헬스체크로 원인 파악
curl http://localhost:8002/api/v1/health/detailed

# 로그 확인
docker compose logs generation-service
```

#### 메트릭 수집 실패
```bash  
# 메트릭 엔드포인트 직접 확인
curl http://localhost:8001/api/v1/metrics

# JSON 형식으로 확인
curl http://localhost:8001/api/v1/metrics/json
```

#### 높은 응답 시간
1. 메트릭에서 성능 지표 확인
2. 활성 작업 수 모니터링
3. 데이터베이스 연결 상태 확인

### 로그 분석
```bash
# 특정 레벨 로그 필터링
docker compose logs generation-service | grep '"level":"ERROR"'

# 보안 이벤트 모니터링
docker compose logs | grep '"security":'

# 성능 관련 로그
docker compose logs | grep '"performance":'
```

## 📋 모니터링 체크리스트

### 운영 환경 배포 전
- [ ] 모든 헬스체크 엔드포인트 정상 작동
- [ ] Prometheus 메트릭 수집 확인
- [ ] Grafana 대시보드 구성 완료
- [ ] 알림 규칙 설정 및 테스트
- [ ] 로그 중앙화 시스템 연동

### 일일 모니터링
- [ ] 서비스 가동 시간 확인
- [ ] 오류율 모니터링
- [ ] 성능 지표 검토
- [ ] 보안 이벤트 검토

### 주간 검토
- [ ] 메트릭 트렌드 분석
- [ ] 용량 계획 검토
- [ ] 알림 규칙 최적화
- [ ] 대시보드 업데이트

---

*마지막 업데이트: 2025년 8월 - 포괄적인 관찰가능성 시스템 구현 완료*