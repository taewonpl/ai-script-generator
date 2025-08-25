# Episode 번호 할당 시스템 분석 보고서

## 🔍 현재 구현 상태 분석

### 1. SQLite Episode 저장 구조

#### ✅ Episode 테이블 스키마
**파일**: `services/project-service/src/project_service/models/episode.py`

```sql
CREATE TABLE episodes (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
    number INTEGER NOT NULL,  -- 자동 할당 에피소드 번호
    order INTEGER DEFAULT 1 NOT NULL,  -- 표시 순서
    status ENUM('draft', 'in_progress', 'completed', 'review', 'approved', 'published'),
    is_published BOOLEAN DEFAULT FALSE,
    description TEXT,
    duration INTEGER,  -- 분 단위
    notes TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE CONSTRAINT uq_episode_project_number (project_id, number)
);
```

#### ✅ 핵심 제약 조건
- **UNIQUE 제약**: `(project_id, number)` 조합으로 중복 방지
- **Foreign Key**: `project_id → projects(id)` 참조 무결성
- **Index**: `project_id`에 인덱스 설정

#### ❌ Projects 테이블 분석
**파일**: `services/project-service/src/project_service/models/project.py`

```sql
CREATE TABLE projects (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    type ENUM(...),
    status ENUM(...),
    description TEXT,
    progress_percentage INTEGER DEFAULT 0
    -- ❌ next_episode_number 컬럼 없음
);
```

**⚠️ 문제점**: Projects 테이블에 `next_episode_number` 카운터 컬럼이 없어서 분산 환경에서 원자적 번호 할당이 어려움.

---

### 2. 번호 할당 로직 분석

#### 현재 구현 방식 (MAX+1 방식)
**파일**: `services/project-service/src/project_service/repositories/episode.py:90-97`

```python
def get_next_episode_number(self, project_id: str) -> int:
    """Get the next available episode number for a project"""
    max_number = (
        self.db.query(func.max(Episode.number))
        .filter(Episode.project_id == project_id)
        .scalar()
    )
    return (max_number + 1) if max_number is not None else 1
```

#### 트랜잭션 처리
**파일**: `services/project-service/src/project_service/services/episode_service.py:63-94`

```python
def create_episode(self, project_id: str, title: str, description: Optional[str] = None) -> dict:
    try:
        self.db.begin()  # 명시적 트랜잭션 시작
        next_number = self.repository.get_next_episode_number(project_id)
        next_order = self.repository.get_next_order(project_id)
        
        db_data = {
            "id": episode_id,
            "number": next_number,  # 자동 할당된 에피소드 번호
            "order": next_order,
            # ... 기타 필드
        }
        
        episode = self.repository.create(db_data)
        self.db.commit()  # 트랜잭션 커밋
        return episode.to_dict()
        
    except Exception as e:
        self.db.rollback()  # 에러 시 롤백
        raise ValidationError(message=f"Failed to create episode: {str(e)}")
```

---

### 3. 동시성 문제 분석

#### ❌ 현재 방식의 문제점

1. **Race Condition 발생 가능**:
   ```
   시점 T1: 프로세스 A가 MAX(number) = 3 조회
   시점 T2: 프로세스 B가 MAX(number) = 3 조회  
   시점 T3: 프로세스 A가 number=4로 INSERT
   시점 T4: 프로세스 B가 number=4로 INSERT → UNIQUE 제약 위반!
   ```

2. **SQLite WAL 모드의 한계**:
   - SQLite는 writer 1개만 허용 (동시 쓰기 불가)
   - 분산 환경에서는 파일 잠금 문제
   - 네트워크 파일시스템에서 안전하지 않음

3. **트랜잭션 격리 수준 문제**:
   ```python
   # 현재 코드의 문제
   self.db.begin()  # 트랜잭션 시작
   max_number = self.db.query(func.max(Episode.number))...  # READ
   # 🚨 여기서 다른 프로세스가 INSERT 할 수 있음
   episode = self.repository.create(db_data)  # INSERT
   self.db.commit()
   ```

#### 🔍 테스트 범위 검토

**기존 테스트 파일들**:
- `test_api_integration.py`: 순차적 Episode 생성 테스트만 존재
- `test_chroma_episodes.py`: ChromaDB 통합 테스트

**❌ 누락된 테스트들**:
- 동시성 테스트 없음
- Race condition 시나리오 테스트 없음
- UNIQUE 제약 위반 처리 테스트 없음
- 분산 환경 시뮬레이션 테스트 없음

---

### 4. 분산 환경 안전성 평가

#### ❌ 현재 시스템의 분산 환경 문제점

1. **SQLite 파일 기반의 한계**:
   - 단일 파일 데이터베이스
   - 네트워크 공유 불가능
   - 인스턴스별 독립적 데이터베이스

2. **번호 할당의 일관성 부족**:
   - 서로 다른 인스턴스에서 동일한 번호 할당 가능
   - 로드밸런서 환경에서 번호 충돌 위험

3. **트랜잭션 동기화 미흡**:
   - 글로벌 잠금 메커니즘 부재
   - 원자적 증가 연산 부재

---

## 🚨 위험도 평가

### 높음 (Critical)
- **동시성 Race Condition**: 동일 번호 할당으로 인한 UNIQUE 제약 위반
- **분산 환경 비호환**: SQLite 기반으로 확장성 제한

