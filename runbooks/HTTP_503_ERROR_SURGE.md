# ⚠️ 503 오류 급증 처리 Runbook

## 📋 개요

HTTP 503 Service Unavailable 오류 급증 시 신속한 진단 및 대응을 위한 운영 절차입니다.

## 🚨 증상 식별

### 주요 증상
- `http_requests_total{status="503"}` 메트릭 급증
- 사용자로부터 "서비스 이용 불가" 신고 증가
- 프론트엔드에서 API 호출 실패율 상승
- 로드밸런서 헬스체크 실패

### 알림 임계값
```yaml
# Prometheus 알림 조건
- alert: HTTP503ErrorSpike
  expr: rate(http_requests_total{status="503"}[5m]) > 20
  for: 2m
  labels:
    severity: critical
```

### 로그에서 확인할 패턴
```
ERROR: Service unavailable - upstream timeout
WARNING: All backend servers are down
ERROR: Connection pool exhausted
INFO: Scaling up workers due to high load
```

---

## 🔍 진단 단계

### 1단계: 서비스 상태 즉시 확인
```bash
# 전체 서비스 헬스체크
curl -f http://localhost:8001/health  # Project Service
curl -f http://localhost:8002/health  # Generation Service
curl -f http://localhost:3000         # Frontend

# 응답 시간 측정
time curl -s http://localhost:8002/api/generation/health
```

### 2단계: 리소스 사용률 확인
```bash
# CPU 사용률 (80% 이상이면 위험)
top -b -n1 | grep "Cpu(s)"

# 메모리 사용률 (85% 이상이면 위험)
free -m | awk 'NR==2{printf "Memory Usage: %s/%sMB (%.2f%%)\n", $3,$2,$3*100/$2}'

# 디스크 I/O 확인
iostat -x 1 3

# 네트워크 연결 수
ss -tuln | wc -l
```

### 3단계: 데이터베이스 상태 확인
```bash
# SQLite 잠금 상태 확인
lsof | grep "\.db$" | wc -l

# Redis 연결 상태 확인
redis-cli ping
redis-cli info clients

# ChromaDB 상태 확인
curl -f http://localhost:8000/api/v1/heartbeat
```

### 4단계: 업스트림 서비스 확인
```bash
# OpenAI API 상태 확인
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models | jq '.data | length'

# 외부 서비스 응답 시간 측정
time curl -s https://api.openai.com/v1/models > /dev/null
```

---

## ⚡ 즉시 대응 조치 (우선순위별)

### 우선순위 1: 트래픽 제어 (30초 이내)
```bash
# 1. Rate limiting 강화
curl -X POST http://localhost:8002/api/admin/rate-limit/emergency \
     -d '{"requests_per_minute": 100, "burst": 10}' \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer ${ADMIN_TOKEN}"

# 2. 비필수 엔드포인트 일시 차단
curl -X POST http://localhost:8002/api/admin/circuit-breaker/enable \
     -d '{"endpoints": ["/api/generation/batch", "/api/rag/search"]}'

# 3. 로드밸런서에서 트래픽 쉐이핑
# Nginx upstream 설정 동적 업데이트
nginx -s reload
```

### 우선순위 2: 리소스 확보 (2분 이내)
```bash
# 1. 메모리 사용량이 높은 프로세스 재시작
if [ $(free | awk '/^Mem:/{print $3/$2 * 100.0}' | cut -d. -f1) -gt 85 ]; then
    echo "High memory usage detected, restarting services"
    
    # Generation service 재시작 (무중단)
    curl -X POST http://localhost:8002/api/admin/graceful-restart
    
    # Worker processes 스케일 다운
    curl -X POST http://localhost:8002/api/admin/workers/scale \
         -d '{"target_workers": 2}'  # 기본 4개에서 2개로 축소
fi

# 2. 임시 파일 정리
find /tmp -name "ai-script-*" -mmin +60 -delete
docker system prune -f  # Docker 사용 시

# 3. 로그 파일 정리 (디스크 공간 확보)
find /var/log -name "*.log" -mtime +7 -exec gzip {} \;
```

