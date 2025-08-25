# Claude Code Configuration for AI Script Generator v3.0 Core

이 파일은 Claude Code가 AI Script Generator v3.0 Core 패키지를 효율적으로 작업할 수 있도록 프로젝트 구조와 작업 컨텍스트를 정의합니다.

## 📁 프로젝트 구조

```
ai-script-generator-v3/shared/core/
├── src/
│   ├── __init__.py                 # 메인 패키지 엔트리포인트
│   └── ai_script_core/            # 핵심 모듈
│       ├── __init__.py
│       ├── schemas/               # Pydantic DTO 스키마
│       │   ├── __init__.py
│       │   ├── base.py           # 기본 스키마 클래스
│       │   ├── common.py         # 공통 타입 및 응답 스키마
│       │   ├── project.py        # 프로젝트 관련 스키마
│       │   └── generation.py     # AI 생성 관련 스키마
│       ├── exceptions/           # 구조화된 예외 시스템
│       │   ├── __init__.py
│       │   ├── base.py          # 기본 예외 클래스
│       │   ├── service_errors.py # 서비스별 예외
│       │   └── utils.py         # 예외 처리 유틸리티
│       ├── utils/               # 공통 유틸리티
│       │   ├── __init__.py
│       │   ├── config.py        # 설정 관리 (pydantic-settings)
│       │   ├── logger.py        # 구조화된 로깅
│       │   └── helpers.py       # 헬퍼 함수들
│       └── observability/       # 관찰가능성 시스템
│           ├── __init__.py
│           ├── health.py        # 헬스체크 시스템
│           ├── metrics.py       # 메트릭 수집
│           ├── errors.py        # 에러 응답 포맷팅
│           ├── idempotency.py   # 멱등성 처리
│           └── fastapi_middleware.py # FastAPI 미들웨어
├── tests/                      # 테스트 파일
├── scripts/                    # 스크립트
├── quick_test.py              # 빠른 기능 검증
├── pyproject.toml            # 프로젝트 설정
├── requirements.txt          # 의존성
└── claude.md                # 이 파일
```

## 🎯 주요 기능

### 1. 스키마 시스템 (Pydantic v2)
- **BaseSchema**: 모든 DTO의 기본 클래스
- **IDMixin, TimestampMixin**: 공통 필드 믹스인
- **ProjectCreateDTO, EpisodeCreateDTO**: 생성 요청 스키마
- **GenerationRequestDTO, GenerationResponseDTO**: AI 생성 관련 스키마
- **ErrorResponseDTO, SuccessResponseDTO**: 표준 응답 포맷

### 2. 예외 처리 시스템
- **BaseServiceException**: 구조화된 예외 기본 클래스
- **서비스별 예외**: ProjectNotFoundError, EpisodeNotFoundError 등
- **예외 데코레이터**: @exception_handler, @async_exception_handler
- **에러 포매터**: 일관된 에러 응답 생성

### 3. 설정 관리 (pydantic-settings)
- **환경 변수 자동 매핑**: pydantic-settings 기반
- **타입 안전성**: 모든 설정값의 타입 검증
- **검증 시스템**: 설정값 유효성 자동 확인
- **계층 구조**: DatabaseSettings, APISettings, SecuritySettings 등

### 4. 로깅 시스템
- **구조화된 JSON 로깅**: StructuredFormatter
- **컨텍스트 로거**: ContextualLoggerAdapter
- **서비스별 로거**: get_service_logger()
- **요청별 로거**: create_request_logger()

### 5. 관찰가능성 (Observability)
- **헬스체크**: 의존성 상태 모니터링
- **메트릭 수집**: 성능 지표 추적
- **에러 추적**: 에러 패턴 분석
- **FastAPI 미들웨어**: 요청/응답 자동 추적

## 🛠 개발 환경 설정

### 필수 요구사항
- Python 3.9+
- pydantic>=2.5.0
- pydantic-settings>=2.1.0
- fastapi>=0.104.1

### 설치 방법
```bash
# 개발 모드 설치
pip install -e .

# 개발 의존성 포함 설치
pip install -e ".[dev]"

# 타입 스텁 설치
pip install types-redis types-requests
```

### 타입 체크
```bash
# MyPy 실행 (strict 모드)
python -m mypy src/ --strict

# 현재 상태: ✅ Success: no issues found in 25 source files
```

