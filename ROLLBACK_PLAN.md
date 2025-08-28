# 🔄 Durable Worker 시스템 롤백 계획

## 📋 개요

RQ 기반 Durable Worker 시스템에서 FastAPI BackgroundTasks로 안전하게 롤백하는 절차입니다.

---

## 🚨 롤백 시나리오

### 언제 롤백하나?
1. **RQ 서버 장애**: Redis 완전 중단, 복구 불가능한 데이터 손실
2. **성능 저하**: 워커 시스템으로 인한 처리 속도 저하 (>50% 지연)
3. **메모리 누수**: RQ 프로세스 메모리 사용량 급증으로 시스템 불안정
4. **호환성 문제**: 의존성 충돌, 라이브러리 호환성 문제
5. **긴급 대응**: 프로덕션 장애 시 빠른 정상화 필요

### 롤백 의사결정 기준
```yaml
# 자동 롤백 트리거
- Redis 연결 실패 > 5분
- Worker 프로세스 크래시 > 3회/10분
- Queue 처리 지연 > 10분
- 시스템 메모리 사용률 > 90%

# 수동 롤백 고려
- 사용자 신고 급증 (>10건/시간)
- API 응답 시간 >5초 지속
- 데이터 일관성 문제 발견
```

---

## ⚡ 긴급 롤백 (2분 이내)

### 1단계: Feature Flag OFF
```bash
# 1. 환경변수 즉시 변경
export USE_DURABLE_WORKER=false
export WORKER_SYSTEM_ENABLED=false

# 2. Generation Service 재시작 (무중단)
curl -X POST http://localhost:8002/api/admin/graceful-restart \
     -H "Authorization: Bearer ${ADMIN_TOKEN}"

# 3. 설정 확인
curl -s http://localhost:8002/health | jq '.worker_system'
# 결과: {"enabled": false, "type": "background_tasks"}
```

### 2단계: 진행 중인 작업 처리
```bash
# 큐에 남은 작업 확인
redis-cli LLEN rq:queue:rag_processing
redis-cli LRANGE rq:queue:rag_processing 0 -1

# 진행 중인 작업 BackgroundTasks로 재전송
curl -X POST http://localhost:8002/api/admin/migrate-pending-jobs \
     -d '{"source": "rq_queue", "target": "background_tasks"}' \
     -H "Content-Type: application/json"
```

### 3단계: 즉시 검증
```bash
# 새 작업이 BackgroundTasks로 처리되는지 확인
curl -X POST http://localhost:8002/api/generation \
     -H "Content-Type: application/json" \
     -H "Idempotency-Key: rollback-test-$(date +%s)" \
     -d '{"project_id": "test", "episode_data": {"title": "test"}}'

# 처리 방식 확인 (로그에서)
tail -f /var/log/generation-service.log | grep "Processing.*background_task"
```

---

## 🛠️ 체계적 롤백 (10분 이내)

### 4단계: 데이터 동기화
```python
# rollback_data_sync.py
import asyncio
import redis
from generation_service.database import get_db
from generation_service.models import GenerationJob

async def sync_job_statuses():
    """RQ 작업 상태를 DB에 동기화"""
    redis_client = redis.Redis(host='localhost', port=6379, db=5)
    
    # RQ에서 완료된 작업들 확인
    completed_jobs = redis_client.keys("rq:job:*")
    
    async with get_db() as db:
        for job_key in completed_jobs:
            job_data = redis_client.hgetall(job_key)
            if job_data.get('status') == 'finished':
                job_id = job_key.decode().split(':')[-1]
                
                # DB 상태 업데이트
                db_job = db.query(GenerationJob).filter_by(id=job_id).first()
                if db_job and db_job.status != 'completed':
                    db_job.status = 'completed'
                    db_job.completed_at = datetime.utcnow()
                    db.commit()
                    print(f"Synced job {job_id}: completed")

# 실행
asyncio.run(sync_job_statuses())
```

