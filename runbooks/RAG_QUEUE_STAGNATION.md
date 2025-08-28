# 📊 RAG 작업 정체 해결 Runbook

## 📋 개요

RAG (Retrieval-Augmented Generation) 작업 대기열이 정체되어 문서 처리가 지연될 때의 대응 절차입니다.

## 🚨 증상 식별

### 주요 증상
- `rag_queue_length` 메트릭이 지속적으로 증가
- `rag_worker_active_jobs` 메트릭이 0 또는 매우 낮음
- 사용자 신고: "문서 업로드 후 처리 중단", "임베딩 생성 안 됨"
- 대시보드에서 "Processing..." 상태로 오래 머무름

### 알림 임계값
```yaml
# Prometheus 알림 조건
- alert: RAGQueueStagnation
  expr: rag_queue_length > 50 and increase(rag_jobs_completed_total[10m]) == 0
  for: 5m
  labels:
    severity: critical

- alert: NoActiveRAGWorkers
  expr: rag_worker_active_jobs == 0 and rag_queue_length > 0
  for: 2m
  labels:
    severity: warning
```

### 로그에서 확인할 패턴
```
ERROR: RQ worker connection lost
WARNING: Redis connection timeout in RAG worker
ERROR: Embedding API rate limit exceeded
INFO: RAG worker started processing job xyz
ERROR: ChromaDB connection failed
WARNING: Worker process terminated unexpectedly
```

---

## 🔍 진단 단계

### 1단계: 큐 상태 즉시 확인
```bash
# RQ 대시보드로 큐 상태 확인
curl -s http://localhost:9181/api/queues | jq '.queues[] | select(.name=="rag_processing")'

# 또는 Redis에서 직접 확인
redis-cli LLEN rq:queue:rag_processing
redis-cli LRANGE rq:queue:rag_processing 0 10

# DLQ (Dead Letter Queue) 확인
redis-cli LLEN rq:queue:rag_dlq
```

### 2단계: 워커 상태 확인
```bash
# 활성 워커 프로세스 확인
ps aux | grep "rq worker"

# RQ 워커 정보 조회
rq info --url redis://localhost:6379/5

# 워커 로그 확인
tail -f /var/log/rag-worker.log | grep -E "(ERROR|WARNING|started|finished)"
```

### 3단계: Redis 연결 상태 확인
```bash
# Redis 서버 상태
redis-cli ping
redis-cli info stats | grep -E "(connected_clients|total_connections_received)"

# Redis 메모리 사용률
redis-cli info memory | grep used_memory_human

# Redis 연결 수 확인
redis-cli client list | wc -l
```

### 4단계: 외부 서비스 의존성 확인
```bash
# ChromaDB 연결 테스트
curl -f http://localhost:8000/api/v1/heartbeat

# OpenAI API 연결 테스트 (임베딩)
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"input":"test","model":"text-embedding-ada-002"}' \
     https://api.openai.com/v1/embeddings

# 파일 저장소 접근 테스트
ls -la /path/to/document/storage
df -h /path/to/document/storage  # 디스크 공간 확인
```

---

## ⚡ 즉시 대응 조치

### 우선순위 1: 워커 프로세스 복구 (1분 이내)
```bash
# 1. 먼저 워커 상태 확인
rq info --url redis://localhost:6379/5

# 2. 멈춘 워커가 있다면 재시작
pkill -f "rq worker rag_processing"

# 3. 새로운 워커 시작 (백그라운드)
nohup rq worker rag_processing --url redis://localhost:6379/5 > /var/log/rag-worker.log 2>&1 &
nohup rq worker rag_processing --url redis://localhost:6379/5 > /var/log/rag-worker2.log 2>&1 &

# 4. 워커 시작 확인
sleep 5
rq info --url redis://localhost:6379/5
```

### 우선순위 2: 정체된 작업 처리 (3분 이내)
```bash
# 1. 실패한 작업들을 DLQ에서 재시도
rq requeue --url redis://localhost:6379/5 --queue rag_dlq

# 2. 오래된 작업 우선순위 재조정
curl -X POST http://localhost:8002/api/rag/admin/reorder-queue \
     -H "Authorization: Bearer ${ADMIN_TOKEN}" \
     -d '{"strategy": "oldest_first", "limit": 100}'

# 3. 대형 문서 작업을 별도 큐로 분리 (시스템 부하 감소)
curl -X POST http://localhost:8002/api/rag/admin/separate-large-jobs \
     -d '{"size_threshold_mb": 10, "target_queue": "rag_large_docs"}'
```

### 우선순위 3: 리소스 최적화 (5분 이내)
```bash
# 1. 임베딩 배치 크기 축소 (메모리 절약)
export RAG_EMBEDDING_BATCH_SIZE=16  # 기본 32에서 축소
export RAG_EMBEDDING_CONCURRENCY=2  # 기본 3에서 축소

# 2. 워커 프로세스 재시작으로 설정 적용
pkill -f "rq worker"
sleep 3

# 더 많은 워커 시작 (병렬 처리 향상)
for i in {1..4}; do
    nohup rq worker rag_processing --url redis://localhost:6379/5 \
          > /var/log/rag-worker$i.log 2>&1 &
done

# 3. Redis 메모리 최적화
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET maxmemory 2gb
```

