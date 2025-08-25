# Episode 번호 시스템 전용 모니터링 시스템

## 개요

AI Script Generator v3의 Episode 번호 시스템에 대한 전용 모니터링 시스템으로, 무결성 검사, 성능 추적, 실시간 알림을 통해 시스템의 신뢰성을 보장합니다.

## 1. 번호 무결성 모니터링

### 1.1 핵심 메트릭

#### episode_number_gaps_detected
- **설명**: 감지된 Episode 번호 누락 개수
- **타입**: Gauge
- **라벨**: `project_id`, `gap_count`
- **임계값**: > 0 (즉시 경고)

#### episode_number_duplicates_detected  
- **설명**: 감지된 Episode 번호 중복 개수
- **타입**: Gauge
- **라벨**: `project_id`, `duplicate_count`
- **임계값**: > 0 (즉시 경고)

### 1.2 프로젝트별 번호 연속성 검사

```python
# 무결성 검사 예시
checker = EpisodeIntegrityChecker(db)
result = checker.check_project_integrity("project_123")

print(f"건강 상태: {result.is_healthy}")
print(f"누락 번호: {result.gaps}")          # [3, 7, 12]
print(f"중복 번호: {result.duplicates}")     # [5, 9]
print(f"전체 에피소드: {result.total_episodes}")
```

### 1.3 자동 무결성 검사

#### 기본 검사 (30분 간격)
- 전체 프로젝트 무결성 요약
- 새로운 문제 감지 시 알림 발송
- 빠른 실행으로 실시간성 유지

#### 심화 검사 (6시간 간격)  
- 프로젝트별 상세 분석
- 건강도 점수 계산 (0-100)
- 심각한 문제 프로젝트 우선 처리

## 2. 성능 메트릭

### 2.1 응답시간 메트릭

#### episode_creation_duration_p95
- **설명**: Episode 생성 시간 95 백분위수 (초)
- **타입**: Histogram
- **라벨**: `project_id`, `success`
- **임계값**: > 5.0초 (성능 저하 경고)

```python
# 성능 추적 예시
tracker = EpisodePerformanceTracker()
operation_id = tracker.start_operation("create_ep_123")

# ... 에피소드 생성 작업 ...

duration = tracker.end_operation(
    operation_id=operation_id,
    project_id="project_123",
    episode_id="ep_456",
    success=True,
    retry_count=2,
    had_conflict=False
)
print(f"생성 시간: {duration:.3f}초")
```

### 2.2 충돌 및 재시도 메트릭

#### episode_creation_conflicts_total
- **설명**: Episode 생성 시 발생한 충돌 총 횟수
- **타입**: Counter
- **라벨**: `project_id`
- **임계값**: > 전체 요청의 5% (모니터링 강화)

#### episode_creation_retry_count_total
- **설명**: Episode 생성 재시도 총 횟수
- **타입**: Counter  
- **라벨**: `project_id`, `retry_reason`
- **목표**: 재시도율 < 3%

### 2.3 성공률 메트릭

```python
# 성능 통계 예시
{
  "success_rate_percentage": 98.7,
  "conflict_rate_percentage": 2.1,
  "average_duration_seconds": 0.456,
  "p95_duration_seconds": 1.234,
  "p99_duration_seconds": 2.890,
  "total_operations_today": 1247,
  "failed_operations_today": 16
}
```

## 3. 실시간 알림 시스템

### 3.1 알림 규칙 구성

#### Episode 생성 실패율 경고
```yaml
rule_id: episode_failure_rate
alert_type: HIGH_FAILURE_RATE
severity: WARNING
threshold: 1.0%           # 실패율 1% 초과 시
window_minutes: 15        # 15분 창
description: "Episode creation failure rate exceeds 1%"
```

#### 동시성 충돌률 경고
```yaml
rule_id: episode_conflict_rate  
alert_type: HIGH_CONFLICT_RATE
severity: CRITICAL
threshold: 5.0%           # 충돌률 5% 초과 시
window_minutes: 10        # 10분 창  
description: "Episode creation conflict rate exceeds 5% - monitoring enhanced"
```

### 3.2 알림 처리기

#### Slack 알림
```python
class SlackAlertHandler(AlertHandler):
    def handle(self, alert: Alert):
        payload = {
            "attachments": [{
                "color": "danger" if alert.severity == "critical" else "warning",
                "title": alert.title,
                "text": alert.description,
                "fields": [
                    {"title": "Project", "value": alert.project_id, "short": True},
                    {"title": "Severity", "value": alert.severity.upper(), "short": True}
                ]
            }]
        }
        # Slack 웹훅 전송
```

#### 웹훅 알림
```python
class WebhookAlertHandler(AlertHandler):
    def handle(self, alert: Alert):
        payload = {
            "alert": alert.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
            "service": "project-service",
            "component": "episode-numbering"
        }
        # HTTP POST 전송
```

### 3.3 알림 에스컬레이션

