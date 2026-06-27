"""
Base ingestion interface for Security Copilot data sources
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel, Field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DocumentChunk(BaseModel):
    """Represents a chunk of processed document"""
    chunk_id: str
    doc_id: str
    content: str
    metadata: Dict[str, Any]
    source_type: str
    chunk_index: int
    total_chunks: int
    # Use a factory so each chunk gets its own creation timestamp.
    created_at: datetime = Field(default_factory=_utcnow)


class IngestionResult(BaseModel):
    """Result of ingestion operation"""
    success: bool
    documents_processed: int
    chunks_created: int
    errors: List[str] = []
    metadata: Dict[str, Any] = {}


class BaseIngestor(ABC):
    """Abstract base class for all data ingestors"""
    
    def __init__(self, source_type: str):
        self.source_type = source_type
        self.logger = logging.getLogger(f"{__name__}.{source_type}")
    
    @abstractmethod
    async def fetch_data(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Fetch raw data from source"""
        pass
    
    @abstractmethod
    async def process_document(self, raw_doc: Dict[str, Any]) -> List[DocumentChunk]:
        """Process raw document into chunks"""
        pass
    
    @abstractmethod
    async def validate_document(self, raw_doc: Dict[str, Any]) -> bool:
        """Validate raw document format"""
        pass
    
    @abstractmethod
    def extract_metadata(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from raw document"""
        pass
    
    async def ingest(self, batch_size: int = 100) -> IngestionResult:
        """Main ingestion method"""
        try:
            self.logger.info(f"Starting ingestion for {self.source_type}")
            
            documents_processed = 0
            chunks_created = 0
            errors = []
            
            batch = []
            
            async for raw_doc in self.fetch_data():
                try:
                    # Validate document
                    if not await self.validate_document(raw_doc):
                        errors.append(f"Invalid document format: {raw_doc}")
                        continue
                    
                    # Process document
                    chunks = await self.process_document(raw_doc)
                    
                    # Add to batch
                    batch.extend(chunks)
                    documents_processed += 1
                    chunks_created += len(chunks)
                    
                    # Process batch when full
                    if len(batch) >= batch_size:
                        await self._process_batch(batch)
                        batch = []
                        
                except Exception as e:
                    error_msg = f"Error processing document: {e}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
            
            # Process remaining batch
            if batch:
                await self._process_batch(batch)
            
            result = IngestionResult(
                success=True,
                documents_processed=documents_processed,
                chunks_created=chunks_created,
                errors=errors,
                metadata={
                    "source_type": self.source_type,
                    "completed_at": datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(f"Ingestion completed: {documents_processed} docs, {chunks_created} chunks")
            return result
            
        except Exception as e:
            self.logger.error(f"Ingestion failed: {e}")
            return IngestionResult(
                success=False,
                documents_processed=0,
                chunks_created=0,
                errors=[str(e)]
            )
    
    async def _process_batch(self, chunks: List[DocumentChunk]) -> None:
        """Process a batch of chunks (store in database, create embeddings, etc.)"""
        try:
            # Store chunks in PostgreSQL
            await self._store_chunks_metadata(chunks)
            
            # Generate embeddings and store in Qdrant
            await self._store_chunks_vectors(chunks)
            
        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            raise
    
    def _collection_name(self) -> str:
        """Resolve the Qdrant collection for this ingestor's source type."""
        from app.retrieval.vector_store import COLLECTIONS

        return COLLECTIONS.get(self.source_type, COLLECTIONS["all"])

    async def _store_chunks_vectors(self, chunks: List[DocumentChunk]) -> None:
        """Embed chunks and store them as vectors in Qdrant."""
        from app.ingestion.embeddings import generate_and_store_embeddings

        chunk_dicts = [
            {
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "content": c.content,
                "metadata": c.metadata,
                "source_type": c.source_type,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]
        await generate_and_store_embeddings(chunk_dicts, self._collection_name())

    async def _store_chunks_metadata(self, chunks: List[DocumentChunk]) -> None:
        """Persist one metadata row per document in PostgreSQL (best-effort).

        Metadata storage is non-fatal: a failure here (e.g. Postgres briefly
        unavailable) must not abort the vector ingestion that powers retrieval.
        """
        from sqlalchemy.dialects.postgresql import insert

        from app.database.models import Document
        from app.database.postgres import session_scope

        # Aggregate chunks back into documents.
        documents: Dict[str, Dict[str, Any]] = {}
        for c in chunks:
            doc = documents.setdefault(
                c.doc_id,
                {
                    "doc_id": c.doc_id,
                    "source_type": c.source_type,
                    "title": c.metadata.get("technique_name")
                    or c.metadata.get("cve_id")
                    or c.metadata.get("title")
                    or c.metadata.get("event_name")
                    or c.doc_id,
                    "content_parts": [],
                    "metadata": c.metadata,
                },
            )
            doc["content_parts"].append(c.content)

        try:
            async with session_scope() as session:
                for doc in documents.values():
                    stmt = insert(Document).values(
                        doc_id=doc["doc_id"],
                        source_type=doc["source_type"],
                        title=str(doc["title"])[:500],
                        content="\n\n".join(doc["content_parts"]),
                        doc_metadata=doc["metadata"],
                        processed=True,
                    )
                    # Upsert: re-ingesting a document refreshes its row.
                    stmt = stmt.on_conflict_do_update(
                        index_elements=[Document.doc_id],
                        set_={
                            "content": stmt.excluded.content,
                            "metadata": stmt.excluded.metadata,
                            "processed": True,
                        },
                    )
                    await session.execute(stmt)
        except Exception as exc:  # noqa: BLE001 - metadata persistence is best-effort
            self.logger.warning("Could not persist document metadata: %s", exc)
    
    async def test_connection(self) -> bool:
        """Test connection to data source"""
        try:
            async for _ in self.fetch_data():
                return True  # If we can fetch at least one document, connection is good
            return True  # Empty source is still a valid connection
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
