# Redis/RQ 보안 강화 설정 가이드

## 🔒 필수 보안 설정

### 1. TLS/SSL 암호화
```bash
# Redis TLS 활성화
export REDIS_SSL=true
export REDIS_SSL_CERT_REQS=required
export REDIS_SSL_CA_CERTS=/path/to/ca-cert.pem
export REDIS_SSL_CERTFILE=/path/to/client-cert.pem
export REDIS_SSL_KEYFILE=/path/to/client-key.pem

# 프로덕션 Redis URL
export REDIS_URL=rediss://rag-worker:password@redis.internal:6380/5
```

### 2. ACL 인증 및 권한 제한
```redis
# Redis ACL 설정 예시
ACL SETUSER rag_worker on >secure_password_2024! ~rag:* +@read +@write +@stream -@dangerous
ACL SETUSER rq_dashboard on >dashboard_password_2024! ~* +@read -@dangerous -@write
ACL DELUSER default
```

### 3. 네트워크 보안
```bash
# Redis 설정 (/etc/redis/redis.conf)
bind 127.0.0.1 10.0.0.0/8  # 내부 네트워크만 허용
protected-mode yes
port 0  # 기본 포트 비활성화
tls-port 6380  # TLS 전용 포트
requirepass secure_password_2024!

# 방화벽 규칙
ufw allow from 10.0.0.0/8 to any port 6380
ufw deny 6379  # 기본 포트 완전 차단
```

### 4. 데이터 암호화
```bash
# Fernet 키 생성
export RAG_REDIS_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 메모리 덤프 암호화
echo "rdb-key-derivation-function pbkdf2" >> /etc/redis/redis.conf
echo "masterauth secure_password_2024!" >> /etc/redis/redis.conf
```

## ⚠️ 보안 점검 항목

### ✅ 현재 구현된 보안 기능
- [x] TLS/SSL 연결 지원 (REDIS_SSL 환경변수)
- [x] ACL 사용자 인증 (REDIS_ACL_USERNAME)
- [x] 강력한 비밀번호 요구 (REDIS_PASSWORD)
- [x] 별도 DB 인덱스 사용 (DB 5)
- [x] 데이터 암호화 (Fernet)
- [x] 연결 풀링 보안 (최대 10개 연결)

### ❌ 추가 필요한 보안 조치
- [ ] Redis 서버 방화벽 설정 확인
- [ ] 인증서 교체 주기 설정
- [ ] Redis 메모리 덤프 암호화
- [ ] 감사 로그 활성화