1. **1% 실패율 초과**: WARNING 알림, 개발팀 알림
2. **5% 충돌률 초과**: CRITICAL 알림, 모니터링 강화, 온콜 담당자 호출
3. **무결성 위반**: CRITICAL 알림, 즉시 대응 필요

## 4. 모니터링 대시보드

### 4.1 실시간 대시보드 컴포넌트

#### 개요 탭
- **무결성 건강도**: 전체 프로젝트 건강도 표시
- **성공률**: 실시간 Episode 생성 성공률
- **발견된 문제**: 갭/중복 총 개수
- **활성 알림**: 현재 해결되지 않은 알림 수

#### 성능 탭
- **응답 시간 분포**: 평균, P95, P99 응답 시간
- **작업 통계**: 일일 작업 수, 실패 수, 충돌률
- **트렌드 차트**: 시간대별 성능 변화

#### 무결성 탭
- **프로젝트별 상세**: 각 프로젝트의 무결성 상태
- **문제 프로젝트 목록**: 갭/중복이 있는 프로젝트
- **자동 수정 도구**: 안전한 번호 재정렬 도구

### 4.2 API 엔드포인트

```bash
# 무결성 요약 조회
GET /monitoring/episodes/integrity/summary

# 프로젝트별 무결성 확인
GET /monitoring/episodes/integrity/project/{project_id}

# 성능 통계 조회
GET /monitoring/episodes/performance/stats

# 활성 알림 조회
GET /monitoring/episodes/alerts/active

# 무결성 검사 실행
POST /monitoring/episodes/jobs/integrity/run-check?deep_check=true

# 알림 해결
POST /monitoring/episodes/alerts/{alert_key}/resolve

# 메트릭 내보내기 (Prometheus 형식)
GET /monitoring/episodes/metrics/export?format=prometheus
```

### 4.3 대시보드 기능

#### 자동 새로고침
```tsx
const [autoRefresh, setAutoRefresh] = useState(true);
const [refreshInterval, setRefreshInterval] = useState(30); // 30초

useEffect(() => {
  if (autoRefresh) {
    const interval = setInterval(fetchMonitoringData, refreshInterval * 1000);
    return () => clearInterval(interval);
  }
}, [autoRefresh, refreshInterval]);
```

#### 빠른 액션
- **기본 검사 실행**: 전체 프로젝트 빠른 무결성 확인
- **심화 검사 실행**: 상세한 프로젝트별 분석
- **수리 도구**: 안전한 번호 갭 수정 (시뮬레이션 우선)

## 5. 자동화된 무결성 검사

### 5.1 백그라운드 작업 스케줄러

```python
class EpisodeIntegrityJob:
    async def run_continuous_monitoring(self):
        """연속 모니터링 루프"""
        while self.is_running:
            # 기본 검사 실행
            await self.run_basic_check()
            
            # 심화 검사 시간 확인
            if self._is_deep_check_due():
                await self.run_deep_check()
                
            # 다음 검사까지 대기
            await asyncio.sleep(self.config.check_interval_minutes * 60)
```

### 5.2 검사 결과 처리

#### 기본 검사 결과
```python
{
  "status": "completed",
  "duration_seconds": 1.23,
  "summary": {
    "total_projects": 45,
    "healthy_projects": 42,
    "unhealthy_projects": 3,
    "health_percentage": 93.3,
    "total_gaps": 7,
    "total_duplicates": 2
  }
}
```

#### 심화 검사 결과
```python
{
  "status": "completed",
  "projects_checked": 45,
  "projects_with_issues": 3,
  "total_issues": 9,
  "project_issues": [
    {
      "project_id": "proj_123",
      "gaps": [3, 7, 12],
      "duplicates": [5],
      "health_score": 85.7
    }
  ]
}
```

### 5.3 자동 수정 도구 (선택적)

```python
class IntegrityAutoFixer:
    async def fix_gaps(self, project_id: str, dry_run: bool = True):
        """갭 자동 수정 (주의해서 사용)"""
        changes = []
        episodes = self._get_episodes_ordered(project_id)
        
        # 순차적으로 번호 재할당
        for i, episode in enumerate(episodes, 1):
            if episode.number != i:
                changes.append({
                    "episode_id": episode.id,
                    "old_number": episode.number,
                    "new_number": i
                })
        
        if not dry_run:
            self._apply_changes(changes)
            
        return {"changes_needed": len(changes), "changes": changes}
```

## 6. 메트릭 수집 및 내보내기

### 6.1 Prometheus 메트릭 형식

```
# HELP episode_number_gaps_detected Number of episode number gaps detected
# TYPE episode_number_gaps_detected gauge
episode_number_gaps_detected{project_id="proj_123"} 3

# HELP episode_creation_duration_seconds Episode creation duration in seconds  
# TYPE episode_creation_duration_seconds histogram
episode_creation_duration_seconds_bucket{le="0.5"} 1205
episode_creation_duration_seconds_bucket{le="1.0"} 1834
episode_creation_duration_seconds_bucket{le="2.0"} 1967
episode_creation_duration_seconds_count 2000
episode_creation_duration_seconds_sum 1456.789

# HELP episode_creation_conflicts_total Total episode creation conflicts
# TYPE episode_creation_conflicts_total counter
episode_creation_conflicts_total{project_id="proj_123"} 42
```

