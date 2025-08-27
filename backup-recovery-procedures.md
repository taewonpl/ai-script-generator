# 데이터 백업 및 복구 절차 (Data Backup & Recovery Procedures)

> **AI Script Generator v3.0 - 프로덕션 데이터 신뢰성 검증 가이드**

## 📊 개요 (Overview)

본 문서는 AI Script Generator v3.0의 데이터 백업, 복구 및 신뢰성 검증 절차를 정의합니다.

### 데이터 구성 요소
- **SQLite Database**: 프로젝트 및 에피소드 메타데이터
- **ChromaDB Vector Store**: 대본 콘텐츠 임베딩 및 벡터 데이터
- **Redis Cache**: 임시 데이터 및 작업 큐
- **File Storage**: 생성된 대본 파일 및 첨부파일

## 🔄 자동 백업 시스템

### 1. SQLite 데이터베이스 백업

#### 실시간 백업 스크립트
```bash
#!/bin/bash
# sqlite-backup.sh - SQLite 데이터베이스 실시간 백업

DB_PATH="/data/projects.db"
BACKUP_DIR="/data/backup/sqlite"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="projects_${TIMESTAMP}.db"

# 백업 디렉토리 생성
mkdir -p ${BACKUP_DIR}

# SQLite 온라인 백업 (서비스 중단 없음)
sqlite3 ${DB_PATH} ".backup '${BACKUP_DIR}/${BACKUP_FILE}'"

# 백업 무결성 검증
sqlite3 ${BACKUP_DIR}/${BACKUP_FILE} "PRAGMA integrity_check;"
if [ $? -eq 0 ]; then
    echo "✅ SQLite backup successful: ${BACKUP_FILE}"
    
    # 7일 이상된 백업 파일 정리
    find ${BACKUP_DIR} -name "projects_*.db" -mtime +7 -delete
else
    echo "❌ SQLite backup integrity check failed"
    exit 1
fi
```

#### Kubernetes CronJob 백업 자동화
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: sqlite-backup-job
  namespace: ai-script-generator
spec:
  schedule: "0 */6 * * *"  # 6시간마다 실행
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: sqlite-backup
            image: alpine:3.18
            command:
            - /bin/sh
            - -c
            - |
              apk add --no-cache sqlite
              /scripts/sqlite-backup.sh
            volumeMounts:
            - name: data-volume
              mountPath: /data
            - name: backup-scripts
              mountPath: /scripts
          volumes:
          - name: data-volume
            persistentVolumeClaim:
              claimName: project-service-data
          - name: backup-scripts
            configMap:
              name: backup-scripts
              defaultMode: 0755
          restartPolicy: OnFailure
```

### 2. ChromaDB 백업

#### ChromaDB 백업 스크립트
```bash
#!/bin/bash
# chroma-backup.sh - ChromaDB 벡터 데이터베이스 백업

CHROMA_DATA_DIR="/data/chroma"
BACKUP_DIR="/data/backup/chroma"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_TAR="chroma_${TIMESTAMP}.tar.gz"

# 백업 디렉토리 생성
mkdir -p ${BACKUP_DIR}

# ChromaDB 일관성 있는 백업 (tar + gzip)
cd ${CHROMA_DATA_DIR}
tar -czf "${BACKUP_DIR}/${BACKUP_TAR}" .

# 백업 파일 검증
if [ -f "${BACKUP_DIR}/${BACKUP_TAR}" ] && [ -s "${BACKUP_DIR}/${BACKUP_TAR}" ]; then
    echo "✅ ChromaDB backup successful: ${BACKUP_TAR}"
    
    # 백업 크기 로그
    BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_TAR}" | cut -f1)
    echo "📦 Backup size: ${BACKUP_SIZE}"
    
    # 30일 이상된 백업 파일 정리
    find ${BACKUP_DIR} -name "chroma_*.tar.gz" -mtime +30 -delete
else
    echo "❌ ChromaDB backup failed"
    exit 1
fi
```

### 3. 통합 백업 검증 스크립트

```bash
#!/bin/bash
# backup-verification.sh - 백업 무결성 종합 검증

BACKUP_BASE_DIR="/data/backup"
LOG_FILE="/var/log/backup-verification.log"

