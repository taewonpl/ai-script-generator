# Idempotency-Key 시스템과 저장 실패 복구 메커니즘 구현

## 개요

AI Script Generator v3에 Idempotency-Key 시스템과 저장 실패 복구 메커니즘을 구현하여 안정적이고 신뢰할 수 있는 API 운영을 보장합니다.

## 1. Idempotency-Key 시스템

### 1.1 구현된 기능

#### Redis 기반 키-결과 매핑
- **파일**: `services/generation-service/src/generation_service/cache/idempotency_cache.py`
- **TTL**: 24시간 (설정 가능)
- **저장소**: Redis with fallback to in-memory
- **기능**:
  - 키 생성 및 검증
  - 요청 데이터 해시 비교
  - 응답 캐싱 및 반환
  - 자동 만료 처리

#### API 엔드포인트 통합
- **Generation Service**: `/api/v1/generations`, `/generate`, `/hybrid-script`, `/custom-workflow`
- **Project Service**: `/projects/{id}/episodes`
- **동작 방식**:
  - 201 Created → 200 OK (재요청 시)
  - `Idempotency-Key` 헤더 검증
  - `Idempotency-Replayed: true` 헤더 추가

#### 미들웨어 구현
- **파일**: 
  - `services/generation-service/src/generation_service/api/idempotency_middleware.py`
  - `services/project-service/src/project_service/api/idempotency_middleware.py`
- **기능**:
  - 자동 키 검증 및 충돌 감지
  - 응답 캐싱 및 반환
  - 409 Conflict 처리

### 1.2 사용법

```bash
# 첫 번째 요청
curl -X POST /api/v1/generations \
  -H "Idempotency-Key: idem_1703776800_abc123" \
  -d '{"prompt": "Generate a drama script"}'
# Response: 201 Created

# 동일 키로 재요청  
curl -X POST /api/v1/generations \
  -H "Idempotency-Key: idem_1703776800_abc123" \
  -d '{"prompt": "Generate a drama script"}'
# Response: 200 OK (cached result)
```

## 2. 저장 실패 복구 시스템

### 2.1 Job 상태 확장

**기존 상태**:
- `pending`, `processing`, `completed`, `failed`, `cancelled`

**확장된 상태**:
- `completed_pending_save`: 생성 완료, 저장 대기 중
- `save_failed`: 저장 실패

### 2.2 백그라운드 재시도 큐

#### 구현 파일
- **큐 시스템**: `services/generation-service/src/generation_service/services/retry_queue.py`
- **저장 프로세서**: `services/generation-service/src/generation_service/services/save_processors.py`
- **API 엔드포인트**: `services/generation-service/src/generation_service/api/retry_endpoints.py`

#### 주요 기능
- **Exponential Backoff**: 1s → 2s → 4s → 8s → 16s (최대 5회)
- **Redis 기반 큐**: 분산 환경 지원
- **Dead Letter Queue**: 최대 재시도 후 실패한 작업 격리
- **작업 유형**:
  - `SAVE_GENERATION`: 생성 결과 저장
  - `SAVE_EPISODE`: 에피소드 저장  
  - `SAVE_PROJECT`: 프로젝트 저장
  - `CLEANUP_CACHE`: 캐시 정리

#### 재시도 로직
```python
class ExponentialBackoff:
    @staticmethod
    def calculate_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 16.0):
        delay = base_delay * (2 ** attempt)
        return min(delay, max_delay)

# 재시도 스케줄: 1s, 2s, 4s, 8s, 16s
```

### 2.3 워커 시스템

#### 백그라운드 워커
- **파일**: `services/generation-service/src/generation_service/services/retry_queue.py`
- **기능**:
  - 비동기 작업 처리
  - 배치 처리 (기본 10개)
  - 자동 복구 및 재시작
  - 폴링 간격: 1초

#### 시작/종료 관리
- **파일**: `services/generation-service/src/generation_service/startup/retry_system.py`
- **FastAPI 생명주기 통합**
- **Graceful shutdown** 지원

## 3. Frontend 사용자 경험

### 3.1 저장 진행 상태 표시

#### SaveProgressIndicator 컴포넌트
- **파일**: `frontend/src/features/script-generation/components/SaveProgressIndicator.tsx`
- **상태 표시**:
  - `saving`: 저장 중...
  - `completed_pending_save`: 대본 생성 완료, 저장 중...
  - `save_failed`: 저장에 실패했습니다
  - `completed`: 저장 완료

#### 수동 저장 버튼
```tsx
<Button
  variant="contained" 
  startIcon={<Save />}
  onClick={onManualSave}
  color="primary"
>
  수동 저장
</Button>
```

### 3.2 실시간 재시도 진행 표시