### 5단계: 컴포넌트별 롤백

#### A. Generation Service 롤백
```bash
# 1. RQ 워커 프로세스 종료
pkill -f "rq worker"
systemctl stop rag-worker-service

# 2. RQ 관련 imports 비활성화 (조건부 import로 이미 처리됨)
# worker_adapter.py에서 USE_DURABLE_WORKER=false시 자동 비활성화

# 3. Redis 연결 정리
redis-cli FLUSHDB 5  # RQ 데이터만 삭제 (DB 5)

# 4. 메모리 정리
systemctl restart ai-script-generation-service
```

#### B. Frontend 대응
```typescript
// src/hooks/useGenerationJob.ts 롤백 확인
// Feature flag에 따라 자동으로 BackgroundTasks 모드로 전환됨

// SSE 연결 모니터링 강화
const [connectionMode, setConnectionMode] = useState<'rq' | 'background_tasks'>();

useEffect(() => {
  // 서버 모드 확인
  fetch('/api/generation/system-info')
    .then(res => res.json())
    .then(data => setConnectionMode(data.worker_system.type));
}, []);
```

#### C. 모니터링 시스템 조정
```yaml
# prometheus/alerts.yml - RQ 관련 알림 비활성화
- alert: RQWorkerDown
  expr: up{job="rq-worker"} == 0
  # 임시 비활성화
  # for: 5m
  
- alert: BackgroundTasksHigh
  # BackgroundTasks 모드에서 활성화
  expr: background_tasks_active > 50
  for: 2m
  annotations:
    summary: "High number of background tasks (rollback mode)"
```

### 6단계: 성능 최적화 (롤백 후)
```python
# background_tasks_optimizer.py
from fastapi import BackgroundTasks
from concurrent.futures import ThreadPoolExecutor
import asyncio

# BackgroundTasks 성능 향상
class OptimizedBackgroundTasks(BackgroundTasks):
    def __init__(self, max_workers: int = 4):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def add_task(self, func, *args, **kwargs):
        """비동기 작업을 스레드풀에서 실행"""
        if asyncio.iscoroutinefunction(func):
            # 비동기 함수는 그대로 추가
            super().add_task(func, *args, **kwargs)
        else:
            # 동기 함수는 스레드풀에서 실행
            future = self.executor.submit(func, *args, **kwargs)
            super().add_task(self._await_future, future)
    
    async def _await_future(self, future):
        """Future 결과 대기"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, future.result)
```

---

## ✅ 롤백 검증 체크리스트

### 즉시 확인 (롤백 후 2분)
- [ ] `USE_DURABLE_WORKER=false` 환경변수 적용됨
- [ ] Generation Service 정상 응답 (<2초)
- [ ] 새 작업이 BackgroundTasks로 처리됨
- [ ] RQ 워커 프로세스 완전 종료됨
- [ ] SSE 연결 정상 동작

### 기능 확인 (롤백 후 10분)
- [ ] 대본 생성 기능 정상 동작
- [ ] 실시간 진행률 업데이트 정상
- [ ] 에피소드 저장 및 번호 할당 정상
- [ ] RAG 문서 처리 정상 (BackgroundTasks)
- [ ] 에러 없는 연속 작업 10건 이상 처리

### 성능 확인 (롤백 후 30분)
```bash
# 응답 시간 측정
ab -n 100 -c 10 http://localhost:8002/api/generation

# 결과 확인 기준:
# - 평균 응답 시간 < 3초
# - 99%ile 응답 시간 < 10초
# - 실패율 < 1%

# 메모리 사용량 확인
ps aux | grep generation-service
# RSS < 500MB (롤백 후 메모리 사용량 감소 확인)
```

---

## 📊 롤백 모니터링

