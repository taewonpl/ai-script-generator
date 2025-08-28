# 🚀 Commit 급증 대응 Runbook

## 📋 개요

사용자 Commit 활동이 급증하여 시스템 부하가 증가할 때의 대응 절차입니다. 긍정적인 사용자 활동 증가를 안정적으로 처리하면서 서비스 품질을 유지하는 것이 목표입니다.

## 🚨 증상 식별

### 주요 증상
- `rate(commit_positive_total[5m])` 메트릭 급증 (정상 대비 300% 이상)
- Generation service 응답 시간 증가
- SSE 연결에서 지연 발생
- 메모리 토큰 사용률 급상승
- 데이터베이스 쓰기 부하 증가

### 알림 임계값
```yaml
# Prometheus 알림 조건
- alert: CommitSurgeDetected
  expr: rate(commit_positive_total[5m]) > 10  # 분당 10개 초과
  for: 2m
  labels:
    severity: warning

- alert: HighCommitLatency
  expr: histogram_quantile(0.95, commit_duration_seconds_bucket) > 5
  for: 5m
  labels:
    severity: critical
```

### 정상 vs 급증 기준
```bash
# 정상 상태: 분당 1-3개 커밋
# 주의 상태: 분당 5-10개 커밋  
# 급증 상태: 분당 10개 이상 커밋
# 위험 상태: 분당 20개 이상 커밋
```

---

## 🔍 진단 단계

### 1단계: Commit 패턴 분석
```bash
# 최근 1시간 커밋 통계 확인
curl -s "http://localhost:9090/api/v1/query_range?query=rate(commit_positive_total[5m])&start=$(date -d '1 hour ago' +%s)&end=$(date +%s)&step=60" | jq '.data.result[0].values[-12:]'

# 사용자별 커밋 분포 확인
curl -s http://localhost:8002/api/generation/stats/commits/by-user | jq '.top_users[:10]'

# 프로젝트별 커밋 분포
curl -s http://localhost:8002/api/generation/stats/commits/by-project | jq '.top_projects[:10]'
```

### 2단계: 시스템 리소스 영향도 측정
```bash
# CPU 사용률 확인
top -b -n1 | grep "generation-service" | awk '{print $9"%"}'

# 메모리 사용률 확인
ps -p $(pgrep -f generation-service) -o pid,vsz,rss,pmem | tail -1

# 데이터베이스 연결 수
lsof -p $(pgrep -f generation-service) | grep -c ".db$"

# SSE 연결 수 확인
ss -tuln | grep :8002 | wc -l
```

### 3단계: 메모리 토큰 사용률 분석
```bash
# 현재 토큰 사용률
curl -s http://localhost:8002/api/generation/memory/stats | jq '.token_usage_pct'

# 프로젝트별 메모리 사용량
curl -s http://localhost:8002/api/generation/memory/stats/by-project | head -10

# 메모리 턴 생성 속도
curl -s "http://localhost:9090/api/v1/query?query=rate(memory_turns_created[5m])" | jq '.data.result[0].value[1]'
```

### 4단계: 급증 원인 분석
```bash
# 특정 사용자의 과도한 활동 확인
curl -s http://localhost:8002/api/generation/stats/commits/outliers | \
  jq '.users[] | select(.commits_per_minute > 5)'

# 자동화 도구 사용 패턴 감지
curl -s http://localhost:8002/api/generation/stats/user-agents | \
  grep -E "(bot|script|automation|curl|python-requests)"

# 특정 시간대 집중 현상
curl -s http://localhost:8002/api/generation/stats/commits/timeline | \
  jq '.hourly_distribution'
```

---

## ⚡ 즉시 대응 조치 (단계별)

### 1단계: 트래픽 제어 (1분 이내)
```bash
# 1. 커밋 전용 Rate limiting 활성화
curl -X POST http://localhost:8002/api/admin/rate-limit/commits \
     -d '{
       "commits_per_minute": 20,
       "commits_per_hour": 100,
       "burst_allowance": 5
     }' \
     -H "Authorization: Bearer ${ADMIN_TOKEN}"

# 2. 중복 커밋 방지 강화
curl -X POST http://localhost:8002/api/admin/deduplication/enable \
     -d '{"window_seconds": 300, "similarity_threshold": 0.95}'

# 3. 메모리 토큰 임계값 임시 상향 조정 (35% → 50%)
curl -X POST http://localhost:8002/api/admin/memory/threshold \
     -d '{"max_token_usage_pct": 50, "temporary": true, "duration_minutes": 60}'
```