echo "$(date): Starting backup verification" >> ${LOG_FILE}

# SQLite 백업 검증
echo "🔍 Verifying SQLite backups..."
LATEST_SQLITE=$(ls -t ${BACKUP_BASE_DIR}/sqlite/projects_*.db 2>/dev/null | head -1)
if [ -f "$LATEST_SQLITE" ]; then
    sqlite3 "$LATEST_SQLITE" "SELECT COUNT(*) FROM projects;" > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ SQLite backup verification passed"
    else
        echo "❌ SQLite backup verification failed" >> ${LOG_FILE}
        exit 1
    fi
else
    echo "❌ No SQLite backup found" >> ${LOG_FILE}
    exit 1
fi

# ChromaDB 백업 검증
echo "🔍 Verifying ChromaDB backups..."
LATEST_CHROMA=$(ls -t ${BACKUP_BASE_DIR}/chroma/chroma_*.tar.gz 2>/dev/null | head -1)
if [ -f "$LATEST_CHROMA" ]; then
    tar -tzf "$LATEST_CHROMA" > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ ChromaDB backup verification passed"
    else
        echo "❌ ChromaDB backup verification failed" >> ${LOG_FILE}
        exit 1
    fi
else
    echo "❌ No ChromaDB backup found" >> ${LOG_FILE}
    exit 1
fi

echo "$(date): All backup verifications passed" >> ${LOG_FILE}
```

## 🔧 복구 절차 (Recovery Procedures)

### 1. SQLite 데이터베이스 복구

#### 빠른 복구 (서비스 중단 필요)
```bash
#!/bin/bash
# sqlite-restore-fast.sh - SQLite 빠른 복구

BACKUP_FILE=$1
DB_PATH="/data/projects.db"
DB_BACKUP_PATH="/data/projects.db.backup"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# 현재 데이터베이스 백업
echo "🔄 Backing up current database..."
cp ${DB_PATH} ${DB_BACKUP_PATH}

# 백업에서 복구
echo "🔄 Restoring from backup: ${BACKUP_FILE}"
cp ${BACKUP_FILE} ${DB_PATH}

# 무결성 검증
sqlite3 ${DB_PATH} "PRAGMA integrity_check;"
if [ $? -eq 0 ]; then
    echo "✅ SQLite restore completed successfully"
    rm -f ${DB_BACKUP_PATH}
else
    echo "❌ SQLite restore failed, rolling back..."
    cp ${DB_BACKUP_PATH} ${DB_PATH}
    exit 1
fi
```

#### 무중단 복구 (새 인스턴스로 복구)
```bash
#!/bin/bash
# sqlite-restore-zero-downtime.sh - SQLite 무중단 복구

BACKUP_FILE=$1
NEW_DB_PATH="/data/projects_new.db"
CURRENT_DB_PATH="/data/projects.db"

# 백업에서 새 데이터베이스 생성
cp ${BACKUP_FILE} ${NEW_DB_PATH}

# 무결성 검증
sqlite3 ${NEW_DB_PATH} "PRAGMA integrity_check;"
if [ $? -eq 0 ]; then
    echo "✅ New database verified, preparing for switch..."
    
    # Kubernetes에서 새 데이터베이스로 전환하도록 설정 업데이트
    kubectl patch deployment project-service -p '{"spec":{"template":{"spec":{"containers":[{"name":"project-service","env":[{"name":"DATABASE_URL","value":"sqlite:///data/projects_new.db"}]}]}}}}'
    
    echo "✅ Database switch initiated"
else
    echo "❌ New database verification failed"
    rm -f ${NEW_DB_PATH}
    exit 1
fi
```

### 2. ChromaDB 복구

```bash
#!/bin/bash
# chroma-restore.sh - ChromaDB 복구

BACKUP_TAR=$1
CHROMA_DATA_DIR="/data/chroma"
CHROMA_BACKUP_DIR="/data/chroma_backup"

if [ -z "$BACKUP_TAR" ]; then
    echo "Usage: $0 <backup_tar_file>"
    exit 1
fi

