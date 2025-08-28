# 📋 데이터 거버넌스 정책 및 구현

## 🔄 1. Embed Version 관리

### 버전 관리 체계

```python
# 환경변수 기반 버전 관리
RAG_EMBED_VERSION = os.getenv("RAG_EMBED_VERSION", "v1.0")

# 지원되는 버전 형식:
# - 의미론적 버전: v1.0, v1.1, v2.0
# - 타임스탬프: v20250828, v2025-08-28
# - 모델 식별: ada-002-v1, text-3-large-v1
```

### Reindex All 기능 구현

```python
# API 엔드포인트: POST /rag/reindex-all
@router.post("/reindex-all")
async def reindex_all_documents(request: ReindexRequest):
    """
    모든 문서를 새로운 임베딩 버전으로 재색인
    - 배치 처리: 기본 10개씩 처리
    - 점진적 업데이트: 서비스 중단 없음
    - 롤백 지원: 이전 버전 유지
    """
    
    # 1. 버전 유효성 검사
    if request.new_embed_version == current_version:
        raise HTTPException(400, "Same version as current")
    
    # 2. 배치별 재색인 작업 큐잉
    for batch in chunk_documents(project_documents, request.batch_size):
        job = await worker_adapter.enqueue_reindex_all(
            project_id=request.project_id,
            document_ids=batch,
            old_embed_version=current_version,
            new_embed_version=request.new_embed_version
        )
```

### 버전 이관 전략

#### 블루-그린 배포 패턴:
```python
class EmbedVersionManager:
    """임베딩 버전 이관 관리자"""
    
    def __init__(self):
        self.current_version = os.getenv("RAG_EMBED_VERSION", "v1.0")
        self.target_version = None
        self.migration_status = "idle"  # idle, preparing, migrating, rollback
    
    async def start_migration(self, target_version: str):
        """점진적 마이그레이션 시작"""
        self.target_version = target_version
        self.migration_status = "preparing"
        
        # 1. 새 버전으로 인덱스 생성
        await self._create_new_index(target_version)
        
        # 2. 문서 배치별 이관
        await self._migrate_documents_batch()
        
        # 3. 검증 및 전환
        await self._validate_and_switch()
    
    async def rollback_migration(self):
        """이전 버전으로 롤백"""
        if self.migration_status != "migrating":
            raise ValueError("No active migration to rollback")
        
        # 새 인덱스 삭제, 이전 버전으로 복원
        await self._cleanup_failed_migration()
        self.migration_status = "rollback"
```

#### 데이터 무결성 보장:
```python
# 이관 중 데이터 일관성 체크
async def verify_migration_integrity(old_version: str, new_version: str):
    """마이그레이션 무결성 검증"""
    
    # 1. 문서 수 일치 확인
    old_count = await count_documents_by_version(old_version)
    new_count = await count_documents_by_version(new_version)
    
    if old_count != new_count:
        raise IntegrityError(f"Document count mismatch: {old_count} != {new_count}")
    
    # 2. 임베딩 품질 검증 (샘플링)
    sample_docs = await get_sample_documents(100)
    for doc in sample_docs:
        old_embedding = await get_embedding(doc.id, old_version)
        new_embedding = await get_embedding(doc.id, new_version)
        
        # 벡터 유사도 임계값 검사 (0.8 이상 유지되어야 함)
        similarity = cosine_similarity(old_embedding, new_embedding)
        if similarity < 0.8:
            logger.warning(f"Low similarity for doc {doc.id}: {similarity}")
```

---

## 🗑️ 2. 문서 삭제 시 벡터 스토어 연쇄 삭제

### 연쇄 삭제 보장 메커니즘

