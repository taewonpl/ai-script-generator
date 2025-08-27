"""
RAG-specific models with Core Module integration
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

# Import Core Module components
try:
    from ai_script_core import (
        BaseDTO,
        ErrorResponseDTO,
        SuccessResponseDTO,
        generate_uuid,
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.rag_models")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)

    # Fallback utility functions
    def utc_now() -> datetime:
        """Fallback UTC timestamp"""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)

    def generate_uuid() -> str:
        """Fallback UUID generation"""
        import uuid

        return str(uuid.uuid4())

    def generate_id() -> str:
        """Fallback ID generation"""
        import uuid

        return str(uuid.uuid4())[:8]

    # Fallback base classes
    class BaseDTO:
        """Fallback base DTO class"""

        pass

    class SuccessResponseDTO:
        """Fallback success response DTO"""

        pass

    class ErrorResponseDTO:
        """Fallback error response DTO"""

        pass


from .vector_document import DocumentImportance, DocumentType


class SearchStrategy(str, Enum):
    """Search strategies for RAG operations"""

    SEMANTIC_ONLY = "semantic_only"
    KEYWORD_ONLY = "keyword_only"
    HYBRID = "hybrid"
    METADATA_FILTER = "metadata_filter"
    CONTEXTUAL = "contextual"


class ContextTemplate(str, Enum):
    """Context formatting templates"""

    NARRATIVE = "narrative"
    BULLET_POINTS = "bullet_points"
    STRUCTURED = "structured"
    DIALOGUE_FOCUSED = "dialogue_focused"
    TECHNICAL = "technical"


if CORE_AVAILABLE:
    # Use Core Module DTOs when available
    class RAGConfigDTO(BaseDTO):
        """RAG system configuration using Core DTO pattern"""

        # Database settings
        chroma_db_path: str = Field(
            default="/app/data/chroma", description="ChromaDB storage path"
        )
        collection_name: str = Field(
            default="script_knowledge", description="ChromaDB collection name"
        )

        # Embedding settings
        embedding_model: str = Field(
            default="text-embedding-ada-002", description="OpenAI embedding model"
        )
        embedding_batch_size: int = Field(
            default=100,
            ge=1,
            le=1000,
            description="Batch size for embedding generation",
        )
        max_embedding_retries: int = Field(
            default=3, ge=1, le=10, description="Maximum embedding retry attempts"
        )

        # Search settings
        default_search_strategy: SearchStrategy = Field(
            default=SearchStrategy.HYBRID, description="Default search strategy"
        )
        max_search_results: int = Field(
            default=10, ge=1, le=100, description="Maximum search results to return"
        )
        similarity_threshold: float = Field(
            default=0.7, ge=0.0, le=1.0, description="Minimum similarity threshold"
        )

        # Context settings
        max_context_length: int = Field(
            default=8000,
            ge=100,
            le=50000,
            description="Maximum context length in tokens",
        )
        context_overlap_ratio: float = Field(
            default=0.1,
            ge=0.0,
            le=0.5,
            description="Context overlap ratio for chunking",
        )
        default_context_template: ContextTemplate = Field(
            default=ContextTemplate.STRUCTURED, description="Default context template"
        )

        # Performance settings
        enable_caching: bool = Field(
            default=True, description="Enable embedding caching"
        )
        cache_ttl_hours: int = Field(
            default=24, ge=1, le=168, description="Cache TTL in hours"
        )
        max_concurrent_requests: int = Field(
            default=10, ge=1, le=100, description="Maximum concurrent requests"
        )

        class Config:
            use_enum_values = True

    class RAGSearchRequestDTO(BaseDTO):
        """RAG search request using Core DTO pattern"""

        # Core search parameters
        query: str = Field(
            ..., min_length=1, max_length=5000, description="Search query"
        )
        search_strategy: SearchStrategy = Field(
            default=SearchStrategy.HYBRID, description="Search strategy to use"
        )
        max_results: int = Field(
            default=10, ge=1, le=100, description="Maximum results to return"
        )
        similarity_threshold: float = Field(
            default=0.7, ge=0.0, le=1.0, description="Similarity threshold"
        )

        # Context parameters
        max_context_tokens: int = Field(
            default=8000, ge=100, le=50000, description="Maximum context tokens"
        )
        context_template: ContextTemplate = Field(
            default=ContextTemplate.STRUCTURED, description="Context template"
        )
        include_metadata: bool = Field(
            default=True, description="Include document metadata"
        )

        # Filtering parameters
        project_id: Optional[str] = Field(None, description="Filter by project ID")
        episode_id: Optional[str] = Field(None, description="Filter by episode ID")
        document_types: Optional[list[DocumentType]] = Field(
            None, description="Filter by document types"
        )
        importance_levels: Optional[list[DocumentImportance]] = Field(
            None, description="Filter by importance levels"
        )
        tags: Optional[list[str]] = Field(None, description="Filter by tags")
        character_names: Optional[list[str]] = Field(
            None, description="Filter by character names"
        )

        # Advanced parameters
        boost_recent: bool = Field(default=True, description="Boost recent documents")
        diversify_results: bool = Field(
            default=True, description="Diversify search results"
        )
        custom_weights: Optional[dict[str, float]] = Field(
            None, description="Custom scoring weights"
        )

        @field_validator("query")
        @classmethod
        def validate_query(cls, v: Any) -> str:
            if not v or not v.strip():
                raise ValueError("Query cannot be empty")
            return v.strip()

        class Config:
            use_enum_values = True

    class RAGSearchResultDTO(BaseDTO):
        """Individual RAG search result using Core DTO pattern"""

        document_id: str = Field(..., description="Document identifier")
        content: str = Field(..., description="Document content")
        title: Optional[str] = Field(None, description="Document title")
        summary: Optional[str] = Field(None, description="Document summary")

        # Relevance metrics
        similarity_score: float = Field(
            ..., ge=0.0, le=1.0, description="Similarity score"
        )
        relevance_rank: int = Field(..., ge=1, description="Relevance ranking")
        context_score: float = Field(
            default=0.0, ge=0.0, le=1.0, description="Context relevance score"
        )

        # Document metadata
        document_type: DocumentType = Field(..., description="Type of document")
        importance: DocumentImportance = Field(..., description="Document importance")
        project_id: Optional[str] = Field(None, description="Associated project")
        tags: list[str] = Field(default_factory=list, description="Document tags")

        # Additional metadata
        metadata: dict[str, Any] = Field(
            default_factory=dict, description="Additional metadata"
        )

        class Config:
            use_enum_values = True

    class RAGSearchResponseDTO(SuccessResponseDTO):
        """RAG search response using Core DTO pattern"""

        # Search results
        results: list[RAGSearchResultDTO] = Field(..., description="Search results")
        context: str = Field(..., description="Formatted context")

        # Search metadata
        query: str = Field(..., description="Original search query")
        search_strategy: SearchStrategy = Field(..., description="Search strategy used")
        total_results: int = Field(..., ge=0, description="Total number of results")

        # Performance metrics
        search_time_ms: int = Field(
            ..., ge=0, description="Search time in milliseconds"
        )
        context_build_time_ms: int = Field(
            ..., ge=0, description="Context build time in milliseconds"
        )
        total_time_ms: int = Field(
            ..., ge=0, description="Total processing time in milliseconds"
        )

        # Token usage
        context_tokens: int = Field(..., ge=0, description="Context token count")
        embedding_tokens: int = Field(
            default=0, ge=0, description="Embedding tokens used"
        )

        class Config:
            use_enum_values = True

    class ContextBuildRequestDTO(BaseDTO):
        """Context build request using Core DTO pattern"""

        # Input data
        search_results: list[RAGSearchResultDTO] = Field(
            ..., description="Search results to build context from"
        )
        context_template: ContextTemplate = Field(
            default=ContextTemplate.STRUCTURED, description="Context template"
        )
        max_tokens: int = Field(
            default=8000, ge=100, le=50000, description="Maximum context tokens"
        )

        # Formatting options
        include_metadata: bool = Field(
            default=True, description="Include document metadata"
        )
        include_sources: bool = Field(
            default=True, description="Include source references"
        )
        prioritize_recent: bool = Field(
            default=True, description="Prioritize recent documents"
        )
        remove_duplicates: bool = Field(
            default=True, description="Remove duplicate content"
        )

        # Project context
        project_id: Optional[str] = Field(None, description="Project context")
        generation_type: Optional[str] = Field(
            None, description="Type of generation (script, dialogue, etc.)"
        )

        @field_validator("search_results")
        @classmethod
        def validate_search_results(cls, v: Any) -> Any:
            if not v:
                raise ValueError("Must provide at least one search result")
            return v

        class Config:
            use_enum_values = True

else:
    # Fallback implementations without Core module
    class RAGConfigDTO(BaseModel):
        """RAG system configuration fallback implementation"""

        # Database settings
        chroma_db_path: str = Field(
            default="/app/data/chroma", description="ChromaDB storage path"
        )
        collection_name: str = Field(
            default="script_knowledge", description="ChromaDB collection name"
        )

        # Embedding settings
        embedding_model: str = Field(
            default="text-embedding-ada-002", description="OpenAI embedding model"
        )
        embedding_batch_size: int = Field(
            default=100,
            ge=1,
            le=1000,
            description="Batch size for embedding generation",
        )
        max_embedding_retries: int = Field(
            default=3, ge=1, le=10, description="Maximum embedding retry attempts"
        )

        # Search settings
        default_search_strategy: SearchStrategy = Field(
            default=SearchStrategy.HYBRID, description="Default search strategy"
        )
        max_search_results: int = Field(
            default=10, ge=1, le=100, description="Maximum search results to return"
        )
        similarity_threshold: float = Field(
            default=0.7, ge=0.0, le=1.0, description="Minimum similarity threshold"
        )

        # Context settings
        max_context_length: int = Field(
            default=8000,
            ge=100,
            le=50000,
            description="Maximum context length in tokens",
        )
        context_overlap_ratio: float = Field(
            default=0.1,
            ge=0.0,
            le=0.5,
            description="Context overlap ratio for chunking",
        )
        default_context_template: ContextTemplate = Field(
            default=ContextTemplate.STRUCTURED, description="Default context template"
        )

        # Performance settings
        enable_caching: bool = Field(
            default=True, description="Enable embedding caching"
        )
        cache_ttl_hours: int = Field(
            default=24, ge=1, le=168, description="Cache TTL in hours"
        )
        max_concurrent_requests: int = Field(
            default=10, ge=1, le=100, description="Maximum concurrent requests"
        )

        class Config:
            use_enum_values = True

    class RAGSearchRequestDTO(BaseModel):
        """RAG search request fallback implementation"""

        # Core search parameters
        query: str = Field(
            ..., min_length=1, max_length=5000, description="Search query"
        )
        search_strategy: SearchStrategy = Field(
            default=SearchStrategy.HYBRID, description="Search strategy to use"
        )
        max_results: int = Field(
            default=10, ge=1, le=100, description="Maximum results to return"
        )
        similarity_threshold: float = Field(
            default=0.7, ge=0.0, le=1.0, description="Similarity threshold"
        )

        # Context parameters
        max_context_tokens: int = Field(
            default=8000, ge=100, le=50000, description="Maximum context tokens"
        )
        context_template: ContextTemplate = Field(
            default=ContextTemplate.STRUCTURED, description="Context template"
        )
        include_metadata: bool = Field(
            default=True, description="Include document metadata"
        )

        # Filtering parameters
        project_id: Optional[str] = Field(None, description="Filter by project ID")
        episode_id: Optional[str] = Field(None, description="Filter by episode ID")
        document_types: Optional[list[DocumentType]] = Field(
            None, description="Filter by document types"
        )
        importance_levels: Optional[list[DocumentImportance]] = Field(
            None, description="Filter by importance levels"
        )
        tags: Optional[list[str]] = Field(None, description="Filter by tags")
        character_names: Optional[list[str]] = Field(
            None, description="Filter by character names"
        )

        # Advanced parameters
        boost_recent: bool = Field(default=True, description="Boost recent documents")
        diversify_results: bool = Field(
            default=True, description="Diversify search results"
        )
        custom_weights: Optional[dict[str, float]] = Field(
            None, description="Custom scoring weights"
        )

        @field_validator("query")
        @classmethod
        def validate_query(cls, v: Any) -> str:
            if not v or not v.strip():
                raise ValueError("Query cannot be empty")
            return v.strip()

        class Config:
            use_enum_values = True

    class RAGSearchResultDTO(BaseModel):
        """Individual RAG search result fallback implementation"""

        document_id: str = Field(..., description="Document identifier")
        content: str = Field(..., description="Document content")
        title: Optional[str] = Field(None, description="Document title")
        summary: Optional[str] = Field(None, description="Document summary")

        # Relevance metrics
        similarity_score: float = Field(
            ..., ge=0.0, le=1.0, description="Similarity score"
        )
        relevance_rank: int = Field(..., ge=1, description="Relevance ranking")
        context_score: float = Field(
            default=0.0, ge=0.0, le=1.0, description="Context relevance score"
        )

        # Document metadata
        document_type: DocumentType = Field(..., description="Type of document")
        importance: DocumentImportance = Field(..., description="Document importance")
        project_id: Optional[str] = Field(None, description="Associated project")
        tags: list[str] = Field(default_factory=list, description="Document tags")

        # Additional metadata
        metadata: dict[str, Any] = Field(
            default_factory=dict, description="Additional metadata"
        )

        class Config:
            use_enum_values = True

    class RAGSearchResponseDTO(BaseModel):
        """RAG search response fallback implementation"""

        # Success/error status
        success: bool = Field(default=True, description="Operation success status")
        message: str = Field(default="Success", description="Response message")

        # Search results
        results: list[RAGSearchResultDTO] = Field(..., description="Search results")
        context: str = Field(..., description="Formatted context")

        # Search metadata
        query: str = Field(..., description="Original search query")
        search_strategy: SearchStrategy = Field(..., description="Search strategy used")
        total_results: int = Field(..., ge=0, description="Total number of results")

        # Performance metrics
        search_time_ms: int = Field(
            ..., ge=0, description="Search time in milliseconds"
        )
        context_build_time_ms: int = Field(
            ..., ge=0, description="Context build time in milliseconds"
        )
        total_time_ms: int = Field(
            ..., ge=0, description="Total processing time in milliseconds"
        )

        # Token usage
        context_tokens: int = Field(..., ge=0, description="Context token count")
        embedding_tokens: int = Field(
            default=0, ge=0, description="Embedding tokens used"
        )

        class Config:
            use_enum_values = True

    class ContextBuildRequestDTO(BaseModel):
        """Context build request fallback implementation"""

        # Input data
        search_results: list[RAGSearchResultDTO] = Field(
            ..., description="Search results to build context from"
        )
        context_template: ContextTemplate = Field(
            default=ContextTemplate.STRUCTURED, description="Context template"
        )
        max_tokens: int = Field(
            default=8000, ge=100, le=50000, description="Maximum context tokens"
        )

        # Formatting options
        include_metadata: bool = Field(
            default=True, description="Include document metadata"
        )
        include_sources: bool = Field(
            default=True, description="Include source references"
        )
        prioritize_recent: bool = Field(
            default=True, description="Prioritize recent documents"
        )
        remove_duplicates: bool = Field(
            default=True, description="Remove duplicate content"
        )

        # Project context
        project_id: Optional[str] = Field(None, description="Project context")
        generation_type: Optional[str] = Field(
            None, description="Type of generation (script, dialogue, etc.)"
        )

        @field_validator("search_results")
        @classmethod
        def validate_search_results(cls, v: Any) -> Any:
            if not v:
                raise ValueError("Must provide at least one search result")
            return v

        class Config:
            use_enum_values = True


class RAGMetricsDTO(BaseModel):
    """RAG system performance metrics"""

    # Usage statistics
    total_searches: int = Field(
        default=0, ge=0, description="Total number of searches performed"
    )
    total_documents: int = Field(
        default=0, ge=0, description="Total documents in the system"
    )
    total_tokens_processed: int = Field(
        default=0, ge=0, description="Total tokens processed"
    )

    # Performance metrics
    avg_search_time_ms: float = Field(
        default=0.0, ge=0.0, description="Average search time in milliseconds"
    )
    avg_context_build_time_ms: float = Field(
        default=0.0, ge=0.0, description="Average context build time in milliseconds"
    )
    avg_results_per_search: float = Field(
        default=0.0, ge=0.0, description="Average results per search"
    )

    # Quality metrics
    avg_similarity_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Average similarity score"
    )
    cache_hit_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Cache hit rate"
    )

    # System health
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Last metrics update"
    )
    system_status: str = Field(default="healthy", description="System health status")

    # Cost tracking
    estimated_embedding_cost: float = Field(
        default=0.0, ge=0.0, description="Estimated embedding API cost"
    )
    tokens_per_dollar: float = Field(
        default=0.0, ge=0.0, description="Cost efficiency metric"
    )


class RAGBulkOperationDTO(BaseModel):
    """Bulk operation request for RAG system"""

    operation_type: str = Field(
        ..., description="Type of bulk operation (add, update, delete)"
    )
    document_ids: Optional[list[str]] = Field(
        None, description="Document IDs for bulk operations"
    )
    batch_size: int = Field(
        default=100, ge=1, le=1000, description="Batch size for processing"
    )
    parallel_workers: int = Field(
        default=5, ge=1, le=20, description="Number of parallel workers"
    )

    # Operation-specific data
    documents: Optional[list[dict[str, Any]]] = Field(
        None, description="Documents for bulk add/update"
    )
    metadata_updates: Optional[dict[str, Any]] = Field(
        None, description="Metadata updates for bulk operations"
    )

    # Processing options
    continue_on_error: bool = Field(
        default=True, description="Continue processing on individual errors"
    )
    validate_before_processing: bool = Field(
        default=True, description="Validate data before processing"
    )

    @field_validator("operation_type")
    @classmethod
    def validate_operation_type(cls, v: Any) -> str:
        allowed_operations = ["add", "update", "delete", "reindex", "migrate"]
        if v not in allowed_operations:
            raise ValueError(f"Operation type must be one of: {allowed_operations}")
        return v


# Utility functions for model creation
def create_search_request(
    query: str,
    project_id: Optional[str] = None,
    search_strategy: SearchStrategy = SearchStrategy.HYBRID,
    **kwargs,
) -> RAGSearchRequestDTO:
    """Create a RAG search request with sensible defaults"""

    return RAGSearchRequestDTO(
        query=query, project_id=project_id, search_strategy=search_strategy, **kwargs
    )


def create_rag_config(
    db_path: str = "./data/chroma", collection_name: str = "script_knowledge", **kwargs
) -> RAGConfigDTO:
    """Create RAG configuration with sensible defaults"""

    return RAGConfigDTO(
        chroma_db_path=db_path, collection_name=collection_name, **kwargs
    )
