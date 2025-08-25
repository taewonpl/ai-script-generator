# Claude Code Instructions

## Bug Fixing & Development Guidelines

### 🔍 **디버깅 원칙**
버그 수정 시 디버그 로그를 보며 리버스 엔지니어링으로 근본적인 원인을 찾아내세요. 실마리가 부족할 때에는 더 상세한 디버그 로그를 추가해주세요. 원인을 찾아내서 솔루션을 적용할 때, 가장 근본적으로 해결할 수 있는 방법을 적용하고, 만약 어려울 경우 상황을 보고하고 내 다음 지시를 기다려주세요.

### 🎯 **최소 침습적 수정 원칙**
- **정확한 문제만 해결**: 주어진 문제와 직접 관련된 코드만 수정
- **작동하는 코드 보존**: 이미 잘 작동하는 기존 코드는 건드리지 말 것
- **범위 제한**: 불필요하게 광범위한 리팩토링이나 구조 변경 금지
- **단계적 접근**: 한 번에 하나의 문제만 해결하고 테스트 후 다음 진행

### ⚠️ **금지 사항**
- 문제와 관련 없는 코드 정리나 구조 변경 금지
- "김에 이것도 고치자" 식의 추가 수정 금지
- Over-engineering: 단순한 문제를 복잡하게 해결하지 말 것

### 🛡️ **Claude Code Guardrails (필수)**
- **Plan → Patch(diff) → Proof(logs) 3단계로 PR 생성**
- **Plan**: 변경 파일 경로/영향/DoD 명시
- **Patch**: unified diff만 출력 (산출물·node_modules 등 금지)
- **Proof**: pnpm -r lint/typecheck/build/test 결과 요약 첨부
- **스코프 제한**: 모듈 1개, 변경 파일 ≤ 5개
- **금지 디렉토리**: node_modules/, dist/, coverage/, .playwright/, chroma*/ 등

## 기술 스택 (확정)

**Frontend:** Vite + React 18 + TypeScript + Material-UI(MUI) + React Query
**Backend:** FastAPI + SQLite + ChromaDB + Redis
**AI:** LangGraph (에이전트가 필요 시 외부 API 호출)
**개발도구:** MyPy + Ruff (Python), ESLint + Prettier (TypeScript)

## 프로젝트 구조

```
root/
├─ shared/core/                      # 공통 유틸/도메인 모델/에러/로깅
├─ services/
│  ├─ project-service/               # 프로젝트/에피소드 관리 API (port 8001)
│  └─ generation-service/            # AI 대본 생성 API + SSE (port 8002)
├─ frontend/                         # React 프론트엔드 (port 3000)
└─ tests/e2e/                        # 통합(E2E) 테스트
```

## Governance & Guardrails

### 🔒 **Branch Protection**
- **main**: squash merge only, linear history, 최소 1명 리뷰 필수
- **Required Checks**: pre-commit + typecheck + test + build (모두 green일 때만 merge)
- **목적**: 깨진 코드가 main에 들어오는 일을 제도적으로 차단

### 🪝 **Pre-commit Hooks**
```yaml
# .pre-commit-config.yaml (루트)
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.8
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks:
      - id: black
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]
  - repo: local
    hooks:
      - id: eslint
        name: eslint
        entry: bash -lc 'pnpm eslint "frontend/src/**/*.{ts,tsx,js,jsx}"'
        language: system
        types: [file]
      - id: prettier
        name: prettier
        entry: bash -lc 'pnpm prettier -w "**/*.{ts,tsx,js,jsx,css,md,json,yml,yaml}"'
        language: system
        types: [file]
```

### ✅ **Required Checks (CI)**
```yaml
# .github/workflows/ci.yml
on: [pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'pnpm' }
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: corepack enable
      - run: pnpm i --frozen-lockfile
      - run: pip install pre-commit
      - run: pre-commit run --all-files
      - run: pnpm -r typecheck
      - run: pnpm -r test -- --run --passWithNoTests
      - run: pnpm -r build
```

