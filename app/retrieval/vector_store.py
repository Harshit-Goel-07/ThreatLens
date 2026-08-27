"""
Qdrant vector store interface for Security Copilot
"""

import logging
from typing import List, Dict, Any, Optional, Union
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchText,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import settings

logger = logging.getLogger(__name__)

# Collection names for different data types
COLLECTIONS = {
    "mitre": "mitre_techniques",
    "cve": "cve_entries", 
    "logs": "security_logs",
    "playbooks": "soc_playbooks",
    "all": "all_documents"
}

class VectorStore:
    """Qdrant vector store wrapper for Security Copilot.

    The underlying client is created lazily on first use so that importing this
    module (e.g. during tests or by tooling) never opens a network connection.
    """

    def __init__(self):
        self._client: Optional[QdrantClient] = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            try:
                client = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=settings.qdrant_api_key,
                    timeout=3,
                )
                client.get_collections()
                self._client = client
                logger.info(f"Connected to Qdrant at {settings.qdrant_url}")
            except Exception as e:
                logger.warning(
                    f"Failed to connect to Qdrant at {settings.qdrant_url}: {e}. "
                    "Falling back to embedded in-memory Qdrant instance."
                )
                self._client = QdrantClient(location=":memory:")
        return self._client

    async def create_collection(self, collection_name: str, vector_size: int = 384) -> None:
        """Create a new collection in Qdrant"""
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            existing_names = [c.name for c in collections]
            
            if collection_name in existing_names:
                logger.info(f"Collection {collection_name} already exists")
                return
            
            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            # Full-text index on "content" so keyword (MatchText) search works.
            try:
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name="content",
                    field_schema=qdrant_models.TextIndexParams(
                        type="text",
                        tokenizer=qdrant_models.TokenizerType.WORD,
                        lowercase=True,
                    ),
                )
            except Exception as idx_err:  # noqa: BLE001 - index is best-effort
                logger.warning(f"Could not create text index on {collection_name}: {idx_err}")
            logger.info(f"Created collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise
    
    async def upsert_points(
        self, 
        collection_name: str, 
        points: List[PointStruct]
    ) -> None:
        """Upsert points to collection"""
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"Upserted {len(points)} points to {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to upsert points to {collection_name}: {e}")
            raise
    
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter_conditions: Optional[Filter] = None,
        with_payload: bool = True,
        with_vectors: bool = False
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in collection"""
        try:
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=filter_conditions,
                limit=limit,
                with_payload=with_payload,
                with_vectors=with_vectors
            )
            
            results = []
            for hit in search_result:
                result = {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload if with_payload else None,
                    "vector": hit.vector if with_vectors else None
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} results in {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search in {collection_name}: {e}")
            raise
    
    async def hybrid_search(
        self,
        collection_name: str,
        query_vector: List[float],
        query_text: str,
        limit: int = 10,
        filter_conditions: Optional[Filter] = None,
        vector_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search (semantic + keyword)"""
        try:
            # Semantic search
            semantic_results = await self.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit * 2,  # Get more for reranking
                filter_conditions=filter_conditions
            )
            
            # Keyword search using full-text match on the indexed "content" field.
            must_conditions: List[FieldCondition] = [
                FieldCondition(key="content", match=MatchText(text=query_text))
            ]
            if filter_conditions and filter_conditions.must:
                must_conditions.extend(filter_conditions.must)
            keyword_filter = Filter(must=must_conditions)

            try:
                keyword_results = await self.search(
                    collection_name=collection_name,
                    query_vector=query_vector,  # Still need vector for ordering
                    limit=limit * 2,
                    filter_conditions=keyword_filter
                )
            except Exception as kw_err:  # noqa: BLE001 - keyword leg is optional
                logger.warning(f"Keyword search leg failed, using semantic only: {kw_err}")
                keyword_results = []
            
            # Combine and rerank results
            combined_results = self._combine_search_results(
                semantic_results, 
                keyword_results, 
                vector_weight
            )
            
            return combined_results[:limit]
            
        except Exception as e:
            logger.error(f"Failed hybrid search in {collection_name}: {e}")
            # Fallback to semantic search
            return await self.search(collection_name, query_vector, limit)
    
    def _combine_search_results(
        self,
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        vector_weight: float
    ) -> List[Dict[str, Any]]:
        """Combine semantic and keyword search results"""
        combined = {}
        
        # Add semantic results
        for result in semantic_results:
            payload = result.get("payload") or {}
            doc_id = payload.get("doc_id", result["id"])
            combined[doc_id] = {
                **result,
                "semantic_score": result["score"],
                "keyword_score": 0.0
            }
        
        # Add keyword results
        for result in keyword_results:
            payload = result.get("payload") or {}
            doc_id = payload.get("doc_id", result["id"])
            if doc_id in combined:
                combined[doc_id]["keyword_score"] = result["score"]
            else:
                combined[doc_id] = {
                    **result,
                    "semantic_score": 0.0,
                    "keyword_score": result["score"]
                }
        
        # Calculate combined scores
        for doc_id, result in combined.items():
            combined_score = (
                vector_weight * result["semantic_score"] + 
                (1 - vector_weight) * result["keyword_score"]
            )
            result["combined_score"] = combined_score
        
        # Sort by combined score
        sorted_results = sorted(
            combined.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )
        
        return sorted_results
    
    async def get_point(self, collection_name: str, point_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Get a specific point by ID"""
        try:
            point = self.client.retrieve(
                collection_name=collection_name,
                ids=[point_id],
                with_payload=True,
                with_vectors=False
            )
            
            if point:
                return {
                    "id": point[0].id,
                    "payload": point[0].payload
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get point {point_id} from {collection_name}: {e}")
            return None
    
    async def delete_points(self, collection_name: str, point_ids: List[Union[str, int]]) -> None:
        """Delete points from collection"""
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=qdrant_models.PointIdsList(
                    points=point_ids
                )
            )
            logger.info(f"Deleted {len(point_ids)} points from {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to delete points from {collection_name}: {e}")
            raise
    
    async def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get collection information"""
        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count or 0,
                "indexed_vectors_count": info.indexed_vectors_count or 0,
                "points_count": info.points_count or 0,
                "status": str(info.status)
            }
        except Exception as e:
            logger.error(f"Failed to get collection info for {collection_name}: {e}")
            return None
    
    async def list_collections(self) -> List[str]:
        """List all collections"""
        try:
            collections = self.client.get_collections().collections
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []


# Global vector store instance
vector_store = VectorStore()


async def init_qdrant() -> None:
    """Initialize Qdrant with all required collections.

    The vector size matches the configured embedding model so OpenAI (1536-d)
    and local (384-d) embeddings both work without manual reconfiguration.
    """
    try:
        logger.info("Initializing Qdrant collections...")

        # Determine embedding dimension from the active generator.
        from app.ingestion.embeddings import get_embedding_generator

        vector_size = get_embedding_generator().get_embedding_dimension()
        logger.info(f"Using embedding dimension: {vector_size}")

        for collection_name in COLLECTIONS.values():
            await vector_store.create_collection(collection_name, vector_size=vector_size)

        logger.info("Qdrant initialization complete")

    except Exception as e:
        logger.error(f"Failed to initialize Qdrant: {e}")
        raise


async def check_qdrant_health() -> bool:
    """Check Qdrant health"""
    try:
        collections = await vector_store.list_collections()
        logger.info(f"Qdrant is healthy with {len(collections)} collections")
        return True
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        return False
