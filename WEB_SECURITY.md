# 웹 보안 헤더 및 정책 가이드

## 🛡️ 보안 헤더 설정 현황

### ✅ 현재 구현된 보안 헤더
```python
# SecurityHeadersMiddleware에서 적용 중:
{
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY", 
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "설정 가능"  # 옵션
}
```

### 🔧 추가 권장 보안 헤더
```python
# 프로덕션용 강화 설정
PRODUCTION_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' wss: https:; font-src 'self'; object-src 'none'; media-src 'self'; child-src 'none';",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",  # 최신 브라우저에서는 비활성화 권장
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site"
}
```

## 🌐 CORS 설정 보안

### 현재 CORS 설정:
```python
# ✅ 환경별 분리 구현됨
cors_origins = [
    "https://your-domain.com",  # 프로덕션
    "https://staging.your-domain.com",  # 스테이징  
    "http://localhost:3000"  # 개발용 (프로덕션에서 제거)
]

# ⚠️ 와일드카드 감지 및 경고 시스템 구현됨
if "*" in cors_origins and is_production():
    security_issues.append("Wildcard CORS origin allowed - restrict for production")
```

### 권장 프로덕션 CORS 설정:
```bash
# 환경변수 설정
export CORS_ORIGINS='["https://ai-script-generator.com","https://api.ai-script-generator.com"]'
export CORS_METHODS='["GET","POST","PUT","DELETE","OPTIONS"]'
export CORS_HEADERS='["Content-Type","Authorization","X-API-Key","X-Request-ID"]'
export CORS_CREDENTIALS=true
```

## 🍪 SameSite 쿠키 설정

### 현재 상태: ❌ 미구현
### 권장 구현:
```python
# services/*/src/*/middleware/cookie_security.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecureCookieMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        
        # 쿠키 보안 설정 강제
        if "set-cookie" in response.headers:
            cookies = response.headers.getlist("set-cookie")
            response.headers.pop("set-cookie")
            
            for cookie in cookies:
                # SameSite=Strict, Secure, HttpOnly 강제
                if "SameSite" not in cookie:
                    cookie += "; SameSite=Strict"
                if "Secure" not in cookie and request.url.scheme == "https":
                    cookie += "; Secure"
                if "HttpOnly" not in cookie:
                    cookie += "; HttpOnly"
                    
                response.headers.append("set-cookie", cookie)
                
        return response
```

## 🔐 서비스 간 mTLS/토큰 인증

### 현재 상태: 부분 구현
```python
# RequestSignatureMiddleware 구현됨:
# - HMAC-SHA256 서명 검증
# - 웹훅 엔드포인트 보호
# - 상수 시간 비교

# 추가 권장: JWT 서비스 토큰
class ServiceTokenMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_tokens: Dict[str, str]):
        super().__init__(app)
        self.service_tokens = service_tokens
        
    async def dispatch(self, request, call_next):
        # 서비스 간 호출 인증
        if request.url.path.startswith("/internal/"):
            service_token = request.headers.get("X-Service-Token")
            if not self._verify_service_token(service_token):
                raise HTTPException(403, "Invalid service token")
        
        return await call_next(request)
```

## 📋 보안 점검 체크리스트

### ✅ 구현 완료
- [x] HSTS 헤더 (1년, includeSubDomains)
- [x] X-Content-Type-Options: nosniff
- [x] X-Frame-Options: DENY  
- [x] XSS Protection 헤더
- [x] Referrer Policy 설정
- [x] CORS origins 환경별 분리
- [x] Rate limiting (100req/60s)
- [x] Request signature validation
- [x] Content length 제한 (16MB)
- [x] 의심스러운 패턴 감지

### ❌ 추가 필요
- [ ] CSP 헤더 상세 정책
- [ ] SameSite 쿠키 강제
- [ ] Permissions-Policy 헤더
- [ ] Cross-Origin 정책 헤더
- [ ] 서비스 간 JWT 토큰 인증
- [ ] 쿠키 보안 강화 미들웨어

## 🚀 즉시 적용 권장사항

```python
# main.py에 추가
app.add_middleware(
    SecurityHeadersMiddleware,
    content_security_policy="default-src 'self'; script-src 'self' 'unsafe-eval'"
)

# 환경변수 추가
export CSP_POLICY="default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'"
export ENABLE_SECURE_COOKIES=true
export SERVICE_TOKEN_SECRET="your-service-secret-2024!"
```