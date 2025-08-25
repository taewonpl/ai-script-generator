# Pydantic v2 model_ Field Warning 제거

## 개요

Generation Service의 Pydantic v2 model_ 접두어 필드 경고를 완전히 제거했습니다.

## 문제 배경

- **문제**: GenerationResponse, GenerationUpdate, ScriptGenerationRequest, NodeExecutionResult 모델에서 `model_used`, `model_preferences` 같은 `model_` 접두어 필드 사용
- **원인**: Pydantic v2에서 `model_` 접두어는 보호된 네임스페이스로 지정되어 경고 발생
- **영향**: 동작은 정상이지만 시끄러운 경고 메시지 생성

## 해결 방법

### ConfigDict(protected_namespaces=()) 사용

Option A (필드명 변경)와 Option B (ConfigDict 설정) 중 **Option B**를 선택하여 API 호환성을 완전히 유지했습니다.

### 수정된 모델들

1. **GenerationResponse** (Core 버전)
```python
class GenerationResponse(GenerationResponseDTO):
    """Enhanced generation response using Core DTO"""
    
    model_config = ConfigDict(protected_namespaces=())
    
    # Legacy compatibility fields
    model_used: Optional[str] = Field(None, description="Legacy model field")
    # ... other fields
```

2. **GenerationResponse** (Fallback 버전)
```python
class GenerationResponse(BaseSchema):
    """Response model for script generation"""
    
    model_config = ConfigDict(protected_namespaces=())
    
    # Generation details
    model_used: Optional[str] = Field(None, description="AI model used for generation")
    # ... other fields
```

3. **GenerationUpdate**
```python
class GenerationUpdate(BaseSchema):
    """Model for updating generation status"""
    
    model_config = ConfigDict(protected_namespaces=())
    
    model_used: Optional[str] = None
    # ... other fields
```

4. **ScriptGenerationRequest**
```python
class ScriptGenerationRequest(BaseSchema):
    """Enhanced script generation request for hybrid workflow"""
    
    model_config = ConfigDict(protected_namespaces=())
    
    # AI model preferences
    model_preferences: Optional[Dict[str, str]] = Field(None, description="Model preferences per node")
    # ... other fields
```

5. **NodeExecutionResult**
```python
class NodeExecutionResult(BaseSchema):
    """Result from individual node execution"""
    
    model_config = ConfigDict(protected_namespaces=())
    
    model_used: Optional[str] = Field(None, description="AI model used")
    # ... other fields
```

### 추가 수정사항

- **Pydantic v2 호환성**: `Config` 클래스를 `model_config = ConfigDict()`로 변경
- **Deprecation 해결**: `json_encoders` 사용 중단 (Pydantic v2에서 deprecated)

## 테스트 및 검증

### 1. 단위 테스트 통과
```bash
python3 scripts/test-pydantic-v2-model-fields.py
```
- ✅ 18개 테스트 모두 통과
- ✅ model_ 필드 경고: 0개
- ✅ 네임스페이스 경고: 0개

### 2. 서비스 시작 검증
```bash  
python3 scripts/test-service-warnings.py
```
- ✅ FastAPI 앱 초기화 성공
- ✅ OpenAPI 스키마 생성 성공
- ✅ model_used 필드가 스키마에 정상 포함
- ✅ model_ 경고: 0개

### 3. 실제 동작 검증
```bash
timeout 10 python3 -c "from generation_service.models.generation import *; ..."
```
- ✅ 모든 model_ 필드 모델 인스턴스 생성 성공
- ✅ 경고 없음 확인

## 결과

### ✅ 성공한 목표
1. **완전한 경고 제거**: `model_` 접두어 관련 경고 0개
2. **API 호환성 유지**: 기존 필드명 그대로 유지
3. **기능 보존**: 직렬화/역직렬화 정상 동작
4. **OpenAPI 스키마**: 정상 생성 및 필드 포함
5. **서비스 시작**: 깨끗한 시작 (model_ 경고 없음)

### 📊 통계
- **수정된 모델**: 5개 (GenerationResponse 2버전, GenerationUpdate, ScriptGenerationRequest, NodeExecutionResult)  
- **영향받은 필드**: `model_used`, `model_preferences`
- **보존된 API**: 100% 호환성 유지
- **제거된 경고**: model_ namespace 관련 모든 경고

## 향후 고려사항

1. **새 모델 추가 시**: `model_` 접두어 필드 사용 시 `ConfigDict(protected_namespaces=())` 추가
2. **Core Module 업데이트**: Core Module이 업데이트되면 해당 DTO도 동일하게 설정 필요
3. **Pydantic v3**: 향후 Pydantic v3 업그레이드 시 재검토 필요

## 코드 예시

### Before (경고 발생)
```python
class GenerationResponse(BaseSchema):
    model_used: Optional[str] = Field(None)  # ⚠️ Warning 발생
```

### After (경고 제거)  
```python
class GenerationResponse(BaseSchema):
    model_config = ConfigDict(protected_namespaces=())  # ✅ Warning 제거
    
    model_used: Optional[str] = Field(None)  # ✅ 경고 없음
```

## 결론

**Pydantic v2 model_ 필드 경고가 완전히 제거되었습니다!**

- ✅ ConfigDict(protected_namespaces=()) 솔루션 성공 적용
- ✅ API 스키마 호환성 100% 유지
- ✅ 모든 테스트 통과 
- ✅ 서비스 시작 시 깨끗한 로그
- ✅ 기존 기능 완전 보존