### 중간 (High)  
- **에러 처리 부족**: UNIQUE 제약 위반 시 사용자 친화적 에러 처리 부족
- **테스트 커버리지 부족**: 동시성 시나리오 테스트 없음

### 낮음 (Medium)
- **성능 최적화 여지**: MAX+1 방식보다 효율적인 카운터 방식 고려 필요

---

## 💡 개선 권장 사항

### 즉시 개선 (Critical Priority)

#### 1. 원자적 번호 할당 구현
```python
# 권장: 원자적 UPDATE + SELECT 방식
def get_next_episode_number_atomic(self, project_id: str) -> int:
    """원자적 번호 할당 (PostgreSQL/MySQL 권장)"""
    # 방법 1: UPDATE counter table
    result = self.db.execute(text("""
        UPDATE project_counters 
        SET next_episode_number = next_episode_number + 1 
        WHERE project_id = :project_id
        RETURNING next_episode_number - 1
    """), {"project_id": project_id})
    
    # 방법 2: SQLite 전용 - SERIALIZABLE 트랜잭션
    with self.db.begin():
        self.db.execute(text("BEGIN IMMEDIATE"))  # 즉시 배타 잠금
        max_number = self.db.query(func.max(Episode.number))...
        return max_number + 1
```

#### 2. Projects 테이블에 카운터 컬럼 추가
```sql
ALTER TABLE projects 
ADD COLUMN next_episode_number INTEGER DEFAULT 1;

-- 기존 프로젝트용 초기값 설정
UPDATE projects 
SET next_episode_number = (
    SELECT COALESCE(MAX(number), 0) + 1 
    FROM episodes 
    WHERE episodes.project_id = projects.id
);
```

#### 3. 동시성 테스트 추가
```python
async def test_concurrent_episode_creation():
    """동시 Episode 생성 테스트"""
    import asyncio
    import aiohttp
    
    tasks = []
    for i in range(10):
        task = asyncio.create_task(
            create_episode_api_call(f"Concurrent Episode {i}")
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 모든 Episode가 고유한 번호를 가져야 함
    numbers = [r['number'] for r in results if isinstance(r, dict)]
    assert len(numbers) == len(set(numbers)), "중복된 Episode 번호 발견"
```

### 중장기 개선 (High Priority)

#### 4. 데이터베이스 경로 설정 (SQLite)
```python
# config/settings.py
DATA_ROOT_PATH = "/app/data"
SQLITE_DATABASE_PATH = "/app/data/app.db"  # Local SQLite database

# 또는 분산 ID 생성기 도입 (Snowflake, UUID 등)
```

#### 5. 분산 잠금 메커니즘 도입
```python
# Redis 기반 분산 잠금
import redis
import time

class DistributedLock:
    def __init__(self, redis_client, lock_key, timeout=10):
        self.redis = redis_client
        self.lock_key = lock_key
        self.timeout = timeout
    
    def __enter__(self):
        # 분산 잠금 획득
        while True:
            if self.redis.set(self.lock_key, "locked", nx=True, ex=self.timeout):
                return self
            time.sleep(0.001)  # 1ms 대기
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 잠금 해제
        self.redis.delete(self.lock_key)

# 사용 예시
def create_episode_with_distributed_lock(self, project_id: str, ...):
    with DistributedLock(redis_client, f"episode_lock:{project_id}"):
        # 원자적 번호 할당 및 Episode 생성
        next_number = self.get_next_episode_number(project_id)
        return self.create_episode_with_number(project_id, next_number, ...)
```

---

## 📋 액션 플랜

### 🚀 Phase 1: 즉시 안전성 개선 (1-2주)
- [ ] Projects 테이블에 `next_episode_number` 컬럼 추가
- [ ] 원자적 번호 할당 로직 구현 (SQLite SERIALIZABLE 모드)
- [ ] UNIQUE 제약 위반 에러 핸들링 개선
- [ ] 동시성 테스트 케이스 작성

### 🏗️ Phase 2: 아키텍처 개선 (4-6주)  
- [ ] PostgreSQL/MySQL로 데이터베이스 마이그레이션
- [ ] 분산 잠금 메커니즘 도입 (Redis 기반)
- [ ] 부하 테스트 및 성능 최적화
- [ ] 모니터링 및 알림 시스템 구축

### 🔄 Phase 3: 운영 안정화 (2-4주)
- [ ] 프로덕션 배포 및 모니터링
- [ ] 장애 복구 시나리오 테스트
- [ ] 문서화 및 운영 가이드 작성

---

## 📊 결론

**현재 Episode 번호 할당 시스템은 분산 환경에서 안전하지 않습니다.**

### 🚨 주요 위험 요소:
1. SQLite 기반의 단일 인스턴스 제약
2. MAX+1 방식의 Race Condition 취약성  
3. 원자적 번호 할당 메커니즘 부재
4. 동시성 테스트 커버리지 부족

### 🎯 개선 우선순위:
1. **즉시**: 원자적 번호 할당 및 에러 처리 개선
2. **단기**: 동시성 테스트 및 모니터링 추가
3. **중기**: PostgreSQL 마이그레이션 및 분산 잠금 도입

현재 시스템은 **개발/테스트 환경**에서는 사용 가능하지만, **프로덕션 분산 환경**에서는 데이터 무결성 문제가 발생할 수 있으므로 즉시 개선이 필요합니다.