### 2단계: 리소스 확보 (3분 이내)
```bash
# 1. 메모리 정리 및 최적화
curl -X POST http://localhost:8002/api/admin/memory/optimize \
     -d '{"compress_old_contexts": true, "cleanup_inactive_sessions": true}'

# 2. 커밋 처리 배치 크기 조정
export COMMIT_BATCH_SIZE=5  # 기본 10에서 축소
export COMMIT_PROCESSING_DELAY=200  # 200ms 지연 추가

# 3. 비필수 백그라운드 작업 일시 중단
curl -X POST http://localhost:8002/api/admin/background-jobs/pause \
     -d '{"job_types": ["analytics", "cleanup", "non_critical_indexing"]}'

# 서비스 재시작으로 설정 적용 (무중단)
curl -X POST http://localhost:8002/api/admin/graceful-reload
```

### 3단계: 부하 분산 및 스케일링 (5분 이내)
```bash
# 1. 워커 프로세스 증설
curl -X POST http://localhost:8002/api/admin/workers/scale \
     -d '{"target_workers": 6, "worker_type": "commit_processor"}'  # 기본 3에서 증설

# 2. 데이터베이스 연결 풀 확장
curl -X POST http://localhost:8002/api/admin/db/scale-pool \
     -d '{"max_connections": 20, "min_connections": 5}'  # 기본 10에서 확장

# 3. 캐시 정책 최적화 (자주 사용되는 데이터 우선 캐시)
curl -X POST http://localhost:8002/api/admin/cache/optimize-for-commits \
     -d '{"strategy": "commit_heavy", "ttl_seconds": 300}'

# 4. 컨테이너 환경에서 자동 스케일링 (Kubernetes)
kubectl scale deployment generation-service --replicas=3  # 기본 2에서 증설
```

---

## 🛠️ 시나리오별 세부 대응

### 시나리오 1: 특정 사용자의 과도한 활동
```bash
# 진단: 상위 활동 사용자 식별
TOP_USER=$(curl -s http://localhost:8002/api/generation/stats/commits/by-user | \
           jq -r '.top_users[0].user_id')
USER_COMMITS=$(curl -s http://localhost:8002/api/generation/stats/commits/by-user | \
               jq -r '.top_users[0].commits_per_minute')

echo "Top user: $TOP_USER with $USER_COMMITS commits/min"

# 대응: 사용자별 개별 제한 적용
if (( $(echo "$USER_COMMITS > 10" | bc -l) )); then
    curl -X POST http://localhost:8002/api/admin/rate-limit/user \
         -d "{
           \"user_id\": \"$TOP_USER\",
           \"commits_per_minute\": 5,
           \"notification\": true,
           \"reason\": \"High activity protection\"
         }"
    
    echo "Rate limit applied to user $TOP_USER"
fi
```

### 시나리오 2: 자동화 도구의 대량 커밋
```bash
# 진단: 자동화 도구 패턴 감지
AUTOMATION_REQUESTS=$(curl -s http://localhost:8002/api/generation/stats/user-agents | \
                      grep -c -E "(bot|script|curl|python)")

if [ $AUTOMATION_REQUESTS -gt 50 ]; then
    echo "High automation activity detected: $AUTOMATION_REQUESTS requests"
    
    # 대응: API 키별 제한 강화
    curl -X POST http://localhost:8002/api/admin/rate-limit/api-keys \
         -d '{
           "default_limit": 30,
           "automation_detection": true,
           "require_human_verification": false
         }'
    
    # 자동화 친화적인 배치 API 안내
    curl -X POST http://localhost:8002/api/admin/notifications/broadcast \
         -d '{
           "message": "High API usage detected. Consider using batch commit API for better performance.",
           "target": "high_activity_users",
           "include_batch_api_docs": true
         }'
fi
```

### 시나리오 3: 특정 프로젝트에 집중된 활동
```bash
# 진단: 핫 프로젝트 식별
HOT_PROJECT=$(curl -s http://localhost:8002/api/generation/stats/commits/by-project | \
              jq -r '.top_projects[0].project_id')
PROJECT_COMMITS=$(curl -s http://localhost:8002/api/generation/stats/commits/by-project | \
                  jq -r '.top_projects[0].commits_per_minute')

echo "Hot project: $HOT_PROJECT with $PROJECT_COMMITS commits/min"

# 대응: 프로젝트별 리소스 분리
if (( $(echo "$PROJECT_COMMITS > 15" | bc -l) )); then
    # 전용 워커 풀 할당
    curl -X POST http://localhost:8002/api/admin/projects/isolate \
         -d "{
           \"project_id\": \"$HOT_PROJECT\",
           \"dedicated_workers\": 2,
           \"memory_quota_mb\": 1024,
           \"priority\": \"high\"
         }"
    
    # 다른 프로젝트 보호
    curl -X POST http://localhost:8002/api/admin/projects/throttle-others \
         -d "{
           \"exclude_project_id\": \"$HOT_PROJECT\",
           \"max_concurrent_commits\": 3
         }"
fi
```

