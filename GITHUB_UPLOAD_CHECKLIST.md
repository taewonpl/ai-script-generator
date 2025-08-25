# GitHub 업로드 전 보안 체크리스트 🔒

> **AI Script Generator v3.0 GitHub 공개 전 필수 보안 점검 가이드**

## 🚨 업로드 전 필수 확인사항

### ✅ 1. 민감 정보 하드코딩 제거
- [ ] **API 키**: OpenAI, Anthropic, Google API 키가 코드에 하드코딩되어 있지 않음
- [ ] **데이터베이스 URL**: PostgreSQL, MySQL, Redis 등 실제 인증정보 없음
- [ ] **JWT 시크릿**: 실제 프로덕션 시크릿 키 없음
- [ ] **비밀번호**: 모든 패스워드가 환경변수로 분리됨
- [ ] **토큰**: GitHub, Slack 등 액세스 토큰 없음

```bash
# 최종 보안 스캔 실행
rg "sk-[A-Za-z0-9_-]{20,}|postgresql://[^:]+:[^@]+@|password[=:]['\"][^'\"]{8,}" --type py --type ts --type js --type json
```

### ✅ 2. 환경 파일 설정
- [ ] **루트 디렉토리**: `.env.example` 존재하며 예시 값만 포함
- [ ] **Generation Service**: `services/generation-service/.env.example` 완성
- [ ] **Project Service**: `services/project-service/.env.example` 완성 
- [ ] **Frontend**: `frontend/.env.example` 완성
- [ ] **Docker**: `services/generation-service/docker/.env.example` 완성

**환경파일 검증:**
```bash
# .env.example 파일 확인
find . -name ".env.example" -exec echo "=== {} ===" \; -exec cat {} \; -exec echo \;

# 실제 .env 파일이 Git에 포함되지 않았는지 확인
git status --ignored | grep -E "\.env$|\.env\."
```

### ✅ 3. .gitignore 완전성
- [ ] **환경파일**: `.env*` 모든 변형 제외
- [ ] **데이터베이스**: `*.db`, `*.sqlite*` 제외
- [ ] **로그파일**: `*.log`, `logs/` 제외
- [ ] **인증서**: `*.pem`, `*.key`, `ssl/` 제외
- [ ] **민감 JSON**: `secrets.json`, `credentials.json` 등 제외
- [ ] **백업파일**: `*.dump`, `*.sql.gz` 제외

```bash
# .gitignore 테스트
git status --ignored | grep -E "(\.env|\.key|\.pem|secrets|credentials)"
```

### ✅ 4. 테스트 데이터 점검
- [ ] **테스트 파일**: 실제 API 키나 인증정보 포함되지 않음
- [ ] **Mock 데이터**: 예시용 더미값만 사용
- [ ] **데이터베이스 URL**: 테스트용 SQLite 메모리 DB 사용
- [ ] **샘플 설정**: 모든 예시 값이 명확히 구분됨

```bash
# 테스트 파일 내 실제 인증정보 확인
rg "sk-[A-Za-z0-9]|postgresql://[^:]+:[^@]+@" tests/ --type py
rg "sk-[A-Za-z0-9]|postgresql://[^:]+:[^@]+@" */tests/ --type py
```

### ✅ 5. 문서화 완성
- [ ] **README.md**: 환경설정 가이드 포함
- [ ] **SECURITY_BEST_PRACTICES.md**: 보안 가이드라인 완성
- [ ] **설치 가이드**: 환경변수 설정 방법 명시
- [ ] **개발 가이드**: 보안 규칙 설명

## 📋 상세 점검 항목

### A. 코드 스캔 결과 확인
```bash
# 1. Python 파일 스캔
rg "postgresql://[^:]+:[^@]+@|mysql://[^:]+:[^@]+@" --type py

# 2. JavaScript/TypeScript 파일 스캔  
rg "sk-[A-Za-z0-9_-]{20,}|api[_-]?key.*[=:]['\"][^'\"]{10,}" --type js --type ts

# 3. JSON 설정 파일 스캔
rg "\"[A-Za-z0-9_-]{32,}\"" --type json | grep -v package

# 4. 환경 관련 패턴 스캔
rg "password|secret|key.*[=:]['\"][^'\"]{8,}" --ignore-case
```

### B. 서비스별 .env.example 검증

#### 루트 디렉토리
```bash
# 필수 항목들
POSTGRES_PASSWORD=postgres123  # 예시값
JWT_SECRET=your-super-secret-jwt-key-change-in-production
OPENAI_API_KEY=sk-your-openai-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
```