### 실시간 대시보드
```bash
# 롤백 상태 모니터링 스크립트
while true; do
    echo "=== Rollback Status Check ==="
    echo "Worker System: $(curl -s http://localhost:8002/health | jq -r '.worker_system.enabled')"
    echo "Active Tasks: $(curl -s http://localhost:8002/api/admin/stats | jq '.background_tasks.active')"
    echo "Memory Usage: $(ps -o rss= -p $(pgrep generation-service) | awk '{print $1/1024 "MB"}')"
    echo "RQ Processes: $(pgrep -f 'rq worker' | wc -l)"
    echo "========================="
    sleep 10
done
```

### 핵심 메트릭 추적
```python
# rollback_metrics.py
import time
import requests
from prometheus_client import start_http_server, Gauge, Counter

# 롤백 상태 메트릭
rollback_active = Gauge('system_rollback_active', 'System is in rollback mode')
rollback_performance = Gauge('rollback_performance_ratio', 'Performance vs pre-rollback')
rollback_errors = Counter('rollback_errors_total', 'Errors during rollback')

def track_rollback_metrics():
    """롤백 상태 메트릭 수집"""
    try:
        # 시스템 상태 확인
        response = requests.get('http://localhost:8002/health')
        health_data = response.json()
        
        rollback_active.set(0 if health_data['worker_system']['enabled'] else 1)
        
        # 성능 비교 (롤백 전 기준점 대비)
        stats_response = requests.get('http://localhost:8002/api/admin/stats')
        stats = stats_response.json()
        
        avg_response_time = stats.get('average_response_time', 0)
        baseline_response_time = 2.0  # 롤백 전 기준
        
        performance_ratio = baseline_response_time / max(avg_response_time, 0.1)
        rollback_performance.set(performance_ratio)
        
    except Exception as e:
        rollback_errors.inc()
        print(f"Rollback monitoring error: {e}")

if __name__ == '__main__':
    start_http_server(8090)  # 메트릭 서버
    
    while True:
        track_rollback_metrics()
        time.sleep(30)
```

---

## 🔧 문제별 대응 시나리오

### 시나리오 1: 일부 작업이 RQ에 남아있는 경우
```bash
# 문제: 롤백 후에도 RQ 큐에 작업이 남음
redis-cli LLEN rq:queue:rag_processing  # > 0

# 해결: 수동 작업 마이그레이션
python3 scripts/migrate_rq_to_background.py
```

```python
# scripts/migrate_rq_to_background.py
import redis
import json
import asyncio
from generation_service.services.generation import GenerationService

async def migrate_pending_jobs():
    """RQ 대기열의 작업을 BackgroundTasks로 마이그레이션"""
    redis_client = redis.Redis(host='localhost', port=6379, db=5)
    generation_service = GenerationService()
    
    # RQ 대기열에서 작업 가져오기
    while True:
        job_data = redis_client.lpop('rq:queue:rag_processing')
        if not job_data:
            break
            
        job_info = json.loads(job_data)
        job_id = job_info['id']
        args = job_info['data']['args']
        
        # BackgroundTasks로 재전송
        try:
            await generation_service.restart_job_as_background_task(
                job_id=job_id,
                **args[0]  # 첫 번째 인자는 일반적으로 job payload
            )
            print(f"Migrated job {job_id} to BackgroundTasks")
        except Exception as e:
            print(f"Failed to migrate job {job_id}: {e}")
            # DLQ에 추가
            redis_client.lpush('rq:queue:migration_failed', job_data)

asyncio.run(migrate_pending_jobs())
```

