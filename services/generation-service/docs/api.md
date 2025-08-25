# Generation Service API 문서

이 문서는 Generation Service의 RESTful API 사용법을 설명합니다.

## 개요

Generation Service는 AI 콘텐츠 생성을 위한 고성능 마이크로서비스로, 다음과 같은 주요 기능을 제공합니다:

- **워크플로우 실행**: 복잡한 AI 생성 워크플로우 관리
- **캐싱 시스템**: 지능형 결과 캐싱으로 성능 최적화
- **모니터링**: 실시간 성능 모니터링 및 메트릭 수집
- **성능 최적화**: 자동 리소스 관리 및 최적화

## 기본 정보

- **Base URL**: `http://localhost:8000` (개발), `https://api.yourdomain.com` (프로덕션)
- **API 버전**: v1
- **데이터 형식**: JSON
- **인증**: API Key (선택적 엔드포인트)

## 성능 목표

| 메트릭 | 목표 값 |
|--------|---------|
| 워크플로우 실행 시간 | < 30초 |
| 동시 워크플로우 처리 | 20개 |
| API 응답 시간 (캐시됨) | < 100ms |
| 메모리 사용량 | < 2GB |
| 캐시 적중률 | > 70% |
| 전체 성공률 | > 95% |

## 인증

일부 엔드포인트는 API 키 인증이 필요합니다:

```bash
curl -H "X-API-Key: your-api-key" https://api.yourdomain.com/api/protected/endpoint
```

## API 엔드포인트

### 모니터링 API

#### GET /api/monitoring/health
서비스 헬스체크를 수행합니다.

**응답 예시:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "overall_status": "healthy",
  "components": {
    "cache": "healthy",
    "database": "healthy",
    "redis": "healthy",
    "memory": "healthy"
  },
  "uptime": 3600,
  "version": "1.0.0",
  "memory_usage": {
    "current_mb": 1024,
    "limit_mb": 2048,
    "percentage": 50.0
  }
}
```

#### GET /api/monitoring/metrics
시스템 메트릭을 조회합니다.

**응답 예시:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "metrics": {
    "workflow_execution_time": 25.5,
    "concurrent_workflows": 8,
    "cache_hit_ratio": 0.75,
    "memory_usage_mb": 1024,
    "cpu_usage_percent": 45.2,
    "requests_per_second": 15.3,
    "error_rate": 0.02
  },
  "performance_targets": {
    "all_met": true,
    "workflow_time_target": 30.0,
    "cache_ratio_target": 0.7,
    "memory_limit_mb": 2048
  }
}
```

#### GET /api/monitoring/status
상세한 서비스 상태를 조회합니다.

**응답 예시:**
```json
{
  "service_name": "generation-service",
  "version": "1.0.0",
  "environment": "production",
  "status": "healthy",
  "started_at": "2024-01-15T09:00:00Z",
  "components": [
    {
      "name": "cache",
      "status": "healthy",
      "last_checked": "2024-01-15T10:30:00Z",
      "response_time_ms": 5.2
    },
    {
      "name": "database",
      "status": "healthy", 
      "last_checked": "2024-01-15T10:30:00Z",
      "response_time_ms": 12.8
    }
  ]
}
```

#### GET /api/monitoring/dashboard
대시보드용 집계 데이터를 조회합니다.

**응답 예시:**
```json
{
  "summary": {
    "total_requests": 10000,
    "successful_requests": 9850,
    "error_rate": 0.015,
    "avg_response_time": 0.25
  },
  "real_time_metrics": {
    "timestamp": "2024-01-15T10:30:00Z",
    "metrics": {
      "workflow_execution_time": 25.5,
      "concurrent_workflows": 8,
      "memory_usage_mb": 1024
    }
  },
  "alerts": [
    {
      "id": "high_memory_usage",
      "level": "warning",
      "message": "Memory usage approaching limit",
      "timestamp": "2024-01-15T10:25:00Z",
      "component": "memory"
    }
  ]
}
```

#### GET /api/monitoring/metrics/prometheus
Prometheus 형식의 메트릭을 조회합니다.

**응답 예시:**
```
# HELP generation_service_requests_total Total number of requests
# TYPE generation_service_requests_total counter
generation_service_requests_total{method="GET",endpoint="/api/monitoring/health"} 1234

# HELP generation_service_memory_usage_bytes Current memory usage in bytes
# TYPE generation_service_memory_usage_bytes gauge
generation_service_memory_usage_bytes 1073741824

# HELP generation_service_workflow_duration_seconds Workflow execution time
# TYPE generation_service_workflow_duration_seconds histogram
generation_service_workflow_duration_seconds_bucket{le="1"} 100
generation_service_workflow_duration_seconds_bucket{le="5"} 450
generation_service_workflow_duration_seconds_bucket{le="10"} 800
generation_service_workflow_duration_seconds_bucket{le="+Inf"} 1000
```

