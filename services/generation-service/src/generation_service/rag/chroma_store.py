"""
ChromaDB vector store implementation with Core Module integration
"""

import logging
import os
from datetime import datetime
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Import Core Module components
try:
    from ai_script_core import (
        BaseServiceException,
        ExternalServiceError,
        ValidationException,
        calculate_hash,
        generate_uuid,
        get_service_logger,
        safe_json_dumps,
        safe_json_loads,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.chroma_store")
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


class ChromaStoreError(Exception):
    """Base exception for ChromaDB store operations"""

    def __init__(
        self, message: str, operation: str = "chroma_operation", **kwargs: Any
    ):
        super().__init__(message)
        self.operation = operation
        self.kwargs = kwargs


if CORE_AVAILABLE:

    class ChromaStoreError(ExternalServiceError):
        """ChromaDB store error using Core exception"""

        def __init__(self, message: str, operation: str = "chroma_operation", **kwargs):
            super().__init__(
                service_name="chromadb",
                operation=operation,
                response_body=message,
                **kwargs,
            )


class ChromaStore:
    """ChromaDB vector store with Core Module integration"""

    def __init__(
        self,
        db_path: str = "./data/chroma",
        collection_name: str = "script_knowledge",
        embedding_function: Any | None = None,
    ):
        if not CHROMADB_AVAILABLE:
            raise ChromaStoreError(
                "ChromaDB is not available. Install with: pip install chromadb"
            )

        self.db_path = db_path
        self.collection_name = collection_name
        self._client = None
        self._collection = None

        # Core Module integration
        if CORE_AVAILABLE:
            self.store_id = generate_uuid()
            self.created_at = utc_now()
            logger.info(
                "ChromaDB store initialized with Core integration",
                extra={
                    "store_id": self.store_id,
                    "db_path": db_path,
                    "collection_name": collection_name,
                },
            )
        else:
            self.store_id = f"chroma_{hash(db_path + collection_name)}"
            self.created_at = datetime.now()
            logger.info(f"ChromaDB store initialized: {collection_name}")

        # Initialize embedding function
        self.embedding_function = (
            embedding_function
            or embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.getenv("OPENAI_API_KEY"), model_name="text-embedding-ada-002"
            )
        )

        # Initialize client
        self._initialize_client()

    def _initialize_client(self):
        """Initialize ChromaDB client"""
        try:
            # Ensure directory exists
            os.makedirs(self.db_path, exist_ok=True)

            # Initialize client with persistent storage
            self._client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )

            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"created_by": "generation_service"},
            )

            if CORE_AVAILABLE:
                logger.info(
                    "ChromaDB client initialized successfully",
                    extra={
                        "store_id": self.store_id,
                        "collection_name": self.collection_name,
                        "collection_count": self._collection.count(),
                    },
                )
            else:
                logger.info(f"ChromaDB client initialized: {self.collection_name}")

        except Exception as e:
            error_msg = f"Failed to initialize ChromaDB client: {e!s}"
            logger.error(error_msg)
            raise ChromaStoreError(error_msg, operation="client_initialization")

    def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> list[str]:
        """Add documents to the vector store"""

        if not documents:
            raise ChromaStoreError("No documents provided", operation="add_documents")

        try:
            # Generate IDs if not provided
            if ids is None:
                if CORE_AVAILABLE:
                    ids = [generate_uuid() for _ in documents]
                else:
                    ids = [f"doc_{hash(doc)}" for doc in documents]

            # Enhance metadata with Core information
            if metadatas is None:
                metadatas = [{} for _ in documents]

            enhanced_metadatas = []
            for i, metadata in enumerate(metadatas):
                enhanced_metadata = metadata.copy()
                if CORE_AVAILABLE:
                    enhanced_metadata.update(
                        {
                            "added_at": utc_now().isoformat(),
                            "store_id": self.store_id,
                            "document_hash": calculate_hash(documents[i]),
                        }
                    )
                else:
                    enhanced_metadata.update(
                        {
                            "added_at": datetime.now().isoformat(),
                            "store_id": self.store_id,
                        }
                    )
                enhanced_metadatas.append(enhanced_metadata)

            # Add to collection
            self._collection.add(
                documents=documents, metadatas=enhanced_metadatas, ids=ids
            )

            if CORE_AVAILABLE:
                logger.info(
                    f"Added {len(documents)} documents to ChromaDB",
                    extra={
                        "store_id": self.store_id,
                        "collection_name": self.collection_name,
                        "document_count": len(documents),
                        "document_ids": ids[:5],  # Log first 5 IDs
                    },
                )
            else:
                logger.info(
                    f"Added {len(documents)} documents to {self.collection_name}"
                )

            return ids

        except Exception as e:
            error_msg = f"Failed to add documents: {e!s}"
            logger.error(error_msg)
            raise ChromaStoreError(error_msg, operation="add_documents")

    def search(
        self,
        query_texts: str | list[str],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        where_document: dict[str, Any] | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        """Search for similar documents"""

        if isinstance(query_texts, str):
            query_texts = [query_texts]

        try:
            start_time = utc_now() if CORE_AVAILABLE else datetime.now()

            # Set default includes
            if include is None:
                include = ["documents", "metadatas", "distances"]

            # Perform search
            results = self._collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=include,
            )

            search_time = (
                (utc_now() - start_time).total_seconds()
                if CORE_AVAILABLE
                else (datetime.now() - start_time).total_seconds()
            )

            # Log search metrics
            if CORE_AVAILABLE:
                logger.info(
                    "ChromaDB search completed",
                    extra={
                        "store_id": self.store_id,
                        "query_count": len(query_texts),
                        "results_per_query": n_results,
                        "search_time_seconds": search_time,
                        "total_results": (
                            len(results.get("ids", [[]])[0])
                            if results.get("ids")
                            else 0
                        ),
                    },
                )

            return results

        except Exception as e:
            error_msg = f"Search failed: {e!s}"
            logger.error(error_msg)
            raise ChromaStoreError(error_msg, operation="search")

    def get_documents(
        self,
        ids: list[str] | None = None,
        where: dict[str, Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get documents by IDs or filter criteria"""

        try:
            if include is None:
                include = ["documents", "metadatas"]

            results = self._collection.get(
                ids=ids, where=where, limit=limit, offset=offset, include=include
            )

            if CORE_AVAILABLE:
                logger.debug(
                    "Retrieved documents from ChromaDB",
                    extra={
                        "store_id": self.store_id,
                        "requested_ids": len(ids) if ids else "all",
                        "returned_count": len(results.get("ids", [])),
                    },
                )

            return results

        except Exception as e:
            error_msg = f"Failed to get documents: {e!s}"
            logger.error(error_msg)
            raise ChromaStoreError(error_msg, operation="get_documents")

    def update_documents(
        self,
        ids: list[str],
        documents: list[str] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Update existing documents"""

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
                    enhanced_metadatas.append(enhanced_metadata)
            else:
                enhanced_metadatas = metadatas

            self._collection.update(
                ids=ids, documents=documents, metadatas=enhanced_metadatas
            )

            if CORE_AVAILABLE:
                logger.info(
                    f"Updated {len(ids)} documents in ChromaDB",
                    extra={
                        "store_id": self.store_id,
                        "updated_ids": ids[:5],  # Log first 5 IDs
                    },
                )
            else:
                logger.info(f"Updated {len(ids)} documents")

        except Exception as e:
            error_msg = f"Failed to update documents: {e!s}"
            logger.error(error_msg)
            raise ChromaStoreError(error_msg, operation="update_documents")

    def delete_documents(self, ids: list[str]) -> None:
        """Delete documents by IDs"""

        try:
            self._collection.delete(ids=ids)

            if CORE_AVAILABLE:
                logger.info(
                    f"Deleted {len(ids)} documents from ChromaDB",
                    extra={
                        "store_id": self.store_id,
                        "deleted_ids": ids[:5],  # Log first 5 IDs
                    },
                )
            else:
                logger.info(f"Deleted {len(ids)} documents")

        except Exception as e:
            error_msg = f"Failed to delete documents: {e!s}"
            logger.error(error_msg)
            raise ChromaStoreError(error_msg, operation="delete_documents")

    def get_collection_stats(self) -> dict[str, Any]:
        """Get collection statistics"""

        try:
            count = self._collection.count()

            stats = {
                "collection_name": self.collection_name,
                "document_count": count,
                "store_id": self.store_id,
                "db_path": self.db_path,
            }

            if CORE_AVAILABLE:
                stats.update(
                    {
                        "created_at": self.created_at.isoformat(),
                        "last_checked": utc_now().isoformat(),
                    }
                )
            else:
                stats.update(
                    {
                        "created_at": self.created_at.isoformat(),
                        "last_checked": datetime.now().isoformat(),
                    }
                )

            return stats

        except Exception as e:
            error_msg = f"Failed to get collection stats: {e!s}"
            logger.error(error_msg)
            raise ChromaStoreError(error_msg, operation="get_stats")

    def reset_collection(self) -> None:
        """Reset the collection (delete all documents)"""

        try:
            self._client.delete_collection(self.collection_name)
            self._collection = self._client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"created_by": "generation_service", "reset": True},
            )

            if CORE_AVAILABLE:
                logger.warning(
                    "ChromaDB collection reset",
                    extra={
                        "store_id": self.store_id,
                        "collection_name": self.collection_name,
                    },
                )
            else:
                logger.warning(f"Collection {self.collection_name} reset")

        except Exception as e:
            error_msg = f"Failed to reset collection: {e!s}"
            logger.error(error_msg)
            raise ChromaStoreError(error_msg, operation="reset_collection")

    def health_check(self) -> dict[str, Any]:
        """Perform health check on ChromaDB"""

        try:
            # Test basic operations
            test_doc = "Health check test document"
            test_id = "health_check_test"

            # Add test document
            self._collection.add(
                documents=[test_doc], ids=[test_id], metadatas=[{"test": True}]
            )

            # Search for test document
            results = self._collection.query(query_texts=[test_doc], n_results=1)

            # Clean up test document
            self._collection.delete(ids=[test_id])

            health_status = {
                "status": "healthy",
                "collection_name": self.collection_name,
                "document_count": self._collection.count(),
                "test_results": {
                    "add_document": True,
                    "search_document": len(results.get("ids", [[]])[0]) > 0,
                    "delete_document": True,
                },
            }

            if CORE_AVAILABLE:
                health_status["store_id"] = self.store_id
                health_status["checked_at"] = utc_now().isoformat()

            return health_status

        except Exception as e:
            error_msg = f"Health check failed: {e!s}"
            logger.error(error_msg)
            return {
                "status": "unhealthy",
                "error": error_msg,
                "collection_name": self.collection_name,
            }