### 시나리오 2: SSE 연결 문제
```python
# 문제: 롤백 후 SSE 연결 불안정
# 해결: SSE 연결 강화 및 재연결 로직

# frontend/src/hooks/useGenerationSSE.ts
const useGenerationSSE = (jobId: string) => {
  const [eventSource, setEventSource] = useState<EventSource | null>(null);
  const [reconnectCount, setReconnectCount] = useState(0);
  
  useEffect(() => {
    const connectSSE = () => {
      const source = new EventSource(`/api/generation/${jobId}/events`);
      
      source.addEventListener('error', (e) => {
        if (source.readyState === EventSource.CLOSED) {
          // 롤백 모드에서는 더 빠른 재연결
          const delay = Math.min(1000 * Math.pow(1.5, reconnectCount), 5000);
          setTimeout(() => {
            setReconnectCount(prev => prev + 1);
            connectSSE();
          }, delay);
        }
      });
      
      setEventSource(source);
    };
    
    connectSSE();
    return () => eventSource?.close();
  }, [jobId, reconnectCount]);
};
```

### 시나리오 3: 메모리 사용량 급증
```bash
# 문제: 롤백 후에도 메모리 사용량 높음
# 해결: 강제 가비지 컬렉션 및 캐시 정리

# 메모리 정리 스크립트
curl -X POST http://localhost:8002/api/admin/cleanup \
     -d '{"force_gc": true, "clear_caches": true}'

# 프로세스 재시작 (최후 수단)
systemctl restart ai-script-generation-service
```

---

## 📋 롤백 후 정상화 절차

### 1. 설정 파일 복원
```bash
# 1. 환경변수 영구 설정
echo "USE_DURABLE_WORKER=false" >> /etc/environment
echo "WORKER_SYSTEM_ENABLED=false" >> /etc/environment

# 2. 시스템 서비스 설정 업데이트
systemctl daemon-reload
systemctl restart ai-script-generation-service

# 3. 모니터링 설정 조정
cp config/prometheus/alerts-rollback.yml config/prometheus/alerts.yml
systemctl reload prometheus
```

### 2. 문서 업데이트
```markdown
# DEPLOYMENT.md 업데이트
## Current System Status: ROLLBACK MODE
- Worker System: FastAPI BackgroundTasks
- RQ System: DISABLED
- Redis: Used for idempotency keys only
- Rollback Date: $(date)
- Reason: [롤백 사유 기입]
```

### 3. 팀 커뮤니케이션
```yaml
# 롤백 완료 보고서 템플릿
rollback_report:
  timestamp: "2024-XX-XX XX:XX:XX"
  duration: "X minutes"
  affected_users: X
  failed_jobs: X
  root_cause: "원인 분석"
  actions_taken:
    - "Feature flag disabled"
    - "RQ workers terminated"  
    - "Jobs migrated to BackgroundTasks"
  current_status: "STABLE"
  next_steps:
    - "Monitor for 24 hours"
    - "Plan re-deployment strategy"
    - "Fix identified issues"
```

---

## 🔄 재배포 준비

### 롤백 후 개선 계획
1. **근본 원인 분석**: 롤백을 야기한 문제 해결
2. **테스트 강화**: 부하 테스트, 안정성 테스트 보완
3. **모니터링 개선**: 더 세밀한 알림 및 메트릭 추가
4. **단계적 재배포**: Feature flag를 통한 점진적 활성화

### 재배포 기준
- [ ] 근본 원인 완전 해결
- [ ] 부하 테스트 통과 (24시간 연속)
- [ ] 메모리 누수 없음 확인
- [ ] 팀 승인 및 배포 계획 수립

---

## 📞 비상 연락망

### 롤백 권한자
- **Level 1**: 개발팀 리드 (즉시 롤백 가능)
- **Level 2**: 시스템 관리자 (서비스 재시작 권한)
- **Level 3**: DevOps 엔지니어 (인프라 수정 권한)

### 에스컬레이션 절차
1. **2분 이내**: 자동 롤백 시도
2. **5분 이내**: 팀 리드 보고
3. **10분 이내**: 관리자 개입
4. **30분 이내**: 전체 서비스 점검

---

이 롤백 계획은 RQ 기반 Durable Worker 시스템에서 FastAPI BackgroundTasks로 안전하고 신속하게 되돌릴 수 있는 완전한 절차를 제공합니다.