### 캐시 관리 API

#### GET /api/cache/status
캐시 시스템 상태를 조회합니다.

**응답 예시:**
```json
{
  "enabled": true,
  "backend": "redis",
  "statistics": {
    "hits": 1500,
    "misses": 350,
    "hit_ratio": 0.81,
    "total_operations": 1850
  },
  "health": "healthy",
  "memory_usage_mb": 128,
  "key_count": 1250,
  "configuration": {
    "ttl_seconds": 3600,
    "max_size_mb": 512,
    "cleanup_interval": 300
  }
}
```

#### GET /api/cache/stats
상세한 캐시 통계를 조회합니다.

**응답 예시:**
```json
{
  "operations": {
    "total": 1850,
    "hits": 1500,
    "misses": 350,
    "sets": 1200,
    "deletes": 50
  },
  "performance": {
    "avg_response_time_ms": 2.5,
    "hit_ratio": 0.81,
    "throughput_ops_per_second": 150.2
  },
  "by_cache_type": {
    "prompt_result": {
      "hits": 800,
      "misses": 150,
      "hit_ratio": 0.84
    },
    "model_info": {
      "hits": 450,
      "misses": 100,
      "hit_ratio": 0.82
    },
    "workflow_state": {
      "hits": 250,
      "misses": 100,
      "hit_ratio": 0.71
    }
  }
}
```

#### GET /api/cache/health
캐시 시스템 헬스체크를 수행합니다.

**응답 예시:**
```json
{
  "component": "cache",
  "status": "healthy",
  "response_time_ms": 3.2,
  "timestamp": "2024-01-15T10:30:00Z",
  "details": {
    "redis_connection": "healthy",
    "memory_cache": "healthy",
    "operation_latency": "normal"
  }
}
```

#### GET /api/cache/analytics
캐시 성능 분석 데이터를 조회합니다.

**쿼리 파라미터:**
- `period`: 분석 기간 (1h, 24h, 7d, 30d)

**응답 예시:**
```json
{
  "period": "24h",
  "trends": {
    "hit_ratio_trend": "increasing",
    "usage_trend": "stable"
  },
  "hottest_keys": [
    {
      "key_pattern": "prompt_result:gpt-*",
      "access_count": 450
    },
    {
      "key_pattern": "model_info:*",
      "access_count": 320
    }
  ],
  "recommendations": [
    "Consider increasing TTL for frequently accessed prompt results",
    "Implement cache warming for popular model information"
  ]
}
```

#### POST /api/cache/clear
캐시를 정리합니다. (인증 필요)

**요청 예시:**
```json
{
  "cache_type": "prompt_result",
  "pattern": "gpt-*",
  "confirm": true
}
```

**응답 예시:**
```json
{
  "cleared_count": 150,
  "cache_type": "prompt_result", 
  "pattern": "gpt-*",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 성능 관리 API

#### GET /api/performance/status
성능 시스템 상태를 조회합니다.

**응답 예시:**
```json
{
  "optimization_enabled": true,
  "async_enabled": true,
  "current_load": 0.45,
  "performance_rating": "good",
  "resource_usage": {
    "memory_percent": 42.3,
    "cpu_percent": 35.8,
    "disk_percent": 25.1
  },
  "active_optimizations": [
    "connection_pooling",
    "request_batching", 
    "smart_caching"
  ]
}
```

#### GET /api/performance/resources
리소스 사용량 메트릭을 조회합니다.

**응답 예시:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "memory": {
    "used_mb": 1024,
    "available_mb": 1024,
    "percentage": 50.0
  },
  "cpu": {
    "usage_percent": 45.2,
    "load_average": [1.2, 1.1, 0.9]
  },
  "disk": {
    "used_gb": 15.2,
    "available_gb": 44.8,
    "percentage": 25.3
  },
  "network": {
    "bytes_sent": 1048576000,
    "bytes_received": 2097152000
  }
}
```

#### GET /api/performance/load
현재 시스템 부하를 조회합니다.

**응답 예시:**
```json
{
  "current_load": 0.45,
  "capacity": {
    "max_concurrent_requests": 100,
    "current_concurrent_requests": 15
  },
  "queues": {
    "pending_requests": 5,
    "processing_requests": 15
  },
  "bottlenecks": [
    "database_connections",
    "external_api_rate_limits"
  ]
}
```