#### Generation Service
```bash
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/generation_db  # pragma: allowlist secret
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

#### Project Service (새로 생성됨)
```bash
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/project_db
GENERATION_SERVICE_URL=http://generation-service:8002
```

#### Frontend
```bash
REACT_APP_CORE_SERVICE_URL=http://localhost:8000
REACT_APP_PROJECT_SERVICE_URL=http://localhost:8001
REACT_APP_GENERATION_SERVICE_URL=http://localhost:8002
```

### C. Git 히스토리 검증
```bash
# Git 히스토리에서 민감정보 검색
git log --all -S "sk-" --source --all -p
git log --all -S "postgresql://" --source --all -p
git log --grep="password\|secret\|key" --all --oneline
```

### D. Docker 설정 점검
```bash
# Docker Compose 환경변수 확인
grep -r "API_KEY\|SECRET\|PASSWORD" docker-compose*.yml
grep -r "\${.*}" docker-compose*.yml  # 환경변수 참조 확인
```

## 🔒 최종 보안 검증 스크립트

```bash
#!/bin/bash
echo "🔍 AI Script Generator v3.0 보안 검증 시작..."

# 1. 하드코딩된 인증정보 스캔
echo "1. 민감 정보 하드코딩 스캔..."
FOUND_SECRETS=$(rg "sk-[A-Za-z0-9_-]{20,}|postgresql://[^:]+:[^@]+@|password.*[=:]['\"][^'\"]{8,}" \
  --type py --type js --type ts --type json --count)

if [ "$FOUND_SECRETS" -gt 0 ]; then
  echo "❌ 하드코딩된 민감정보 발견! 수정 후 재검사 필요"
  exit 1
else
  echo "✅ 하드코딩된 민감정보 없음"
fi

# 2. .env 파일 Git 포함 여부 확인
echo "2. .env 파일 Git 추적 여부 확인..."
ENV_FILES=$(git ls-files | grep -E "\.env$|\.env\.")
if [ -n "$ENV_FILES" ]; then
  echo "❌ .env 파일이 Git에 포함됨: $ENV_FILES"
  exit 1
else
  echo "✅ .env 파일 제외됨"
fi

# 3. .env.example 파일 존재 확인
echo "3. .env.example 파일 존재 확인..."
REQUIRED_ENV_FILES=(
  ".env.example"
  "services/generation-service/.env.example"
  "services/project-service/.env.example"
  "frontend/.env.example"
)

for file in "${REQUIRED_ENV_FILES[@]}"; do
  if [ ! -f "$file" ]; then
    echo "❌ 필수 .env.example 파일 없음: $file"
    exit 1
  fi
done
echo "✅ 모든 .env.example 파일 존재"

# 4. 보안 문서 존재 확인
echo "4. 보안 문서 확인..."
if [ ! -f "SECURITY_BEST_PRACTICES.md" ]; then
  echo "❌ SECURITY_BEST_PRACTICES.md 파일 없음"
  exit 1
fi
echo "✅ 보안 문서 존재"

echo "🎉 모든 보안 검증 통과! GitHub 업로드 준비 완료"
```

## 📤 업로드 전 최종 단계

### 1. 최종 검토
```bash
# 보안 검증 스크립트 실행
chmod +x security-check.sh
./security-check.sh
```

### 2. Git 준비
```bash
# staging된 파일 확인
git status

# .env 파일들이 staged되지 않았는지 확인
git diff --cached --name-only | grep -E "\.env$"
```

### 3. 커밋 메시지 예시
```
feat: AI Script Generator v3.0 - 완전한 타입 안전성 및 보안 강화

- 하드코딩된 인증정보 완전 제거
- 모든 서비스 .env.example 파일 완성
- .gitignore 보안 강화
- 보안 모범사례 문서화 완료
- GitHub 업로드 체크리스트 작성

Security: All credentials moved to environment variables
```

## ⚠️ 주의사항

1. **절대 포함하면 안되는 파일들:**
   - `.env` (모든 변형)
   - `secrets.json`, `credentials.json`
   - `*.key`, `*.pem` (인증서)
   - `*.db`, `*.sqlite` (데이터베이스)

2. **실수하기 쉬운 부분:**
   - 테스트 파일에 실제 API 키 포함
   - Docker Compose에 하드코딩된 패스워드
   - 로그 파일에 민감정보 출력

3. **업로드 후 확인:**
   - GitHub에서 파일 목록 점검
   - 검색을 통한 민감정보 노출 여부 확인
   - Issues/Discussions에서 보안 가이드 공유

---

**✅ 체크리스트 완료 후 GitHub 업로드 진행 가능**

*마지막 업데이트: 2024년 12월 - 전체 보안 감사 완료*