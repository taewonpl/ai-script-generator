"""
분산 추적 미들웨어
Request ID / Trace ID 전구간 추적 시스템
"""

import asyncio
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Optional, Dict, Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Context variables for distributed tracing
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

logger = logging.getLogger(__name__)


class DistributedTracingMiddleware(BaseHTTPMiddleware):
    """분산 추적을 위한 미들웨어"""
    
    def __init__(self, app: ASGIApp, service_name: str = "ai-script-generator"):
        super().__init__(app)
        self.service_name = service_name
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract or generate tracing IDs
        request_id = self._extract_or_generate_request_id(request)
        trace_id = self._extract_or_generate_trace_id(request)
        correlation_id = self._extract_correlation_id(request)
        user_id = self._extract_user_id(request)
        
        # Set context variables
        request_id_token = request_id_var.set(request_id)
        trace_id_token = trace_id_var.set(trace_id)
        correlation_id_token = correlation_id_var.set(correlation_id)
        user_id_token = user_id_var.set(user_id)
        
        try:
            # Add to request state for downstream access
            request.state.request_id = request_id
            request.state.trace_id = trace_id
            request.state.correlation_id = correlation_id
            request.state.user_id = user_id
            
            # Process request
            start_time = time.time()
            
            try:
                response = await call_next(request)
            except Exception as e:
                # Log error with tracing context
                logger.error(
                    f"Request failed: {str(e)}",
                    extra={
                        "request_id": request_id,
                        "trace_id": trace_id,
                        "correlation_id": correlation_id,
                        "user_id": user_id,
                        "path": request.url.path,
                        "method": request.method,
                        "error": str(e)
                    }
                )
                raise
            
            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = trace_id
            if correlation_id:
                response.headers["X-Correlation-ID"] = correlation_id
            
            # Log successful request
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "correlation_id": correlation_id,
                    "user_id": user_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "service": self.service_name
                }
            )
            
            return response
            
        finally:
            # Reset context variables
            request_id_var.reset(request_id_token)
            trace_id_var.reset(trace_id_token)
            correlation_id_var.reset(correlation_id_token)
            user_id_var.reset(user_id_token)
    
    def _extract_or_generate_request_id(self, request: Request) -> str:
        """Extract or generate request ID"""
        # Try various header names
        for header in ["X-Request-ID", "X-Request-Id", "request-id"]:
            request_id = request.headers.get(header)
            if request_id:
                return request_id
        
        # Generate new request ID
        return f"req-{uuid.uuid4().hex[:16]}"
    
    def _extract_or_generate_trace_id(self, request: Request) -> str:
        """Extract or generate trace ID"""
        # Try various header names
        for header in ["X-Trace-ID", "X-Trace-Id", "trace-id", "traceparent"]:
            trace_id = request.headers.get(header)
            if trace_id:
                # Handle W3C Trace Context format
                if header == "traceparent":
                    parts = trace_id.split("-")
                    if len(parts) >= 2:
                        return parts[1]  # Extract trace-id part
                return trace_id
        
        # Generate new trace ID
        return f"trace-{uuid.uuid4().hex}"
    
    def _extract_correlation_id(self, request: Request) -> Optional[str]:
        """Extract correlation ID"""
        return request.headers.get("X-Correlation-ID")
    
    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from various sources"""
        # Try JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # This would require JWT decoding
                # For now, just extract from custom header
                pass
            except Exception:
                pass
        
        # Try custom header
        return request.headers.get("X-User-ID")


class TracingLoggerAdapter(logging.LoggerAdapter):
    """로거 어댑터: 자동으로 추적 컨텍스트 추가"""
    
    def process(self, msg, kwargs):
        # Get current context
        extra = kwargs.get('extra', {})
        
        # Add tracing context
        if request_id_var.get():
            extra['request_id'] = request_id_var.get()
        if trace_id_var.get():
            extra['trace_id'] = trace_id_var.get()
        if correlation_id_var.get():
            extra['correlation_id'] = correlation_id_var.get()
        if user_id_var.get():
            extra['user_id'] = user_id_var.get()
        
        kwargs['extra'] = extra
        return msg, kwargs


def get_current_request_id() -> Optional[str]:
    """현재 요청 ID 반환"""
    return request_id_var.get()


def get_current_trace_id() -> Optional[str]:
    """현재 추적 ID 반환"""
    return trace_id_var.get()


def get_current_correlation_id() -> Optional[str]:
    """현재 상관관계 ID 반환"""
    return correlation_id_var.get()


def get_current_user_id() -> Optional[str]:
    """현재 사용자 ID 반환"""
    return user_id_var.get()


def get_tracing_context() -> Dict[str, Any]:
    """현재 추적 컨텍스트 반환"""
    return {
        'request_id': get_current_request_id(),
        'trace_id': get_current_trace_id(),
        'correlation_id': get_current_correlation_id(),
        'user_id': get_current_user_id(),
    }


class TracingHandler(logging.Handler):
    """로그 핸들러: 구조화된 로그 출력"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFormatter(StructuredFormatter())
    
    def emit(self, record):
        # Add tracing context to record
        if not hasattr(record, 'request_id'):
            record.request_id = get_current_request_id()
        if not hasattr(record, 'trace_id'):
            record.trace_id = get_current_trace_id()
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = get_current_correlation_id()
        if not hasattr(record, 'user_id'):
            record.user_id = get_current_user_id()
        
        super().emit(record)


class StructuredFormatter(logging.Formatter):
    """구조화된 JSON 로그 포매터"""
    
    def format(self, record):
        import json
        from datetime import datetime
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add tracing context
        if hasattr(record, 'request_id') and record.request_id:
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'trace_id') and record.trace_id:
            log_entry['trace_id'] = record.trace_id
        if hasattr(record, 'correlation_id') and record.correlation_id:
            log_entry['correlation_id'] = record.correlation_id
        if hasattr(record, 'user_id') and record.user_id:
            log_entry['user_id'] = record.user_id
        
        # Add any extra fields
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


# 로거 설정 헬퍼
def setup_distributed_logging(service_name: str = "ai-script-generator"):
    """분산 로깅 설정"""
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add structured handler
    handler = TracingHandler()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    return root_logger


# 사용 예시
"""
# FastAPI 앱에 미들웨어 추가
app.add_middleware(DistributedTracingMiddleware, service_name="generation-service")

# 로거 설정
setup_distributed_logging("generation-service")

# 로거 사용
logger = TracingLoggerAdapter(logging.getLogger(__name__), {})
logger.info("Processing started", extra={
    "document_id": "doc-123",
    "project_id": "proj-456"
})

# 현재 컨텍스트 조회
trace_id = get_current_trace_id()
request_id = get_current_request_id()
"""