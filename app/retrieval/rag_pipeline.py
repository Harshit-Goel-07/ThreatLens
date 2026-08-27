"""
Complete RAG pipeline for Security Copilot
Orchestrates retrieval, reranking, context building, and LLM generation
"""

import logging
import time
from typing import Dict, Any, List, Optional, AsyncGenerator

from app.config import settings
from app.retrieval.hybrid_search import get_hybrid_searcher
from app.retrieval.reranker import get_reranker
from app.retrieval.context_builder import get_context_builder
from app.llm.openai_provider import OpenAIProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.prompts import build_messages, classify_query_type
from app.llm.guardrails import get_guardrails, get_hallucination_detector
from app.llm.provider import LLMMessage

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Complete RAG pipeline orchestrator"""
    
    def __init__(self, use_openai: Optional[bool] = None, use_ollama: bool = False):
        self.hybrid_searcher = get_hybrid_searcher()
        self.reranker = get_reranker()
        self.context_builder = get_context_builder()
        self.guardrails = get_guardrails()
        self.hallucination_detector = get_hallucination_detector()

        # Select LLM provider: explicit args win, otherwise honour settings.
        if use_ollama or (use_openai is False and settings.llm_provider == "ollama"):
            self.llm_provider = OllamaProvider()
        elif use_openai is None and settings.llm_provider == "ollama":
            self.llm_provider = OllamaProvider()
        else:
            self.llm_provider = OpenAIProvider()
    
    async def _prepare(
        self,
        query: str,
        top_k: int,
        rerank_top_k: int,
        source_types: Optional[List[str]],
        filters: Optional[Dict[str, Any]],
        start_time: float,
    ) -> Dict[str, Any]:
        """Run validation + retrieval + context building.

        Returns a dict with key ``status`` of:
          - ``"invalid"``  -> early error response in ``response``
          - ``"empty"``    -> early "no results" response in ``response``
          - ``"ready"``    -> prepared ``llm_messages``, ``context``,
                              ``reranked`` and ``query_type``
        """
        # Step 1: Input validation
        input_check = self.guardrails.check_input(query)
        if not input_check['valid']:
            return {
                'status': 'invalid',
                'response': {
                    'success': False,
                    'error': 'Input validation failed',
                    'issues': input_check['issues'],
                },
            }

        sanitized_query = input_check['sanitized_input']

        # Step 2: Classify query type
        query_type = classify_query_type(sanitized_query)
        logger.info(f"Query classified as: {query_type}")

        # Step 3: Hybrid search
        search_results = await self.hybrid_searcher.search(
            query=sanitized_query,
            top_k=top_k,
            source_types=source_types,
            filters=filters,
        )

        if not search_results:
            fallback_prompt = (
                f"You are Security Copilot, an expert AI Assistant for SOC Analysts.\n"
                f"Answer the following security question thoroughly using your expert "
                f"cybersecurity domain knowledge, MITRE ATT&CK concepts, and incident response best practices:\n\n"
                f"Question: {sanitized_query}"
            )
            llm_messages = [LLMMessage(role="user", content=fallback_prompt)]
            return {
                'status': 'ready',
                'sanitized_query': sanitized_query,
                'query_type': query_type,
                'llm_messages': llm_messages,
                'context': {'sources': [], 'context_text': '', 'total_length': 0},
                'reranked': [],
            }

        # Step 4: Reranking
        reranked_results = self.reranker.rerank_with_fusion(
            query=sanitized_query,
            results=search_results,
            top_k=rerank_top_k,
        )

        # Step 5: Build context
        context = self.context_builder.build_context(
            query=sanitized_query,
            results=reranked_results,
            include_metadata=True,
        )
        context['results'] = reranked_results

        # Step 6: Build LLM messages
        messages = build_messages(
            query=sanitized_query,
            context=context['context_text'],
            prompt_type=query_type,
        )
        llm_messages = [
            LLMMessage(role=msg['role'], content=msg['content']) for msg in messages
        ]

        return {
            'status': 'ready',
            'sanitized_query': sanitized_query,
            'query_type': query_type,
            'llm_messages': llm_messages,
            'context': context,
            'reranked': reranked_results,
        }

    async def query(
        self,
        query: str,
        top_k: int = 10,
        rerank_top_k: int = 5,
        source_types: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute the complete (non-streaming) RAG pipeline."""
        start_time = time.time()

        try:
            prepared = await self._prepare(
                query, top_k, rerank_top_k, source_types, filters, start_time
            )
            if prepared['status'] != 'ready':
                return prepared['response']

            sanitized_query = prepared['sanitized_query']
            query_type = prepared['query_type']
            llm_messages = prepared['llm_messages']
            context = prepared['context']
            reranked_results = prepared['reranked']

            llm_response = await self.llm_provider.generate(
                messages=llm_messages,
                temperature=0.7,
                max_tokens=2000,
            )

            # Step 8: Output validation
            output_check = self.guardrails.check_output(
                llm_response.content,
                context['sources']
            )
            
            # Step 9: Hallucination detection
            hallucination_check = self.hallucination_detector.detect(
                output=llm_response.content,
                sources=context['sources'],
                query=sanitized_query
            )
            
            # Step 10: Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                search_results=reranked_results,
                output_validation=output_check,
                hallucination_check=hallucination_check
            )
            
            # Build final response
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'success': True,
                'answer': llm_response.content,
                'sources': context['sources'],
                'confidence_score': confidence_score,
                'token_count': llm_response.token_count,
                'response_time_ms': response_time_ms,
                'metadata': {
                    'query_type': query_type,
                    'num_sources': len(context['sources']),
                    'context_length': context['total_length'],
                    'model': llm_response.model,
                    'validation': {
                        'output_valid': output_check['valid'],
                        'hallucination_detected': hallucination_check['hallucination_detected'],
                        'hallucination_score': hallucination_check['hallucination_score']
                    }
                }
            }
            
        except Exception as e:
            logger.exception("RAG pipeline failed")
            return {
                'success': False,
                'error': 'An internal error occurred while processing the query.',
                'response_time_ms': int((time.time() - start_time) * 1000)
            }

    async def query_stream(
        self,
        query: str,
        top_k: int = 10,
        rerank_top_k: int = 5,
        source_types: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the RAG pipeline, streaming the answer as it is generated."""
        start_time = time.time()
        try:
            prepared = await self._prepare(
                query, top_k, rerank_top_k, source_types, filters, start_time
            )

            if prepared['status'] == 'invalid':
                yield {'type': 'error', 'error': 'Input validation failed',
                       'issues': prepared['response'].get('issues', [])}
                return
            if prepared['status'] == 'empty':
                yield {'type': 'metadata', 'sources': [], 'num_sources': 0}
                yield {'type': 'content', 'content': prepared['response']['answer']}
                yield {'type': 'complete', 'confidence_score': 0.0,
                       'response_time_ms': int((time.time() - start_time) * 1000)}
                return

            context = prepared['context']
            messages = prepared['llm_messages']

            # Send initial metadata (sources) so the UI can render citations early.
            yield {
                'type': 'metadata',
                'sources': context['sources'],
                'num_sources': len(context['sources']),
            }

            full_response = ""
            async for chunk in self.llm_provider.generate_stream(messages):
                full_response += chunk
                yield {'type': 'content', 'content': chunk}

            output_check = self.guardrails.check_output(full_response, context['sources'])
            hallucination_check = self.hallucination_detector.detect(
                full_response, context['sources'], prepared['sanitized_query']
            )
            confidence_score = self._calculate_confidence_score(
                search_results=context.get('results', []),
                output_validation=output_check,
                hallucination_check=hallucination_check,
            )

            yield {
                'type': 'complete',
                'confidence_score': confidence_score,
                'response_time_ms': int((time.time() - start_time) * 1000),
                'validation': {
                    'output_valid': output_check['valid'],
                    'hallucination_detected': hallucination_check['hallucination_detected'],
                },
            }

        except Exception:
            logger.exception("Streaming RAG pipeline failed")
            yield {'type': 'error', 'error': 'An internal error occurred while streaming the response.'}
    
    def _calculate_confidence_score(
        self,
        search_results: List[Dict[str, Any]],
        output_validation: Dict[str, Any],
        hallucination_check: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for response"""
        # Base score from search relevance
        if search_results:
            avg_relevance = sum(
                r.get('rerank_score', r.get('combined_score', 0))
                for r in search_results
            ) / len(search_results)
            relevance_score = min(avg_relevance, 1.0)
        else:
            relevance_score = 0.0
        
        # Penalty for validation issues
        validation_penalty = 0.0
        if not output_validation['valid']:
            validation_penalty = 0.2
        
        # Penalty for hallucinations
        hallucination_penalty = hallucination_check['hallucination_score'] * 0.5
        
        # Calculate final confidence
        confidence = max(0.0, relevance_score - validation_penalty - hallucination_penalty)
        
        return round(confidence, 2)
    
    async def explain_alert(
        self,
        alert_description: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Specialized method for alert explanation"""
        return await self.query(
            query=f"Explain this security alert: {alert_description}",
            top_k=top_k,
            source_types=['mitre', 'logs']
        )
    
    async def lookup_cve(
        self,
        cve_query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Specialized method for CVE lookup"""
        return await self.query(
            query=f"Provide information about {cve_query}",
            top_k=top_k,
            source_types=['cve']
        )
    
    async def get_incident_response_guidance(
        self,
        incident_description: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Specialized method for incident response guidance"""
        return await self.query(
            query=f"Provide incident response guidance for: {incident_description}",
            top_k=top_k,
            source_types=['playbooks', 'mitre']
        )
    
    async def threat_intelligence_query(
        self,
        threat_query: str,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """Specialized method for threat intelligence queries"""
        return await self.query(
            query=threat_query,
            top_k=top_k,
            source_types=['mitre', 'cve']
        )


# Global RAG pipeline instance
_rag_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline(use_openai: Optional[bool] = None) -> RAGPipeline:
    """Get or create the global RAG pipeline (provider from settings by default)."""
    global _rag_pipeline

    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline(use_openai=use_openai)

    return _rag_pipeline