### 우선순위 3: 서비스 복구 (5분 이내)
```bash
# 1. 서비스별 순차 재시작
systemctl restart ai-script-project-service
sleep 30
systemctl restart ai-script-generation-service
sleep 30

# 2. 데이터베이스 연결 풀 초기화
curl -X POST http://localhost:8001/api/admin/db/reset-pool
curl -X POST http://localhost:8002/api/admin/db/reset-pool

# 3. Redis 캐시 정리 (메모리 확보)
redis-cli FLUSHDB 1  # 임시 데이터만 삭제 (DB 1)

# 4. 헬스체크 강제 성공 (일시적)
curl -X POST http://localhost:8002/api/admin/health/force-ok \
     -d '{"duration_minutes": 10}'
```

---

## 🛠️ 근본 원인별 대응

### 시나리오 1: 리소스 고갈 (CPU/Memory)
```bash
# 진단
htop -p $(pgrep -f "python.*generation-service")

# 대응
if [ CPU_USAGE -gt 80 ]; then
    # 워커 프로세스 수 축소
    export RAG_MAX_CONCURRENT_JOBS=10  # 기본 50에서 축소
    export RAG_EMBEDDING_CONCURRENCY=1  # 기본 3에서 축소
    
    # 서비스 재시작으로 설정 적용
    systemctl restart ai-script-generation-service
fi

if [ MEMORY_USAGE -gt 85 ]; then
    # 메모리 집약적 작업 중단
    curl -X POST http://localhost:8002/api/admin/jobs/pause-heavy \
         -d '{"job_types": ["batch_generation", "large_document_rag"]}'
    
    # 캐시 크기 축소
    redis-cli CONFIG SET maxmemory 512mb
fi
```

### 시나리오 2: 데이터베이스 병목
```bash
# SQLite 잠금 진단
lsof /path/to/database.db

# 대응: 읽기 전용 복제본으로 트래픽 분산
export DATABASE_READ_REPLICA_URL="sqlite:///readonly.db"

# 장기간 실행 중인 쿼리 강제 종료
curl -X POST http://localhost:8001/api/admin/db/kill-long-queries \
     -d '{"max_duration_seconds": 30}'
```

### 시나리오 3: 외부 API 장애 (OpenAI/Anthropic)
```bash
# API 상태 확인
curl -s https://status.openai.com/api/v2/status.json | jq '.status.description'

# 대응: Circuit breaker 활성화
curl -X POST http://localhost:8002/api/admin/circuit-breaker/openai/enable
curl -X POST http://localhost:8002/api/admin/circuit-breaker/anthropic/enable

# Fallback 모델로 전환
export FALLBACK_MODEL_ENABLED=true
export PRIMARY_MODEL="gpt-3.5-turbo"  # 더 가벼운 모델로 전환
```

### 시나리오 4: 네트워크 연결 포화
```bash
# 연결 수 확인
ss -s | grep TCP

# 대응: 연결 풀 크기 조정
curl -X POST http://localhost:8002/api/admin/connection-pool/resize \
     -d '{"max_connections": 50, "min_connections": 5}'

# Keep-alive 시간 단축
echo 'net.ipv4.tcp_keepalive_time = 300' >> /etc/sysctl.conf
sysctl -p
```

---

## 📊 자동 스케일링 활성화

### 수평적 스케일링 (컨테이너 환경)
```bash
# Kubernetes HPA 즉시 활성화
kubectl autoscale deployment generation-service \
  --cpu-percent=70 \
  --min=2 \
  --max=10

# Docker Swarm 스케일링
docker service scale ai-script-generation=5
```

### 수직적 스케일링 (단일 서버)
```bash
# 프로세스 워커 수 동적 증가
curl -X POST http://localhost:8002/api/admin/workers/auto-scale \
     -d '{
       "enable": true,
       "min_workers": 2,
       "max_workers": 8,
       "cpu_threshold": 70,
       "memory_threshold": 80
     }'
```

---

## 📈 모니터링 강화