### 시나리오 4: 시간대별 집중 현상 (점심시간, 퇴근시간)
```bash
# 진단: 현재 시간대 패턴 확인
CURRENT_HOUR=$(date +%H)
TYPICAL_LOAD=$(curl -s http://localhost:8002/api/generation/stats/commits/hourly-average | \
               jq -r ".hour_${CURRENT_HOUR}")

echo "Current hour: $CURRENT_HOUR, Typical load: $TYPICAL_LOAD"

# 대응: 시간대별 자동 조정
if [ $CURRENT_HOUR -eq 12 ] || [ $CURRENT_HOUR -eq 18 ]; then
    echo "Peak hour detected, applying peak-time configuration"
    
    # 피크타임 설정 적용
    curl -X POST http://localhost:8002/api/admin/config/peak-time \
         -d '{
           "mode": "peak",
           "auto_scaling": true,
           "cache_aggressive": true,
           "batch_processing": true,
           "duration_minutes": 120
         }'
    
    # 사용자에게 피크타임 안내
    curl -X POST http://localhost:8002/api/admin/notifications/peak-time \
         -d '{"message": "Peak usage detected. Response times may be slightly longer."}'
fi
```

---

## 📊 실시간 모니터링 강화

### 커밋 특화 대시보드 활성화
```bash
# 실시간 커밋 통계 대시보드
watch -n 10 "
echo '=== Commit Surge Dashboard ==='
echo 'Current commit rate:' \$(curl -s 'http://localhost:9090/api/v1/query?query=rate(commit_positive_total[5m])' | jq -r '.data.result[0].value[1]' | cut -d. -f1) '/min'
echo 'Queue length:' \$(curl -s http://localhost:8002/api/generation/stats/queue-length)
echo 'Memory usage:' \$(curl -s http://localhost:8002/api/generation/memory/stats | jq -r '.token_usage_pct')%
echo 'Active users:' \$(curl -s http://localhost:8002/api/generation/stats/active-users)
echo 'Response time P95:' \$(curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,http_request_duration_seconds_bucket{endpoint=\"commit\"})' | jq -r '.data.result[0].value[1]' | cut -d. -f1)s
"
```

### 알림 강화
```yaml
# 커밋 급증 전용 알림 추가
- alert: CommitSurgeLevel2
  expr: rate(commit_positive_total[5m]) > 20
  for: 1m
  labels:
    severity: critical
    pager: "true"
  annotations:
    summary: "Critical commit surge detected - immediate action required"

- alert: CommitLatencySpike
  expr: histogram_quantile(0.95, commit_duration_seconds_bucket) > 10
  for: 3m
  labels:
    severity: warning
  annotations:
    summary: "Commit processing latency is high - performance degraded"
```

---

## ✅ 성공 지표 및 복구 확인

### 즉시 확인 (대응 후 5분 이내)
```bash
# 1. 커밋 처리 속도 정상화 확인
COMMIT_RATE=$(curl -s 'http://localhost:9090/api/v1/query?query=rate(commit_positive_total[5m])' | jq -r '.data.result[0].value[1]')
echo "Current commit rate: $COMMIT_RATE/min (target: <10/min)"

# 2. 응답 시간 개선 확인
RESPONSE_TIME=$(curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,http_request_duration_seconds_bucket{endpoint="commit"})' | jq -r '.data.result[0].value[1]')
echo "Commit response time P95: ${RESPONSE_TIME}s (target: <5s)"

# 3. 메모리 토큰 사용률 안정화
MEMORY_USAGE=$(curl -s http://localhost:8002/api/generation/memory/stats | jq -r '.token_usage_pct')
echo "Memory token usage: $MEMORY_USAGE% (target: <50%)"
```

### 안정성 확인 (대응 후 30분 이내)
```bash
# 지속적인 안정성 검증
for i in {1..6}; do
    echo "Check $i/6:"
    COMMIT_RATE=$(curl -s 'http://localhost:9090/api/v1/query?query=rate(commit_positive_total[5m])' | jq -r '.data.result[0].value[1]')
    echo "  Commit rate: $COMMIT_RATE/min"
    
    QUEUE_LENGTH=$(curl -s http://localhost:8002/api/generation/stats/queue-length)
    echo "  Queue length: $QUEUE_LENGTH"
    
    sleep 300  # 5분 간격
done
```