# 현재 데이터 백업
echo "🔄 Backing up current ChromaDB data..."
if [ -d "${CHROMA_DATA_DIR}" ]; then
    mv ${CHROMA_DATA_DIR} ${CHROMA_BACKUP_DIR}
fi

# 백업에서 복구
echo "🔄 Restoring ChromaDB from: ${BACKUP_TAR}"
mkdir -p ${CHROMA_DATA_DIR}
cd ${CHROMA_DATA_DIR}
tar -xzf ${BACKUP_TAR}

# 복구 검증 (기본 구조 확인)
if [ -d "${CHROMA_DATA_DIR}" ] && [ "$(ls -A ${CHROMA_DATA_DIR})" ]; then
    echo "✅ ChromaDB restore completed successfully"
    rm -rf ${CHROMA_BACKUP_DIR}
else
    echo "❌ ChromaDB restore failed, rolling back..."
    rm -rf ${CHROMA_DATA_DIR}
    if [ -d "${CHROMA_BACKUP_DIR}" ]; then
        mv ${CHROMA_BACKUP_DIR} ${CHROMA_DATA_DIR}
    fi
    exit 1
fi
```

## 🧪 재해 복구 테스트 (Disaster Recovery Testing)

### 테스트 시나리오 1: 부분 데이터 손실
```bash
#!/bin/bash
# dr-test-partial-loss.sh - 부분 데이터 손실 시나리오 테스트

echo "🧪 Testing partial data loss recovery..."

# 1. 현재 상태 백업
CURRENT_PROJECTS=$(sqlite3 /data/projects.db "SELECT COUNT(*) FROM projects;")
echo "📊 Current projects count: ${CURRENT_PROJECTS}"

# 2. 일부 데이터 삭제 (최근 1시간 데이터)
sqlite3 /data/projects.db "DELETE FROM projects WHERE created_at > datetime('now', '-1 hour');"

# 3. 가장 최근 백업에서 복구
LATEST_BACKUP=$(ls -t /data/backup/sqlite/projects_*.db | head -1)
./sqlite-restore-fast.sh ${LATEST_BACKUP}

# 4. 복구 검증
RECOVERED_PROJECTS=$(sqlite3 /data/projects.db "SELECT COUNT(*) FROM projects;")
echo "📊 Recovered projects count: ${RECOVERED_PROJECTS}"

if [ ${RECOVERED_PROJECTS} -ge ${CURRENT_PROJECTS} ]; then
    echo "✅ Partial data loss recovery test PASSED"
else
    echo "❌ Partial data loss recovery test FAILED"
fi
```

### 테스트 시나리오 2: 전체 시스템 복구
```bash
#!/bin/bash
# dr-test-full-system.sh - 전체 시스템 복구 테스트

echo "🧪 Testing full system disaster recovery..."

# 1. 백업 가용성 확인
SQLITE_BACKUP=$(ls -t /data/backup/sqlite/projects_*.db 2>/dev/null | head -1)
CHROMA_BACKUP=$(ls -t /data/backup/chroma/chroma_*.tar.gz 2>/dev/null | head -1)

if [ -z "$SQLITE_BACKUP" ] || [ -z "$CHROMA_BACKUP" ]; then
    echo "❌ Required backups not found"
    exit 1
fi

