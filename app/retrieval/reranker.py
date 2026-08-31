"""
Reranking module for ThreatLens
Uses cross-encoder models to refine search results
"""

import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import CrossEncoder
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class Reranker:
    """Rerank search results using cross-encoder model"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load cross-encoder model"""
        try:
            self.model = CrossEncoder(self.model_name)
            logger.info(f"Loaded reranker model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load reranker model: {e}")
            self.model = None
    
    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank search results based on query relevance
        
        Args:
            query: Search query
            results: List of search results with 'content' field
            top_k: Number of top results to return (None = all)
            
        Returns:
            Reranked list of results with 'rerank_score' added
        """
        if not self.model or not results:
            return results
        
        try:
            # Prepare query-document pairs
            pairs = []
            for result in results:
                content = result.get('payload', {}).get('content', '')
                if content:
                    pairs.append([query, content])
            
            if not pairs:
                logger.warning("No valid content found for reranking")
                return results
            
            # Get reranking scores
            scores = self.model.predict(pairs)
            
            # Add rerank scores to results
            for idx, result in enumerate(results):
                if idx < len(scores):
                    result['rerank_score'] = float(scores[idx])
                else:
                    result['rerank_score'] = 0.0
            
            # Sort by rerank score
            reranked = sorted(results, key=lambda x: x['rerank_score'], reverse=True)
            
            # Return top_k if specified
            if top_k:
                reranked = reranked[:top_k]
            
            logger.info(f"Reranked {len(results)} results, returning top {len(reranked)}")
            return reranked
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return results
    
    def rerank_with_fusion(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: Optional[int] = None,
        rerank_weight: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Rerank with score fusion between original and rerank scores
        
        Args:
            query: Search query
            results: Search results
            top_k: Number of results to return
            rerank_weight: Weight for rerank score (0-1)
            
        Returns:
            Reranked results with fused scores
        """
        if not self.model or not results:
            return results
        
        try:
            # Get reranked results
            reranked = self.rerank(query, results, top_k=None)
            
            # Normalize scores to 0-1 range
            original_scores = [r.get('combined_score', r.get('score', 0)) for r in reranked]
            rerank_scores = [r.get('rerank_score', 0) for r in reranked]
            
            if max(original_scores) > 0:
                original_scores = [s / max(original_scores) for s in original_scores]
            if max(rerank_scores) > 0:
                rerank_scores = [s / max(rerank_scores) for s in rerank_scores]
            
            # Compute fused scores
            for idx, result in enumerate(reranked):
                fused_score = (
                    (1 - rerank_weight) * original_scores[idx] +
                    rerank_weight * rerank_scores[idx]
                )
                result['fused_score'] = fused_score
            
            # Sort by fused score
            reranked.sort(key=lambda x: x['fused_score'], reverse=True)
            
            # Return top_k
            if top_k:
                reranked = reranked[:top_k]
            
            return reranked
            
        except Exception as e:
            logger.error(f"Fusion reranking failed: {e}")
            return results
    
    def batch_rerank(
        self,
        queries: List[str],
        results_list: List[List[Dict[str, Any]]],
        top_k: Optional[int] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Rerank multiple query-results pairs in batch
        
        Args:
            queries: List of queries
            results_list: List of result lists (one per query)
            top_k: Number of results per query
            
        Returns:
            List of reranked result lists
        """
        reranked_list = []
        
        for query, results in zip(queries, results_list):
            reranked = self.rerank(query, results, top_k)
            reranked_list.append(reranked)
        
        return reranked_list
    
    def compute_relevance_score(self, query: str, document: str) -> float:
        """
        Compute relevance score for a single query-document pair
        
        Args:
            query: Query text
            document: Document text
            
        Returns:
            Relevance score
        """
        if not self.model:
            return 0.0
        
        try:
            score = self.model.predict([[query, document]])[0]
            return float(score)
        except Exception as e:
            logger.error(f"Relevance scoring failed: {e}")
            return 0.0


class ReciprocaRankFusion:
    """Reciprocal Rank Fusion for combining multiple ranked lists"""
    
    @staticmethod
    def fuse(
        ranked_lists: List[List[Dict[str, Any]]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Fuse multiple ranked lists using RRF
        
        Args:
            ranked_lists: List of ranked result lists
            k: RRF constant (default 60)
            
        Returns:
            Fused and reranked results
        """
        doc_scores = {}
        
        for ranked_list in ranked_lists:
            for rank, result in enumerate(ranked_list):
                doc_id = result.get('id') or result.get('payload', {}).get('doc_id')
                
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        'result': result,
                        'rrf_score': 0.0
                    }
                
                # RRF score: 1 / (k + rank)
                doc_scores[doc_id]['rrf_score'] += 1.0 / (k + rank + 1)
        
        # Sort by RRF score
        fused_results = sorted(
            doc_scores.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )
        
        # Extract results and add RRF score
        final_results = []
        for item in fused_results:
            result = item['result']
            result['rrf_score'] = item['rrf_score']
            final_results.append(result)
        
        return final_results


# Global reranker instance
_reranker: Optional[Reranker] = None


def get_reranker() -> Reranker:
    """Get or create global reranker"""
    global _reranker
    
    if _reranker is None:
        _reranker = Reranker()
    
    return _reranker
