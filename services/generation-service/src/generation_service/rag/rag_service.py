"""
RAG Service - Unified interface for Retrieval Augmented Generation
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Import Core Module components
try:
    from ai_script_core import (
        BaseServiceException,
        ExternalServiceError,
        ValidationException,
        generate_uuid,
        get_service_logger,
        safe_json_dumps,
        safe_json_loads,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.rag_service")
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


from .chroma_store import ChromaStore, ChromaStoreError
from .context_builder import (
    ContextBuilder,
    ContextBuildError,
    ContextBuildRequest,
    ContextType,
)
from .embeddings import EmbeddingService
from .retriever import DocumentRetriever, RetrievalError, SearchRequest, SearchType


@dataclass
class DocumentAddRequest:
    """Request for adding documents to RAG system"""

    documents: list[str]
    metadatas: Optional[list[dict[str, Any]]] = None
    document_ids: Optional[list[str]] = None
    project_id: Optional[str] = None
    document_type: str = "general"

    def __post_init__(self) -> None:
        if CORE_AVAILABLE and not hasattr(self, "request_id"):
            self.request_id = generate_uuid()


@dataclass
class RAGSearchRequest:
    """Unified RAG search and context building request"""

    query: str
    project_id: Optional[str] = None
    search_type: SearchType = SearchType.SEMANTIC
    context_type: ContextType = ContextType.MIXED
    max_results: int = 10
    max_context_tokens: int = 8000
    similarity_threshold: float = 0.7
    include_metadata: bool = True
    document_type_filter: Optional[str] = None

    def __post_init__(self) -> None:
        if CORE_AVAILABLE and not hasattr(self, "request_id"):
            self.request_id = generate_uuid()


@dataclass
class RAGResponse:
    """Response from RAG system with context and metadata"""

    context: str
    search_results: list[dict[str, Any]]
    total_tokens: int
    search_time: float
    build_time: float
    total_time: float
    request_id: Optional[str] = None

    def __post_init__(self) -> None:
        if CORE_AVAILABLE and self.request_id is None:
            self.request_id = generate_uuid()


class RAGServiceError(Exception):
    """Base exception for RAG service operations"""

    def __init__(self, message: str, operation: str = "rag_operation", **kwargs: Any):
        super().__init__(message)
        self.operation = operation
        self.kwargs = kwargs


if CORE_AVAILABLE:

    class RAGServiceError(BaseServiceException):
        """RAG service error using Core exception"""

        def __init__(self, message: str, operation: str = "rag_operation", **kwargs):
            super().__init__(
                message=message, error_code=f"RAG_{operation.upper()}_ERROR", **kwargs
            )


class RAGService:
    """Unified RAG service with Core Module integration"""

    def __init__(
        self,
        db_path: str = "./data/chroma",
        collection_name: str = "script_knowledge",
        openai_api_key: Optional[str] = None,
        embedding_model: str = "text-embedding-ada-002",
        max_context_tokens: int = 8000,
    ):
        # Initialize components
        self.db_path = db_path
        self.collection_name = collection_name
        self.max_context_tokens = max_context_tokens

        # Create data directory if it doesn't exist
        Path(db_path).mkdir(parents=True, exist_ok=True)

        # Core Module integration
        if CORE_AVAILABLE:
            self.service_id = generate_uuid()
            self.created_at = utc_now()
            logger.info(
                "RAG service initializing with Core integration",
                extra={
                    "service_id": self.service_id,
                    "db_path": db_path,
                    "collection_name": collection_name,
                    "embedding_model": embedding_model,
                },
            )
        else:
            self.service_id = f"rag_{hash(db_path + collection_name)}"
            self.created_at = datetime.now()
            logger.info("RAG service initializing")

        try:
            # Initialize ChromaDB store
            self.chroma_store = ChromaStore(
                db_path=db_path, collection_name=collection_name
            )

            # Initialize embedding service
            self.embedding_service = EmbeddingService(
                api_key=openai_api_key, model=embedding_model
            )

            # Initialize document retriever
            self.retriever = DocumentRetriever(chroma_store=self.chroma_store)

            # Initialize context builder
            self.context_builder = ContextBuilder(default_max_tokens=max_context_tokens)

            # Service metrics
            self._service_metrics = {
                "total_documents_added": 0,
                "total_searches": 0,
                "total_contexts_built": 0,
                "avg_search_time": 0.0,
                "avg_context_build_time": 0.0,
                "total_tokens_generated": 0,
            }

            if CORE_AVAILABLE:
                logger.info(
                    "RAG service initialized successfully",
                    extra={
                        "service_id": self.service_id,
                        "components": [
                            "chroma_store",
                            "embedding_service",
                            "retriever",
                            "context_builder",
                        ],
                    },
                )
            else:
                logger.info("RAG service initialized successfully")

        except Exception as e:
            error_msg = f"Failed to initialize RAG service: {e!s}"
            logger.error(error_msg)
            raise RAGServiceError(error_msg, operation="initialization")

    async def add_documents(self, request: DocumentAddRequest) -> dict[str, Any]:
        """Add documents to the RAG system"""

        if not request.documents:
            raise RAGServiceError("No documents provided", operation="add_documents")

        start_time = utc_now() if CORE_AVAILABLE else datetime.now()

        try:
            # Prepare metadata
            enhanced_metadatas = []
            if request.metadatas:
                enhanced_metadatas = request.metadatas.copy()
            else:
                enhanced_metadatas = [{} for _ in request.documents]

            # Enhance metadata with common fields
            for i, metadata in enumerate(enhanced_metadatas):
                enhanced_metadata = metadata.copy()
                enhanced_metadata.update(
                    {
                        "document_type": request.document_type,
                        "added_by": "rag_service",
                        "service_id": self.service_id,
                    }
                )

                if request.project_id:
                    enhanced_metadata["project_id"] = request.project_id

                if CORE_AVAILABLE:
                    enhanced_metadata["added_at"] = utc_now().isoformat()
                else:
                    enhanced_metadata["added_at"] = datetime.now().isoformat()

                enhanced_metadatas[i] = enhanced_metadata

            # Add documents to ChromaDB
            document_ids = self.chroma_store.add_documents(
                documents=request.documents,
                metadatas=enhanced_metadatas,
                ids=request.document_ids,
            )

            # Update metrics
            self._service_metrics["total_documents_added"] += len(request.documents)

            add_time = (
                (utc_now() - start_time).total_seconds()
                if CORE_AVAILABLE
                else (datetime.now() - start_time).total_seconds()
            )

            if CORE_AVAILABLE:
                logger.info(
                    "Documents added to RAG system",
                    extra={
                        "service_id": self.service_id,
                        "document_count": len(request.documents),
                        "document_type": request.document_type,
                        "project_id": request.project_id,
                        "add_time_seconds": add_time,
                        "request_id": getattr(request, "request_id", None),
                    },
                )

            return {
                "document_ids": document_ids,
                "documents_added": len(request.documents),
                "add_time": add_time,
                "request_id": getattr(request, "request_id", None),
            }

        except ChromaStoreError as e:
            error_msg = f"Failed to add documents to ChromaDB: {e!s}"
            logger.error(error_msg)
            raise RAGServiceError(error_msg, operation="add_documents")
        except Exception as e:
            error_msg = f"Failed to add documents: {e!s}"
            logger.error(error_msg)
            raise RAGServiceError(error_msg, operation="add_documents")

    async def search_and_build_context(self, request: RAGSearchRequest) -> RAGResponse:
        """Search for relevant documents and build context"""

        total_start_time = utc_now() if CORE_AVAILABLE else datetime.now()

        try:
            # Build search request
            search_request = SearchRequest(
                query=request.query,
                search_type=request.search_type,
                max_results=request.max_results,
                similarity_threshold=request.similarity_threshold,
                metadata_filters=self._build_project_filter(
                    request.project_id, request.document_type_filter
                ),
                include_metadata=request.include_metadata,
                project_id=request.project_id,
                document_type=request.document_type_filter,
            )

            # Perform search
            search_start = utc_now() if CORE_AVAILABLE else datetime.now()
            search_response = await self.retriever.search(search_request)
            search_time = (
                (utc_now() - search_start).total_seconds()
                if CORE_AVAILABLE
                else (datetime.now() - search_start).total_seconds()
            )

            # Build context if results found
            context = ""
            build_time = 0.0

            if search_response.results:
                # Build context request
                context_request = ContextBuildRequest(
                    search_results=search_response.results,
                    context_type=request.context_type,
                    max_context_tokens=request.max_context_tokens,
                    include_metadata=request.include_metadata,
                    project_id=request.project_id,
                )

                # Build context
                build_start = utc_now() if CORE_AVAILABLE else datetime.now()
                context_response = await self.context_builder.build_context(
                    context_request
                )
                build_time = (
                    (utc_now() - build_start).total_seconds()
                    if CORE_AVAILABLE
                    else (datetime.now() - build_start).total_seconds()
                )

                context = context_response.formatted_context
                total_tokens = context_response.total_tokens
            else:
                total_tokens = 0

            # Calculate total time
            total_time = (
                (utc_now() - total_start_time).total_seconds()
                if CORE_AVAILABLE
                else (datetime.now() - total_start_time).total_seconds()
            )

            # Update metrics
            self._update_service_metrics(search_time, build_time, total_tokens)

            # Prepare search results for response
            search_results_data = [
                {
                    "document_id": result.document_id,
                    "content": (
                        result.content[:500] + "..."
                        if len(result.content) > 500
                        else result.content
                    ),
                    "similarity_score": result.similarity_score,
                    "rank": result.rank,
                    "metadata": result.metadata if request.include_metadata else {},
                }
                for result in search_response.results
            ]

            if CORE_AVAILABLE:
                logger.info(
                    "RAG search and context build completed",
                    extra={
                        "service_id": self.service_id,
                        "query_length": len(request.query),
                        "search_type": request.search_type.value,
                        "context_type": request.context_type.value,
                        "results_found": len(search_response.results),
                        "context_tokens": total_tokens,
                        "search_time_seconds": search_time,
                        "build_time_seconds": build_time,
                        "total_time_seconds": total_time,
                        "request_id": getattr(request, "request_id", None),
                    },
                )

            return RAGResponse(
                context=context,
                search_results=search_results_data,
                total_tokens=total_tokens,
                search_time=search_time,
                build_time=build_time,
                total_time=total_time,
                request_id=getattr(request, "request_id", None),
            )

        except (RetrievalError, ContextBuildError) as e:
            error_msg = f"RAG operation failed: {e!s}"
            logger.error(error_msg)
            raise RAGServiceError(error_msg, operation="search_and_build")
        except Exception as e:
            error_msg = f"Unexpected error in RAG operation: {e!s}"
            logger.error(error_msg)
            raise RAGServiceError(error_msg, operation="search_and_build")

    def _build_project_filter(
        self, project_id: Optional[str], document_type: Optional[str]
    ) -> Optional[dict[str, Any]]:
        """Build metadata filter for project and document type"""

        filters = []

        if project_id:
            filters.append({"project_id": {"$eq": project_id}})

        if document_type:
            filters.append({"document_type": {"$eq": document_type}})

        if len(filters) == 0:
            return None
        elif len(filters) == 1:
            return filters[0]
        else:
            return {"$and": filters}

    def _update_service_metrics(
        self, search_time: float, build_time: float, tokens: int
    ):
        """Update service-level metrics"""

        self._service_metrics["total_searches"] += 1
        self._service_metrics["total_contexts_built"] += 1
        self._service_metrics["total_tokens_generated"] += tokens

        # Update averages
        total_searches = self._service_metrics["total_searches"]
        self._service_metrics["avg_search_time"] = (
            self._service_metrics["avg_search_time"] * (total_searches - 1)
            + search_time
        ) / total_searches

        total_contexts = self._service_metrics["total_contexts_built"]
        self._service_metrics["avg_context_build_time"] = (
            self._service_metrics["avg_context_build_time"] * (total_contexts - 1)
            + build_time
        ) / total_contexts

    async def delete_documents(self, document_ids: list[str]) -> dict[str, Any]:
        """Delete documents from the RAG system"""

        try:
            self.chroma_store.delete_documents(document_ids)

            if CORE_AVAILABLE:
                logger.info(
                    "Documents deleted from RAG system",
                    extra={
                        "service_id": self.service_id,
                        "deleted_count": len(document_ids),
                        "document_ids": document_ids[:5],  # Log first 5 IDs
                    },
                )

            return {"deleted_count": len(document_ids), "document_ids": document_ids}

        except ChromaStoreError as e:
            error_msg = f"Failed to delete documents: {e!s}"
            logger.error(error_msg)
            raise RAGServiceError(error_msg, operation="delete_documents")

    async def update_documents(
        self,
        document_ids: list[str],
        documents: Optional[list[str]] = None,
        metadatas: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Update existing documents in the RAG system"""

        try:
            # Enhance metadata with update information
            if metadatas:
                enhanced_metadatas = []
                for metadata in metadatas:
                    enhanced_metadata = metadata.copy()
                    if CORE_AVAILABLE:
                        enhanced_metadata["updated_at"] = utc_now().isoformat()
                    else:
                        enhanced_metadata["updated_at"] = datetime.now().isoformat()
                    enhanced_metadata["updated_by"] = self.service_id
                    enhanced_metadatas.append(enhanced_metadata)
            else:
                enhanced_metadatas = metadatas

            self.chroma_store.update_documents(
                ids=document_ids, documents=documents, metadatas=enhanced_metadatas
            )

            if CORE_AVAILABLE:
                logger.info(
                    "Documents updated in RAG system",
                    extra={
                        "service_id": self.service_id,
                        "updated_count": len(document_ids),
                        "document_ids": document_ids[:5],  # Log first 5 IDs
                    },
                )

            return {"updated_count": len(document_ids), "document_ids": document_ids}

        except ChromaStoreError as e:
            error_msg = f"Failed to update documents: {e!s}"
            logger.error(error_msg)
            raise RAGServiceError(error_msg, operation="update_documents")

    async def get_collection_stats(self) -> dict[str, Any]:
        """Get RAG system statistics"""

        try:
            # Get ChromaDB stats
            chroma_stats = self.chroma_store.get_collection_stats()

            # Get component metrics
            embedding_metrics = self.embedding_service.get_metrics()
            retriever_metrics = self.retriever.get_search_metrics()
            builder_metrics = self.context_builder.get_build_metrics()

            # Combine all stats
            stats = {
                "service_id": self.service_id,
                "collection_stats": chroma_stats,
                "service_metrics": self._service_metrics,
                "embedding_metrics": embedding_metrics,
                "retriever_metrics": retriever_metrics,
                "builder_metrics": builder_metrics,
            }

            if CORE_AVAILABLE:
                stats.update(
                    {
                        "created_at": self.created_at.isoformat(),
                        "last_updated": utc_now().isoformat(),
                    }
                )

            return stats

        except Exception as e:
            error_msg = f"Failed to get collection stats: {e!s}"
            logger.error(error_msg)
            raise RAGServiceError(error_msg, operation="get_stats")

    async def reset_collection(self) -> dict[str, Any]:
        """Reset the entire RAG collection"""

        try:
            self.chroma_store.reset_collection()

            # Reset service metrics
            self._service_metrics = {
                "total_documents_added": 0,
                "total_searches": 0,
                "total_contexts_built": 0,
                "avg_search_time": 0.0,
                "avg_context_build_time": 0.0,
                "total_tokens_generated": 0,
            }

            if CORE_AVAILABLE:
                logger.warning(
                    "RAG collection reset",
                    extra={
                        "service_id": self.service_id,
                        "collection_name": self.collection_name,
                    },
                )

            return {
                "status": "collection_reset",
                "service_id": self.service_id,
                "collection_name": self.collection_name,
            }

        except ChromaStoreError as e:
            error_msg = f"Failed to reset collection: {e!s}"
            logger.error(error_msg)
            raise RAGServiceError(error_msg, operation="reset_collection")

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check on RAG system"""

        try:
            # Test all components
            health_checks = await asyncio.gather(
                self.chroma_store.health_check(),
                self.embedding_service.health_check(),
                self.retriever.health_check(),
                self.context_builder.health_check(),
                return_exceptions=True,
            )

            # Analyze results
            component_status = {
                "chroma_store": (
                    health_checks[0]
                    if not isinstance(health_checks[0], Exception)
                    else {"status": "unhealthy", "error": str(health_checks[0])}
                ),
                "embedding_service": (
                    health_checks[1]
                    if not isinstance(health_checks[1], Exception)
                    else {"status": "unhealthy", "error": str(health_checks[1])}
                ),
                "retriever": (
                    health_checks[2]
                    if not isinstance(health_checks[2], Exception)
                    else {"status": "unhealthy", "error": str(health_checks[2])}
                ),
                "context_builder": (
                    health_checks[3]
                    if not isinstance(health_checks[3], Exception)
                    else {"status": "unhealthy", "error": str(health_checks[3])}
                ),
            }

            # Determine overall status
            all_healthy = all(
                component.get("status") == "healthy"
                for component in component_status.values()
            )

            overall_status = {
                "status": "healthy" if all_healthy else "unhealthy",
                "service_id": self.service_id,
                "components": component_status,
                "metrics": await self.get_collection_stats(),
            }

            if CORE_AVAILABLE:
                overall_status["checked_at"] = utc_now().isoformat()

            return overall_status

        except Exception as e:
            error_msg = f"Health check failed: {e!s}"
            logger.error(error_msg)
            return {
                "status": "unhealthy",
                "service_id": self.service_id,
                "error": error_msg,
            }

    async def search_for_architect_context(
        self,
        title: str,
        description: str,
        script_type: str,
        project_id: Optional[str] = None,
    ) -> str:
        """Specialized method for Architect node context retrieval"""

        # Construct search query from generation request
        query_parts = []
        if title:
            query_parts.append(f"Title: {title}")
        if description:
            query_parts.append(f"Description: {description}")
        if script_type:
            query_parts.append(f"Type: {script_type}")

        search_query = " ".join(query_parts)

        # Create RAG search request optimized for architecture
        request = RAGSearchRequest(
            query=search_query,
            project_id=project_id,
            search_type=SearchType.HYBRID,
            context_type=ContextType.STORY_BIBLE,
            max_results=15,  # More results for comprehensive context
            max_context_tokens=6000,  # Reserve space for generation prompt
            similarity_threshold=0.6,  # Lower threshold for broader context
            document_type_filter=None,  # Include all document types
        )

        try:
            # Execute RAG search and context building
            response = await self.search_and_build_context(request)

            if CORE_AVAILABLE:
                logger.info(
                    "Architect context retrieved",
                    extra={
                        "service_id": self.service_id,
                        "project_id": project_id,
                        "query_length": len(search_query),
                        "context_tokens": response.total_tokens,
                        "results_found": len(response.search_results),
                        "total_time_seconds": response.total_time,
                    },
                )

            return response.context

        except RAGServiceError:
            # Log error but don't fail the generation
            logger.warning(
                "Failed to retrieve architect context, proceeding without RAG"
            )
            return ""

    def get_service_metrics(self) -> dict[str, Any]:
        """Get comprehensive service metrics"""

        metrics = self._service_metrics.copy()

        if CORE_AVAILABLE:
            metrics.update(
                {
                    "service_id": self.service_id,
                    "created_at": self.created_at.isoformat(),
                    "last_updated": utc_now().isoformat(),
                    "db_path": self.db_path,
                    "collection_name": self.collection_name,
                }
            )
        else:
            metrics.update(
                {
                    "service_id": self.service_id,
                    "created_at": self.created_at.isoformat(),
                    "db_path": self.db_path,
                    "collection_name": self.collection_name,
                }
            )

        return metrics
