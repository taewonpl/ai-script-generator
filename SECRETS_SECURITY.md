# Secrets 관리 보안 가이드

## 🔐 Secrets Manager 이관 계획

### 1. 임베딩 API 키 관리
```python
# services/generation-service/src/generation_service/config/secrets_manager.py
import boto3
import os
from typing import Dict, Optional

class SecretManager:
    """AWS Secrets Manager 또는 HashiCorp Vault 연동"""
    
    def __init__(self):
        self.secrets_client = boto3.client('secretsmanager', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        self.cache = {}
        self.cache_ttl = 300  # 5분 캐시
    
    def get_api_key(self, service: str) -> str:
        """API 키 안전하게 조회"""
        secret_name = f"ai-script-generator/{service}/api-key"
        
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            return response['SecretString']
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            # 폴백: 환경변수 (개발용)
            return os.getenv(f"{service.upper()}_API_KEY", "")

# 사용 예시
secrets = SecretManager()
openai_key = secrets.get_api_key("openai")
anthropic_key = secrets.get_api_key("anthropic")
```

### 2. 크리덴셜 회전 주기 설정
```bash
# AWS Secrets Manager 자동 회전 설정
aws secretsmanager update-secret --secret-id ai-script-generator/redis/password \
  --description "Redis password for RAG workers" \
  --rotation-rules AutomaticallyAfterDays=30

# Lambda 함수로 자동 회전
aws secretsmanager rotate-secret --secret-id ai-script-generator/redis/password
```

### 3. 환경별 Secrets 분리
```yaml
# Production
ai-script-generator/prod/openai/api-key
ai-script-generator/prod/redis/password  
ai-script-generator/prod/redis/encryption-key

# Staging  
ai-script-generator/staging/openai/api-key
ai-script-generator/staging/redis/password

# Development
ai-script-generator/dev/openai/api-key
ai-script-generator/dev/redis/password
```

## ✅ 하드코딩된 비밀 정보 점검 결과

### 발견된 잠재적 위험:
1. **테스트 파일의 예시 키**: 
   - `test_memory_system.py:332` - 예시 API 키 (마스킹 처리됨)
   
2. **문서화된 예시**:
   - `__init__.py:83` - Redis 비밀번호 예시
   - `OBSERVABILITY.md` - API 키 플레이스홀더

### 보안 상태:
- ✅ 실제 API 키는 환경변수로만 접근
- ✅ detect-secrets 도구로 스캔 자동화
- ✅ pragma allowlist 주석으로 예외 처리
- ✅ 테스트 키는 마스킹 처리됨

## 🔄 권장 보안 개선사항

### 즉시 적용 필요:
```bash
# 1. Secrets Manager 설정
export SECRETS_MANAGER_ENABLED=true
export AWS_REGION=us-east-1
export SECRET_PREFIX=ai-script-generator/prod/

# 2. 로컬 개발용 백업
export FALLBACK_TO_ENV=true  # 개발 환경에서만
```

### 모니터링 및 알림:
```python
# CloudWatch 알림 설정
import boto3

def setup_secret_access_alerts():
    cloudwatch = boto3.client('cloudwatch')
    
    # API 키 접근 빈도 모니터링
    cloudwatch.put_metric_alarm(
        AlarmName='HighAPIKeyUsage',
        MetricName='SecretAccess',
        Threshold=1000,  # 시간당 1000회 초과시 알림
        ComparisonOperator='GreaterThanThreshold'
    )
```