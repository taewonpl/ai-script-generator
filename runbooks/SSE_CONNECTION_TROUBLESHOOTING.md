# 🔄 SSE 연결 장애 대응 Runbook

## 📋 개요

Server-Sent Events (SSE) 연결 문제로 인한 실시간 업데이트 중단 시 대응 절차입니다.

## 🚨 증상 식별

### 주요 증상
- 프론트엔드에서 실시간 생성 상태 업데이트 중단
- `sse_connections_open` 메트릭 0 또는 급격한 감소
- `sse_reconnect_count` 메트릭 급증
- 사용자 신고: "진행률이 멈춤", "완료 알림 안 옴"

### 관련 메트릭 확인
```bash
# Prometheus 쿼리
sse_connections_open                    # 현재 열린 연결 수
rate(sse_reconnect_count[5m])          # 재연결 시도율
rate(sse_message_sent_total[5m])       # 메시지 전송률
```

### 로그에서 확인할 패턴
```
ERROR: SSE connection lost for client xyz
WARNING: EventSource connection timeout
ERROR: Failed to send SSE heartbeat
INFO: SSE connection established (client reconnected)
```

---

## 🔍 진단 단계

### 1단계: 연결 상태 확인
```bash
# 현재 활성 연결 수 확인
curl -s http://localhost:8002/api/generation/health | jq '.sse_connections'

# 네트워크 연결 확인
netstat -an | grep :8002 | grep ESTABLISHED | wc -l

# 프록시/로드밸런서 로그 확인
tail -f /var/log/nginx/access.log | grep "GET.*events"
```

### 2단계: 서버 리소스 확인
```bash
# 메모리 사용률 확인
free -h

# CPU 사용률 확인  
top -p $(pgrep -f "generation-service")

# 파일 디스크립터 사용률
lsof -p $(pgrep -f "generation-service") | wc -l
```

### 3단계: SSE 특화 진단
```bash
# SSE 엔드포인트 직접 테스트
curl -N -H "Accept: text/event-stream" \
     http://localhost:8002/api/generation/jobs/test-job-id/events

# 프론트엔드에서 연결 테스트 (브라우저 콘솔)
const eventSource = new EventSource('/api/generation/jobs/test-job-id/events');
eventSource.addEventListener('message', e => console.log(e.data));
```

### 4단계: 프록시/방화벽 확인
```bash
# Nginx 설정 확인 (버퍼링 비활성화 필요)
grep -n "proxy_buffering\|proxy_cache" /etc/nginx/sites-enabled/*

# 클라우드 로드밸런서 설정 확인 (타임아웃 연장 필요)
# AWS ALB: 유휴 타임아웃 > 300초
# CloudFlare: WebSocket 지원 활성화
```

---

## ⚡ 즉시 대응 조치

### 우선순위 1: 서비스 복구
```bash
# 1. SSE 서비스 재시작 (무중단)
curl -X POST http://localhost:8002/api/admin/sse/restart \
     -H "Authorization: Bearer ${ADMIN_TOKEN}"

# 2. 연결 풀 초기화
curl -X POST http://localhost:8002/api/admin/connections/reset

# 3. 클라이언트 강제 재연결 트리거
curl -X POST http://localhost:8002/api/admin/sse/broadcast-reconnect
```

### 우선순위 2: 프록시 설정 수정 (필요시)
```nginx
# /etc/nginx/sites-enabled/ai-script-generator
location /api/generation/jobs/*/events {
    proxy_pass http://generation-service;
    
    # SSE 최적화 설정
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    proxy_connect_timeout 5s;
    
    # 청크 전송 활성화
    chunked_transfer_encoding on;
    
    # Keep-alive 연결 유지
    proxy_set_header Connection "keep-alive";
    proxy_set_header Cache-Control "no-cache";
}
```

### 우선순위 3: 클라이언트 자동 복구
```javascript
// 프론트엔드 자동 복구 로직 확인
const reconnectSSE = () => {
    if (eventSource) {
        eventSource.close();
    }
    
    eventSource = new EventSource(`/api/generation/jobs/${jobId}/events`);
    
    eventSource.addEventListener('error', (e) => {
        if (eventSource.readyState === EventSource.CLOSED) {
            // 3초 후 자동 재연결
            setTimeout(reconnectSSE, 3000);
        }
    });
};
```

---

## 🛠️ 근본 원인 해결

### 일반적인 원인과 해결책