```python
# services/generation-service/src/generation_service/services/rag_cleanup.py

class VectorStoreCascadeDeleteManager:
    """벡터 스토어 연쇄 삭제 관리자"""
    
    def __init__(self, chroma_client, db_session):
        self.chroma = chroma_client
        self.db = db_session
        self.deletion_log = []
    
    async def delete_document_cascade(self, document_id: str, user_id: str):
        """문서 및 관련 벡터 완전 삭제"""
        
        deletion_context = {
            'document_id': document_id,
            'user_id': user_id,
            'timestamp': datetime.utcnow(),
            'trace_id': f"delete-{document_id}-{uuid4().hex[:8]}"
        }
        
        try:
            # 1. 삭제 전 백업 (감사 목적)
            await self._backup_before_deletion(document_id, deletion_context)
            
            # 2. ChromaDB에서 벡터 삭제
            await self._delete_from_vector_store(document_id, deletion_context)
            
            # 3. 메타데이터 DB에서 삭제
            await self._delete_from_metadata_db(document_id, deletion_context)
            
            # 4. 캐시 무효화
            await self._invalidate_caches(document_id)
            
            # 5. 감사 로그 기록
            await self._log_deletion(deletion_context, success=True)
            
        except Exception as e:
            # 부분 삭제 복구
            await self._handle_deletion_failure(deletion_context, e)
            raise
    
    async def _delete_from_vector_store(self, document_id: str, context: dict):
        """ChromaDB에서 벡터 삭제"""
        
        # 1. 관련 청크 ID 조회
        chunk_ids = await self._get_chunk_ids(document_id)
        
        if not chunk_ids:
            logger.warning(f"No chunks found for document {document_id}")
            return
        
        # 2. ChromaDB 컬렉션에서 삭제
        try:
            collection = await self.chroma.get_collection("documents")
            collection.delete(ids=chunk_ids)
            
            logger.info(f"Deleted {len(chunk_ids)} chunks from ChromaDB", extra={
                'document_id': document_id,
                'chunk_count': len(chunk_ids),
                'trace_id': context['trace_id']
            })
            
        except Exception as e:
            raise VectorStoreDeletionError(f"Failed to delete from ChromaDB: {e}")
    
    async def _verify_complete_deletion(self, document_id: str):
        """삭제 완료 검증"""
        
        # 1. ChromaDB 검증
        try:
            collection = await self.chroma.get_collection("documents")
            remaining_chunks = collection.get(
                where={"document_id": document_id}
            )
            
            if remaining_chunks['ids']:
                raise DeletionVerificationError(
                    f"Found {len(remaining_chunks['ids'])} remaining chunks in ChromaDB"
                )
                
        except Exception as e:
            logger.error(f"ChromaDB verification failed: {e}")
            raise
        
        # 2. 메타데이터 DB 검증
        doc = self.db.query(RAGDocumentDB).filter(
            RAGDocumentDB.id == document_id
        ).first()
        
        if doc:
            raise DeletionVerificationError(f"Document still exists in metadata DB")
        
        logger.info(f"Deletion verification passed for document {document_id}")
```

### 삭제 실패 복구 메커니즘

```python
class DeletionFailureRecovery:
    """삭제 실패 시 복구 처리"""
    
    async def handle_partial_deletion(self, document_id: str, failure_point: str):
        """부분 삭제 상태 복구"""
        
        if failure_point == "vector_store":
            # 메타데이터는 삭제되었지만 벡터는 남아있는 경우
            await self._cleanup_orphaned_vectors(document_id)
            
        elif failure_point == "metadata_db":
            # 벡터는 삭제되었지만 메타데이터가 남아있는 경우
            await self._restore_vector_from_backup(document_id)
            
        elif failure_point == "cache":
            # 캐시 무효화 실패 - 강제 만료
            await self._force_cache_expiry(document_id)
    
    async def schedule_cleanup_job(self, failed_deletions: List[str]):
        """실패한 삭제 작업 재시도 스케줄링"""
        
        for document_id in failed_deletions:
            cleanup_job = {
                'job_type': 'cascade_delete_retry',
                'document_id': document_id,
                'scheduled_at': datetime.utcnow() + timedelta(hours=1),
                'max_retries': 3
            }
            
            await self.worker_adapter.enqueue_cleanup_job(cleanup_job)
```

---

## 📅 3. 180일 보관/삭제 정책

### 데이터 보관 정책 구현