#### GET /api/performance/analytics
성능 분석 데이터를 조회합니다.

**쿼리 파라미터:**
- `period`: 분석 기간 (1h, 24h, 7d, 30d)
- `metrics`: 포함할 메트릭 (쉼표로 구분)

**응답 예시:**
```json
{
  "period": "24h",
  "metrics": {
    "response_times": {
      "avg": 0.25,
      "p50": 0.20,
      "p95": 0.45,
      "p99": 0.80
    },
    "throughput": {
      "requests_per_second": 15.3,
      "peak_rps": 45.2
    },
    "error_rates": {
      "overall": 0.015,
      "by_endpoint": {
        "/api/monitoring/health": 0.001,
        "/api/cache/status": 0.005
      }
    }
  },
  "trends": {
    "response_time": "improving",
    "throughput": "stable",
    "error_rate": "improving"
  }
}
```

#### POST /api/performance/optimize
성능 최적화를 실행합니다. (인증 필요)

**요청 예시:**
```json
{
  "optimization_type": "memory",
  "force": false,
  "parameters": {
    "target_memory_mb": 1024
  }
}
```

**응답 예시:**
```json
{
  "optimization_id": "opt_2024011510300001",
  "status": "completed",
  "actions_taken": [
    "garbage_collection_executed",
    "cache_cleanup_performed",
    "connection_pool_optimized"
  ],
  "estimated_improvement": {
    "memory_saved_mb": 256,
    "performance_gain_percent": 15.0
  },
  "completion_time": "2024-01-15T10:31:00Z"
}
```

## 에러 처리

### 표준 에러 응답 형식

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "Additional error details",
    "suggestion": "Recommended action"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_2024011510300001"
}
```

### HTTP 상태 코드

| 코드 | 의미 | 설명 |
|------|------|------|
| 200 | OK | 요청 성공 |
| 400 | Bad Request | 잘못된 요청 형식 |
| 401 | Unauthorized | 인증 필요 |
| 403 | Forbidden | 권한 부족 |
| 404 | Not Found | 리소스를 찾을 수 없음 |
| 429 | Too Many Requests | 요청 제한 초과 |
| 500 | Internal Server Error | 서버 내부 오류 |
| 503 | Service Unavailable | 서비스 이용 불가 |

### 일반적인 에러 코드

| 에러 코드 | 설명 | 해결 방법 |
|-----------|------|-----------|
| `invalid_request` | 요청 형식이 올바르지 않음 | 요청 데이터 확인 |
| `authentication_required` | 인증이 필요함 | API 키 제공 |
| `rate_limit_exceeded` | 요청 제한 초과 | 요청 빈도 조절 |
| `resource_not_found` | 리소스를 찾을 수 없음 | 요청 경로 확인 |
| `service_unavailable` | 서비스 이용 불가 | 잠시 후 재시도 |
| `internal_error` | 서버 내부 오류 | 기술 지원팀 문의 |

## 사용 예시

### Python으로 API 호출

```python
import requests
import json

# 기본 설정
base_url = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

# 헬스체크
response = requests.get(f"{base_url}/api/monitoring/health")
print(f"Health status: {response.json()['status']}")

# 메트릭 조회
response = requests.get(f"{base_url}/api/monitoring/metrics")
metrics = response.json()["metrics"]
print(f"Workflow time: {metrics['workflow_execution_time']}s")
print(f"Cache hit ratio: {metrics['cache_hit_ratio']:.1%}")

# 캐시 상태 확인
response = requests.get(f"{base_url}/api/cache/status")
cache_info = response.json()
print(f"Cache enabled: {cache_info['enabled']}")
print(f"Hit ratio: {cache_info['statistics']['hit_ratio']:.1%}")
```

### cURL로 API 호출

```bash
# 헬스체크
curl http://localhost:8000/api/monitoring/health

# 메트릭 조회 (포맷팅)
curl -s http://localhost:8000/api/monitoring/metrics | jq '.'

# 캐시 분석 (특정 기간)
curl "http://localhost:8000/api/cache/analytics?period=1h"

# 성능 최적화 실행 (인증 필요)
curl -X POST http://localhost:8000/api/performance/optimize \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"optimization_type": "memory"}'
```

### JavaScript/Node.js로 API 호출

```javascript
const axios = require('axios');

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'  // 인증이 필요한 경우
  }
});

// 헬스체크
async function checkHealth() {
  try {
    const response = await apiClient.get('/api/monitoring/health');
    console.log('Service status:', response.data.status);
    return response.data;
  } catch (error) {
    console.error('Health check failed:', error.message);
  }
}

