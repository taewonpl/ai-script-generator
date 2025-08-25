"""
Service-specific Exception Classes for AI Script Generator v3.0

각 마이크로서비스별 특화된 예외 클래스들을 정의합니다.
"""

from typing import Any

from .base import BaseServiceException, ErrorCategory, ErrorSeverity, NotFoundError

# =============================================================================
# Project Service Errors
# =============================================================================


class ProjectServiceError(BaseServiceException):
    """프로젝트 서비스 기본 예외"""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("error_code", "PROJECT_SERVICE_ERROR")
        super().__init__(message, **kwargs)


class ProjectNotFoundError(NotFoundError):
    """프로젝트를 찾을 수 없는 예외"""

    def __init__(self, project_id: str, **kwargs: Any) -> None:
        super().__init__("Project", project_id, **kwargs)
        self.project_id = project_id

    def _get_default_user_message(self) -> str:
        return "요청하신 프로젝트를 찾을 수 없습니다."


class EpisodeNotFoundError(NotFoundError):
    """에피소드를 찾을 수 없는 예외"""

    def __init__(
        self, episode_id: str, project_id: str | None = None, **kwargs: Any
    ) -> None:
        identifier = {"episode_id": episode_id}
        if project_id:
            identifier["project_id"] = project_id

        super().__init__("Episode", identifier, **kwargs)
        self.episode_id = episode_id
        self.project_id = project_id

    def _get_default_user_message(self) -> str:
        return "요청하신 에피소드를 찾을 수 없습니다."


