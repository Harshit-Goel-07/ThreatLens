"""
Embedding generation for Security Copilot
Supports both local sentence-transformers and OpenAI embeddings
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import numpy as np

from app.config import settings
from app.llm.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for text chunks"""
    
    def __init__(self, model_name: Optional[str] = None, use_openai: bool = False):
        self.model_name = model_name or settings.embedding_model
        self.use_openai = use_openai
        
        if use_openai:
            self.provider = OpenAIProvider()
            self.model = None
            logger.info(f"Using OpenAI embeddings: {settings.openai_embedding_model}")
        else:
            self.provider = None
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Using local embeddings: {self.model_name}")
    
    async def generate_embeddings(
        self, 
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """Generate embeddings for list of texts"""
        try:
            if self.use_openai:
                return await self._generate_openai_embeddings(texts)
            else:
                return self._generate_local_embeddings(texts, batch_size)
                
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    async def generate_single_embedding(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        embeddings = await self.generate_embeddings([text])
        return embeddings[0]
    
    def _generate_local_embeddings(
        self, 
        texts: List[str], 
        batch_size: int = 32
    ) -> List[List[float]]:
        """Generate embeddings using local sentence-transformers model"""
        try:
            # Process in batches for efficiency
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_embeddings = self.model.encode(
                    batch,
                    convert_to_numpy=True,
                    show_progress_bar=False
                )
                all_embeddings.extend(batch_embeddings.tolist())
            
            logger.info(f"Generated {len(all_embeddings)} local embeddings")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Local embedding generation failed: {e}")
            raise
    
    async def _generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API"""
        try:
            # OpenAI has a limit of ~8000 texts per request
            # Process in smaller batches
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = await self.provider.embed(batch)
                all_embeddings.extend(response.embeddings)
            
            logger.info(f"Generated {len(all_embeddings)} OpenAI embeddings")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        if self.use_openai:
            # OpenAI text-embedding-3-small: 1536 dimensions
            # OpenAI text-embedding-3-large: 3072 dimensions
            if 'large' in settings.openai_embedding_model:
                return 3072
            else:
                return 1536
        else:
            # Get dimension from local model
            return self.model.get_sentence_embedding_dimension()
    
    def compute_similarity(
        self, 
        embedding1: List[float], 
        embedding2: List[float]
    ) -> float:
        """Compute cosine similarity between two embeddings"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Cosine similarity
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return float(similarity)
    
    def batch_compute_similarity(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]]
    ) -> List[float]:
        """Compute similarity between query and multiple candidates"""
        query_vec = np.array(query_embedding)
        candidate_vecs = np.array(candidate_embeddings)
        
        # Batch cosine similarity
        similarities = np.dot(candidate_vecs, query_vec) / (
            np.linalg.norm(candidate_vecs, axis=1) * np.linalg.norm(query_vec)
        )
        
        return similarities.tolist()


# Global embedding generator instance
_embedding_generator: Optional[EmbeddingGenerator] = None


# Namespace used to derive deterministic UUID point IDs from string chunk ids,
# so re-ingesting the same chunk updates (rather than duplicates) the point.
_POINT_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00cf4fc964ff")


def chunk_id_to_point_id(chunk_id: str) -> str:
    """Convert an arbitrary string chunk id into a Qdrant-valid UUID string."""
    return str(uuid.uuid5(_POINT_NAMESPACE, chunk_id))


def get_embedding_generator(use_openai: Optional[bool] = None) -> EmbeddingGenerator:
    """Get or create the global embedding generator.

    When ``use_openai`` is ``None`` the provider is selected from settings
    (``USE_OPENAI_EMBEDDINGS``), keeping ingestion and retrieval consistent.
    """
    global _embedding_generator

    if use_openai is None:
        use_openai = settings.use_openai_embeddings

    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator(use_openai=use_openai)

    return _embedding_generator


async def generate_and_store_embeddings(
    chunks: List[Dict[str, Any]],
    collection_name: str,
    use_openai: Optional[bool] = None,
) -> None:
    """Generate embeddings for chunks and store them in Qdrant."""
    from app.retrieval.vector_store import vector_store
    from qdrant_client.http.models import PointStruct

    if not chunks:
        return

    try:
        generator = get_embedding_generator(use_openai)

        texts = [chunk["content"] for chunk in chunks]
        embeddings = await generator.generate_embeddings(texts)

        points = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = chunk.get("chunk_id", f"{collection_name}_chunk_{idx}")
            metadata = chunk.get("metadata", {}) or {}
            point = PointStruct(
                # Qdrant requires uint or UUID ids; derive a stable UUID.
                id=chunk_id_to_point_id(chunk_id),
                vector=embedding,
                payload={
                    "chunk_id": chunk_id,
                    "doc_id": chunk.get("doc_id"),
                    "content": chunk.get("content"),
                    "metadata": metadata,
                    # Promote commonly-filtered fields to the top level.
                    "source_type": chunk.get("source_type") or metadata.get("source_type"),
                    "chunk_index": chunk.get("chunk_index", 0),
                },
            )
            points.append(point)

        await vector_store.upsert_points(collection_name, points)
        logger.info(f"Stored {len(points)} embeddings in collection {collection_name}")

    except Exception as e:
        logger.error(f"Failed to generate and store embeddings: {e}")
        raise