### 실시간 대시보드 확인
```bash
# Grafana 대시보드 URL
echo "Check: https://monitoring.ai-script-generator.com/d/503-errors"

# 주요 메트릭 CLI 조회
curl -s "http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=\"503\"}[5m])" \
  | jq '.data.result[0].value[1]'
```

### 추가 알림 설정
```yaml
# 긴급 알림 활성화
- alert: CriticalServiceDown
  expr: up{job="generation-service"} == 0
  for: 1m
  labels:
    severity: critical
    pager: "true"
  annotations:
    summary: "Generation service is completely down"
```

---

## ✅ 복구 확인 체크리스트

### 즉시 확인 (복구 후 5분 이내)
- [ ] HTTP 503 오류율 < 1%
- [ ] 평균 응답 시간 < 2초
- [ ] 헬스체크 엔드포인트 정상 응답
- [ ] 핵심 기능 수동 테스트 통과

### 안정성 확인 (복구 후 30분 이내)
- [ ] CPU 사용률 < 70%
- [ ] 메모리 사용률 < 80%
- [ ] 데이터베이스 연결 수 정상
- [ ] 에러 로그 증가 중단

### 성능 확인 (복구 후 1시간 이내)
```bash
# 부하 테스트 실행
ab -n 1000 -c 10 http://localhost:8002/api/generation/health

# 결과 확인: 99%가 2초 이내 응답해야 함
# Requests per second: > 50
# Time per request (mean): < 2000ms
```

---

## 🔄 정상화 후 조치

### Rate Limiting 정상화
```bash
# 긴급 제한 해제
curl -X DELETE http://localhost:8002/api/admin/rate-limit/emergency

# 정상 설정 복원
curl -X POST http://localhost:8002/api/admin/rate-limit/restore-default
```

### Circuit Breaker 해제
```bash
# 비필수 엔드포인트 재개
curl -X POST http://localhost:8002/api/admin/circuit-breaker/disable-all

# 외부 API Circuit Breaker 해제 (단계적)
curl -X POST http://localhost:8002/api/admin/circuit-breaker/openai/test
sleep 300  # 5분 대기 후
curl -X POST http://localhost:8002/api/admin/circuit-breaker/openai/disable
```

### 리소스 설정 복원
```bash
# 워커 수 정상화
export RAG_MAX_CONCURRENT_JOBS=50
export RAG_EMBEDDING_CONCURRENCY=3
systemctl restart ai-script-generation-service
```

---

## 📝 사후 분석 필수 항목

### 1. 타임라인 작성
- 장애 발생 시각
- 알림 수신 시각
- 대응 시작 시각
- 각 조치별 실행 시각
- 완전 복구 시각

### 2. 영향 범위 분석
```sql
-- 장애 기간 중 실패한 요청 수
SELECT COUNT(*) FROM api_logs 
WHERE status_code = 503 
AND timestamp BETWEEN '${START_TIME}' AND '${END_TIME}';

-- 영향받은 사용자 수
SELECT COUNT(DISTINCT user_id) FROM api_logs 
WHERE status_code >= 500 
AND timestamp BETWEEN '${START_TIME}' AND '${END_TIME}';
```

### 3. 근본 원인 분석 (5 Whys)
1. Why did 503 errors spike?
2. Why did the servers become overloaded?
3. Why wasn't auto-scaling triggered earlier?
4. Why didn't monitoring catch this sooner?
5. Why don't we have better capacity planning?

### 4. 재발 방지 조치
- [ ] 알림 임계값 조정
- [ ] 자동 스케일링 정책 개선
- [ ] 용량 계획 수립
- [ ] 모니터링 강화
- [ ] 장애 대응 절차 개선

---

## 🔗 관련 문서

- [시스템 아키텍처](../docs/architecture/overview.md)
- [모니터링 대시보드](https://monitoring.ai-script-generator.com)
- [자동 스케일링 가이드](../docs/operations/auto-scaling.md)
- [성능 튜닝 가이드](../docs/operations/performance-tuning.md)
- [장애 대응 체크리스트](../docs/operations/incident-response.md)