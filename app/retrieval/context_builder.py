"""
Context builder for Security Copilot
Assembles retrieved documents into structured context with citations
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Build structured context from retrieved documents"""
    
    def __init__(self, max_context_length: int = 4000):
        self.max_context_length = max_context_length
    
    def build_context(
        self,
        query: str,
        results: List[Dict[str, Any]],
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Build context from search results
        
        Args:
            query: Original query
            results: Retrieved and reranked results
            include_metadata: Whether to include source metadata
            
        Returns:
            Dictionary with context, sources, and metadata
        """
        try:
            # Extract and format sources
            sources = self._extract_sources(results)
            
            # Build context text
            context_text = self._build_context_text(results, sources)
            
            # Truncate if needed
            if len(context_text) > self.max_context_length:
                context_text = self._truncate_context(context_text, sources)
            
            # Build structured context
            context = {
                'query': query,
                'context_text': context_text,
                'sources': sources,
                'num_sources': len(sources),
                'total_length': len(context_text),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if include_metadata:
                context['metadata'] = self._extract_metadata(results)
            
            return context
            
        except Exception as e:
            logger.error(f"Context building failed: {e}")
            return {
                'query': query,
                'context_text': '',
                'sources': [],
                'num_sources': 0,
                'error': str(e)
            }
    
    def _extract_sources(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract source information from results"""
        sources = []
        
        for idx, result in enumerate(results):
            payload = result.get('payload', {})
            metadata = payload.get('metadata', {})
            
            source = {
                'index': idx + 1,
                'doc_id': payload.get('doc_id', f'doc_{idx}'),
                'source_type': payload.get('source_type', 'unknown'),
                'content': payload.get('content', ''),
                'relevance_score': result.get('rerank_score', result.get('combined_score', result.get('score', 0))),
                'metadata': metadata
            }
            
            # Add source-specific fields
            source_type = source['source_type']
            
            if source_type == 'mitre':
                source['technique_id'] = metadata.get('technique_id', 'Unknown')
                source['technique_name'] = metadata.get('technique_name', 'Unknown')
                source['title'] = f"MITRE {source['technique_id']}: {source['technique_name']}"
            
            elif source_type == 'cve':
                source['cve_id'] = metadata.get('cve_id', 'Unknown')
                source['severity'] = metadata.get('severity', 'Unknown')
                source['cvss_score'] = metadata.get('cvss_score', 0.0)
                source['title'] = f"{source['cve_id']} ({source['severity']})"
            
            elif source_type == 'playbooks':
                source['playbook_id'] = metadata.get('playbook_id', 'Unknown')
                source['incident_type'] = metadata.get('incident_type', 'Unknown')
                source['title'] = f"Playbook: {metadata.get('incident_type', 'Unknown')}"
            
            elif source_type == 'logs':
                source['log_type'] = metadata.get('log_type', 'Unknown')
                source['event_id'] = metadata.get('event_id', 'Unknown')
                source['title'] = f"Log: {source['log_type']} - Event {source['event_id']}"
            
            else:
                source['title'] = f"Document {idx + 1}"
            
            sources.append(source)
        
        return sources
    
    def _build_context_text(
        self,
        results: List[Dict[str, Any]],
        sources: List[Dict[str, Any]]
    ) -> str:
        """Build formatted context text with citations"""
        context_parts = []
        
        for source in sources:
            # Format source header
            header = f"[Source {source['index']}] {source['title']}"
            
            # Add relevance score
            score = source['relevance_score']
            header += f" (Relevance: {score:.2f})"
            
            # Add content
            content = source['content'].strip()
            
            # Truncate very long content
            if len(content) > 800:
                content = content[:800] + "..."
            
            # Combine
            source_text = f"{header}\n{content}\n"
            context_parts.append(source_text)
        
        return "\n".join(context_parts)
    
    def _truncate_context(
        self,
        context_text: str,
        sources: List[Dict[str, Any]]
    ) -> str:
        """Truncate context to fit within max length"""
        # Keep most relevant sources
        truncated_parts = []
        current_length = 0
        
        for source in sources:
            header = f"[Source {source['index']}] {source['title']}"
            content = source['content'].strip()
            
            # Calculate available space
            available = self.max_context_length - current_length - len(header) - 50
            
            if available <= 0:
                break
            
            # Truncate content if needed
            if len(content) > available:
                content = content[:available] + "..."
            
            source_text = f"{header}\n{content}\n\n"
            truncated_parts.append(source_text)
            current_length += len(source_text)
        
        return "".join(truncated_parts)
    
    def _extract_metadata(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract aggregate metadata from results"""
        source_types = {}
        severity_counts = {}
        
        for result in results:
            payload = result.get('payload', {})
            metadata = payload.get('metadata', {})
            
            # Count source types
            source_type = payload.get('source_type', 'unknown')
            source_types[source_type] = source_types.get(source_type, 0) + 1
            
            # Count severities (for CVEs and logs)
            severity = metadata.get('severity')
            if severity:
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'source_type_distribution': source_types,
            'severity_distribution': severity_counts,
            'total_results': len(results)
        }
    
    def build_citation_text(self, sources: List[Dict[str, Any]]) -> str:
        """Build formatted citation list"""
        citations = []
        
        for source in sources:
            citation = f"[{source['index']}] {source['title']}"
            
            # Add source-specific details
            if source['source_type'] == 'mitre':
                citation += f" - {source.get('technique_id', '')}"
            elif source['source_type'] == 'cve':
                citation += f" - CVSS: {source.get('cvss_score', 'N/A')}"
            
            citations.append(citation)
        
        return "\n".join(citations)
    
    def format_for_llm(
        self,
        query: str,
        results: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format context specifically for LLM consumption
        
        Returns:
            Dictionary with formatted prompt and metadata
        """
        context = self.build_context(query, results, include_metadata=True)
        
        # Build LLM prompt
        prompt_parts = []
        
        if system_prompt:
            prompt_parts.append(system_prompt)
        
        prompt_parts.append("# Retrieved Context")
        prompt_parts.append(context['context_text'])
        prompt_parts.append("\n# User Query")
        prompt_parts.append(query)
        prompt_parts.append("\n# Instructions")
        prompt_parts.append(
            "Based on the retrieved context above, provide a comprehensive answer to the user's query. "
            "Always cite your sources using [Source N] notation. "
            "If the context doesn't contain enough information, acknowledge this limitation."
        )
        
        llm_prompt = "\n\n".join(prompt_parts)
        
        return {
            'prompt': llm_prompt,
            'sources': context['sources'],
            'metadata': context.get('metadata', {}),
            'context_length': len(llm_prompt)
        }


# Global context builder instance
_context_builder: Optional[ContextBuilder] = None


def get_context_builder() -> ContextBuilder:
    """Get or create global context builder"""
    global _context_builder
    
    if _context_builder is None:
        _context_builder = ContextBuilder()
    
    return _context_builder
