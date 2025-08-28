"""
Document retriever with semantic search and hybrid filtering
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

# Import Core Module components
try:
    from ai_script_core import (
        BaseServiceException,
        ValidationException,
        generate_uuid,
        get_service_logger,
        safe_json_dumps,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.retriever")
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


class SearchType(str, Enum):
    """Types of search operations"""

    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    METADATA_FILTER = "metadata_filter"


@dataclass
class SearchRequest:
    """Request for document search"""

    query: str
    search_type: SearchType = SearchType.SEMANTIC
    max_results: int = 10
    similarity_threshold: float = 0.7
    metadata_filters: Optional[dict[str, Any]] = None
    document_filters: Optional[dict[str, Any]] = None
    include_metadata: bool = True
    include_distances: bool = True
    project_id: Optional[str] = None
    document_type: Optional[str] = None

    def __post_init__(self):
        if CORE_AVAILABLE and not hasattr(self, "request_id"):
            self.request_id = generate_uuid()


@dataclass
class SearchResult:
    """Individual search result"""

    document_id: str
    content: str
    metadata: dict[str, Any]
    similarity_score: float
    rank: int

    def __post_init__(self):
        # Ensure similarity score is in [0, 1] range
        self.similarity_score = max(0.0, min(1.0, self.similarity_score))


@dataclass
class SearchResponse:
    """Response from document search"""

    results: list[SearchResult]
    query: str
    search_type: SearchType
    total_results: int
    search_time: float
    request_id: Optional[str] = None

    def __post_init__(self):
        if CORE_AVAILABLE and self.request_id is None:
            self.request_id = generate_uuid()


class RetrievalError(Exception):
    """Base exception for retrieval operations"""

    pass


if CORE_AVAILABLE:

    class RetrievalError(ValidationException):
        """Retrieval error using Core exception"""

        def __init__(self, message: str, field: str = "search_query", **kwargs):
            super().__init__(message, field=field, **kwargs)


class DocumentRetriever:
    """Document retriever with semantic search and hybrid filtering"""

    def __init__(
        self,
        chroma_store: ChromaStore,
        default_similarity_threshold: float = 0.7,
        max_results_limit: int = 100,
        enable_keyword_boost: bool = True,
    ):
        self.chroma_store = chroma_store
        self.default_similarity_threshold = default_similarity_threshold
        self.max_results_limit = max_results_limit
        self.enable_keyword_boost = enable_keyword_boost

        # Core Module integration
        if CORE_AVAILABLE:
            self.retriever_id = generate_uuid()
            self.created_at = utc_now()
            logger.info(
                "Document retriever initialized with Core integration",
                extra={
                    "retriever_id": self.retriever_id,
                    "similarity_threshold": default_similarity_threshold,
                    "max_results_limit": max_results_limit,
                },
            )
        else:
            self.retriever_id = f"retriever_{hash(str(default_similarity_threshold))}"
            self.created_at = datetime.now()
            logger.info("Document retriever initialized")

        # Search metrics
        self._search_metrics = {
            "total_searches": 0,
            "semantic_searches": 0,
            "keyword_searches": 0,
            "hybrid_searches": 0,
            "avg_search_time": 0.0,
            "avg_results_returned": 0.0,
        }

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Perform document search based on request type"""

        start_time = utc_now() if CORE_AVAILABLE else datetime.now()

        # Validate request
        self._validate_search_request(request)

        try:
            # Execute search based on type
            if request.search_type == SearchType.SEMANTIC:
                results = await self._semantic_search(request)
            elif request.search_type == SearchType.KEYWORD:
                results = await self._keyword_search(request)
            elif request.search_type == SearchType.HYBRID:
                results = await self._hybrid_search(request)
            elif request.search_type == SearchType.METADATA_FILTER:
                results = await self._metadata_filter_search(request)
            else:
                raise RetrievalError(f"Unknown search type: {request.search_type}")

            # Calculate search time
            search_time = (
                (utc_now() - start_time).total_seconds()
                if CORE_AVAILABLE
                else (datetime.now() - start_time).total_seconds()
            )

            # Update metrics
            self._update_search_metrics(request.search_type, search_time, len(results))

            # Log search completion
            if CORE_AVAILABLE:
                logger.info(
                    "Document search completed",
                    extra={
                        "retriever_id": self.retriever_id,
                        "search_type": request.search_type.value,
                        "query_length": len(request.query),
                        "results_count": len(results),
                        "search_time_seconds": search_time,
                        "similarity_threshold": request.similarity_threshold,
                    },
                )

            return SearchResponse(
                results=results,
                query=request.query,
                search_type=request.search_type,
                total_results=len(results),
                search_time=search_time,
                request_id=getattr(request, "request_id", None),
            )

        except ChromaStoreError as e:
            error_msg = f"ChromaDB search failed: {e!s}"
            logger.error(error_msg)
            raise RetrievalError(error_msg) from e
        except Exception as e:
            error_msg = f"Search failed: {e!s}"
            logger.error(error_msg)
            raise RetrievalError(error_msg) from e

    def _validate_search_request(self, request: SearchRequest) -> None:
        """Validate search request parameters"""

        if not request.query or not request.query.strip():
            raise RetrievalError("Search query cannot be empty", field="query") from e

        if request.max_results <= 0:
            raise RetrievalError("max_results must be positive", field="max_results")

        if request.max_results > self.max_results_limit:
            raise RetrievalError(
                f"max_results exceeds limit of {self.max_results_limit}",
                field="max_results",
            )

        if not 0.0 <= request.similarity_threshold <= 1.0:
            raise RetrievalError(
                "similarity_threshold must be between 0.0 and 1.0",
                field="similarity_threshold",
            )

    async def _semantic_search(self, request: SearchRequest) -> list[SearchResult]:
        """Perform semantic similarity search"""

        # Build ChromaDB query parameters
        where_filter = self._build_metadata_filter(request)
        where_document = self._build_document_filter(request)

        include_params = ["documents", "metadatas", "distances"]

        # Execute search
        chroma_results = self.chroma_store.search(
            query_texts=[request.query],
            n_results=request.max_results,
            where=where_filter,
            where_document=where_document,
            include=include_params,
        )

        # Process results
        return self._process_chroma_results(
            chroma_results, request.similarity_threshold
        )

    async def _keyword_search(self, request: SearchRequest) -> list[SearchResult]:
        """Perform keyword-based search using document filters"""

        # Extract keywords from query
        keywords = self._extract_keywords(request.query)

        # Build keyword-based document filter
        keyword_filter = (
            {"$or": [{"$contains": keyword} for keyword in keywords]}
            if keywords
            else None
        )

        # Combine with user-provided document filters
        where_document = self._combine_document_filters(
            keyword_filter, request.document_filters
        )
        where_filter = self._build_metadata_filter(request)

        # Get documents using filters (this will return all matching docs)
        chroma_results = self.chroma_store.get_documents(
            where=where_filter,
            limit=request.max_results,
            include=["documents", "metadatas"],
        )

        # Convert to search results with keyword-based scoring
        return self._process_keyword_results(chroma_results, keywords, request.query)

    async def _hybrid_search(self, request: SearchRequest) -> list[SearchResult]:
        """Perform hybrid search combining semantic and keyword approaches"""

        # Get semantic results
        semantic_request = SearchRequest(
            query=request.query,
            search_type=SearchType.SEMANTIC,
            max_results=request.max_results * 2,  # Get more for merging
            similarity_threshold=request.similarity_threshold
            * 0.8,  # Lower threshold for combining
            metadata_filters=request.metadata_filters,
            document_filters=request.document_filters,
            project_id=request.project_id,
            document_type=request.document_type,
        )
        semantic_results = await self._semantic_search(semantic_request)

        # Get keyword results
        keyword_request = SearchRequest(
            query=request.query,
            search_type=SearchType.KEYWORD,
            max_results=request.max_results * 2,  # Get more for merging
            metadata_filters=request.metadata_filters,
            document_filters=request.document_filters,
            project_id=request.project_id,
            document_type=request.document_type,
        )
        keyword_results = await self._keyword_search(keyword_request)

        # Merge and rank results
        merged_results = self._merge_search_results(
            semantic_results, keyword_results, request.query, request.max_results
        )

        return merged_results

    async def _metadata_filter_search(
        self, request: SearchRequest
    ) -> list[SearchResult]:
        """Perform search based primarily on metadata filters"""

        where_filter = self._build_metadata_filter(request)

        if not where_filter:
            raise RetrievalError(
                "Metadata filters required for metadata_filter search",
                field="metadata_filters",
            )

        # Get documents using metadata filters
        chroma_results = self.chroma_store.get_documents(
            where=where_filter,
            limit=request.max_results,
            include=["documents", "metadatas"],
        )

        # Convert to search results with metadata-based scoring
        return self._process_metadata_results(chroma_results, request.query)

    def _build_metadata_filter(
        self, request: SearchRequest
    ) -> Optional[dict[str, Any]]:
        """Build metadata filter for ChromaDB"""

        filters = []

        # Add user-provided metadata filters
        if request.metadata_filters:
            filters.append(request.metadata_filters)

        # Add project filter
        if request.project_id:
            filters.append({"project_id": {"$eq": request.project_id}})

        # Add document type filter
        if request.document_type:
            filters.append({"document_type": {"$eq": request.document_type}})

        # Combine filters with AND logic
        if len(filters) == 0:
            return None
        elif len(filters) == 1:
            return filters[0]
        else:
            return {"$and": filters}

    def _build_document_filter(
        self, request: SearchRequest
    ) -> Optional[dict[str, Any]]:
        """Build document content filter for ChromaDB"""

        return request.document_filters

    def _combine_document_filters(
        self, filter1: Optional[dict[str, Any]], filter2: Optional[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        """Combine two document filters with AND logic"""

        if not filter1 and not filter2:
            return None
        elif filter1 and not filter2:
            return filter1
        elif filter2 and not filter1:
            return filter2
        else:
            return {"$and": [filter1, filter2]}

    def _extract_keywords(self, query: str) -> list[str]:
        """Extract meaningful keywords from query"""

        # Simple keyword extraction (can be enhanced with NLP)
        # Remove stop words and extract meaningful terms
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "what",
            "where",
            "when",
            "how",
            "why",
            "who",
        }

        # Extract words (alphanumeric sequences)
        words = re.findall(r"\b\w+\b", query.lower())

        # Filter out stop words and short words
        keywords = [word for word in words if word not in stop_words and len(word) > 2]

        return keywords

    def _process_chroma_results(
        self, chroma_results: dict[str, Any], similarity_threshold: float
    ) -> list[SearchResult]:
        """Process ChromaDB semantic search results"""

        results = []

        if not chroma_results.get("ids") or not chroma_results["ids"][0]:
            return results

        ids = chroma_results["ids"][0]
        documents = chroma_results.get("documents", [[]])[0]
        metadatas = chroma_results.get("metadatas", [[]])[0]
        distances = chroma_results.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            # Convert distance to similarity score (distance is 0-2, similarity is 1-0)
            distance = distances[i] if i < len(distances) else 1.0
            similarity_score = max(0.0, 1.0 - (distance / 2.0))

            # Apply similarity threshold
            if similarity_score >= similarity_threshold:
                result = SearchResult(
                    document_id=doc_id,
                    content=documents[i] if i < len(documents) else "",
                    metadata=metadatas[i] if i < len(metadatas) else {},
                    similarity_score=similarity_score,
                    rank=i + 1,
                )
                results.append(result)

        return results

    def _process_keyword_results(
        self, chroma_results: dict[str, Any], keywords: list[str], original_query: str
    ) -> list[SearchResult]:
        """Process keyword search results"""

        results = []

        if not chroma_results.get("ids"):
            return results

        ids = chroma_results["ids"]
        documents = chroma_results.get("documents", [])
        metadatas = chroma_results.get("metadatas", [])

        for i, doc_id in enumerate(ids):
            document = documents[i] if i < len(documents) else ""
            metadata = metadatas[i] if i < len(metadatas) else {}

            # Calculate keyword-based similarity score
            score = self._calculate_keyword_score(document, keywords, original_query)

            result = SearchResult(
                document_id=doc_id,
                content=document,
                metadata=metadata,
                similarity_score=score,
                rank=i + 1,
            )
            results.append(result)

        # Sort by similarity score
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Update ranks
        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def _process_metadata_results(
        self, chroma_results: dict[str, Any], query: str
    ) -> list[SearchResult]:
        """Process metadata filter search results"""

        results = []

        if not chroma_results.get("ids"):
            return results

        ids = chroma_results["ids"]
        documents = chroma_results.get("documents", [])
        metadatas = chroma_results.get("metadatas", [])

        for i, doc_id in enumerate(ids):
            document = documents[i] if i < len(documents) else ""
            metadata = metadatas[i] if i < len(metadatas) else {}

            # Simple relevance scoring based on query terms in content
            score = self._calculate_content_relevance(document, query)

            result = SearchResult(
                document_id=doc_id,
                content=document,
                metadata=metadata,
                similarity_score=score,
                rank=i + 1,
            )
            results.append(result)

        # Sort by similarity score
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Update ranks
        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def _calculate_keyword_score(
        self, document: str, keywords: list[str], original_query: str
    ) -> float:
        """Calculate keyword-based similarity score"""

        if not keywords:
            return 0.0

        doc_lower = document.lower()
        total_score = 0.0

        # Score based on keyword presence and frequency
        for keyword in keywords:
            count = doc_lower.count(keyword.lower())
            if count > 0:
                # Base score for presence
                score = 0.5
                # Bonus for frequency (diminishing returns)
                frequency_bonus = min(count * 0.1, 0.4)
                total_score += score + frequency_bonus

        # Normalize by number of keywords
        normalized_score = total_score / len(keywords)

        # Bonus for exact phrase matches
        if original_query.lower() in doc_lower:
            normalized_score += 0.2

        return min(normalized_score, 1.0)

    def _calculate_content_relevance(self, document: str, query: str) -> float:
        """Calculate content relevance score"""

        if not query or not document:
            return 0.0

        doc_lower = document.lower()
        query_lower = query.lower()

        # Exact match bonus
        if query_lower in doc_lower:
            return 0.9

        # Word overlap score
        query_words = set(query_lower.split())
        doc_words = set(doc_lower.split())

        if not query_words:
            return 0.0

        overlap = len(query_words.intersection(doc_words))
        overlap_score = overlap / len(query_words)

        return min(overlap_score, 0.8)

    def _merge_search_results(
        self,
        semantic_results: list[SearchResult],
        keyword_results: list[SearchResult],
        query: str,
        max_results: int,
    ) -> list[SearchResult]:
        """Merge semantic and keyword search results"""

        # Combine results by document ID
        result_map = {}

        # Add semantic results with weight
        for result in semantic_results:
            result_map[result.document_id] = {
                "result": result,
                "semantic_score": result.similarity_score,
                "keyword_score": 0.0,
            }

        # Add/update with keyword results
        for result in keyword_results:
            if result.document_id in result_map:
                result_map[result.document_id][
                    "keyword_score"
                ] = result.similarity_score
            else:
                result_map[result.document_id] = {
                    "result": result,
                    "semantic_score": 0.0,
                    "keyword_score": result.similarity_score,
                }

        # Calculate hybrid scores
        merged_results = []
        for doc_id, data in result_map.items():
            result = data["result"]

            # Weighted combination (favor semantic slightly)
            semantic_weight = 0.6
            keyword_weight = 0.4

            hybrid_score = (
                semantic_weight * data["semantic_score"]
                + keyword_weight * data["keyword_score"]
            )

            # Create new result with hybrid score
            hybrid_result = SearchResult(
                document_id=result.document_id,
                content=result.content,
                metadata=result.metadata,
                similarity_score=hybrid_score,
                rank=0,  # Will be set after sorting
            )
            merged_results.append(hybrid_result)

        # Sort by hybrid score
        merged_results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Update ranks and limit results
        final_results = []
        for i, result in enumerate(merged_results[:max_results]):
            result.rank = i + 1
            final_results.append(result)

        return final_results

    def _update_search_metrics(
        self, search_type: SearchType, search_time: float, results_count: int
    ):
        """Update search metrics"""

        self._search_metrics["total_searches"] += 1

        if search_type == SearchType.SEMANTIC:
            self._search_metrics["semantic_searches"] += 1
        elif search_type == SearchType.KEYWORD:
            self._search_metrics["keyword_searches"] += 1
        elif search_type == SearchType.HYBRID:
            self._search_metrics["hybrid_searches"] += 1

        # Update averages
        total = self._search_metrics["total_searches"]
        self._search_metrics["avg_search_time"] = (
            self._search_metrics["avg_search_time"] * (total - 1) + search_time
        ) / total
        self._search_metrics["avg_results_returned"] = (
            self._search_metrics["avg_results_returned"] * (total - 1) + results_count
        ) / total

    def get_search_metrics(self) -> dict[str, Any]:
        """Get search performance metrics"""

        metrics = self._search_metrics.copy()

        if CORE_AVAILABLE:
            metrics.update(
                {
                    "retriever_id": self.retriever_id,
                    "created_at": self.created_at.isoformat(),
                    "last_updated": utc_now().isoformat(),
                }
            )
        else:
            metrics.update(
                {
                    "retriever_id": self.retriever_id,
                    "created_at": self.created_at.isoformat(),
                }
            )

        return metrics

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on retriever"""

        try:
            # Test basic search functionality
            test_request = SearchRequest(
                query="test query", search_type=SearchType.SEMANTIC, max_results=1
            )

            test_response = await self.search(test_request)

            health_status = {
                "status": "healthy",
                "retriever_id": self.retriever_id,
                "test_search_time": test_response.search_time,
                "metrics": self.get_search_metrics(),
            }

            if CORE_AVAILABLE:
                health_status["checked_at"] = utc_now().isoformat()

            return health_status

        except Exception as e:
            error_msg = f"Health check failed: {e!s}"
            logger.error(error_msg)
            return {
                "status": "unhealthy",
                "retriever_id": self.retriever_id,
                "error": error_msg,
            }
