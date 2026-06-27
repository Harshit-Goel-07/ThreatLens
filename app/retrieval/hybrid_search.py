"""
Hybrid search implementation for Security Copilot
Combines semantic (vector) and keyword (BM25) search
"""

import logging
from typing import List, Dict, Any, Optional
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from app.config import settings
from app.retrieval.vector_store import vector_store, COLLECTIONS
from app.ingestion.embeddings import get_embedding_generator

logger = logging.getLogger(__name__)


class HybridSearcher:
    """Hybrid search combining semantic and keyword search"""
    
    def __init__(self, vector_weight: float = 0.7):
        self.vector_weight = vector_weight
        self.keyword_weight = 1.0 - vector_weight
        self.embedding_generator = get_embedding_generator()
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        source_types: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search across collections
        
        Args:
            query: Search query text
            top_k: Number of results to return
            source_types: List of source types to search (mitre, cve, logs, playbooks)
            filters: Additional metadata filters
            
        Returns:
            List of search results with scores and metadata
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_generator.generate_single_embedding(query)
            
            # Determine collections to search
            collections_to_search = self._get_collections(source_types)
            
            # Build filter conditions
            filter_conditions = self._build_filters(filters)
            
            # Search each collection
            all_results = []
            for collection_name in collections_to_search:
                try:
                    # Perform hybrid search on this collection
                    results = await vector_store.hybrid_search(
                        collection_name=collection_name,
                        query_vector=query_embedding,
                        query_text=query,
                        limit=top_k * 2,  # Get more for reranking
                        filter_conditions=filter_conditions,
                        vector_weight=self.vector_weight
                    )
                    
                    all_results.extend(results)
                    
                except Exception as e:
                    logger.error(f"Search failed for collection {collection_name}: {e}")
                    continue
            
            # Sort by combined score and take top_k
            all_results.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
            top_results = all_results[:top_k]
            
            logger.info(f"Hybrid search returned {len(top_results)} results for query: {query[:50]}...")
            return top_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []
    
    async def search_by_source_type(
        self,
        query: str,
        source_type: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search within a specific source type"""
        return await self.search(
            query=query,
            top_k=top_k,
            source_types=[source_type],
            filters=filters
        )
    
    async def search_mitre_techniques(
        self,
        query: str,
        top_k: int = 5,
        tactic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search MITRE ATT&CK techniques"""
        filters = {}
        if tactic:
            filters['tactic'] = tactic
        
        return await self.search_by_source_type(
            query=query,
            source_type='mitre',
            top_k=top_k,
            filters=filters
        )
    
    async def search_cves(
        self,
        query: str,
        top_k: int = 5,
        min_severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search CVE vulnerabilities"""
        filters = {}
        if min_severity:
            # Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)
            severity_order = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
            filters['min_severity_score'] = severity_order.get(min_severity, 0)
        
        return await self.search_by_source_type(
            query=query,
            source_type='cve',
            top_k=top_k,
            filters=filters
        )
    
    async def search_playbooks(
        self,
        query: str,
        top_k: int = 5,
        incident_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search SOC playbooks"""
        filters = {}
        if incident_type:
            filters['incident_type'] = incident_type
        
        return await self.search_by_source_type(
            query=query,
            source_type='playbooks',
            top_k=top_k,
            filters=filters
        )
    
    async def search_logs(
        self,
        query: str,
        top_k: int = 5,
        log_type: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search security logs"""
        filters = {}
        if log_type:
            filters['log_type'] = log_type
        if severity:
            filters['severity'] = severity
        
        return await self.search_by_source_type(
            query=query,
            source_type='logs',
            top_k=top_k,
            filters=filters
        )
    
    def _get_collections(self, source_types: Optional[List[str]] = None) -> List[str]:
        """Get collection names to search.

        Documents are stored in per-source collections, so searching "all"
        means iterating those collections (excluding the unused ``all`` alias
        to avoid duplicate hits).
        """
        per_type = {k: v for k, v in COLLECTIONS.items() if k != "all"}
        if not source_types:
            return list(per_type.values())

        return [per_type[s] for s in source_types if s in per_type]
    
    def _build_filters(self, filters: Optional[Dict[str, Any]] = None) -> Optional[Filter]:
        """Build Qdrant filter conditions from filter dict"""
        if not filters:
            return None
        
        conditions = []
        
        for key, value in filters.items():
            if isinstance(value, list):
                # Multiple values - use should (OR)
                for v in value:
                    conditions.append(
                        FieldCondition(
                            key=f"metadata.{key}",
                            match=MatchValue(value=v)
                        )
                    )
            else:
                # Single value
                conditions.append(
                    FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=value)
                    )
                )
        
        if conditions:
            return Filter(must=conditions)
        
        return None
    
    async def multi_query_search(
        self,
        queries: List[str],
        top_k: int = 10,
        source_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform search with multiple query variations
        Useful for query expansion and better recall
        """
        all_results = {}
        
        for query in queries:
            results = await self.search(
                query=query,
                top_k=top_k * 2,
                source_types=source_types
            )
            
            # Merge results, keeping highest score for each doc
            for result in results:
                doc_id = result['payload'].get('doc_id')
                if doc_id not in all_results or result['combined_score'] > all_results[doc_id]['combined_score']:
                    all_results[doc_id] = result
        
        # Sort and return top_k
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x['combined_score'],
            reverse=True
        )
        
        return sorted_results[:top_k]


# Global hybrid searcher instance
_hybrid_searcher: Optional[HybridSearcher] = None


def get_hybrid_searcher() -> HybridSearcher:
    """Get or create global hybrid searcher"""
    global _hybrid_searcher
    
    if _hybrid_searcher is None:
        _hybrid_searcher = HybridSearcher()
    
    return _hybrid_searcher