#### RetryProgressDisplay 컴포넌트
- **파일**: `frontend/src/features/script-generation/components/RetryProgressDisplay.tsx`
- **기능**:
  - 재시도 진행률 표시
  - 실시간 카운트다운
  - 재시도 내역 상세 정보
  - 자동 새로고침 (5초 간격)

#### 진행 상황 요소
- 진행률 바 (Linear Progress)
- 재시도 횟수 표시 (2/5)
- 다음 재시도까지 시간 표시
- 오류 메시지 표시
- 재시도 내역 타임라인

### 3.3 통합된 사용자 인터페이스

#### GenerationResults 컴포넌트 업데이트
- **파일**: `frontend/src/features/script-generation/components/GenerationResults.tsx`
- **추가된 기능**:
  - 저장 진행 상태 표시
  - 재시도 진행 상황 모니터링
  - 수동 저장 옵션

## 4. API 엔드포인트

### 4.1 재시도 관리 API

```bash
# 큐 통계 조회
GET /api/v1/retry/queue/stats

# 작업 상태 조회  
GET /api/v1/retry/job/{job_id}/status

# 생성 재시도 진행 상황
GET /api/v1/retry/generation/{generation_id}/retry-progress

# 수동 저장 트리거
POST /api/v1/retry/generation/{generation_id}/manual-save

# 오래된 작업 정리
POST /api/v1/retry/cleanup/old-jobs?older_than_hours=24
```

### 4.2 응답 형식

```json
{
  "success": true,
  "message": "Queue statistics retrieved successfully",
  "data": {
    "pending": 3,
    "processing": 1,
    "dead_letter": 0,
    "total": 4
  }
}
```

## 5. 설정 및 배포

### 5.1 Redis 설정

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
```

### 5.2 환경 변수

```env
REDIS_URL=redis://localhost:6379
IDEMPOTENCY_TTL_SECONDS=86400
MAX_RETRY_ATTEMPTS=5
RETRY_BASE_DELAY=1.0
RETRY_MAX_DELAY=16.0
PROJECT_SERVICE_URL=http://localhost:8002
```

### 5.3 미들웨어 설정

```python
# main.py
from .startup.middleware_setup import setup_all_middleware
from .startup.retry_system import startup_event, shutdown_event

app = FastAPI()
setup_all_middleware(app)

@app.on_event("startup")
async def startup():
    await startup_event()

@app.on_event("shutdown") 
async def shutdown():
    await shutdown_event()
```

## 6. 모니터링 및 로깅

### 6.1 메트릭스

- **대기 중인 작업**: `pending_jobs_count`
- **처리 중인 작업**: `processing_jobs_count` 
- **실패한 작업**: `failed_jobs_count`
- **DLQ 작업**: `dead_letter_jobs_count`
- **평균 재시도 횟수**: `avg_retry_attempts`
- **성공률**: `success_rate_percent`

### 6.2 로그 포맷

```json
{
  "timestamp": "2024-01-01T10:00:00Z",
  "level": "INFO",
  "service": "generation-service",
  "component": "retry-queue",
  "message": "Job processed successfully",
  "job_id": "retry_123",
  "job_type": "SAVE_GENERATION",
  "attempt": 2,
  "duration_ms": 1250
}
```

## 7. 장점 및 효과

### 7.1 안정성 향상
- **중복 요청 방지**: Idempotency-Key로 완전한 멱등성 보장
- **저장 실패 복구**: 자동 재시도로 일시적 장애 극복
- **데이터 일관성**: 원자적 작업 처리

### 7.2 사용자 경험 개선
- **실시간 진행 상황**: 투명한 저장 과정 표시
- **수동 복구 옵션**: 사용자가 직접 문제 해결 가능
- **명확한 상태 표시**: 각 단계별 상태 정보 제공

### 7.3 운영 효율성
- **자동 복구**: 인력 개입 없이 대부분의 장애 해결
- **모니터링**: 실시간 큐 상태 및 성능 지표
- **확장성**: Redis 기반 분산 처리 지원

## 8. 향후 개선 사항

### 8.1 고급 기능
- **우선순위 큐**: 중요도별 작업 처리 순서 조정
- **배치 처리**: 관련 작업들 그룹화하여 효율성 향상
- **조건부 재시도**: 오류 유형별 맞춤 재시도 정책

### 8.2 모니터링 강화
- **알림 시스템**: 임계치 초과 시 자동 알림
- **대시보드**: 실시간 큐 상태 시각화
- **성능 분석**: 재시도 패턴 및 성공률 분석

### 8.3 보안 강화
- **키 암호화**: Idempotency-Key 암호화 저장
- **접근 제어**: 재시도 관리 API 권한 제어
- **감사 로그**: 모든 재시도 작업 추적 기록