# 2. 시뮬레이션: 전체 데이터 디렉토리 삭제
echo "⚠️  Simulating catastrophic data loss..."
rm -rf /data/projects.db
rm -rf /data/chroma/*

# 3. 전체 시스템 복구
echo "🔄 Starting full system recovery..."
./sqlite-restore-fast.sh ${SQLITE_BACKUP}
./chroma-restore.sh ${CHROMA_BACKUP}

# 4. 서비스 재시작 및 검증
kubectl rollout restart deployment/project-service
kubectl rollout restart deployment/generation-service

# 5. 서비스 헬스체크
sleep 30
curl -f http://project-service:8001/api/v1/health || exit 1
curl -f http://generation-service:8002/api/v1/health || exit 1

echo "✅ Full system disaster recovery test PASSED"
```

## 📋 데이터 무결성 검증

### 일일 무결성 검사 스크립트
```bash
#!/bin/bash
# daily-integrity-check.sh - 일일 데이터 무결성 검사

LOG_FILE="/var/log/integrity-check.log"
echo "$(date): Starting daily integrity check" >> ${LOG_FILE}

# 1. SQLite 무결성 검사
echo "🔍 Running SQLite integrity check..."
SQLITE_RESULT=$(sqlite3 /data/projects.db "PRAGMA integrity_check;")
if [ "$SQLITE_RESULT" = "ok" ]; then
    echo "✅ SQLite integrity check passed" >> ${LOG_FILE}
else
    echo "❌ SQLite integrity check failed: ${SQLITE_RESULT}" >> ${LOG_FILE}
    # 알림 발송
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 SQLite integrity check failed"}' \
        ${SLACK_WEBHOOK_URL}
fi

# 2. 프로젝트-에피소드 참조 무결성 검사
echo "🔍 Checking project-episode referential integrity..."
ORPHANED_EPISODES=$(sqlite3 /data/projects.db "SELECT COUNT(*) FROM episodes e WHERE NOT EXISTS (SELECT 1 FROM projects p WHERE p.id = e.project_id);")
if [ ${ORPHANED_EPISODES} -eq 0 ]; then
    echo "✅ Project-episode integrity check passed" >> ${LOG_FILE}
else
    echo "⚠️  Found ${ORPHANED_EPISODES} orphaned episodes" >> ${LOG_FILE}
fi

# 3. ChromaDB 접근성 테스트
echo "🔍 Testing ChromaDB accessibility..."
if [ -d "/data/chroma" ] && [ "$(ls -A /data/chroma)" ]; then
    echo "✅ ChromaDB accessibility check passed" >> ${LOG_FILE}
else
    echo "❌ ChromaDB accessibility check failed" >> ${LOG_FILE}
fi

echo "$(date): Daily integrity check completed" >> ${LOG_FILE}
```

## 🔄 자동화된 백업 정책

### Kubernetes 백업 정책 ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backup-policy
  namespace: ai-script-generator
data:
  retention-policy: |
    # 백업 보존 정책
    - 시간별 백업: 24시간 보존
    - 일일 백업: 30일 보존  
    - 주간 백업: 12주 보존
    - 월간 백업: 12개월 보존
    
  backup-schedule: |
    # 백업 일정
    SQLite: 매 6시간 (00:00, 06:00, 12:00, 18:00)
    ChromaDB: 매일 02:00
    무결성 검사: 매일 04:00
    
  recovery-rto: |
    # 복구 목표 시간 (RTO: Recovery Time Objective)
    SQLite 부분 복구: 5분 이내
    SQLite 전체 복구: 15분 이내
    ChromaDB 복구: 30분 이내
    전체 시스템 복구: 60분 이내
    
  recovery-rpo: |
    # 복구 목표 지점 (RPO: Recovery Point Objective)  
    SQLite: 최대 6시간 데이터 손실
    ChromaDB: 최대 24시간 데이터 손실
```

## 📈 모니터링 및 알림

### Prometheus 백업 메트릭
```yaml
# backup-metrics.yaml
groups:
- name: backup.rules
  rules:
  - alert: BackupFailed
    expr: backup_job_success{job="sqlite-backup"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Database backup job failed"
      
  - alert: BackupAging
    expr: time() - backup_last_success_timestamp > 86400
    for: 1h  
    labels:
      severity: warning
    annotations:
      summary: "Backup aging - no successful backup in 24h"
```

## 📝 복구 절차 체크리스트

### 긴급 복구 체크리스트
- [ ] 1. 백업 파일 가용성 확인
- [ ] 2. 복구 목표 시간(RTO) 설정
- [ ] 3. 현재 데이터 상태 백업 (가능한 경우)
- [ ] 4. 복구 스크립트 실행
- [ ] 5. 데이터 무결성 검증
- [ ] 6. 서비스 재시작
- [ ] 7. 애플리케이션 기능 테스트
- [ ] 8. 모니터링 및 로그 확인
- [ ] 9. 이해관계자 복구 완료 알림
- [ ] 10. 복구 후 검토 회의 일정 조정

---

*마지막 업데이트: 2025년 8월 - 프로덕션 데이터 신뢰성 검증 완료*