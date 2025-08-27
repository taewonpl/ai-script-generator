# 보안 모범 사례 가이드 (Security Best Practices)

> **AI Script Generator v3.0 보안 가이드라인 및 인증 정보 관리 규칙**

## 🔐 1. 인증 정보 관리 (Credential Management)

### ✅ 준수 사항 (Requirements)

#### API 키 및 시크릿 관리
- **NEVER** 하드코딩: 소스 코드에 API 키, 비밀번호, 토큰 직접 작성 금지
- **환경변수 사용**: 모든 민감 정보는 `.env` 파일 또는 환경변수로 관리
- **템플릿 사용**: `.env.example` 파일에 예제값만 제공

```bash
# ✅ 올바른 방법 - 환경변수 사용
OPENAI_API_KEY=${OPENAI_API_KEY}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
DATA_ROOT_PATH=${DATA_ROOT_PATH}
CHROMA_PERSIST_DIRECTORY=${CHROMA_PERSIST_DIRECTORY}

# ❌ 잘못된 방법 - 하드코딩 금지
OPENAI_API_KEY=sk-proj-abc123...
DATA_ROOT_PATH=/app/data
CHROMA_PERSIST_DIRECTORY=/app/data/chroma
```

#### 데이터 경로 관리
```python
# ✅ 올바른 방법 - 환경변수 참조
data_root = os.getenv('DATA_ROOT_PATH', './data')
chroma_path = os.getenv('CHROMA_PERSIST_DIRECTORY', f'{data_root}/chroma')

# ❌ 잘못된 방법 - 하드코딩된 경로
data_root = "/hardcoded/path/data"
chroma_path = "/hardcoded/path/chroma"
```

### 🔍 감지된 보안 패턴들 (Detected Security Patterns)

**2024년 12월 스캔 결과:**
- ✅ 1건의 하드코딩된 PostgreSQL URL 발견 후 수정 완료
- ✅ 모든 API 키는 환경변수로 관리됨 확인
- ✅ `.gitignore`에 민감 파일들 제외 확인

## 🛡️ 2. Git 보안 설정 (.gitignore)

### 필수 제외 파일들
```gitignore
# Environment Variables
.env
.env.local
.env.development
.env.staging
.env.production

# API Keys and Secrets
secrets.json
config.json
credentials.json
api_keys.json

# Database Files
*.db
*.sqlite
*.sqlite3

# Log Files
*.log
logs/
```

### 검증 방법
```bash
# .gitignore 확인
git status --ignored
git ls-files --ignored --exclude-standard
```

## 🔧 3. 개발 환경 설정

### 환경변수 템플릿 구조
```bash
# .env.example (안전한 템플릿)
OPENAI_API_KEY=your_openai_api_key_here  # pragma: allowlist secret
ANTHROPIC_API_KEY=your_anthropic_api_key_here  # pragma: allowlist secret
DATABASE_URL=sqlite:///app.db
JWT_SECRET=your-super-secret-jwt-key-change-in-production
```

### 프로덕션 배포
```bash
# 안전한 시크릿 생성
export JWT_SECRET=$(openssl rand -base64 64)
export GRAFANA_SECRET_KEY=$(openssl rand -base64 32)

# 환경별 설정
export ENVIRONMENT=production
export DEBUG=false
```

## 🚨 4. 보안 검사 자동화

### Pre-commit 훅 설정
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

### 정기 보안 스캔
```bash
# 하드코딩된 인증정보 검색
rg "postgresql://[^:]+:[^@]+@" --type py
rg "api[_-]?key|secret[_-]?key" --ignore-case --type py
rg "sk-[A-Za-z0-9_-]+|ak_[A-Za-z0-9_-]+" --type py
```

## 📝 5. 로깅 보안

