# Generation Service 트러블슈팅 가이드

이 가이드는 Generation Service 운영 중 발생할 수 있는 일반적인 문제와 해결 방법을 제공합니다.

## 목차
1. [일반적인 문제](#일반적인-문제)
2. [성능 문제](#성능-문제)
3. [배포 및 컨테이너 문제](#배포-및-컨테이너-문제)
4. [네트워크 및 연결 문제](#네트워크-및-연결-문제)
5. [모니터링 및 로그 분석](#모니터링-및-로그-분석)
6. [캐시 관련 문제](#캐시-관련-문제)
7. [보안 및 인증 문제](#보안-및-인증-문제)
8. [디버깅 도구 및 명령어](#디버깅-도구-및-명령어)

## 일반적인 문제

### 1. 서비스 시작 실패

#### 문제: 컨테이너가 시작되지 않음
```bash
# 증상 확인
docker ps -a
docker logs generation-service

# 해결 방법
# 1. 환경 변수 확인
docker exec generation-service env | grep -E "(ENVIRONMENT|DEBUG|REDIS)"

# 2. 설정 파일 검증
docker exec generation-service cat /app/.env

# 3. 의존성 서비스 상태 확인
docker exec generation-service nc -zv redis 6379
```

#### 문제: "ModuleNotFoundError" 발생
```bash
# 증상
ModuleNotFoundError: No module named 'generation_service'

# 해결 방법
# 1. PYTHONPATH 확인
docker exec generation-service echo $PYTHONPATH

# 2. 패키지 설치 확인
docker exec generation-service pip list | grep generation

# 3. 소스 코드 마운트 확인
docker exec generation-service ls -la /app/src/
```

#### 문제: 포트 바인딩 실패
```bash
# 증상
Error: Port 8000 is already in use

# 해결 방법
# 1. 포트 사용 확인
sudo netstat -tulpn | grep :8000
lsof -i :8000

# 2. 기존 프로세스 종료
sudo kill $(lsof -t -i:8000)

# 3. 다른 포트 사용
docker run -p 8001:8000 generation-service
```

### 2. 헬스체크 실패

#### 문제: API 엔드포인트 응답 없음
```bash
# 증상 확인
curl -v http://localhost:8000/api/monitoring/health

# 해결 방법
# 1. 서비스 상태 확인
docker exec generation-service ps aux | grep uvicorn

# 2. 로그 분석
docker logs generation-service | tail -50

# 3. 내부에서 헬스체크 실행
docker exec generation-service curl localhost:8000/api/monitoring/health
```

#### 문제: 503 Service Unavailable
```bash
# 증상
HTTP/1.1 503 Service Unavailable

# 해결 방법
# 1. 메모리 사용량 확인
docker stats generation-service

# 2. 리소스 제한 확인
docker inspect generation-service | grep -A5 -B5 Memory

# 3. 워커 프로세스 상태 확인
docker exec generation-service ps aux | grep worker
```

## 성능 문제

### 1. 느린 응답 시간

#### 문제: API 응답 시간 > 30초
```bash
# 진단
curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8000/api/monitoring/health

# curl-format.txt 내용:
#     time_namelookup:  %{time_namelookup}\n
#     time_connect:     %{time_connect}\n
#     time_appconnect:  %{time_appconnect}\n
#     time_pretransfer: %{time_pretransfer}\n
#     time_redirect:    %{time_redirect}\n
#     time_starttransfer: %{time_starttransfer}\n
#     ----------\n
#     time_total:       %{time_total}\n

# 해결 방법
# 1. 성능 메트릭 확인
curl http://localhost:8000/api/performance/status | jq '.'

# 2. 캐시 상태 확인
curl http://localhost:8000/api/cache/status | jq '.statistics'

# 3. 리소스 사용량 확인
curl http://localhost:8000/api/performance/resources | jq '.'
```

#### 문제: 높은 메모리 사용량
```bash
# 증상 확인
docker stats generation-service

# 해결 방법
# 1. 메모리 프로파일링
docker exec generation-service python -c "
import psutil
process = psutil.Process()
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
print(f'Memory %: {process.memory_percent():.2f}%')
"

# 2. 메모리 최적화 실행
curl -X POST http://localhost:8000/api/performance/optimize \
  -H "Content-Type: application/json" \
  -d '{"optimization_type": "memory", "force": true}'

# 3. 가비지 컬렉션 강제 실행
docker exec generation-service python -c "import gc; gc.collect()"
```

#### 문제: 높은 CPU 사용률
```bash
# 증상 확인
docker exec generation-service top -bn1 | head -20

# 해결 방법
# 1. CPU 집약적 작업 확인
docker exec generation-service python -c "
import psutil
for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
    if proc.info['cpu_percent'] > 50:
        print(proc.info)
"

# 2. 워커 수 조정
docker exec generation-service curl -X POST http://localhost:8000/api/performance/optimize \
  -H "Content-Type: application/json" \
  -d '{"optimization_type": "cpu", "parameters": {"max_workers": 2}}'

# 3. 비동기 처리 확인
curl http://localhost:8000/api/performance/load | jq '.queues'
```

### 2. 캐시 성능 문제

#### 문제: 낮은 캐시 적중률 (< 70%)
```bash
# 진단
curl http://localhost:8000/api/cache/analytics?period=1h | jq '.'

# 해결 방법
# 1. 캐시 설정 확인
curl http://localhost:8000/api/cache/status | jq '.configuration'

# 2. 캐시 통계 분석
curl http://localhost:8000/api/cache/stats | jq '.by_cache_type'

# 3. 캐시 워밍 실행
curl -X POST http://localhost:8000/api/cache/warm \
  -H "Content-Type: application/json" \
  -d '{"cache_types": ["prompt_result", "model_info"]}'
```

#### 문제: Redis 연결 실패
```bash
# 증상
redis.exceptions.ConnectionError: Error connecting to Redis

# 해결 방법
# 1. Redis 서버 상태 확인
docker exec redis redis-cli ping

# 2. 네트워크 연결 확인
docker exec generation-service nc -zv redis 6379

# 3. Redis 로그 확인
docker logs redis | tail -20

# 4. 연결 설정 확인
docker exec generation-service env | grep REDIS
```

## 배포 및 컨테이너 문제

### 1. Docker 빌드 실패

#### 문제: 이미지 빌드 에러
```bash
# 증상
ERROR: failed to solve: process "/bin/sh -c pip install -r requirements.txt" did not complete successfully

# 해결 방법
# 1. 빌드 로그 상세 확인
docker build --no-cache --progress=plain -f docker/Dockerfile .

# 2. 의존성 충돌 확인
docker run --rm python:3.11-slim pip install -r requirements.txt

# 3. 단계별 빌드 테스트
docker build --target builder -t generation-service:builder .
docker run --rm generation-service:builder pip list
```

#### 문제: 멀티 아키텍처 빌드 실패
```bash
# 증상
ERROR: failed to solve: failed to read dockerfile

# 해결 방법
# 1. Buildx 설정 확인
docker buildx ls

# 2. 플랫폼별 빌드 테스트
docker buildx build --platform linux/amd64 -t generation-service:amd64 .
docker buildx build --platform linux/arm64 -t generation-service:arm64 .

# 3. 에뮬레이션 설정
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

### 2. Kubernetes 배포 문제

#### 문제: Pod 시작 실패
```bash
# 증상 확인
kubectl get pods -n generation-service
kubectl describe pod generation-service-xxx -n generation-service

# 해결 방법
# 1. 이벤트 확인
kubectl get events -n generation-service --sort-by='.lastTimestamp'

# 2. 로그 확인
kubectl logs generation-service-xxx -n generation-service

# 3. 리소스 할당 확인
kubectl top pods -n generation-service
kubectl describe node
```

#### 문제: ImagePullBackOff
```bash
# 증상
STATUS: ImagePullBackOff

# 해결 방법
# 1. 이미지 레지스트리 접근 확인
docker pull ghcr.io/your-org/generation-service:latest

# 2. Secret 확인
kubectl get secret -n generation-service
kubectl describe secret regcred -n generation-service

# 3. 이미지 태그 확인
kubectl describe pod generation-service-xxx -n generation-service | grep Image
```

#### 문제: CrashLoopBackOff
```bash
# 증상
STATUS: CrashLoopBackOff

# 해결 방법
# 1. 종료 원인 확인
kubectl logs generation-service-xxx -n generation-service --previous

# 2. 컨테이너 진입 시도
kubectl exec -it generation-service-xxx -n generation-service -- /bin/bash

# 3. 리소스 제한 확인
kubectl describe pod generation-service-xxx -n generation-service | grep -A10 Limits
```

## 네트워크 및 연결 문제

### 1. 외부 API 연결 실패

#### 문제: OpenAI API 호출 실패
```bash
# 증상
OpenAI API error: Connection timeout

# 해결 방법
# 1. 네트워크 연결 확인
docker exec generation-service curl -I https://api.openai.com

# 2. DNS 해상도 확인
docker exec generation-service nslookup api.openai.com

# 3. API 키 확인
docker exec generation-service env | grep OPENAI_API_KEY

# 4. 프록시 설정 확인
docker exec generation-service env | grep -i proxy
```

#### 문제: 내부 서비스 통신 실패
```bash
# 증상
ConnectionError: HTTPConnectionPool(host='redis', port=6379)

# 해결 방법
# 1. 서비스 디스커버리 확인
docker network ls
docker network inspect generation-network

# 2. 컨테이너 간 통신 테스트
docker exec generation-service ping redis
docker exec generation-service telnet redis 6379

# 3. 포트 바인딩 확인
docker port redis
netstat -tulpn | grep 6379
```

### 2. 로드 밸런서 문제

#### 문제: 502 Bad Gateway
```bash
# 증상
HTTP/1.1 502 Bad Gateway

# 해결 방법
# 1. 백엔드 서비스 상태 확인
curl http://generation-service:8000/api/monitoring/health

# 2. Nginx 설정 확인
docker exec nginx nginx -t
docker logs nginx | tail -20

# 3. 업스트림 연결 테스트
docker exec nginx curl http://generation-service:8000/api/monitoring/health
```

#### 문제: 타임아웃 에러
```bash
# 증상
504 Gateway Timeout

# 해결 방법
# 1. 타임아웃 설정 확인
docker exec nginx grep -r timeout /etc/nginx/

# 2. 백엔드 응답 시간 확인
curl -w "Total time: %{time_total}s\n" http://generation-service:8000/api/monitoring/health

# 3. 워커 프로세스 상태 확인
docker exec generation-service ps aux | grep uvicorn
```

## 모니터링 및 로그 분석

### 1. 로그 분석

#### 구조화된 로그 분석
```bash
# JSON 로그 파싱
docker logs generation-service | jq 'select(.level == "ERROR")'

# 에러 패턴 분석
docker logs generation-service | grep -E "(ERROR|CRITICAL|Exception)" | tail -20

# 성능 로그 분석
docker logs generation-service | grep "workflow_execution_time" | tail -10
```

#### 로그 레벨 조정
```bash
# 현재 로그 레벨 확인
curl http://localhost:8000/api/monitoring/logging/level

# 로그 레벨 변경
curl -X POST http://localhost:8000/api/monitoring/logging/level \
  -H "Content-Type: application/json" \
  -d '{"level": "DEBUG"}'

# 특정 모듈 로그 레벨 변경
curl -X POST http://localhost:8000/api/monitoring/logging/level \
  -H "Content-Type: application/json" \
  -d '{"module": "generation_service.cache", "level": "DEBUG"}'
```

### 2. 메트릭 분석

#### Prometheus 메트릭 확인
```bash
# 메트릭 스크래핑 테스트
curl http://localhost:8000/api/monitoring/metrics/prometheus

# 특정 메트릭 확인
curl http://localhost:9090/api/v1/query?query=generation_service_requests_total

# 메트릭 히스토리 확인
curl "http://localhost:9090/api/v1/query_range?query=generation_service_memory_usage&start=$(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%SZ)&end=$(date -u +%Y-%m-%dT%H:%M:%SZ)&step=60s"
```

#### 커스텀 메트릭 생성
```bash
# 메트릭 수집 시작
curl -X POST http://localhost:8000/api/monitoring/metrics/start

# 커스텀 메트릭 기록
curl -X POST http://localhost:8000/api/monitoring/metrics/record \
  -H "Content-Type: application/json" \
  -d '{"metric_name": "custom_operation_duration", "value": 1.5, "labels": {"operation": "test"}}'
```

### 3. 성능 프로파일링

#### 메모리 프로파일링
```bash
# 메모리 스냅샷 생성
docker exec generation-service python -c "
import tracemalloc
import psutil
import gc

# 메모리 추적 시작
tracemalloc.start()

# 현재 메모리 사용량
process = psutil.Process()
print(f'RSS: {process.memory_info().rss / 1024 / 1024:.2f} MB')

# 가장 많은 메모리를 사용하는 객체들
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

print('Top 10 memory consumers:')
for stat in top_stats[:10]:
    print(stat)
"
```

#### CPU 프로파일링
```bash
# CPU 사용량 모니터링
docker exec generation-service python -c "
import psutil
import time

# CPU 사용량 측정
cpu_percent = psutil.cpu_percent(interval=1)
print(f'CPU Usage: {cpu_percent}%')

# 프로세스별 CPU 사용량
for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
    if proc.info['cpu_percent'] > 1:
        print(f'PID: {proc.info[\"pid\"]}, Name: {proc.info[\"name\"]}, CPU: {proc.info[\"cpu_percent\"]}%')
"
```

## 캐시 관련 문제

### 1. Redis 성능 문제

#### Redis 슬로우 쿼리 분석
```bash
# 슬로우 로그 확인
docker exec redis redis-cli SLOWLOG GET 10

# 현재 연결 확인
docker exec redis redis-cli CLIENT LIST

# 메모리 사용량 확인
docker exec redis redis-cli INFO memory
```

#### Redis 설정 최적화
```bash
# 현재 설정 확인
docker exec redis redis-cli CONFIG GET "*"

# 메모리 정책 확인
docker exec redis redis-cli CONFIG GET maxmemory-policy

# 메모리 정책 변경
docker exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### 2. 캐시 무효화 문제

#### 캐시 일관성 확인
```bash
# 캐시 키 패턴 확인
docker exec redis redis-cli KEYS "generation:*" | head -10

# 특정 캐시 엔트리 확인
docker exec redis redis-cli GET "generation:prompt_result:hash123"

# 캐시 TTL 확인
docker exec redis redis-cli TTL "generation:prompt_result:hash123"
```

#### 캐시 수동 관리
```bash
# 특정 패턴 캐시 삭제
curl -X POST http://localhost:8000/api/cache/clear \
  -H "Content-Type: application/json" \
  -d '{"pattern": "generation:prompt_result:*", "confirm": true}'

# 전체 캐시 플러시 (주의!)
docker exec redis redis-cli FLUSHALL
```

## 보안 및 인증 문제

### 1. 인증 실패

#### API 키 검증
```bash
# API 키 헤더 테스트
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/cache/clear

# JWT 토큰 검증
curl -H "Authorization: Bearer your-jwt-token" http://localhost:8000/api/performance/optimize
```

#### SSL/TLS 문제
```bash
# SSL 인증서 확인
openssl s_client -connect api.yourdomain.com:443

# 인증서 만료일 확인
echo | openssl s_client -servername api.yourdomain.com -connect api.yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
```

### 2. 권한 문제

#### 파일 권한 확인
```bash
# 컨테이너 내 파일 권한 확인
docker exec generation-service ls -la /app/

# 사용자 확인
docker exec generation-service whoami
docker exec generation-service id
```

#### 네트워크 보안 정책
```bash
# Kubernetes Network Policy 확인
kubectl get networkpolicy -n generation-service
kubectl describe networkpolicy generation-service-netpol -n generation-service

# 포트 접근 테스트
kubectl exec -it generation-service-xxx -n generation-service -- nc -zv redis 6379
```

## 디버깅 도구 및 명령어

### 1. 컨테이너 디버깅

#### 컨테이너 진입 및 디버깅
```bash
# 컨테이너 쉘 접속
docker exec -it generation-service /bin/bash

# 디버그 모드로 실행
docker run --rm -e DEBUG=true -e LOG_LEVEL=DEBUG \
  -p 8000:8000 generation-service:dev

# 컨테이너 프로세스 확인
docker exec generation-service ps aux
docker exec generation-service top -bn1
```

#### 네트워크 디버깅
```bash
# 네트워크 연결 확인
docker exec generation-service netstat -tulpn
docker exec generation-service ss -tulpn

# DNS 해상도 테스트
docker exec generation-service nslookup redis
docker exec generation-service dig redis

# 패킷 캡처 (tcpdump 설치 필요)
docker exec generation-service tcpdump -i any -n host redis
```

### 2. 성능 디버깅 도구

#### 시스템 리소스 모니터링
```bash
# 실시간 리소스 사용량
docker stats generation-service

# 상세 시스템 정보
docker exec generation-service python -c "
import psutil
import json

info = {
    'cpu_count': psutil.cpu_count(),
    'memory_total': psutil.virtual_memory().total,
    'disk_usage': psutil.disk_usage('/').percent,
    'network_io': psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
}
print(json.dumps(info, indent=2))
"
```

#### 애플리케이션 디버깅
```bash
# Python 스택 트레이스
docker exec generation-service python -c "
import faulthandler
import sys
faulthandler.dump_traceback(sys.stdout)
"

# 활성 스레드 확인
docker exec generation-service python -c "
import threading
for thread in threading.enumerate():
    print(f'Thread: {thread.name}, Alive: {thread.is_alive()}')
"
```

### 3. 로그 수집 및 분석

#### 중앙 집중식 로그 수집
```bash
# 로그 수집 스크립트
cat > collect-logs.sh << 'EOF'
#!/bin/bash
mkdir -p logs/$(date +%Y%m%d_%H%M%S)
cd logs/$(date +%Y%m%d_%H%M%S)

# 서비스 로그
docker logs generation-service > generation-service.log 2>&1
docker logs redis > redis.log 2>&1
docker logs nginx > nginx.log 2>&1

# 시스템 로그
docker exec generation-service dmesg > dmesg.log 2>/dev/null || true

# 설정 파일
docker exec generation-service cat /app/.env > env.txt 2>/dev/null || true

# 메트릭 스냅샷
curl -s http://localhost:8000/api/monitoring/metrics > metrics.json
curl -s http://localhost:8000/api/cache/status > cache-status.json
curl -s http://localhost:8000/api/performance/status > performance-status.json

echo "로그 수집 완료: $(pwd)"
EOF

chmod +x collect-logs.sh
```

### 4. 자동화된 헬스체크

#### 종합 헬스체크 스크립트
```bash
cat > health-check-comprehensive.sh << 'EOF'
#!/bin/bash
set -e

echo "🏥 Generation Service 종합 헬스체크 시작..."

# 기본 서비스 확인
echo "1. 기본 서비스 헬스체크..."
curl -f http://localhost:8000/api/monitoring/health || echo "❌ 기본 헬스체크 실패"

# 성능 메트릭 확인
echo "2. 성능 메트릭 확인..."
RESPONSE_TIME=$(curl -w "%{time_total}" -s -o /dev/null http://localhost:8000/api/monitoring/health)
if (( $(echo "$RESPONSE_TIME > 5.0" | bc -l) )); then
    echo "⚠️ 응답 시간이 느림: ${RESPONSE_TIME}s"
else
    echo "✅ 응답 시간 양호: ${RESPONSE_TIME}s"
fi

# 캐시 상태 확인
echo "3. 캐시 상태 확인..."
CACHE_HIT_RATIO=$(curl -s http://localhost:8000/api/cache/status | jq -r '.statistics.hit_ratio // 0')
if (( $(echo "$CACHE_HIT_RATIO < 0.7" | bc -l) )); then
    echo "⚠️ 캐시 적중률 낮음: ${CACHE_HIT_RATIO}"
else
    echo "✅ 캐시 적중률 양호: ${CACHE_HIT_RATIO}"
fi

# 메모리 사용량 확인
echo "4. 메모리 사용량 확인..."
MEMORY_USAGE=$(docker stats generation-service --no-stream --format "{{.MemUsage}}" | cut -d'/' -f1 | sed 's/MiB//')
if (( $(echo "$MEMORY_USAGE > 1800" | bc -l) )); then
    echo "⚠️ 메모리 사용량 높음: ${MEMORY_USAGE}MiB"
else
    echo "✅ 메모리 사용량 정상: ${MEMORY_USAGE}MiB"
fi

echo "🏥 헬스체크 완료!"
EOF

chmod +x health-check-comprehensive.sh
```

이 트러블슈팅 가이드를 참조하여 Generation Service 운영 중 발생하는 문제들을 효과적으로 해결할 수 있습니다. 문제가 지속되거나 이 가이드에서 다루지 않은 문제가 발생하면 로그와 메트릭을 수집하여 기술 지원팀에 문의하세요.