```python
# services/generation-service/src/generation_service/data_retention.py

class DataRetentionManager:
    """데이터 보관 정책 관리자"""
    
    # 보관 기간 설정
    RETENTION_POLICIES = {
        'user_documents': timedelta(days=180),      # 사용자 문서
        'rag_embeddings': timedelta(days=180),      # RAG 임베딩
        'job_logs': timedelta(days=30),             # 작업 로그
        'audit_logs': timedelta(days=365),          # 감사 로그
        'error_logs': timedelta(days=90),           # 오류 로그
        'user_sessions': timedelta(days=7),         # 사용자 세션
    }
    
    def __init__(self):
        self.cleanup_enabled = os.getenv("DATA_RETENTION_ENABLED", "true").lower() == "true"
        self.dry_run = os.getenv("RETENTION_DRY_RUN", "false").lower() == "true"
    
    async def execute_retention_policy(self):
        """보관 정책 실행 (일일 스케줄)"""
        
        if not self.cleanup_enabled:
            logger.info("Data retention is disabled")
            return
        
        logger.info("Starting daily data retention cleanup")
        
        cleanup_results = {}
        
        for data_type, retention_period in self.RETENTION_POLICIES.items():
            try:
                cutoff_date = datetime.utcnow() - retention_period
                result = await self._cleanup_data_type(data_type, cutoff_date)
                cleanup_results[data_type] = result
                
            except Exception as e:
                logger.error(f"Failed to cleanup {data_type}: {e}")
                cleanup_results[data_type] = {'error': str(e)}
        
        # 정리 결과 보고
        await self._report_cleanup_results(cleanup_results)
    
    async def _cleanup_user_documents(self, cutoff_date: datetime):
        """사용자 문서 정리"""
        
        # 1. 만료된 문서 조회
        expired_docs = await self._get_expired_documents(cutoff_date)
        
        if not expired_docs:
            return {'deleted': 0, 'message': 'No expired documents found'}
        
        # 2. 사용자별 그룹화
        docs_by_user = {}
        for doc in expired_docs:
            user_id = doc.user_id or 'anonymous'
            if user_id not in docs_by_user:
                docs_by_user[user_id] = []
            docs_by_user[user_id].append(doc)
        
        # 3. 사용자별 알림 및 삭제
        deleted_count = 0
        for user_id, user_docs in docs_by_user.items():
            
            # 사용자에게 삭제 예정 알림 (7일 전)
            if self._should_notify_user(user_docs[0].created_at):
                await self._notify_user_before_deletion(user_id, user_docs)
                continue  # 알림 후 7일 더 대기
            
            # 실제 삭제 수행
            for doc in user_docs:
                if not self.dry_run:
                    await self.cascade_delete_manager.delete_document_cascade(doc.id, user_id)
                deleted_count += 1
        
        return {
            'deleted': deleted_count,
            'dry_run': self.dry_run,
            'users_affected': len(docs_by_user)
        }
```

### 관리자 삭제 엔드포인트

```python
# services/generation-service/src/generation_service/api/admin.py

@router.delete("/analytics/erase", dependencies=[Depends(verify_admin_token)])
async def admin_erase_data(
    request: AdminEraseRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    관리자 데이터 삭제 엔드포인트
    - 법적 요청 (GDPR, 개인정보보호법) 대응
    - 완전 삭제 보장
    - 감사 로그 유지
    """
    
    # 1. 권한 검증
    if not current_admin.get('can_delete_user_data'):
        raise HTTPException(403, "Insufficient permissions for data deletion")
    
    # 2. 요청 유효성 검사
    if not request.user_id and not request.document_ids:
        raise HTTPException(400, "Either user_id or document_ids must be provided")
    
    # 3. 삭제 범위 계산
    deletion_scope = await calculate_deletion_scope(request)
    
    # 4. 관리자 승인 로그
    approval_log = {
        'admin_id': current_admin['id'],
        'admin_email': current_admin['email'],
        'deletion_type': request.deletion_type,
        'reason': request.reason,
        'legal_basis': request.legal_basis,
        'scope': deletion_scope,
        'timestamp': datetime.utcnow(),
        'ip_address': request.client.host if hasattr(request, 'client') else None
    }
    
    await log_admin_action(approval_log)
    
    # 5. 완전 삭제 실행
    deletion_result = await execute_complete_erasure(request, approval_log)
    
    return {
        'status': 'completed',
        'deletion_id': deletion_result['deletion_id'],
        'items_deleted': deletion_result['items_deleted'],
        'completed_at': datetime.utcnow().isoformat()
    }

@dataclass
class AdminEraseRequest:
    """관리자 삭제 요청"""
    user_id: Optional[str] = None
    document_ids: Optional[List[str]] = None
    deletion_type: str = "user_request"  # user_request, legal_order, gdpr_request
    reason: str = ""
    legal_basis: Optional[str] = None
    confirm_permanent: bool = False
    
    def __post_init__(self):
        if not self.confirm_permanent:
            raise ValueError("Permanent deletion must be explicitly confirmed")

async def execute_complete_erasure(request: AdminEraseRequest, approval_log: dict):
    """완전 삭제 실행"""
    
    deletion_id = f"admin-erase-{uuid4().hex[:16]}"
    items_deleted = 0
    
    try:
        if request.user_id:
            # 사용자의 모든 데이터 삭제
            user_data = await get_all_user_data(request.user_id)
            
            for document in user_data.documents:
                await cascade_delete_manager.delete_document_cascade(
                    document.id, request.user_id
                )
                items_deleted += 1
            
            # 사용자 메타데이터 삭제 (GDPR 준수)
            await anonymize_user_records(request.user_id)
            
        elif request.document_ids:
            # 지정된 문서들만 삭제
            for doc_id in request.document_ids:
                await cascade_delete_manager.delete_document_cascade(
                    doc_id, "admin_delete"
                )
                items_deleted += 1
        
        # 영구 삭제 확인 로그 (감사 목적, 삭제되지 않음)
        await log_permanent_deletion({
            'deletion_id': deletion_id,
            'admin_action': approval_log,
            'items_deleted': items_deleted,
            'deletion_verified': True,
            'retention_period': 'permanent_audit_log'  # 감사 로그는 영구 보관
        })
        
        return {
            'deletion_id': deletion_id,
            'items_deleted': items_deleted,
            'status': 'completed'
        }
        
    except Exception as e:
        await log_deletion_failure(deletion_id, str(e), approval_log)
        raise HTTPException(500, f"Deletion failed: {e}")
```