### 6.2 메트릭 라벨 구조

```python
METRIC_LABELS = {
    "project_id": "프로젝트 식별자",
    "success": "작업 성공/실패 여부", 
    "retry_reason": "재시도 이유 (conflict, timeout, error)",
    "severity": "알림 심각도 (info, warning, critical)",
    "alert_type": "알림 유형"
}
```

## 7. 설정 및 배포

### 7.1 환경 변수

```env
# 모니터링 설정
EPISODE_MONITORING_ENABLED=true
INTEGRITY_CHECK_INTERVAL_MINUTES=30
DEEP_CHECK_INTERVAL_HOURS=6
ALERT_ON_ISSUES=true
AUTO_FIX_ENABLED=false

# 알림 설정
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
MONITORING_WEBHOOK_URL=https://monitoring.company.com/webhook

# 임계값 설정
FAILURE_RATE_THRESHOLD=1.0
CONFLICT_RATE_THRESHOLD=5.0
PERFORMANCE_THRESHOLD_SECONDS=5.0
```

### 7.2 FastAPI 통합

```python
from .startup.monitoring_setup import monitoring_startup_event, monitoring_shutdown_event

app = FastAPI()

@app.on_event("startup")
async def startup():
    await monitoring_startup_event()

@app.on_event("shutdown") 
async def shutdown():
    await monitoring_shutdown_event()
```

### 7.3 Docker 구성

```dockerfile
# 모니터링 의존성 추가
RUN pip install prometheus_client asyncio-mqtt

# 환경 변수 설정
ENV EPISODE_MONITORING_ENABLED=true
ENV INTEGRITY_CHECK_INTERVAL_MINUTES=30

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8002/monitoring/episodes/integrity/summary || exit 1
```

## 8. 운영 가이드

### 8.1 일상 모니터링 체크리스트

#### 매일
- [ ] 대시보드 무결성 건강도 확인 (> 98%)
- [ ] 활성 알림 검토 및 처리
- [ ] 성능 지표 트렌드 확인

#### 매주  
- [ ] 심화 무결성 검사 결과 리뷰
- [ ] 성능 저하 프로젝트 분석
- [ ] 알림 규칙 효과성 평가

### 8.2 문제 해결 가이드

#### 무결성 문제 발견 시
1. **영향 범위 파악**: 어떤 프로젝트에 얼마나 많은 갭/중복이 있는가?
2. **근본 원인 분석**: 언제부터 문제가 시작되었는가?
3. **수동 검증**: 실제 데이터베이스와 대시보드 결과 비교
4. **수정 계획 수립**: 자동 수정 vs 수동 수정 결정
5. **수정 실행**: dry-run으로 시뮬레이션 후 실행

#### 성능 저하 감지 시
1. **지표 분석**: P95, P99 응답시간 및 충돌률 확인
2. **부하 패턴 확인**: 특정 시간대나 프로젝트에 집중되는가?
3. **데이터베이스 성능**: 인덱스, 쿼리 최적화 검토
4. **동시성 설정**: 원자적 트랜잭션 재시도 정책 조정

### 8.3 알림 대응 절차

#### WARNING 알림
- 15분 이내 확인
- 트렌드 분석 및 근본 원인 파악
- 필요시 모니터링 강화

#### CRITICAL 알림
- 5분 이내 즉시 대응
- 온콜 담당자 호출
- 임시 조치 및 근본 해결책 병행

## 9. 향후 개선 계획

### 9.1 고급 분석
- **ML 기반 이상 탐지**: 정상 패턴 학습 후 이상 상황 자동 감지
- **예측적 모니터링**: 성능 저하 예측 및 선제적 대응
- **프로젝트 위험도 점수**: 과거 이력 기반 프로젝트별 위험도 평가

### 9.2 자동화 강화
- **스마트 자동 수정**: AI 기반 안전한 자동 수정 결정
- **동적 알림 임계값**: 시간대/요일별 적응적 임계값 조정
- **자동 롤백**: 문제 감지 시 이전 안정 상태로 자동 복구

### 9.3 통합 모니터링
- **크로스 서비스 추적**: Generation-Project 서비스 간 연관성 분석
- **사용자 영향도 분석**: Episode 문제가 사용자 경험에 미치는 영향 측정
- **비즈니스 메트릭 연동**: Episode 품질이 비즈니스 목표에 미치는 영향 추적

Episode 번호 시스템 모니터링을 통해 시스템의 신뢰성과 성능을 지속적으로 보장하고, 문제 발생 시 빠른 감지 및 대응이 가능합니다.