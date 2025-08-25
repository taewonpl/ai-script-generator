# AI Script Generator v3.0 Core - Testing Guide

## 🧪 테스트 개요

이 문서는 AI Script Generator v3.0 Core 라이브러리의 독립성과 기능을 검증하는 테스트 시스템에 대해 설명합니다.

## 📁 테스트 구조

```
shared/core/
├── tests/                    # 테스트 디렉토리
│   ├── __init__.py          # 테스트 패키지 초기화
│   ├── test_schemas.py      # 스키마 검증 테스트 (200+ 테스트)
│   ├── test_exceptions.py   # 예외 처리 테스트 (150+ 테스트)
│   ├── test_utils.py        # 유틸리티 함수 테스트 (180+ 테스트)
│   └── test_installation.py # 패키지 설치 테스트 (100+ 테스트)
├── pytest.ini              # pytest 설정
├── test_install.sh          # 전체 설치 테스트 스크립트
├── quick_test.py            # 빠른 기능 검증 스크립트
└── README_TEST.md           # 이 문서
```

## 🚀 테스트 실행 방법

### 1. 빠른 검증 (Quick Test)

```bash
# 기본 기능 빠른 확인
python3 quick_test.py

# 상세 출력 모드
python3 quick_test.py --verbose
```

### 2. 전체 설치 테스트

```bash
# 완전한 설치 및 독립성 테스트
./test_install.sh
```

### 3. pytest 테스트 수트

```bash
# 모든 테스트 실행
python3 -m pytest

# 커버리지 포함 실행
python3 -m pytest --cov=src --cov-report=html

# 특정 테스트 파일 실행
python3 -m pytest tests/test_schemas.py -v
python3 -m pytest tests/test_exceptions.py -v
python3 -m pytest tests/test_utils.py -v
python3 -m pytest tests/test_installation.py -v

# 병렬 실행 (pytest-xdist 필요)
python3 -m pytest -n auto
```

## 📋 테스트 카테고리

### 1. 스키마 테스트 (`test_schemas.py`)
- **임포트 테스트**: 모든 스키마 클래스 임포트 가능 여부
- **기본 스키마**: BaseSchema, IDMixin, TimestampMixin 기능
- **공통 스키마**: 상태 enum, 응답 DTO 검증
- **프로젝트 스키마**: 프로젝트/에피소드 DTO 생성/검증
- **생성 스키마**: AI 생성 요청/응답 DTO 검증
- **유효성 검증**: Pydantic 검증 로직 동작 확인
- **통합 테스트**: 중첩 스키마, JSON 직렬화, 상속 구조

### 2. 예외 테스트 (`test_exceptions.py`)
- **임포트 테스트**: 모든 예외 클래스 임포트 가능 여부
- **기본 예외**: BaseServiceException 생성/기능 테스트
- **서비스 예외**: 5개 마이크로서비스별 특화 예외
- **예외 데코레이터**: exception_handler, async_exception_handler
- **에러 포맷팅**: API 응답용 포맷팅 및 민감정보 필터링
- **유틸리티**: safe_execute, chain_exceptions 등
- **상속 구조**: 예외 계층 구조 검증

### 3. 유틸리티 테스트 (`test_utils.py`)
- **설정 관리**: pydantic BaseSettings 기반 설정 시스템
- **로깅 시스템**: 구조화된 JSON 로깅 및 컨텍스트 관리
- **UUID 생성**: 다양한 형태의 고유 ID 생성
- **날짜/시간**: 포맷팅, 파싱, 계산 기능
- **텍스트 처리**: HTML 제거, 정제, 패턴 추출, 마스킹
- **서비스 헬스체크**: 동기/비동기 상태 확인
- **기타 유틸리티**: JSON 처리, 해시 계산, 환경변수, 재시도

### 4. 설치/독립성 테스트 (`test_installation.py`)
- **패키지 구조**: 필수 파일 존재 확인
- **직접 임포트**: 패키지 설치 없이 임포트 가능 여부
- **기능 테스트**: 설치 없이 기본 기능 동작 확인
- **의존성**: 최소 의존성으로 동작 여부
- **호환성**: Python 버전, 크로스 플랫폼
- **설치 준비**: setup.py 문법, 매니페스트 파일