### 민감정보 마스킹
```python
# services/generation-service/src/generation_service/utils/logging_filters.py
SENSITIVE_PATTERNS = [
    re.compile(r"postgresql://[^:]*:([^@]+)@", re.IGNORECASE),
    re.compile(r"redis://[^:]*:([^@]+)@", re.IGNORECASE),
    re.compile(r"api[_-]?key['\"]?\s*[:=]\s*['\"]([^'\"]+)", re.IGNORECASE),
]
```

### 안전한 로깅
```python
# ✅ 올바른 방법 - URL 마스킹
logger.info("Database connected", extra={
    "database_url": mask_sensitive_info(database_url)
})

# ❌ 잘못된 방법 - 민감정보 노출
logger.info(f"Using database: {database_url}")
```

## 🔄 6. CI/CD 보안

### GitHub Actions 시크릿 관리
```yaml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  JWT_SECRET: ${{ secrets.JWT_SECRET }}
```

### Docker 보안
```dockerfile
# 환경변수로 시크릿 전달
ENV DATABASE_URL=$DATABASE_URL
ENV OPENAI_API_KEY=$OPENAI_API_KEY

# 빌드 시 시크릿 하드코딩 금지
# COPY secrets.json /app/  # ❌ 금지
```

## 🏥 7. 응급 대응 절차

### 인증정보 노출 발견 시
1. **즉시 조치**: 노출된 키/토큰 비활성화
2. **코드 수정**: 하드코딩된 값을 환경변수로 교체
3. **이력 정리**: Git history에서 민감정보 제거
4. **새 인증정보**: 새로운 API 키/시크릿 생성 및 배포

### Git History 정리
```bash
# BFG Repo-Cleaner 사용
java -jar bfg.jar --replace-text passwords.txt
git reflog expire --expire=now --all && git gc --prune=now --aggressive
```

## ✅ 8. 보안 체크리스트

### 개발 시 확인사항
- [ ] 모든 API 키는 환경변수로 관리
- [ ] `.env` 파일은 `.gitignore`에 포함
- [ ] 하드코딩된 비밀번호/토큰 없음
- [ ] 로그에 민감정보 출력 안됨
- [ ] 테스트 코드에 실제 인증정보 없음

### 배포 전 확인사항
- [ ] 프로덕션용 시크릿 생성 완료
- [ ] 환경변수 설정 완료
- [ ] 보안 스캔 실행 완료
- [ ] 로그 마스킹 동작 확인

---

## 📞 보안 문제 신고

보안 취약점 발견 시:
- **이메일**: security@yourproject.com
- **이슈**: GitHub Private Security Advisory
- **긴급**: Slack #security-alerts 채널

**⚠️ 주의**: 퍼블릭 이슈나 풀 리퀘스트에 보안 취약점 보고 금지

## 🛡️ 8. 보안 미들웨어 (Security Middleware)

### 자동 보안 기능

AI Script Generator v3.0에는 다음 보안 미들웨어가 자동 적용됩니다:

#### 보안 헤더 (Security Headers)
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

#### 속도 제한 (Rate Limiting)
- **Generation Service**: 100 requests/minute per IP
- **Project Service**: 200 requests/minute per IP
- 429 상태 코드 반환 시 적절한 재시도 로직 구현

#### 요청 검증 (Request Validation)
- 최대 요청 크기: 16MB
- 허용된 Content-Type만 처리
- 악성 패턴 자동 차단 (XSS, 경로 탐색 등)

#### API 키 검증 (선택사항)
- Generation Service의 민감한 엔드포인트 보호
- X-API-Key 헤더 또는 Authorization Bearer 토큰 지원

### 설정 방법

```python
# services/*/src/*/main.py
from .middleware import setup_security_middleware

setup_security_middleware(
    app,
    enable_rate_limiting=True,
    rate_limit_calls=100,
    rate_limit_period=60,
)
```

### 보안 모니터링

- Rate limit 위반 시 자동 로그 생성
- 악성 요청 패턴 탐지 및 기록
- 클라이언트 IP 추적 (프록시 헤더 고려)

---

*마지막 업데이트: 2025년 8월 - 보안 미들웨어 및 자동화된 보안 검증 추가*