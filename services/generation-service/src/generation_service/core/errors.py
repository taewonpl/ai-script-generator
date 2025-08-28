"""
Core error classes for the Generation Service
"""

from typing import Optional, Dict, Any


class APIError(Exception):
    """Base API error class"""
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code or "API_ERROR"
        self.status = status or 500
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses"""
        return {
            "code": self.code,
            "message": self.message,
            "status": self.status,
            "details": self.details,
        }


class ValidationError(APIError):
    """Validation error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="VALIDATION_ERROR", status=400, details=details)


class NotFoundError(APIError):
    """Resource not found error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="NOT_FOUND", status=404, details=details)


class ConflictError(APIError):
    """Conflict error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="CONFLICT", status=409, details=details)


class RateLimitError(APIError):
    """Rate limit exceeded error"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(message, code="RATE_LIMITED", status=429, details=details)


class ProcessingError(APIError):
    """Processing error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="PROCESSING_ERROR", status=500, details=details)