class ProjectStatusError(ProjectServiceError):
    """프로젝트 상태 관련 오류"""

    def __init__(
        self,
        message: str,
        project_id: str,
        current_status: str,
        required_status: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.project_id = project_id
        self.current_status = current_status
        self.required_status = required_status

        details = kwargs.get("details", {})
        details.update(
            {
                "project_id": project_id,
                "current_status": current_status,
                "required_status": required_status,
            }
        )

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.BUSINESS_LOGIC
        kwargs["severity"] = ErrorSeverity.MEDIUM

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return "프로젝트의 현재 상태에서는 이 작업을 수행할 수 없습니다."


class ProjectQuotaExceededError(ProjectServiceError):
    """프로젝트 할당량 초과 오류"""

    def __init__(
        self, resource_type: str, current_count: int, max_allowed: int, **kwargs: Any
    ) -> None:
        self.resource_type = resource_type
        self.current_count = current_count
        self.max_allowed = max_allowed

        message = f"{resource_type} quota exceeded: {current_count}/{max_allowed}"

        details = kwargs.get("details", {})
        details.update(
            {
                "resource_type": resource_type,
                "current_count": current_count,
                "max_allowed": max_allowed,
            }
        )

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.BUSINESS_LOGIC
        kwargs["severity"] = ErrorSeverity.MEDIUM

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return f"{self.resource_type} 할당량({self.max_allowed}개)을 초과했습니다."


# =============================================================================
# Generation Service Errors
# =============================================================================


class GenerationServiceError(BaseServiceException):
    """AI 생성 서비스 기본 예외"""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("error_code", "GENERATION_SERVICE_ERROR")
        super().__init__(message, **kwargs)


class AIModelError(GenerationServiceError):
    """AI 모델 관련 오류"""

    def __init__(
        self, model_name: str, operation: str, error_message: str, **kwargs: Any
    ) -> None:
        self.model_name = model_name
        self.operation = operation
        self.error_message = error_message

        message = f"AI model '{model_name}' error during '{operation}': {error_message}"

        details = kwargs.get("details", {})
        details.update(
            {
                "model_name": model_name,
                "operation": operation,
                "model_error": error_message,
            }
        )

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.EXTERNAL_SERVICE
        kwargs["severity"] = ErrorSeverity.HIGH

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return "AI 모델 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."


class TokenLimitExceededError(GenerationServiceError):
    """토큰 한계 초과 오류"""

    def __init__(
        self, model_name: str, token_count: int, max_tokens: int, **kwargs: Any
    ) -> None:
        self.model_name = model_name
        self.token_count = token_count
        self.max_tokens = max_tokens

        message = f"Token limit exceeded for model '{model_name}': {token_count} > {max_tokens}"

        details = kwargs.get("details", {})
        details.update(
            {
                "model_name": model_name,
                "token_count": token_count,
                "max_tokens": max_tokens,
            }
        )

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.VALIDATION
        kwargs["severity"] = ErrorSeverity.MEDIUM

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return f"입력 텍스트가 너무 깁니다. 최대 {self.max_tokens} 토큰까지 처리 가능합니다."


class GenerationTimeoutError(GenerationServiceError):
    """생성 시간 초과 오류"""

    def __init__(
        self, timeout_seconds: int, generation_id: str | None = None, **kwargs: Any
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.generation_id = generation_id

        message = f"Generation timed out after {timeout_seconds} seconds"
        if generation_id:
            message += f" (id: {generation_id})"

        details = kwargs.get("details", {})
        details.update(
            {"timeout_seconds": timeout_seconds, "generation_id": generation_id}
        )

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.SYSTEM
        kwargs["severity"] = ErrorSeverity.HIGH

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return (
            f"생성 처리가 {self.timeout_seconds}초를 초과했습니다. 다시 시도해주세요."
        )


class ContentFilterError(GenerationServiceError):
    """콘텐츠 필터링 오류"""

    def __init__(self, reason: str, filter_type: str, **kwargs: Any) -> None:
        self.reason = reason
        self.filter_type = filter_type

        message = f"Content filtered: {reason} (filter: {filter_type})"

        details = kwargs.get("details", {})
        details.update({"reason": reason, "filter_type": filter_type})

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.VALIDATION
        kwargs["severity"] = ErrorSeverity.LOW

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return "생성된 콘텐츠가 정책에 위배되어 필터링되었습니다."


# =============================================================================
# RAG Service Errors
# =============================================================================


class RAGServiceError(BaseServiceException):
    """RAG 서비스 기본 예외"""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("error_code", "RAG_SERVICE_ERROR")
        super().__init__(message, **kwargs)


class KnowledgeBaseNotFoundError(NotFoundError):
    """지식베이스를 찾을 수 없는 예외"""

    def __init__(self, kb_id: str, **kwargs: Any) -> None:
        super().__init__("KnowledgeBase", kb_id, **kwargs)
        self.kb_id = kb_id

    def _get_default_user_message(self) -> str:
        return "요청하신 지식베이스를 찾을 수 없습니다."


class EmbeddingError(RAGServiceError):
    """임베딩 생성 오류"""

    def __init__(
        self, text: str, embedding_model: str, error_message: str, **kwargs: Any
    ) -> None:
        self.text_preview = text[:100] + "..." if len(text) > 100 else text
        self.embedding_model = embedding_model
        self.error_message = error_message

        message = f"Embedding failed for model '{embedding_model}': {error_message}"

        details = kwargs.get("details", {})
        details.update(
            {
                "embedding_model": embedding_model,
                "text_length": len(text),
                "embedding_error": error_message,
            }
        )

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.EXTERNAL_SERVICE
        kwargs["severity"] = ErrorSeverity.HIGH

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return "텍스트 분석 중 오류가 발생했습니다."


class VectorSearchError(RAGServiceError):
    """벡터 검색 오류"""

    def __init__(self, query: str, error_message: str, **kwargs: Any) -> None:
        self.query_preview = query[:100] + "..." if len(query) > 100 else query
        self.error_message = error_message

        message = f"Vector search failed: {error_message}"

        details = kwargs.get("details", {})
        details.update({"query_length": len(query), "search_error": error_message})

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.SYSTEM
        kwargs["severity"] = ErrorSeverity.HIGH

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return "검색 중 오류가 발생했습니다."


# =============================================================================
# Gateway Errors
# =============================================================================


class GatewayError(BaseServiceException):
    """API 게이트웨이 기본 예외"""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("error_code", "GATEWAY_ERROR")
        super().__init__(message, **kwargs)


class ServiceDiscoveryError(GatewayError):
    """서비스 디스커버리 오류"""

    def __init__(self, service_name: str, operation: str, **kwargs: Any) -> None:
        self.service_name = service_name
        self.operation = operation

        message = f"Service discovery failed for '{service_name}' during '{operation}'"

        details = kwargs.get("details", {})
        details.update({"service_name": service_name, "operation": operation})

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.SYSTEM
        kwargs["severity"] = ErrorSeverity.HIGH

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return f"{self.service_name} 서비스를 찾을 수 없습니다."


class LoadBalancingError(GatewayError):
    """로드 밸런싱 오류"""

    def __init__(
        self, service_name: str, available_instances: int, **kwargs: Any
    ) -> None:
        self.service_name = service_name
        self.available_instances = available_instances

        message = f"Load balancing failed for '{service_name}': {available_instances} instances available"

        details = kwargs.get("details", {})
        details.update(
            {"service_name": service_name, "available_instances": available_instances}
        )

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.SYSTEM
        kwargs["severity"] = ErrorSeverity.HIGH

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return f"{self.service_name} 서비스가 일시적으로 과부하 상태입니다."


class RateLimitExceededError(GatewayError):
    """요청 제한 초과 오류"""

    def __init__(
        self,
        client_id: str,
        limit: int,
        window_seconds: int,
        retry_after: int | None = None,
        **kwargs: Any,
    ) -> None:
        self.client_id = client_id
        self.limit = limit
        self.window_seconds = window_seconds
        self.retry_after = retry_after

        message = f"Rate limit exceeded for client '{client_id}': {limit} requests per {window_seconds}s"
        if retry_after:
            message += f", retry after {retry_after}s"

        details = kwargs.get("details", {})
        details.update(
            {
                "client_id": client_id,
                "limit": limit,
                "window_seconds": window_seconds,
                "retry_after": retry_after,
            }
        )

        kwargs["details"] = details
        kwargs["category"] = ErrorCategory.SYSTEM
        kwargs["severity"] = ErrorSeverity.MEDIUM

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        if self.retry_after:
            return (
                f"요청 한도를 초과했습니다. {self.retry_after}초 후 다시 시도해주세요."
            )
        return "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요."


# =============================================================================
# Database Errors
# =============================================================================


class DatabaseError(BaseServiceException):
    """데이터베이스 기본 예외"""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("error_code", "DATABASE_ERROR")
        kwargs.setdefault("category", ErrorCategory.DATABASE)
        kwargs.setdefault("severity", ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


class DatabaseConnectionError(DatabaseError):
    """데이터베이스 연결 오류"""

    def __init__(self, database_url: str, error_message: str, **kwargs: Any) -> None:
        # URL에서 민감한 정보 제거
        safe_url = self._sanitize_db_url(database_url)
        self.database_url = safe_url
        self.error_message = error_message

        message = f"Database connection failed to '{safe_url}': {error_message}"

        details = kwargs.get("details", {})
        details.update({"database_url": safe_url, "connection_error": error_message})

        kwargs["details"] = details
        kwargs["severity"] = ErrorSeverity.CRITICAL

        super().__init__(message, **kwargs)

    def _sanitize_db_url(self, url: str) -> str:
        """데이터베이스 URL에서 비밀번호 제거"""
        import re

        # postgresql://user:password@host:port/db -> postgresql://user:***@host:port/db  # pragma: allowlist secret
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)

    def _get_default_user_message(self) -> str:
        return "데이터베이스 연결 오류가 발생했습니다. 관리자에게 문의하세요."


class DatabaseTransactionError(DatabaseError):
    """데이터베이스 트랜잭션 오류"""

    def __init__(self, operation: str, error_message: str, **kwargs: Any) -> None:
        self.operation = operation
        self.error_message = error_message

        message = f"Database transaction failed during '{operation}': {error_message}"

        details = kwargs.get("details", {})
        details.update({"operation": operation, "transaction_error": error_message})

        kwargs["details"] = details

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        return "데이터 처리 중 오류가 발생했습니다. 다시 시도해주세요."


class DatabaseIntegrityError(DatabaseError):
    """데이터베이스 무결성 제약 위반 오류"""

    def __init__(
        self, constraint: str, table: str, error_message: str, **kwargs: Any
    ) -> None:
        self.constraint = constraint
        self.table = table
        self.error_message = error_message

        message = f"Database integrity constraint '{constraint}' violated in table '{table}': {error_message}"

        details = kwargs.get("details", {})
        details.update(
            {"constraint": constraint, "table": table, "integrity_error": error_message}
        )

        kwargs["details"] = details
        kwargs["severity"] = ErrorSeverity.MEDIUM

        super().__init__(message, **kwargs)

    def _get_default_user_message(self) -> str:
        if "unique" in self.constraint.lower():
            return "이미 존재하는 데이터입니다."
        elif "foreign" in self.constraint.lower():
            return "참조하는 데이터가 존재하지 않습니다."
        return "데이터 규칙 위반으로 저장할 수 없습니다."
