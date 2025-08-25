# Generation Service 성능 튜닝 가이드

이 가이드는 Generation Service의 성능을 최적화하고 모니터링하는 방법을 제공합니다.

## 목차
1. [성능 목표 및 지표](#성능-목표-및-지표)
2. [시스템 아키텍처 최적화](#시스템-아키텍처-최적화)
3. [애플리케이션 레벨 최적화](#애플리케이션-레벨-최적화)
4. [캐시 최적화](#캐시-최적화)
5. [데이터베이스 최적화](#데이터베이스-최적화)
6. [네트워크 최적화](#네트워크-최적화)
7. [모니터링 및 프로파일링](#모니터링-및-프로파일링)
8. [스케일링 전략](#스케일링-전략)

## 성능 목표 및 지표

### 1. 핵심 성능 목표

| 메트릭 | 목표 값 | 측정 방법 |
|--------|---------|-----------|
| 워크플로우 실행 시간 | < 30초 | E2E 측정 |
| 동시 워크플로우 처리 | 20개 | 부하 테스트 |
| API 응답 시간 (캐시됨) | < 100ms | P95 측정 |
| 메모리 사용량 | < 2GB | RSS 메모리 |
| 캐시 적중률 | > 70% | Redis 통계 |
| 전체 성공률 | > 95% | 에러율 기반 |

### 2. 성능 지표 측정

#### 실시간 성능 모니터링
```bash
# 현재 성능 상태 확인
curl http://localhost:8000/api/performance/status | jq '.'

# 상세 리소스 메트릭 확인
curl http://localhost:8000/api/performance/resources | jq '.'

# 시스템 부하 확인
curl http://localhost:8000/api/performance/load | jq '.'
```

#### 성능 검증 스크립트
```bash
cat > performance-validation.sh << 'EOF'
#!/bin/bash
set -e

echo "🎯 Generation Service 성능 검증 시작..."

# 성능 메트릭 수집
METRICS=$(curl -s http://localhost:8000/api/monitoring/metrics)
CACHE_STATUS=$(curl -s http://localhost:8000/api/cache/status)
PERFORMANCE_STATUS=$(curl -s http://localhost:8000/api/performance/status)

# 워크플로우 실행 시간 확인
WORKFLOW_TIME=$(echo $METRICS | jq -r '.metrics.workflow_execution_time // 0')
if (( $(echo "$WORKFLOW_TIME > 30" | bc -l) )); then
    echo "❌ 워크플로우 실행 시간 초과: ${WORKFLOW_TIME}s (목표: 30s)"
else
    echo "✅ 워크플로우 실행 시간 양호: ${WORKFLOW_TIME}s"
fi

# 캐시 적중률 확인
CACHE_HIT_RATIO=$(echo $CACHE_STATUS | jq -r '.statistics.hit_ratio // 0')
if (( $(echo "$CACHE_HIT_RATIO < 0.7" | bc -l) )); then
    echo "❌ 캐시 적중률 낮음: ${CACHE_HIT_RATIO} (목표: 0.7)"
else
    echo "✅ 캐시 적중률 양호: ${CACHE_HIT_RATIO}"
fi

# 메모리 사용량 확인
MEMORY_MB=$(echo $METRICS | jq -r '.metrics.memory_usage_mb // 0')
if (( $(echo "$MEMORY_MB > 2048" | bc -l) )); then
    echo "❌ 메모리 사용량 초과: ${MEMORY_MB}MB (목표: 2048MB)"
else
    echo "✅ 메모리 사용량 양호: ${MEMORY_MB}MB"
fi

# 전체 성공률 확인
SUCCESS_RATE=$(echo $METRICS | jq -r '.metrics.success_rate // 1')
if (( $(echo "$SUCCESS_RATE < 0.95" | bc -l) )); then
    echo "❌ 성공률 낮음: ${SUCCESS_RATE} (목표: 0.95)"
else
    echo "✅ 성공률 양호: ${SUCCESS_RATE}"
fi

echo "🎯 성능 검증 완료!"
EOF

chmod +x performance-validation.sh
```

## 시스템 아키텍처 최적화

### 1. 컨테이너 리소스 최적화

#### Docker 리소스 제한 설정
```yaml
# docker-compose.yml
services:
  generation-service:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

#### Kubernetes 리소스 최적화
```yaml
# k8s/deployment.yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

### 2. 마이크로서비스 아키텍처 최적화

#### 서비스 분리 전략
```python
# 성능 집약적 작업을 별도 서비스로 분리
class WorkflowExecutionService:
    """워크플로우 실행 전용 서비스"""
    
    async def execute_workflow(self, workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        # CPU 집약적 작업
        pass

class CacheService:
    """캐싱 전용 서비스"""
    
    async def get_cached_result(self, key: str) -> Optional[Any]:
        # 메모리 집약적 작업
        pass
```

#### 비동기 처리 최적화
```python
# src/generation_service/optimization/async_manager.py
class AsyncManager:
    def __init__(self, config: Dict[str, Any]):
        self.pools = {
            "ai_api": asyncio.Semaphore(config.get("ai_api_concurrency", 5)),
            "io_operations": asyncio.Semaphore(config.get("io_concurrency", 20)),
            "cpu_intensive": asyncio.Semaphore(config.get("cpu_concurrency", 2))
        }
    
    async def execute_with_pool(self, pool_name: str, coro):
        async with self.pools[pool_name]:
            return await coro
```

## 애플리케이션 레벨 최적화

### 1. Python 성능 최적화

#### 메모리 관리 최적화
```python
# src/generation_service/optimization/memory_optimizer.py
import gc
import psutil
from typing import Optional

class MemoryOptimizer:
    def __init__(self, threshold_mb: int = 1024):
        self.threshold_mb = threshold_mb
        self.last_gc_time = time.time()
    
    def optimize_memory(self) -> Dict[str, Any]:
        """메모리 최적화 실행"""
        before_mb = self._get_memory_usage_mb()
        
        # 강제 가비지 컬렉션
        collected = gc.collect()
        
        # 순환 참조 정리
        gc.collect()
        
        after_mb = self._get_memory_usage_mb()
        freed_mb = before_mb - after_mb
        
        return {
            "before_mb": before_mb,
            "after_mb": after_mb,
            "freed_mb": freed_mb,
            "objects_collected": collected
        }
    
    def _get_memory_usage_mb(self) -> float:
        """현재 메모리 사용량 반환 (MB)"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
```

#### CPU 집약적 작업 최적화
```python
# src/generation_service/optimization/cpu_optimizer.py
import asyncio
import concurrent.futures
from functools import lru_cache

class CPUOptimizer:
    def __init__(self, max_workers: int = 4):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    
    async def run_cpu_intensive_task(self, func, *args, **kwargs):
        """CPU 집약적 작업을 별도 스레드에서 실행"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)
    
    @lru_cache(maxsize=1000)
    def cached_computation(self, input_data: str) -> str:
        """계산 결과 캐싱"""
        # 복잡한 계산 로직
        return f"processed_{input_data}"
```

### 2. 요청 처리 최적화

#### 배치 처리 구현
```python
# src/generation_service/optimization/batch_processor.py
import asyncio
from collections import defaultdict
from typing import List, Dict, Any

class BatchProcessor:
    def __init__(self, batch_size: int = 10, wait_time: float = 0.1):
        self.batch_size = batch_size
        self.wait_time = wait_time
        self.pending_requests = defaultdict(list)
        self.processing = False
    
    async def add_request(self, request_type: str, request_data: Any) -> Any:
        """요청을 배치에 추가하고 결과 반환"""
        future = asyncio.Future()
        self.pending_requests[request_type].append((request_data, future))
        
        if not self.processing:
            asyncio.create_task(self._process_batches())
        
        return await future
    
    async def _process_batches(self):
        """배치 처리 실행"""
        if self.processing:
            return
        
        self.processing = True
        
        try:
            await asyncio.sleep(self.wait_time)
            
            for request_type, requests in self.pending_requests.items():
                if len(requests) >= self.batch_size or len(requests) > 0:
                    await self._process_batch(request_type, requests)
                    self.pending_requests[request_type].clear()
        
        finally:
            self.processing = False
    
    async def _process_batch(self, request_type: str, requests: List[tuple]):
        """단일 배치 처리"""
        # 배치 단위로 요청 처리
        data_list = [req[0] for req in requests]
        futures = [req[1] for req in requests]
        
        try:
            results = await self._execute_batch(request_type, data_list)
            for future, result in zip(futures, results):
                future.set_result(result)
        except Exception as e:
            for future in futures:
                future.set_exception(e)
```

#### 연결 풀링 최적화
```python
# src/generation_service/optimization/connection_pool.py
import aiohttp
import asyncio
from typing import Optional

class ConnectionPoolManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self):
        """연결 풀 초기화"""
        connector = aiohttp.TCPConnector(
            limit=self.config.get("max_connections", 100),
            limit_per_host=self.config.get("max_connections_per_host", 30),
            ttl_dns_cache=self.config.get("dns_cache_ttl", 300),
            use_dns_cache=True,
            keepalive_timeout=self.config.get("keepalive_timeout", 30),
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=self.config.get("total_timeout", 30),
            connect=self.config.get("connect_timeout", 5)
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
    
    async def make_request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """최적화된 HTTP 요청"""
        if not self.session:
            await self.initialize()
        
        return await self.session.request(method, url, **kwargs)
```

## 캐시 최적화

### 1. Redis 성능 튜닝

#### Redis 설정 최적화
```bash
# redis-performance.conf
# 메모리 최적화
maxmemory 1gb
maxmemory-policy allkeys-lru

# 지속성 최적화 (성능 우선시)
save 900 1
save 300 10
save 60 10000

# 네트워크 최적화
tcp-keepalive 300
tcp-backlog 511

# 성능 최적화
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
```

#### Redis 모니터링 및 최적화
```bash
# Redis 성능 통계 확인
redis-cli INFO stats | grep -E "(total_commands_processed|instantaneous_ops_per_sec|used_memory_human)"

# 슬로우 쿼리 확인
redis-cli SLOWLOG GET 10

# 키 분포 확인
redis-cli --bigkeys

# 메모리 사용량 분석
redis-cli MEMORY USAGE key_name
```

### 2. 다층 캐시 전략

#### L1 (메모리) + L2 (Redis) 캐시 구현
```python
# src/generation_service/cache/multi_level_cache.py
import asyncio
from typing import Any, Optional
from dataclasses import dataclass
import time

@dataclass
class CacheEntry:
    value: Any
    expire_time: float
    access_count: int = 0

class MultiLevelCache:
    def __init__(self, l1_size: int = 1000, l1_ttl: int = 300):
        self.l1_cache = {}  # 메모리 캐시
        self.l1_size = l1_size
        self.l1_ttl = l1_ttl
        self.redis_client = None  # Redis 클라이언트
    
    async def get(self, key: str) -> Optional[Any]:
        """다층 캐시에서 값 조회"""
        # L1 캐시 확인
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if time.time() < entry.expire_time:
                entry.access_count += 1
                return entry.value
            else:
                del self.l1_cache[key]
        
        # L2 (Redis) 캐시 확인
        if self.redis_client:
            value = await self.redis_client.get(key)
            if value is not None:
                # L1 캐시에 승격
                await self._set_l1(key, value)
                return value
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """다층 캐시에 값 저장"""
        # L1 캐시에 저장
        await self._set_l1(key, value)
        
        # L2 (Redis) 캐시에 저장
        if self.redis_client:
            await self.redis_client.setex(key, ttl, value)
    
    async def _set_l1(self, key: str, value: Any):
        """L1 캐시에 값 저장"""
        if len(self.l1_cache) >= self.l1_size:
            # LRU 정책으로 제거
            oldest_key = min(
                self.l1_cache.keys(),
                key=lambda k: self.l1_cache[k].access_count
            )
            del self.l1_cache[oldest_key]
        
        self.l1_cache[key] = CacheEntry(
            value=value,
            expire_time=time.time() + self.l1_ttl
        )
```

### 3. 스마트 캐시 전략

#### 예측 기반 캐시 워밍
```python
# src/generation_service/cache/smart_warmer.py
import asyncio
from typing import List, Dict, Any
from collections import defaultdict

class SmartCacheWarmer:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.access_patterns = defaultdict(int)
        self.warming_in_progress = set()
    
    async def record_access(self, cache_key: str):
        """캐시 접근 패턴 기록"""
        self.access_patterns[cache_key] += 1
        
        # 임계값 초과시 관련 키들 예측 워밍
        if self.access_patterns[cache_key] > 10:
            await self._predictive_warm(cache_key)
    
    async def _predictive_warm(self, hot_key: str):
        """예측 기반 캐시 워밍"""
        if hot_key in self.warming_in_progress:
            return
        
        self.warming_in_progress.add(hot_key)
        
        try:
            # 관련 키 패턴 예측
            related_keys = self._predict_related_keys(hot_key)
            
            # 백그라운드에서 워밍
            warming_tasks = [
                self._warm_key(key) for key in related_keys
                if key not in self.cache_manager.cache
            ]
            
            if warming_tasks:
                await asyncio.gather(*warming_tasks, return_exceptions=True)
        
        finally:
            self.warming_in_progress.discard(hot_key)
    
    def _predict_related_keys(self, key: str) -> List[str]:
        """관련 키 예측 로직"""
        # 패턴 기반 관련 키 생성
        if "prompt_result" in key:
            # 비슷한 프롬프트 키들 반환
            base_pattern = key.split(":")[0] + ":"
            return [
                f"{base_pattern}similar_1",
                f"{base_pattern}similar_2"
            ]
        
        return []
```

## 데이터베이스 최적화

### 1. 연결 풀 최적화

#### PostgreSQL 연결 풀 설정
```python
# src/generation_service/database/connection_pool.py
import asyncpg
import asyncio
from typing import Optional

class DatabasePool:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """데이터베이스 연결 풀 초기화"""
        self.pool = await asyncpg.create_pool(
            host=self.config["host"],
            port=self.config["port"],
            user=self.config["user"],
            password=self.config["password"],
            database=self.config["database"],
            min_size=self.config.get("min_connections", 5),
            max_size=self.config.get("max_connections", 20),
            max_queries=self.config.get("max_queries", 50000),
            max_inactive_connection_lifetime=self.config.get("max_idle_time", 300),
            command_timeout=self.config.get("command_timeout", 30)
        )
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """최적화된 쿼리 실행"""
        async with self.pool.acquire() as connection:
            # 쿼리 실행 시간 측정
            start_time = time.time()
            
            try:
                result = await connection.fetch(query, *args)
                execution_time = time.time() - start_time
                
                # 슬로우 쿼리 로깅
                if execution_time > 1.0:
                    logger.warning(f"Slow query detected: {execution_time:.2f}s - {query[:100]}")
                
                return [dict(row) for row in result]
            
            except Exception as e:
                logger.error(f"Query failed: {query[:100]} - {str(e)}")
                raise
```

### 2. 쿼리 최적화

#### 인덱스 최적화 전략
```sql
-- 성능 크리티컬 쿼리를 위한 인덱스
CREATE INDEX CONCURRENTLY idx_workflows_status_created 
ON workflows(status, created_at) 
WHERE status IN ('running', 'pending');

-- 복합 인덱스 최적화
CREATE INDEX CONCURRENTLY idx_cache_entries_type_key 
ON cache_entries(cache_type, cache_key, expires_at);

-- 파티셔닝을 위한 준비
CREATE INDEX CONCURRENTLY idx_metrics_timestamp 
ON performance_metrics(timestamp DESC);
```

#### 쿼리 성능 모니터링
```python
# src/generation_service/database/query_monitor.py
import time
import asyncio
from collections import defaultdict
from typing import Dict, List

class QueryPerformanceMonitor:
    def __init__(self):
        self.query_stats = defaultdict(list)
        self.slow_query_threshold = 1.0
    
    def record_query(self, query: str, execution_time: float):
        """쿼리 성능 기록"""
        self.query_stats[query].append(execution_time)
        
        if execution_time > self.slow_query_threshold:
            logger.warning(f"Slow query: {execution_time:.2f}s - {query[:100]}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """성능 리포트 생성"""
        report = {}
        
        for query, times in self.query_stats.items():
            if times:
                report[query[:100]] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "max_time": max(times),
                    "min_time": min(times)
                }
        
        return report
```

## 네트워크 최적화

### 1. HTTP/2 및 연결 최적화

#### Nginx HTTP/2 설정
```nginx
# nginx/nginx-performance.conf
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    # HTTP/2 최적화
    http2_push_preload on;
    http2_max_field_size 16k;
    http2_max_header_size 32k;
    
    # 연결 최적화
    keepalive_timeout 65;
    keepalive_requests 1000;
    
    # 압축 최적화
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_types
        application/json
        application/javascript
        text/css
        text/plain
        text/xml;
    
    # 버퍼링 최적화
    client_body_buffer_size 128k;
    client_max_body_size 50m;
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
    
    location /api/ {
        proxy_pass http://generation_service;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        
        # 타임아웃 최적화
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 캐싱 헤더
        add_header Cache-Control "public, max-age=300" always;
    }
}
```

### 2. CDN 및 정적 자산 최적화

#### 정적 자산 캐싱 전략
```nginx
# 정적 파일 최적화
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header Vary Accept-Encoding;
    
    # 압축
    gzip_static on;
    brotli_static on;
}

# API 응답 캐싱
location /api/monitoring/ {
    proxy_pass http://generation_service;
    proxy_cache api_cache;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$request_uri";
    add_header X-Cache-Status $upstream_cache_status;
}
```

## 모니터링 및 프로파일링

### 1. 실시간 성능 모니터링

#### 커스텀 성능 메트릭 수집
```python
# src/generation_service/monitoring/performance_collector.py
import time
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Any
import psutil

@dataclass
class PerformanceSnapshot:
    timestamp: float
    cpu_percent: float
    memory_mb: float
    active_connections: int
    request_rate: float
    response_time_p95: float
    cache_hit_ratio: float
    error_rate: float

class PerformanceCollector:
    def __init__(self):
        self.snapshots: List[PerformanceSnapshot] = []
        self.max_snapshots = 1000
        self.collection_interval = 10.0
        self.collecting = False
    
    async def start_collection(self):
        """성능 데이터 수집 시작"""
        if self.collecting:
            return
        
        self.collecting = True
        asyncio.create_task(self._collection_loop())
    
    async def _collection_loop(self):
        """성능 데이터 수집 루프"""
        while self.collecting:
            try:
                snapshot = await self._collect_snapshot()
                self.snapshots.append(snapshot)
                
                # 오래된 스냅샷 제거
                if len(self.snapshots) > self.max_snapshots:
                    self.snapshots = self.snapshots[-self.max_snapshots:]
                
                await asyncio.sleep(self.collection_interval)
            
            except Exception as e:
                logger.error(f"Performance collection error: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def _collect_snapshot(self) -> PerformanceSnapshot:
        """성능 스냅샷 수집"""
        # 시스템 메트릭
        cpu_percent = psutil.cpu_percent()
        memory_info = psutil.virtual_memory()
        memory_mb = memory_info.used / 1024 / 1024
        
        # 애플리케이션 메트릭 (가정)
        active_connections = await self._get_active_connections()
        request_rate = await self._get_request_rate()
        response_time_p95 = await self._get_response_time_p95()
        cache_hit_ratio = await self._get_cache_hit_ratio()
        error_rate = await self._get_error_rate()
        
        return PerformanceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            active_connections=active_connections,
            request_rate=request_rate,
            response_time_p95=response_time_p95,
            cache_hit_ratio=cache_hit_ratio,
            error_rate=error_rate
        )
    
    def get_performance_trend(self, minutes: int = 60) -> Dict[str, Any]:
        """성능 트렌드 분석"""
        cutoff_time = time.time() - (minutes * 60)
        recent_snapshots = [
            s for s in self.snapshots 
            if s.timestamp > cutoff_time
        ]
        
        if not recent_snapshots:
            return {"error": "No recent data available"}
        
        # 트렌드 계산
        avg_cpu = sum(s.cpu_percent for s in recent_snapshots) / len(recent_snapshots)
        avg_memory = sum(s.memory_mb for s in recent_snapshots) / len(recent_snapshots)
        avg_response_time = sum(s.response_time_p95 for s in recent_snapshots) / len(recent_snapshots)
        
        return {
            "period_minutes": minutes,
            "snapshot_count": len(recent_snapshots),
            "avg_cpu_percent": round(avg_cpu, 2),
            "avg_memory_mb": round(avg_memory, 2),
            "avg_response_time_p95": round(avg_response_time, 3),
            "current_performance_rating": self._calculate_performance_rating(recent_snapshots[-1])
        }
    
    def _calculate_performance_rating(self, snapshot: PerformanceSnapshot) -> str:
        """성능 등급 계산"""
        score = 0
        
        # CPU 점수 (낮을수록 좋음)
        if snapshot.cpu_percent < 50:
            score += 25
        elif snapshot.cpu_percent < 75:
            score += 15
        elif snapshot.cpu_percent < 90:
            score += 5
        
        # 메모리 점수 (2GB 기준)
        if snapshot.memory_mb < 1024:
            score += 25
        elif snapshot.memory_mb < 1536:
            score += 15
        elif snapshot.memory_mb < 2048:
            score += 5
        
        # 응답 시간 점수
        if snapshot.response_time_p95 < 0.1:
            score += 25
        elif snapshot.response_time_p95 < 0.5:
            score += 15
        elif snapshot.response_time_p95 < 1.0:
            score += 5
        
        # 캐시 적중률 점수
        if snapshot.cache_hit_ratio > 0.8:
            score += 25
        elif snapshot.cache_hit_ratio > 0.7:
            score += 15
        elif snapshot.cache_hit_ratio > 0.5:
            score += 5
        
        # 등급 결정
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "fair"
        else:
            return "poor"
```

### 2. 자동화된 성능 최적화

#### 적응형 최적화 시스템
```python
# src/generation_service/optimization/adaptive_optimizer.py
import asyncio
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class OptimizationRule:
    condition: str
    action: str
    threshold: float
    cooldown_seconds: int = 300

class AdaptiveOptimizer:
    def __init__(self, performance_collector):
        self.performance_collector = performance_collector
        self.optimization_rules = [
            OptimizationRule("memory_mb", "gc_collect", 1536),
            OptimizationRule("cpu_percent", "reduce_workers", 80),
            OptimizationRule("response_time_p95", "clear_cache", 2.0),
            OptimizationRule("cache_hit_ratio", "warm_cache", 0.6, 600)
        ]
        self.last_optimization_time = {}
        self.optimizing = False
    
    async def start_optimization(self):
        """적응형 최적화 시작"""
        if self.optimizing:
            return
        
        self.optimizing = True
        asyncio.create_task(self._optimization_loop())
    
    async def _optimization_loop(self):
        """최적화 루프"""
        while self.optimizing:
            try:
                await self._check_and_optimize()
                await asyncio.sleep(60)  # 1분마다 확인
            
            except Exception as e:
                logger.error(f"Adaptive optimization error: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_optimize(self):
        """성능 확인 및 최적화 실행"""
        if not self.performance_collector.snapshots:
            return
        
        latest_snapshot = self.performance_collector.snapshots[-1]
        current_time = time.time()
        
        for rule in self.optimization_rules:
            # 쿨다운 확인
            last_optimization = self.last_optimization_time.get(rule.action, 0)
            if current_time - last_optimization < rule.cooldown_seconds:
                continue
            
            # 조건 확인
            metric_value = getattr(latest_snapshot, rule.condition, 0)
            should_optimize = False
            
            if rule.condition in ["memory_mb", "cpu_percent", "response_time_p95"]:
                should_optimize = metric_value > rule.threshold
            elif rule.condition == "cache_hit_ratio":
                should_optimize = metric_value < rule.threshold
            
            if should_optimize:
                await self._execute_optimization(rule)
                self.last_optimization_time[rule.action] = current_time
    
    async def _execute_optimization(self, rule: OptimizationRule):
        """최적화 실행"""
        logger.info(f"Executing adaptive optimization: {rule.action} (condition: {rule.condition} threshold: {rule.threshold})")
        
        try:
            if rule.action == "gc_collect":
                await self._force_garbage_collection()
            elif rule.action == "reduce_workers":
                await self._reduce_worker_count()
            elif rule.action == "clear_cache":
                await self._clear_expired_cache()
            elif rule.action == "warm_cache":
                await self._warm_popular_cache()
        
        except Exception as e:
            logger.error(f"Optimization action failed: {rule.action} - {e}")
    
    async def _force_garbage_collection(self):
        """강제 가비지 컬렉션"""
        import gc
        collected = gc.collect()
        logger.info(f"Garbage collection completed: {collected} objects collected")
    
    async def _reduce_worker_count(self):
        """워커 수 감소"""
        # 워커 수 조정 로직
        logger.info("Reducing worker count due to high CPU usage")
    
    async def _clear_expired_cache(self):
        """만료된 캐시 정리"""
        # 캐시 정리 로직
        logger.info("Clearing expired cache entries due to slow response time")
    
    async def _warm_popular_cache(self):
        """인기 캐시 워밍"""
        # 캐시 워밍 로직
        logger.info("Warming popular cache entries due to low hit ratio")
```

## 스케일링 전략

### 1. 수평 스케일링

#### Kubernetes HPA 설정
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: generation-service-hpa
  namespace: generation-service
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: generation-service
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 4
        periodSeconds: 60
      selectPolicy: Max
```

#### 수직 스케일링 (VPA)
```yaml
# k8s/vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: generation-service-vpa
  namespace: generation-service
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: generation-service
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: generation-service
      minAllowed:
        cpu: 100m
        memory: 512Mi
      maxAllowed:
        cpu: 2000m
        memory: 4Gi
      controlledResources: ["cpu", "memory"]
```

### 2. 로드 밸런싱 최적화

#### 지능형 로드 밸런싱
```nginx
# nginx/upstream-optimization.conf
upstream generation_service {
    least_conn;
    
    # 서버별 가중치 설정
    server generation-service-1:8000 weight=3 max_fails=2 fail_timeout=30s;
    server generation-service-2:8000 weight=2 max_fails=2 fail_timeout=30s;
    server generation-service-3:8000 weight=1 max_fails=2 fail_timeout=30s;
    
    # 연결 유지
    keepalive 32;
    keepalive_requests 1000;
    keepalive_timeout 60s;
}
```

### 3. 성능 기반 자동 스케일링

#### 커스텀 메트릭 기반 스케일링
```python
# src/generation_service/scaling/custom_scaler.py
import asyncio
import time
from typing import Dict, Any

class CustomAutoScaler:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scaling_enabled = True
        self.last_scale_time = 0
        self.scale_cooldown = config.get("scale_cooldown", 300)  # 5분
    
    async def evaluate_scaling(self) -> Dict[str, Any]:
        """스케일링 필요성 평가"""
        current_time = time.time()
        
        # 쿨다운 확인
        if current_time - self.last_scale_time < self.scale_cooldown:
            return {"action": "none", "reason": "cooldown"}
        
        # 현재 메트릭 수집
        metrics = await self._collect_scaling_metrics()
        
        # 스케일링 결정
        decision = self._make_scaling_decision(metrics)
        
        if decision["action"] != "none":
            self.last_scale_time = current_time
        
        return decision
    
    async def _collect_scaling_metrics(self) -> Dict[str, float]:
        """스케일링 결정을 위한 메트릭 수집"""
        # 성능 메트릭 수집 로직
        return {
            "avg_response_time": 0.5,
            "requests_per_second": 150,
            "cpu_utilization": 65,
            "memory_utilization": 70,
            "queue_length": 25,
            "error_rate": 0.02
        }
    
    def _make_scaling_decision(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """메트릭 기반 스케일링 결정"""
        scale_up_score = 0
        scale_down_score = 0
        
        # 스케일 업 조건 평가
        if metrics["avg_response_time"] > 1.0:
            scale_up_score += 30
        if metrics["cpu_utilization"] > 80:
            scale_up_score += 25
        if metrics["memory_utilization"] > 85:
            scale_up_score += 25
        if metrics["queue_length"] > 50:
            scale_up_score += 20
        
        # 스케일 다운 조건 평가
        if metrics["avg_response_time"] < 0.2:
            scale_down_score += 20
        if metrics["cpu_utilization"] < 30:
            scale_down_score += 25
        if metrics["memory_utilization"] < 40:
            scale_down_score += 25
        if metrics["requests_per_second"] < 50:
            scale_down_score += 30
        
        # 결정 로직
        if scale_up_score > 50:
            return {
                "action": "scale_up",
                "reason": f"High load detected (score: {scale_up_score})",
                "target_replicas": "+2"
            }
        elif scale_down_score > 60:
            return {
                "action": "scale_down",
                "reason": f"Low load detected (score: {scale_down_score})",
                "target_replicas": "-1"
            }
        else:
            return {
                "action": "none",
                "reason": "Metrics within acceptable range"
            }
```

이 성능 튜닝 가이드를 따라 Generation Service의 성능을 체계적으로 최적화할 수 있습니다. 정기적인 모니터링과 점진적인 튜닝을 통해 최상의 성능을 달성하고 유지하세요.