## 📝 코딩 가이드라인

### 1. 타입 안전성
- 모든 함수에 타입 힌트 필수
- MyPy strict 모드 준수
- Any 타입 사용 최소화
- Generic 타입 적극 활용

### 2. 스키마 설계
```python
from pydantic import Field
from ai_script_core.schemas.base import BaseSchema, IDMixin

class MyDTO(BaseSchema, IDMixin):
    name: str = Field(..., min_length=1, max_length=100, description="이름")
    value: Optional[int] = Field(None, ge=0, description="값")
```

### 3. 예외 처리
```python
from ai_script_core.exceptions import BaseServiceException, ErrorCategory

class MyCustomError(BaseServiceException):
    def __init__(self, resource_id: str, **kwargs):
        super().__init__(
            message=f"Resource {resource_id} not found",
            category=ErrorCategory.NOT_FOUND,
            details={"resource_id": resource_id},
            **kwargs
        )
```

### 4. 설정 관리
```python
from pydantic import Field
from pydantic_settings import BaseSettings

class MySettings(BaseSettings):
    api_key: str = Field(..., description="API 키")
    timeout: int = Field(default=30, ge=1, description="타임아웃")
    
    model_config = SettingsConfigDict(env_prefix="MY_")
```

## 🧪 테스트

### 단위 테스트 실행
```bash
python -m pytest tests/ -v
```

### 통합 테스트
```bash
python quick_test.py
```

### 커버리지 확인
```bash
python -m pytest tests/ --cov=ai_script_core --cov-report=html
```

## 🚀 배포

### 빌드
```bash
python -m build
```

### 패키지 검증
```bash
twine check dist/*
```

### 업로드 (테스트)
```bash
twine upload --repository testpypi dist/*
```

## 💡 Claude Code 작업 팁

### 1. 프로젝트 컨텍스트 인식
- **패키지 구조**: `ai_script_core` 네임스페이스 사용
- **Import 경로**: 항상 `from ai_script_core.xxx import`
- **타입 안전성**: MyPy strict 모드 준수 필수

### 2. 주요 작업 영역
- **스키마 수정**: `src/ai_script_core/schemas/`
- **예외 추가**: `src/ai_script_core/exceptions/`
- **유틸리티 확장**: `src/ai_script_core/utils/`
- **관찰가능성**: `src/ai_script_core/observability/`

### 3. 테스트 가이드
- **빠른 검증**: `python quick_test.py`
- **타입 체크**: `python -m mypy src/ --strict`
- **단위 테스트**: `python -m pytest tests/`

### 4. 자주 사용하는 명령어
```bash
# MyPy 체크
mypy src/ --strict

# 테스트 실행
pytest tests/ -v

# 패키지 재설치
pip install -e . --force-reinstall

# 린트 체크
ruff check src/

# 포맷팅
ruff format src/
```

## 📚 참고 자료

### 내부 문서
- [프로젝트 README](README.md)
- [변경 로그](CHANGELOG.md)
- [릴리스 체크리스트](RELEASE_CHECKLIST.md)

### 외부 라이브러리
- [Pydantic v2](https://docs.pydantic.dev/2.0/)
- [pydantic-settings](https://docs.pydantic.dev/2.0/usage/settings/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [MyPy](https://mypy.readthedocs.io/)

## ⚠️ 주의사항

1. **Python 버전**: 3.9+ 지원 (원래 3.10+에서 수정됨)
2. **타입 안전성**: strict 모드에서 0 오류 유지 필수
3. **보안**: 하드코딩된 비밀은 `# pragma: allowlist secret` 주석 필요
4. **호환성**: Pydantic v2 구문 사용 (v1 호환성 없음)

## 🔄 최근 업데이트

- ✅ MyPy strict 모드 0 오류 달성 (25개 파일)
- ✅ Python 3.9 호환성 확보  
- ✅ pydantic-settings 의존성 추가
- ✅ 타입 스텁 설치 (types-redis, types-requests)
- ✅ 중복 파일 정리 및 구조 통일
- ✅ 테스트 import 경로 수정
- ✅ 개발 모드 설치 완료

**현재 상태: 🟢 모든 시스템 정상 작동**