### 사용자 만족도 확인
```bash
# 사용자 피드백 수집
curl -s http://localhost:8002/api/generation/feedback/recent | jq '.satisfaction_scores[-10:]'

# 에러율 확인
ERROR_RATE=$(curl -s 'http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=~"5.."}[5m])' | jq -r '.data.result[0].value[1]')
echo "Error rate: $ERROR_RATE (target: <0.01)"
```

---

## 🔄 정상화 절차

### 임시 조치 해제 (급증 해소 후)
```bash
# 1. Rate limiting 완화
curl -X POST http://localhost:8002/api/admin/rate-limit/commits/restore-default

# 2. 메모리 토큰 임계값 원복 (50% → 35%)
curl -X POST http://localhost:8002/api/admin/memory/threshold \
     -d '{"max_token_usage_pct": 35}'

# 3. 백그라운드 작업 재개
curl -X POST http://localhost:8002/api/admin/background-jobs/resume

# 4. 리소스 스케일 다운 (점진적)
sleep 1800  # 30분 안정화 대기
curl -X POST http://localhost:8002/api/admin/workers/scale \
     -d '{"target_workers": 3, "worker_type": "commit_processor"}'

kubectl scale deployment generation-service --replicas=2  # 원복
```

### 성능 최적화 유지
```bash
# 긍정적인 변경사항 영구 적용
curl -X POST http://localhost:8002/api/admin/config/permanent-improvements \
     -d '{
       "cache_optimization": true,
       "batch_processing": true,
       "connection_pooling": "optimized",
       "monitoring_enhanced": true
     }'
```

---

## 📈 장기적 개선 방안

### 1. 용량 계획 수립
```bash
# 커밋 패턴 분석 자동화
cat > /usr/local/bin/commit-pattern-analysis.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d)
COMMITS_TODAY=$(curl -s http://localhost:8002/api/generation/stats/commits/daily)
PEAK_HOUR=$(curl -s http://localhost:8002/api/generation/stats/commits/peak-hour)
AVG_PROCESSING_TIME=$(curl -s http://localhost:8002/api/generation/stats/commits/avg-time)

echo "$DATE,$COMMITS_TODAY,$PEAK_HOUR,$AVG_PROCESSING_TIME" >> /var/log/commit-capacity.csv

# 주간 리포트 생성 (일요일)
if [ $(date +%u) -eq 7 ]; then
    python3 /usr/local/bin/generate-capacity-report.py
fi
EOF

chmod +x /usr/local/bin/commit-pattern-analysis.sh
echo "0 23 * * * /usr/local/bin/commit-pattern-analysis.sh" | crontab -
```

### 2. 자동 스케일링 정책 개선
```yaml
# Kubernetes HPA 설정 개선
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: generation-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: generation-service
  minReplicas: 2
  maxReplicas: 8
  metrics:
  - type: Pods
    pods:
      metric:
        name: commit_rate_per_pod
      target:
        type: AverageValue
        averageValue: "5"  # 파드당 분당 5커밋
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70
```

### 3. 지능형 부하 예측
```python
# 머신러닝 기반 커밋 급증 예측 모델
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

class CommitSurgePredictor:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100)
        self.features = ['hour', 'day_of_week', 'recent_commits', 'active_users']
    
    def predict_next_hour_commits(self):
        # 현재 상태 기반 다음 시간 커밋 수 예측
        current_features = self.extract_current_features()
        prediction = self.model.predict([current_features])
        
        if prediction[0] > 15:  # 급증 예상
            self.trigger_preemptive_scaling()
        
        return prediction[0]
```

---

## 📝 사후 분석 및 개선

### 성과 지표 정의
- **처리 성공률**: > 99.5%
- **평균 응답시간**: < 3초 (정상시 1초)
- **사용자 만족도**: > 4.0/5.0
- **시스템 안정성**: 메모리/CPU 사용률 < 80%

### 학습 내용 문서화
1. **급증 패턴 분석**: 시간대별, 사용자별, 프로젝트별 패턴
2. **효과적인 대응책**: 어떤 조치가 가장 효과적이었는지
3. **리소스 사용 최적화**: 스케일링 전략의 효과성
4. **사용자 커뮤니케이션**: 급증 시 사용자 안내 방법

---

## 🔗 관련 문서

- [커밋 시스템 아키텍처](../docs/architecture/commit-system.md)
- [메모리 관리 가이드](../docs/operations/memory-management.md)
- [자동 스케일링 설정](../docs/deployment/auto-scaling.md)
- [사용자 커뮤니케이션 가이드](../docs/user-support/communication.md)
- [성능 모니터링 대시보드](https://monitoring.ai-script-generator.com/commit-surge)