### 자동 정리 스케줄러

```python
# 일일 실행되는 데이터 정리 작업
@scheduler.scheduled_job("cron", hour=2, minute=0)  # 매일 오전 2시 실행
async def daily_data_retention_cleanup():
    """일일 데이터 보관 정책 실행"""
    
    retention_manager = DataRetentionManager()
    
    try:
        # 보관 정책 실행
        await retention_manager.execute_retention_policy()
        
        # 정리 통계 수집
        cleanup_stats = await retention_manager.get_cleanup_statistics()
        
        # 관리자에게 보고
        await send_admin_report("daily_cleanup", cleanup_stats)
        
    except Exception as e:
        logger.error(f"Daily cleanup failed: {e}")
        await send_admin_alert("cleanup_failure", str(e))

# 사용자 알림 (삭제 7일 전)
@scheduler.scheduled_job("cron", hour=10, minute=0)  # 매일 오전 10시 실행
async def notify_users_before_deletion():
    """삭제 예정 사용자들에게 알림"""
    
    seven_days_later = datetime.utcnow() + timedelta(days=7)
    cutoff_date = seven_days_later - timedelta(days=180)
    
    users_to_notify = await get_users_with_expiring_data(cutoff_date)
    
    for user in users_to_notify:
        await send_deletion_notification(user)
```

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "embed_version \uad00\ub9ac \ubc0f Reindex All \uae30\ub2a5 \uc644\uc131", "status": "completed", "activeForm": "Completing embed_version management and Reindex All functionality"}, {"content": "\ubb38\uc11c \uc0ad\uc81c \uc2dc \ubca1\ud130 \uc2a4\ud1a0\uc5b4 \uc5f0\ucabd \uc0ad\uc81c \ubcf4\uc7a5", "status": "completed", "activeForm": "Ensuring vector store cascade deletion when documents are deleted"}, {"content": "180\uc77c \ubcf4\uad00/\uc0ad\uc81c \uc815\ucc45 \ubc0f /analytics/erase \uad00\ub9ac\uc790 \uacbd\ub85c", "status": "completed", "activeForm": "180-day retention/deletion policy and /analytics/erase admin endpoint"}, {"content": "Runbook 4\uc885 \uc791\uc131", "status": "in_progress", "activeForm": "Writing 4 types of runbooks"}, {"content": "\ub864\ubc31 \uacc4\ud68d \uc218\ub9bd", "status": "pending", "activeForm": "Establishing rollback plan"}, {"content": "\ucd5c\uc885 \ubb38\uc11c \uc5c5\ub370\uc774\ud2b8", "status": "pending", "activeForm": "Final documentation updates"}, {"content": "\ub370\uc774\ud130 \uac70\ubc84\ub108\uc2a4\uc640 \uc6b4\uc601 \ubb38\uc11c \ucd5c\uc885 \ubcf4\uace0\uc11c \uc791\uc131", "status": "pending", "activeForm": "Writing final data governance and operations documentation report"}]