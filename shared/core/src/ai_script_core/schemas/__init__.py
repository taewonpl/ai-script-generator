"""
Schemas Module for AI Script Generator v3.0

Pydantic-based data schemas and validation for microservices communication.
"""

# Base schemas
from .base import (
    BaseResponseSchema,
    BaseSchema,
    IDMixin,
    PaginatedResponse,
    PaginationSchema,
    RequestMetadata,
    ResponseMetadata,
    TimestampMixin,
)

# Common enums and response types
from .common import (
    CommonResponseDTO,
    EpisodeType,
    ErrorCode,
    ErrorResponseDTO,
    GenerationStatus,
    ProjectStatus,
    ProjectType,
    ServiceStatus,
    ServiceStatusDTO,
    SuccessResponseDTO,
)

# Generation schemas
from .generation import (
    AIModelConfigDTO,
    GenerationMetadataDTO,
    GenerationRequestDTO,
    GenerationResponseDTO,
    RAGConfigDTO,
)

# Project schemas
from .project import (
    EpisodeCreateDTO,
    EpisodeCreateRequest,
    EpisodeDTO,
    EpisodeResponseDTO,
    EpisodeUpdateDTO,
    EpisodeUpdateRequest,
    ProjectCreateDTO,
    ProjectCreateRequest,
    ProjectDTO,
    ProjectListResponse,
    # Aliases for backward compatibility
    ProjectResponseDTO,
    ProjectUpdateDTO,
    ProjectUpdateRequest,
)

# SSE Types for Frontend-Backend type compatibility
from .sse_types import (
    # SSE Event Types
    BaseSSEEvent,
    CompletedEventData,
    CompletionResult,
    FailedEventData,
    GenerationJobDetails,
    GenerationJobRequest,
    GenerationJobResponse,
    # Job Management
    GenerationJobStatus,
    GenerationListResponse,
    # API Response Types
    GenerationStartResponse,
    GenerationStatsResponse,
    GenerationStatusResponse,
    HeartbeatEventData,
    PreviewEventData,
    ProgressEventData,
    # Connection Types
    SSEConnectionState,
    SSEConnectionStatus,
    SSEErrorInfo,
    # Union Types
    SSEEventData,
)

__all__ = [
    # Base schemas
    "BaseSchema",
    "IDMixin",
    "TimestampMixin",
    "BaseResponseSchema",
    "PaginationSchema",
    "PaginatedResponse",
    "RequestMetadata",
    "ResponseMetadata",
    # Common types
    "ProjectStatus",
    "ProjectType",
    "EpisodeType",
    "GenerationStatus",
    "ServiceStatus",
    "ErrorCode",
    "ErrorResponseDTO",
    "SuccessResponseDTO",
    "ServiceStatusDTO",
    "CommonResponseDTO",
    # Project schemas
    "ProjectDTO",
    "ProjectCreateRequest",
    "ProjectUpdateRequest",
    "ProjectListResponse",
    "EpisodeDTO",
    "EpisodeCreateRequest",
    "EpisodeUpdateRequest",
    # Project aliases (backward compatibility)
    "ProjectResponseDTO",
    "ProjectCreateDTO",
    "ProjectUpdateDTO",
    "EpisodeResponseDTO",
    "EpisodeCreateDTO",
    "EpisodeUpdateDTO",
    # Generation schemas
    "AIModelConfigDTO",
    "RAGConfigDTO",
    "GenerationRequestDTO",
    "GenerationMetadataDTO",
    "GenerationResponseDTO",
    # SSE Event Types
    "BaseSSEEvent",
    "ProgressEventData",
    "PreviewEventData",
    "CompletedEventData",
    "CompletionResult",
    "FailedEventData",
    "SSEErrorInfo",
    "HeartbeatEventData",
    # Job Management
    "GenerationJobStatus",
    "GenerationJobRequest",
    "GenerationJobResponse",
    "GenerationJobDetails",
    # API Response Types
    "GenerationStartResponse",
    "GenerationStatusResponse",
    "GenerationListResponse",
    "GenerationStatsResponse",
    # Connection Types
    "SSEConnectionState",
    "SSEConnectionStatus",
    # Union Types
    "SSEEventData",
]