---

## 🛠️ 근본 원인별 해결책

### 시나리오 1: Redis 연결 문제
```bash
# 진단
redis-cli ping
redis-cli client list | grep "age=" | wc -l

# 해결
if [ $? -ne 0 ]; then
    echo "Redis connection issue detected"
    
    # Redis 재시작
    systemctl restart redis
    sleep 10
    
    # 워커 재시작 (새 연결로)
    pkill -f "rq worker"
    sleep 5
    
    # 연결 풀 재생성
    for i in {1..3}; do
        nohup rq worker rag_processing --url redis://localhost:6379/5 &
    done
fi
```

### 시나리오 2: 임베딩 API Rate Limiting
```bash
# 진단: OpenAI API 호출 패턴 확인
grep "rate.*limit" /var/log/rag-worker*.log

# 해결: Rate limiting 완화
export RAG_EMBEDDING_RATE_LIMIT=500  # 기본 1000에서 축소
export RAG_EMBEDDING_BATCH_SIZE=16   # 배치 크기 축소
export RAG_EMBEDDING_DELAY_MS=2000   # 요청 간 2초 대기

# API 키 로테이션 (여러 키 사용)
export OPENAI_API_KEYS="key1,key2,key3"
export USE_API_KEY_ROTATION=true

# 워커 재시작으로 설정 적용
systemctl restart rag-worker-service
```

### 시나리오 3: ChromaDB 연결 장애
```bash
# 진단
curl -f http://localhost:8000/api/v1/heartbeat || echo "ChromaDB DOWN"

# 해결
if [ $? -ne 0 ]; then
    echo "ChromaDB connection failed"
    
    # ChromaDB 재시작
    docker restart chromadb  # Docker 환경
    # 또는
    systemctl restart chromadb
    
    # 연결 대기
    sleep 30
    
    # 연결 테스트
    until curl -f http://localhost:8000/api/v1/heartbeat; do
        echo "Waiting for ChromaDB..."
        sleep 10
    done
    
    echo "ChromaDB restored, restarting workers"
    pkill -f "rq worker"
    sleep 5
    
    # 워커 재시작
    for i in {1..3}; do
        nohup rq worker rag_processing --url redis://localhost:6379/5 &
    done
fi
```

### 시나리오 4: 메모리 부족으로 인한 워커 종료
```bash
# 진단
dmesg | tail -20 | grep -i "killed process"
free -h

# 해결: 메모리 사용량 최적화
echo "Optimizing memory usage for RAG workers"

# 1. 배치 크기 대폭 축소
export RAG_EMBEDDING_BATCH_SIZE=8
export RAG_MAX_CHUNK_SIZE=512  # 기본 1024에서 축소

# 2. 동시 처리 작업 수 제한
export RAG_MAX_CONCURRENT_JOBS=5  # 기본 50에서 대폭 축소

# 3. 가비지 컬렉션 강제 실행
python3 -c "import gc; gc.collect()"

# 4. 메모리 효율적인 워커 재시작
for i in {1..2}; do  # 워커 수도 축소
    nohup rq worker rag_processing --url redis://localhost:6379/5 \
          --worker-class rq.SimpleWorker &  # 간단한 워커 사용
done
```

### 시나리오 5: 대형 파일로 인한 처리 지연
```bash
# 진단: 큐에서 대형 파일 식별
redis-cli LRANGE rq:queue:rag_processing 0 -1 | \
  xargs -I {} redis-cli HGET "rq:job:{}" data | \
  grep -o '"file_size":[0-9]*' | sort -t: -k2 -n

# 해결: 파일 크기별 우선순위 조정
curl -X POST http://localhost:8002/api/rag/admin/prioritize-queue \
     -d '{
       "rules": [
         {"file_size_mb": {"$lt": 5}, "priority": "high"},
         {"file_size_mb": {"$lt": 20}, "priority": "normal"},
         {"file_size_mb": {"$gte": 20}, "priority": "low"}
       ]
     }'

# 대형 파일 전용 워커 추가 (별도 큐)
nohup rq worker rag_large_docs --url redis://localhost:6379/5 \
      --worker-class rq.Worker \
      > /var/log/rag-worker-large.log 2>&1 &
```

---

## 📊 실시간 모니터링 활성화

### 대시보드 지표 확인
```bash
# 주요 지표 실시간 조회
watch -n 5 "
echo '=== RAG Queue Status ==='
redis-cli LLEN rq:queue:rag_processing
echo '=== Active Workers ==='
ps aux | grep 'rq worker' | wc -l
echo '=== Memory Usage ==='
free -h | grep Mem
echo '=== Redis Status ==='
redis-cli ping
"
```