#### 1. 프록시 버퍼링 문제
**원인**: Nginx/CloudFlare가 SSE 응답을 버퍼링
```nginx
# 해결책: SSE 전용 location 설정
location ~* /events$ {
    proxy_buffering off;
    proxy_cache off;
    add_header X-Accel-Buffering no;
}
```

#### 2. 네트워크 타임아웃
**원인**: 로드밸런서 유휴 타임아웃이 너무 짧음
```yaml
# AWS ALB 설정
idle_timeout: 300  # 5분으로 연장

# CloudFlare 설정
websockets: true  # WebSocket 지원 활성화
```

#### 3. 서버 리소스 부족
**원인**: 너무 많은 동시 연결로 인한 메모리/FD 고갈
```python
# 해결책: 연결 수 제한 및 리소스 관리
MAX_SSE_CONNECTIONS = 1000
CONNECTION_CLEANUP_INTERVAL = 30  # 30초마다 정리

async def cleanup_stale_connections():
    """비활성 연결 정리"""
    for connection_id, last_activity in sse_connections.items():
        if datetime.utcnow() - last_activity > timedelta(minutes=5):
            await close_sse_connection(connection_id)
```

#### 4. 하트비트 메시지 누락
**원인**: 클라이언트가 연결 상태를 잘못 판단
```python
# 해결책: 정기적인 하트비트 전송
@scheduled_job("interval", seconds=30)
async def send_sse_heartbeat():
    """모든 활성 SSE 연결에 하트비트 전송"""
    heartbeat_message = {
        "type": "heartbeat",
        "timestamp": datetime.utcnow().isoformat(),
        "server_time": int(time.time())
    }
    
    await broadcast_to_all_connections(heartbeat_message)
```

---

## 📊 모니터링 강화

### 추가 메트릭 수집
```python
# SSE 상태 메트릭
sse_connection_duration_seconds = Histogram('sse_connection_duration_seconds')
sse_message_delivery_success_rate = Gauge('sse_message_delivery_success_rate')
sse_heartbeat_response_time = Histogram('sse_heartbeat_response_time')
```

### 알림 임계값 조정
```yaml
# Prometheus 알림 규칙
- alert: SSEConnectionDropRate
  expr: rate(sse_reconnect_count[5m]) > 10
  for: 2m
  annotations:
    description: "SSE reconnection rate {{ $value }}/min is too high"

- alert: SSENoActiveConnections
  expr: sse_connections_open == 0 and on() http_requests_total{endpoint="*/events"} > 0
  for: 1m
  annotations:
    description: "No active SSE connections but requests are coming in"
```

---

## ✅ 복구 확인

### 성공 지표
1. **연결 수 정상화**: `sse_connections_open > 0`
2. **재연결률 감소**: `rate(sse_reconnect_count[5m]) < 5`
3. **메시지 전송 재개**: `rate(sse_message_sent_total[5m]) > 0`
4. **사용자 피드백**: 프론트엔드에서 실시간 업데이트 정상 동작

### 복구 후 점검 사항
```bash
# 1. SSE 엔드포인트 응답 테스트
for i in {1..5}; do
    curl -N -m 10 -H "Accept: text/event-stream" \
         http://localhost:8002/api/generation/jobs/test-job/events &
    sleep 2
done

# 2. 부하 테스트
ab -n 100 -c 10 http://localhost:8002/api/generation/jobs/test-job/events

# 3. 메모리 누수 확인
watch -n 5 'ps -o pid,vsz,rss,comm -p $(pgrep generation-service)'
```

---

## 📝 사후 분석

### 분석 보고서 작성
1. **장애 시간**: 시작 ~ 복구 완료
2. **영향 범위**: 영향받은 사용자 수, 실패한 작업 수
3. **근본 원인**: 기술적 원인 분석
4. **복구 조치**: 수행한 대응 단계
5. **재발 방지**: 구조적 개선 방안

### 개선 조치
- [ ] SSE 연결 모니터링 강화
- [ ] 자동 복구 메커니즘 구현
- [ ] 프록시 설정 표준화
- [ ] 부하 테스트 정기 실행
- [ ] 사용자 가이드 업데이트 (브라우저별 대응)

---

## 🔗 관련 문서

- [SSE API 문서](../docs/api/sse.md)
- [프록시 설정 가이드](../docs/deployment/proxy-setup.md)
- [모니터링 대시보드](https://monitoring.ai-script-generator.com/grafana)
- [사용자 지원 문서](../docs/user-support/sse-issues.md)