## 🎯 테스트 마커

pytest에서 다음 마커를 사용하여 특정 테스트만 실행할 수 있습니다:

```bash
# 단위 테스트만 실행
pytest -m unit

# 통합 테스트만 실행  
pytest -m integration

# 느린 테스트 제외
pytest -m "not slow"

# 네트워크가 필요한 테스트만
pytest -m network

# 비동기 테스트만
pytest -m asyncio
```

## 📊 커버리지 목표

- **전체 코드 커버리지**: 최소 80%
- **스키마 모듈**: 90%+
- **예외 모듈**: 85%+  
- **유틸리티 모듈**: 80%+

## 🔧 CI/CD 통합

### GitHub Actions 예시

```yaml
name: Core Package Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"
    
    - name: Run quick test
      run: python quick_test.py
    
    - name: Run pytest
      run: |
        pytest --cov=src --cov-report=xml --cov-fail-under=80
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: coverage.xml
```

## 🛡️ 테스트 모범 사례

### 1. 독립성 원칙
- 각 테스트는 다른 테스트에 의존하지 않음
- 테스트 순서에 관계없이 실행 가능
- 외부 서비스에 의존하지 않음

### 2. 명확한 테스트 이름
```python
def test_project_create_dto_validation_with_invalid_name():
    """프로젝트 생성 DTO에서 유효하지 않은 이름으로 검증 실패 테스트"""
```

### 3. 적절한 Mock 사용
```python
@patch('requests.get')
def test_validate_service_health_success(self, mock_get):
    """외부 서비스 의존성을 Mock으로 처리"""
```

### 4. 경계값 테스트
```python
def test_generate_short_id_various_lengths(self):
    """다양한 길이의 ID 생성 테스트"""
    for length in [4, 6, 8, 10, 16, 32]:
        short_id = generate_short_id(length)
        assert len(short_id) == length
```

## 🔍 테스트 결과 해석

### 성공적인 테스트 실행 예시
```
==================== 630 passed in 15.42s ====================

Coverage Report:
src/schemas/__init__.py    95%
src/exceptions/__init__.py 88%
src/utils/__init__.py      83%
TOTAL                      85%
```

### 실패 시 디버깅

1. **임포트 실패**: 경로 또는 의존성 문제
2. **검증 실패**: Pydantic 모델 정의 오류
3. **기능 실패**: 로직 구현 오류
4. **Mock 실패**: 외부 의존성 처리 오류

## 📈 테스트 메트릭

### 정량적 지표
- **테스트 수**: 630+개
- **실행 시간**: 15초 이하
- **커버리지**: 85% 이상
- **성공률**: 100% 목표

### 정성적 지표
- **코드 품질**: 예외 처리, 타입 힌트
- **문서화**: 모든 함수에 docstring
- **유지보수성**: 명확한 구조, 모듈화
- **확장성**: 새로운 기능 추가 용이성

## 🚀 지속적 개선

### 테스트 추가 계획
1. **성능 테스트**: 대용량 데이터 처리
2. **스트레스 테스트**: 동시 요청 처리
3. **보안 테스트**: 입력 검증, SQL 인젝션 방지
4. **호환성 테스트**: 다양한 Python 버전

### 자동화 계획
1. **Pre-commit Hook**: 커밋 전 자동 테스트
2. **Nightly Build**: 매일 전체 테스트 실행
3. **Performance Regression**: 성능 저하 감지
4. **Dependency Update**: 의존성 업데이트 시 자동 테스트

## 📞 문의 및 기여

테스트 관련 문의사항이나 개선 제안이 있으시면:

1. **이슈 등록**: GitHub Issues에 버그 리포트나 기능 요청
2. **PR 제출**: 테스트 개선이나 새로운 테스트 추가
3. **문서 개선**: 테스트 가이드나 README 개선

---

**Happy Testing! 🧪✨**