### 로그 실시간 모니터링
```bash
# 여러 워커 로그 동시 모니터링
tail -f /var/log/rag-worker*.log | grep -E "(Processing|Completed|ERROR|WARNING)"

# 성공/실패 통계
grep -c "Successfully processed" /var/log/rag-worker*.log
grep -c "ERROR" /var/log/rag-worker*.log
```

---

## ✅ 복구 확인 체크리스트

### 즉시 확인 (복구 후 2분 이내)
- [ ] 활성 워커 수 > 0 (`ps aux | grep "rq worker" | wc -l`)
- [ ] 큐 길이 감소 추세 (`redis-cli LLEN rq:queue:rag_processing`)
- [ ] 새로운 작업 처리 시작 (로그에서 "Processing job" 확인)

### 안정성 확인 (복구 후 10분 이내)
- [ ] 큐 길이가 지속적으로 감소
- [ ] 워커 프로세스 안정적으로 실행 중
- [ ] 에러 로그 증가 중단
- [ ] 메모리 사용률 < 80%

### 성능 확인 (복구 후 30분 이내)
```bash
# 처리 속도 측정
echo "Jobs processed in last 10 minutes:"
redis-cli GET rag:stats:jobs_completed:$(date -d '10 minutes ago' +%Y%m%d%H%M)

# 평균 처리 시간 확인
grep "Processing time:" /var/log/rag-worker*.log | tail -20 | \
  awk '{print $NF}' | awk '{sum+=$1; count++} END {print "Avg:", sum/count "ms"}'
```

---

## 🔄 예방 조치

### 자동 복구 스크립트 설치
```bash
# /usr/local/bin/rag-queue-monitor.sh
#!/bin/bash
QUEUE_LENGTH=$(redis-cli LLEN rq:queue:rag_processing)
ACTIVE_WORKERS=$(ps aux | grep "rq worker rag_processing" | grep -v grep | wc -l)

if [ $QUEUE_LENGTH -gt 50 ] && [ $ACTIVE_WORKERS -eq 0 ]; then
    echo "$(date): RAG queue stagnation detected, auto-recovery starting" >> /var/log/rag-auto-recovery.log
    
    # 워커 자동 시작
    for i in {1..3}; do
        nohup rq worker rag_processing --url redis://localhost:6379/5 &
    done
    
    # 알림 발송
    curl -X POST $SLACK_WEBHOOK_URL -d '{"text":"RAG queue auto-recovery executed"}'
fi
```

```bash
# Crontab에 등록 (5분마다 실행)
echo "*/5 * * * * /usr/local/bin/rag-queue-monitor.sh" | crontab -
```

### 용량 계획 수립
```bash
# 일일 처리량 통계 수집
cat > /usr/local/bin/rag-capacity-stats.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d)
JOBS_TODAY=$(redis-cli GET "rag:stats:daily:$DATE" || echo "0")
AVG_PROCESSING_TIME=$(grep "Processing time:" /var/log/rag-worker*.log | 
  tail -100 | awk '{print $NF}' | awk '{sum+=$1; count++} END {print sum/count}')

echo "$DATE,$JOBS_TODAY,$AVG_PROCESSING_TIME" >> /var/log/rag-capacity.csv
EOF

# 일일 실행
echo "0 23 * * * /usr/local/bin/rag-capacity-stats.sh" | crontab -
```

---

## 📈 성능 최적화 권장사항

### 장기적 개선 방안
1. **수평적 스케일링**: 워커 노드 추가
2. **배치 처리 최적화**: 파일 유형별 전용 워커
3. **캐싱 전략**: 중복 문서 임베딩 캐시
4. **비동기 처리**: 단계별 파이프라인 구성

### 모니터링 강화
```yaml
# 추가 알림 규칙
- alert: RAGProcessingTimeHigh
  expr: histogram_quantile(0.95, rag_job_duration_seconds_bucket) > 300
  for: 10m
  
- alert: RAGSuccessRateLow
  expr: rate(rag_jobs_completed_total[30m]) / rate(rag_jobs_started_total[30m]) < 0.9
  for: 15m
```

---

## 📝 사후 분석 보고서 템플릿

### 필수 기록 항목
1. **정체 발생 시각**: `${STAGNATION_START_TIME}`
2. **정체 지속 시간**: `${DURATION_MINUTES}` 분
3. **최대 큐 길이**: `${MAX_QUEUE_LENGTH}`
4. **영향받은 사용자 수**: `${AFFECTED_USERS}`
5. **실패한 작업 수**: `${FAILED_JOBS}`
6. **근본 원인**: `${ROOT_CAUSE}`
7. **적용한 해결책**: `${SOLUTION_APPLIED}`
8. **재발 방지 조치**: `${PREVENTION_MEASURES}`

---

## 🔗 관련 문서

- [RAG 시스템 아키텍처](../docs/architecture/rag-system.md)
- [RQ Dashboard](http://localhost:9181)
- [워커 관리 가이드](../docs/operations/worker-management.md)
- [성능 튜닝 가이드](../docs/operations/performance-tuning.md)
- [Redis 운영 가이드](../docs/operations/redis-operations.md)