// 성능 메트릭 조회
async function getMetrics() {
  try {
    const response = await apiClient.get('/api/monitoring/metrics');
    const metrics = response.data.metrics;
    
    console.log(`Workflow time: ${metrics.workflow_execution_time}s`);
    console.log(`Memory usage: ${metrics.memory_usage_mb}MB`);
    console.log(`Cache hit ratio: ${(metrics.cache_hit_ratio * 100).toFixed(1)}%`);
    
    return metrics;
  } catch (error) {
    console.error('Failed to get metrics:', error.message);
  }
}

// 캐시 상태 모니터링
async function monitorCache() {
  try {
    const response = await apiClient.get('/api/cache/status');
    const cache = response.data;
    
    if (cache.statistics.hit_ratio < 0.7) {
      console.warn('Cache hit ratio below target:', cache.statistics.hit_ratio);
    }
    
    return cache;
  } catch (error) {
    console.error('Cache monitoring failed:', error.message);
  }
}

// 사용 예시
async function main() {
  await checkHealth();
  await getMetrics();
  await monitorCache();
}

main();
```

## 웹훅 및 알림

### 알림 설정

시스템에서 중요한 이벤트 발생 시 웹훅을 통해 알림을 받을 수 있습니다:

```json
{
  "webhook_url": "https://your-app.com/webhooks/generation-service",
  "events": [
    "health_status_changed",
    "performance_threshold_exceeded", 
    "cache_hit_ratio_low",
    "memory_usage_high"
  ],
  "alert_levels": ["warning", "error", "critical"]
}
```

### 웹훅 페이로드 예시

```json
{
  "event": "performance_threshold_exceeded",
  "alert_level": "warning",
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "generation-service",
  "details": {
    "metric": "workflow_execution_time",
    "current_value": 35.2,
    "threshold": 30.0,
    "component": "workflow_engine"
  },
  "suggested_actions": [
    "Check system resources",
    "Review recent workflow changes",
    "Consider scaling up resources"
  ]
}
```

## 모범 사례

### 1. API 호출 최적화

- **배치 요청**: 가능한 경우 여러 요청을 배치로 처리
- **캐싱 활용**: 자주 조회하는 데이터는 클라이언트 측에서 캐싱
- **적절한 폴링**: 실시간 데이터가 필요한 경우 적절한 간격으로 폴링

### 2. 에러 처리

- **재시도 로직**: 일시적 오류에 대한 지수 백오프 재시도
- **에러 로깅**: 모든 API 에러를 적절히 로깅
- **사용자 친화적 메시지**: 기술적 에러를 사용자가 이해할 수 있는 메시지로 변환

### 3. 성능 모니터링

- **정기적 헬스체크**: 서비스 상태를 정기적으로 확인
- **메트릭 추적**: 중요한 성능 지표를 지속적으로 모니터링
- **알림 설정**: 임계값 초과 시 즉시 알림 받을 수 있도록 설정

### 4. 보안

- **API 키 보안**: API 키를 안전하게 저장하고 정기적으로 교체
- **HTTPS 사용**: 프로덕션에서는 반드시 HTTPS 사용
- **요청 제한**: 적절한 요청 제한으로 남용 방지

## 버전 관리

### API 버전 전략

- **URL 기반 버전 관리**: `/api/v1/`, `/api/v2/`
- **하위 호환성**: 기존 버전 지원 기간 명시
- **변경 사항 알림**: API 변경 사항을 사전에 공지

### 변경 로그

| 버전 | 날짜 | 변경 사항 |
|------|------|-----------|
| 1.0.0 | 2024-01-15 | 초기 API 릴리스 |
| 1.1.0 | 2024-02-01 | 성능 분석 엔드포인트 추가 |
| 1.2.0 | 2024-02-15 | 웹훅 알림 기능 추가 |

## 지원 및 문의

- **문서**: [https://docs.yourdomain.com/generation-service](https://docs.yourdomain.com/generation-service)
- **GitHub**: [https://github.com/your-org/generation-service](https://github.com/your-org/generation-service)
- **이슈 신고**: [https://github.com/your-org/generation-service/issues](https://github.com/your-org/generation-service/issues)
- **기술 지원**: support@yourdomain.com

## 추가 리소스

- [설치 가이드](installation.md)
- [배포 가이드](deployment.md)
- [성능 튜닝 가이드](performance.md)
- [트러블슈팅 가이드](troubleshooting.md)
- [OpenAPI 스펙](api/openapi.yaml)