## 핵심 아키텍처

- **SQLite:** Episode 번호 원자적 할당(Atomic) → 초기 운영은 SQLite, 추후 PostgreSQL 전환 예정
- **ChromaDB:** 대본 콘텐츠 임베딩/벡터 저장(검색/추천/중복 감지)
- **Redis:** Idempotency 키 저장, 작업 큐(재시도/지연 처리)
- **SSE:** 실시간 대본 생성 스트리밍(5 이벤트)

### 📡 **SSE 계약**
- **이벤트**: progress | preview | completed | failed | heartbeat
- **Headers**: text/event-stream, no-cache, no-transform, keep-alive
- **Backoff**: 1s→2s→5s (max 15s) + jitter, (선택) id: 지원(Last-Event-ID)

## 사용자 워크플로우

1. 프로젝트 생성 및 설정
2. AI 대본 생성 — 실시간 SSE 스트리밍으로 진행률/프리뷰 확인
3. Episode 자동 번호 할당 및 저장 — 서버가 1,2,3… 순차 부여(UNIQUE 제약)
4. ChromaDB 기반 검색/관리 — 유사 검색/중복 검사/추천

## 개발 가이드라인

### 🎨 **Frontend 규칙**
- **MUI 컴포넌트만 사용** (TailwindCSS 금지)
- **React Query**로 서버 상태/캐시 관리, 키 전략 통일
- **TypeScript strict 모드**: strict, verbatimModuleSyntax, noUncheckedIndexedAccess, exactOptionalPropertyTypes
- **ESLint 핵심 규칙**:
  ```json
  {
    "@typescript-eslint/consistent-type-imports": ["error", { "prefer": "type-imports" }],
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
    "unused-imports/no-unused-imports": "error",
    "no-restricted-imports": ["error", {
      "paths": [{"name": "@mui/material", "importNames": ["Grid"], "message": "Use Grid2 from '@mui/material/Grid2' instead"}]
    }],
    "no-restricted-properties": ["error", { "object": "process", "property": "env", "message": "Use import.meta.env in frontend code." }]
  }
  ```

### 🐍 **Backend 규칙**
- **LangGraph 에이전트** 기반 AI 워크플로우(외부 API 호출은 에이전트 노드에서 수행)
- **MyPy strict 모드** + Ruff/Black
- **Idempotency-Key**: 생성/저장 API 모두 적용(중복 방지)

## API 계약(Contract) 요약

- **Episodes:** `POST /projects/{id}/episodes` (server-assigned number, (project_id, number) UNIQUE)
- **Generation:** `POST /projects/{id}/generations` → `{ jobId }` (Idempotency-Key 필수)
- **SSE:** `GET /generations/{jobId}/events` (5 events)
- **Errors:** `{ code, message, details?, traceId }` (HTTP status 일관화)

## DoD (Definition of Done)

- ✅ PR이 pre-commit + typecheck + test + build 모두 green
- ✅ SSE 5종 스모크 테스트 통과(재연결·하트비트)
- ✅ Episode 서버 자동 번호(1→N) 경합 100건 테스트에서 중복/점프 없음
- ✅ MUI only(TailwindCSS 금지), Grid2 규칙 준수

## 주의사항 / 운영 메모

- **SQLite 동시성 한계** 고려(Lite-level write lock) → 동시 쓰기 많은 구간은 Redis 큐/트랜잭션으로 보정
- **프로덕션:** PostgreSQL 전환 계획(트랜잭션 카운터/시퀀스, 파티셔닝, 인덱스 전략)
- **MUI와 TailwindCSS 혼용 금지** — 스타일 충돌/일관성 저하 방지
- **보안/관측:** traceId/projectId/jobId 태깅, Sentry 연동, CORS/CSP, SSE proxy buffering off