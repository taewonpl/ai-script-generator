"""
RAG management API endpoints with Core Module integration
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status

from generation_service.config_loader import settings
from generation_service.models.rag_models import (
    ContextBuildRequestDTO,
    RAGMetricsDTO,
    RAGSearchRequestDTO,
    RAGSearchResponseDTO,
)
from generation_service.models.vector_document import (
    DocumentBatch,
    DocumentDeleteRequest,
)
from generation_service.rag import RAGService
from generation_service.rag.rag_service import (
    DocumentAddRequest as RAGDocumentAddRequest,
)
from generation_service.rag.rag_service import (
    RAGSearchRequest,
)

# Import Core Module components
try:
    from ai_script_core import (
        BaseServiceException,
        CommonResponseDTO,
        ErrorResponseDTO,
        ExternalServiceError,
        SuccessResponseDTO,
        ValidationException,
        exception_handler,
        get_service_logger,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.api.rag")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)

router = APIRouter()

# Global RAG service instance
_rag_service_instance = None


def get_rag_service() -> RAGService:
    """Dependency to get RAG service instance"""
    global _rag_service_instance
    if _rag_service_instance is None:
        # Initialize RAG service with configuration
        rag_config = settings.get_rag_configuration()
        _rag_service_instance = RAGService(
            db_path=rag_config["chroma_db_path"],
            collection_name=rag_config["collection_name"],
            openai_api_key=settings.OPENAI_API_KEY,
            embedding_model=rag_config["embedding_model"],
            max_context_tokens=rag_config["max_context_length"],
        )
    return _rag_service_instance


@router.post(
    "/add-documents",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Add Documents to RAG System",
    description="Add documents to the vector store for retrieval",
)
async def add_documents(
    request: DocumentBatch,
    http_request: Request,
    rag_service: RAGService = Depends(get_rag_service),
) -> Dict[str, Any]:
    """Add documents to the RAG system"""

    try:
        # Convert to RAG service format
        documents = [doc.content for doc in request.documents]
        metadatas = [doc.metadata.dict() for doc in request.documents]
        document_ids = [doc.document_id for doc in request.documents]

        # Determine project_id and document_type from first document
        first_doc = request.documents[0]
        project_id = first_doc.metadata.project_id
        document_type = first_doc.metadata.document_type.value

        add_request = RAGDocumentAddRequest(
            documents=documents,
            metadatas=metadatas,
            document_ids=document_ids,
            project_id=project_id,
            document_type=document_type,
        )

        result = await rag_service.add_documents(add_request)

        if CORE_AVAILABLE:
            logger.info(
                "Documents added via API",
                extra={
                    "batch_id": request.batch_id,
                    "document_count": len(request.documents),
                    "project_id": project_id,
                    "document_type": document_type,
                },
            )

        return {
            "success": True,
            "message": f"Successfully added {result['documents_added']} documents",
            "batch_id": request.batch_id,
            "document_ids": result["document_ids"],
            "processing_time": result["add_time"],
        }

    except ValidationException as e:
        logger.warning(f"Validation error adding documents: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict()
            )
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except BaseServiceException as e:
        logger.error(f"Service error adding documents: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
    except Exception as e:
        logger.error(f"Unexpected error adding documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add documents: {e!s}",
        )


@router.post(
    "/search",
    response_model=RAGSearchResponseDTO,
    summary="Search Documents",
    description="Search for relevant documents and build context",
)
async def search_documents(
    request: RAGSearchRequestDTO,
    http_request: Request,
    rag_service: RAGService = Depends(get_rag_service),
) -> RAGSearchResponseDTO:
    """Search documents and build context"""

    try:
        # Convert to RAG service format
        from generation_service.rag.context_builder import ContextType
        from generation_service.rag.retriever import SearchType

        # Map search strategies
        search_type_mapping = {
            "semantic_only": SearchType.SEMANTIC,
            "keyword_only": SearchType.KEYWORD,
            "hybrid": SearchType.HYBRID,
            "metadata_filter": SearchType.METADATA_FILTER,
        }

        context_type_mapping = {
            "narrative": ContextType.STORY_BIBLE,
            "bullet_points": ContextType.CHARACTER_PROFILES,
            "structured": ContextType.MIXED,
            "dialogue_focused": ContextType.CHARACTER_PROFILES,
            "technical": ContextType.WORLD_BUILDING,
        }

        search_request = RAGSearchRequest(
            query=request.query,
            project_id=request.project_id,
            search_type=search_type_mapping.get(
                request.search_strategy.value, SearchType.HYBRID
            ),
            context_type=context_type_mapping.get(
                request.context_template.value, ContextType.MIXED
            ),
            max_results=request.max_results,
            max_context_tokens=request.max_context_tokens,
            similarity_threshold=request.similarity_threshold,
            document_type_filter=(
                request.document_types[0].value if request.document_types else None
            ),
        )

        response = await rag_service.search_and_build_context(search_request)

        # Convert to API response format
        search_results = []
        for result in response.search_results:
            from generation_service.models.rag_models import RAGSearchResultDTO
            from generation_service.models.vector_document import (
                DocumentImportance,
                DocumentType,
            )

            search_result = RAGSearchResultDTO(
                document_id=result["document_id"],
                content=result["content"],
                title=result["metadata"].get("title"),
                summary=result["metadata"].get("summary"),
                similarity_score=result["similarity_score"],
                relevance_rank=result["rank"],
                document_type=DocumentType(
                    result["metadata"].get("document_type", "general")
                ),
                importance=DocumentImportance(
                    result["metadata"].get("importance", "medium")
                ),
                project_id=result["metadata"].get("project_id"),
                tags=result["metadata"].get("tags", []),
                metadata=result["metadata"],
            )
            search_results.append(search_result)

        api_response = RAGSearchResponseDTO(
            results=search_results,
            context=response.context,
            query=request.query,
            search_strategy=request.search_strategy,
            total_results=len(search_results),
            search_time_ms=int(response.search_time * 1000),
            context_build_time_ms=int(response.build_time * 1000),
            total_time_ms=int(response.total_time * 1000),
            context_tokens=response.total_tokens,
            embedding_tokens=0,  # Could be tracked in future
        )

        if CORE_AVAILABLE:
            logger.info(
                "RAG search completed via API",
                extra={
                    "query_length": len(request.query),
                    "search_strategy": request.search_strategy.value,
                    "results_found": len(search_results),
                    "context_tokens": response.total_tokens,
                    "total_time_ms": int(response.total_time * 1000),
                },
            )

        return api_response

    except ValidationException as e:
        logger.warning(f"Validation error in search: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict()
            )
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except BaseServiceException as e:
        logger.error(f"Service error in search: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
    except Exception as e:
        logger.error(f"Unexpected error in search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {e!s}",
        )


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Document",
    description="Delete a document from the RAG system",
)
async def delete_document(
    document_id: str, rag_service: RAGService = Depends(get_rag_service)
) -> None:
    """Delete a document from the RAG system"""

    try:
        await rag_service.delete_documents([document_id])

        if CORE_AVAILABLE:
            logger.info("Document deleted via API", extra={"document_id": document_id})

    except BaseServiceException as e:
        logger.error(f"Service error deleting document: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
    except Exception as e:
        logger.error(f"Unexpected error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {e!s}",
        )


@router.delete(
    "/documents",
    response_model=dict[str, Any],
    summary="Bulk Delete Documents",
    description="Delete multiple documents from the RAG system",
)
async def bulk_delete_documents(
    request: DocumentDeleteRequest, rag_service: RAGService = Depends(get_rag_service)
) -> Dict[str, Any]:
    """Bulk delete documents from the RAG system"""

    try:
        result = await rag_service.delete_documents(request.document_ids)

        if CORE_AVAILABLE:
            logger.info(
                "Bulk document deletion via API",
                extra={
                    "deleted_count": result["deleted_count"],
                    "document_ids": request.document_ids[:5],  # Log first 5
                },
            )

        return {
            "success": True,
            "message": f"Successfully deleted {result['deleted_count']} documents",
            "deleted_count": result["deleted_count"],
        }

    except BaseServiceException as e:
        logger.error(f"Service error in bulk delete: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
    except Exception as e:
        logger.error(f"Unexpected error in bulk delete: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete documents: {e!s}",
        )


@router.get(
    "/collections",
    response_model=dict[str, Any],
    summary="Get Collection Information",
    description="Get information about RAG collections",
)
async def get_collections(rag_service: RAGService = Depends(get_rag_service)) -> Dict[str, Any]:
    """Get collection information"""

    try:
        stats = await rag_service.get_collection_stats()

        return {
            "success": True,
            "collections": [
                {
                    "name": stats["collection_stats"]["collection_name"],
                    "document_count": stats["collection_stats"]["document_count"],
                    "service_id": stats["service_id"],
                    "created_at": stats["collection_stats"].get("created_at"),
                    "last_updated": stats["collection_stats"].get("last_checked"),
                }
            ],
            "service_metrics": stats["service_metrics"],
            "component_health": {
                "embedding_service": stats["embedding_metrics"],
                "retriever": stats["retriever_metrics"],
                "context_builder": stats["builder_metrics"],
            },
        }

    except Exception as e:
        logger.error(f"Error getting collections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collections: {e!s}",
        )


@router.post(
    "/build-context",
    response_model=dict[str, Any],
    summary="Build Context",
    description="Build context from search results",
)
async def build_context(
    request: ContextBuildRequestDTO, rag_service: RAGService = Depends(get_rag_service)
) -> Dict[str, Any]:
    """Build context from provided search results"""

    try:
        # This endpoint allows building context from pre-existing search results
        # Convert the DTO format to internal format for context building
        from generation_service.rag.context_builder import (
            ContextBuildRequest,
            ContextType,
        )
        from generation_service.rag.retriever import SearchResult

        # Convert search results
        search_results = []
        for result_dto in request.search_results:
            search_result = SearchResult(
                document_id=result_dto.document_id,
                content=result_dto.content,
                metadata=result_dto.metadata,
                similarity_score=result_dto.similarity_score,
                rank=result_dto.relevance_rank,
            )
            search_results.append(search_result)

        # Map context template to context type
        context_type_mapping = {
            "narrative": ContextType.STORY_BIBLE,
            "bullet_points": ContextType.CHARACTER_PROFILES,
            "structured": ContextType.MIXED,
            "dialogue_focused": ContextType.CHARACTER_PROFILES,
            "technical": ContextType.WORLD_BUILDING,
        }

        context_request = ContextBuildRequest(
            search_results=search_results,
            context_type=context_type_mapping.get(
                request.context_template.value, ContextType.MIXED
            ),
            max_context_tokens=request.max_tokens,
            include_metadata=request.include_metadata,
            prioritize_recent=request.prioritize_recent,
            remove_duplicates=request.remove_duplicates,
            project_id=request.project_id,
        )

        # Build context using the context builder
        context_response = await rag_service.context_builder.build_context(
            context_request
        )

        if CORE_AVAILABLE:
            logger.info(
                "Context built via API",
                extra={
                    "input_results": len(request.search_results),
                    "output_sections": len(context_response.sections),
                    "context_tokens": context_response.total_tokens,
                    "build_time_seconds": context_response.build_time,
                },
            )

        return {
            "success": True,
            "context": context_response.formatted_context,
            "sections": [
                {
                    "title": section.title,
                    "content": section.content,
                    "document_type": section.document_type,
                    "relevance_score": section.relevance_score,
                    "token_count": section.token_count,
                }
                for section in context_response.sections
            ],
            "total_tokens": context_response.total_tokens,
            "build_time_seconds": context_response.build_time,
            "context_type": context_response.context_type.value,
        }

    except ValidationException as e:
        logger.warning(f"Validation error building context: {e}")
        if CORE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict()
            )
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error building context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build context: {e!s}",
        )


@router.get(
    "/metrics",
    response_model=dict[str, Any],
    summary="Get RAG Metrics",
    description="Get comprehensive RAG system metrics",
)
async def get_rag_metrics(rag_service: RAGService = Depends(get_rag_service)) -> Dict[str, Any]:
    """Get RAG system metrics"""

    try:
        # Get comprehensive metrics
        stats = await rag_service.get_collection_stats()
        service_metrics = rag_service.get_service_metrics()

        metrics = RAGMetricsDTO(
            total_searches=stats["service_metrics"]["total_searches"],
            total_documents=stats["collection_stats"]["document_count"],
            total_tokens_processed=stats["service_metrics"]["total_tokens_generated"],
            avg_search_time_ms=stats["service_metrics"]["avg_search_time"] * 1000,
            avg_context_build_time_ms=stats["service_metrics"]["avg_context_build_time"]
            * 1000,
            avg_results_per_search=stats["retriever_metrics"]["avg_results_returned"],
            avg_similarity_score=0.75,  # Could be calculated from actual data
            cache_hit_rate=stats["embedding_metrics"]["cache_hit_rate"],
            estimated_embedding_cost=stats["embedding_metrics"]["total_cost"],
            tokens_per_dollar=stats["embedding_metrics"]["total_tokens"]
            / max(stats["embedding_metrics"]["total_cost"], 0.001),
        )

        return {
            "success": True,
            "metrics": metrics.dict(),
            "detailed_stats": stats,
            "health_status": "healthy",  # Could be enhanced with actual health checks
        }

    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {e!s}",
        )


@router.post(
    "/health",
    response_model=dict[str, Any],
    summary="RAG Health Check",
    description="Perform comprehensive health check on RAG system",
)
async def health_check(rag_service: RAGService = Depends(get_rag_service)) -> Dict[str, Any]:
    """Perform health check on RAG system"""

    try:
        health_status = await rag_service.health_check()

        return {
            "success": health_status["status"] == "healthy",
            "health_status": health_status,
            "timestamp": health_status.get("checked_at"),
            "service_id": health_status["service_id"],
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "health_status": {"status": "unhealthy", "error": str(e)},
            "timestamp": None,
            "service_id": None,
        }


@router.post(
    "/reset",
    response_model=dict[str, Any],
    summary="Reset RAG Collection",
    description="Reset the entire RAG collection (WARNING: This deletes all data)",
)
async def reset_collection(rag_service: RAGService = Depends(get_rag_service)) -> Dict[str, Any]:
    """Reset the RAG collection"""

    try:
        result = await rag_service.reset_collection()

        if CORE_AVAILABLE:
            logger.warning(
                "RAG collection reset via API",
                extra={
                    "service_id": result["service_id"],
                    "collection_name": result["collection_name"],
                },
            )

        return {
            "success": True,
            "message": "RAG collection has been reset",
            "result": result,
        }

    except Exception as e:
        logger.error(f"Error resetting collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset collection: {e!s}",
        )
