"""
Guardrails for ThreatLens
Prompt injection detection and output validation
"""

import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class Guardrails:
    """Security guardrails for LLM inputs and outputs"""
    
    def __init__(self):
        self.prompt_injection_patterns = [
            r'ignore\s+(previous|above|all)\s+instructions',
            r'disregard\s+(previous|above|all)',
            r'forget\s+(everything|all|previous)',
            r'you\s+are\s+now',
            r'new\s+instructions',
            r'system\s*:\s*you\s+are',
            r'<\|im_start\|>',
            r'<\|im_end\|>',
        ]
        
        self.cve_pattern = r'CVE-\d{4}-\d{4,7}'
        self.mitre_pattern = r'T\d{4}(?:\.\d{3})?'
    
    def check_input(self, user_input: str) -> Dict[str, Any]:
        """
        Check user input for potential issues
        
        Args:
            user_input: User query or input
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        
        # Check for prompt injection
        if self._detect_prompt_injection(user_input):
            issues.append({
                'type': 'prompt_injection',
                'severity': 'high',
                'message': 'Potential prompt injection detected'
            })
        
        # Check for excessive length
        if len(user_input) > 5000:
            issues.append({
                'type': 'excessive_length',
                'severity': 'medium',
                'message': 'Input exceeds recommended length'
            })
        
        # Check for suspicious patterns
        if self._detect_suspicious_patterns(user_input):
            issues.append({
                'type': 'suspicious_pattern',
                'severity': 'medium',
                'message': 'Suspicious patterns detected in input'
            })
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'sanitized_input': self._sanitize_input(user_input)
        }
    
    def check_output(self, llm_output: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate LLM output for hallucinations and accuracy
        
        Args:
            llm_output: Generated LLM response
            sources: Source documents used
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        
        # Check for hallucinated CVE IDs
        hallucinated_cves = self._check_hallucinated_cves(llm_output, sources)
        if hallucinated_cves:
            issues.append({
                'type': 'hallucinated_cve',
                'severity': 'critical',
                'message': f'Hallucinated CVE IDs: {", ".join(hallucinated_cves)}',
                'details': hallucinated_cves
            })
        
        # Check for hallucinated MITRE techniques
        hallucinated_techniques = self._check_hallucinated_techniques(llm_output, sources)
        if hallucinated_techniques:
            issues.append({
                'type': 'hallucinated_technique',
                'severity': 'critical',
                'message': f'Hallucinated MITRE techniques: {", ".join(hallucinated_techniques)}',
                'details': hallucinated_techniques
            })
        
        # Check for missing citations
        if not self._has_citations(llm_output) and sources:
            issues.append({
                'type': 'missing_citations',
                'severity': 'medium',
                'message': 'Response lacks source citations'
            })
        
        # Check for invalid citations
        invalid_citations = self._check_invalid_citations(llm_output, sources)
        if invalid_citations:
            issues.append({
                'type': 'invalid_citations',
                'severity': 'medium',
                'message': f'Invalid citation references: {", ".join(map(str, invalid_citations))}',
                'details': invalid_citations
            })
        
        return {
            'valid': len([i for i in issues if i['severity'] == 'critical']) == 0,
            'issues': issues,
            'has_critical_issues': any(i['severity'] == 'critical' for i in issues)
        }
    
    def _detect_prompt_injection(self, text: str) -> bool:
        """Detect potential prompt injection attempts"""
        text_lower = text.lower()
        
        for pattern in self.prompt_injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"Prompt injection pattern detected: {pattern}")
                return True
        
        return False
    
    def _detect_suspicious_patterns(self, text: str) -> bool:
        """Detect other suspicious patterns"""
        suspicious_patterns = [
            r'<script>',
            r'javascript:',
            r'onerror=',
            r'eval\(',
            r'exec\(',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _sanitize_input(self, text: str) -> str:
        """Sanitize user input"""
        # Remove potential HTML/script tags
        sanitized = re.sub(r'<[^>]+>', '', text)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Trim
        sanitized = sanitized.strip()
        
        return sanitized
    
    def _check_hallucinated_cves(
        self,
        output: str,
        sources: List[Dict[str, Any]]
    ) -> List[str]:
        """Check for CVE IDs not present in sources"""
        # Extract CVE IDs from output
        output_cves = set(re.findall(self.cve_pattern, output))
        
        # Extract CVE IDs from sources
        source_cves = set()
        for source in sources:
            content = source.get('content', '')
            metadata = source.get('metadata', {})
            
            # Check content
            source_cves.update(re.findall(self.cve_pattern, content))
            
            # Check metadata
            if 'cve_id' in metadata:
                source_cves.add(metadata['cve_id'])
        
        # Find hallucinated CVEs
        hallucinated = output_cves - source_cves
        
        if hallucinated:
            logger.warning(f"Hallucinated CVE IDs detected: {hallucinated}")
        
        return list(hallucinated)
    
    def _check_hallucinated_techniques(
        self,
        output: str,
        sources: List[Dict[str, Any]]
    ) -> List[str]:
        """Check for MITRE technique IDs not present in sources"""
        # Extract technique IDs from output
        output_techniques = set(re.findall(self.mitre_pattern, output))
        
        # Extract technique IDs from sources
        source_techniques = set()
        for source in sources:
            content = source.get('content', '')
            metadata = source.get('metadata', {})
            
            # Check content
            source_techniques.update(re.findall(self.mitre_pattern, content))
            
            # Check metadata
            if 'technique_id' in metadata:
                source_techniques.add(metadata['technique_id'])
        
        # Find hallucinated techniques
        hallucinated = output_techniques - source_techniques
        
        if hallucinated:
            logger.warning(f"Hallucinated MITRE techniques detected: {hallucinated}")
        
        return list(hallucinated)
    
    def _has_citations(self, output: str) -> bool:
        """Check if output contains citations"""
        return bool(re.search(r'\[Source \d+\]', output))
    
    def _check_invalid_citations(
        self,
        output: str,
        sources: List[Dict[str, Any]]
    ) -> List[int]:
        """Check for citation numbers that don't exist in sources"""
        # Extract citation numbers
        citations = re.findall(r'\[Source (\d+)\]', output)
        citation_numbers = [int(c) for c in citations]
        
        # Check against available sources
        max_source = len(sources)
        invalid = [c for c in citation_numbers if c < 1 or c > max_source]
        
        return invalid
    
    def sanitize_output(self, output: str) -> str:
        """Sanitize LLM output"""
        # Remove any potential code injection
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', output, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove excessive newlines
        sanitized = re.sub(r'\n{3,}', '\n\n', sanitized)
        
        return sanitized.strip()


class HallucinationDetector:
    """Detect hallucinations in LLM outputs"""
    
    def __init__(self):
        self.guardrails = Guardrails()
    
    def detect(
        self,
        output: str,
        sources: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """
        Comprehensive hallucination detection
        
        Args:
            output: LLM generated output
            sources: Source documents
            query: Original query
            
        Returns:
            Detection results with score and details
        """
        issues = []
        
        # Check for fabricated security identifiers
        validation = self.guardrails.check_output(output, sources)
        issues.extend(validation['issues'])
        
        # Check for unsupported claims
        unsupported_claims = self._detect_unsupported_claims(output, sources)
        if unsupported_claims:
            issues.append({
                'type': 'unsupported_claim',
                'severity': 'medium',
                'message': 'Output contains claims not supported by sources'
            })
        
        # Calculate hallucination score (0 = no hallucination, 1 = severe)
        hallucination_score = self._calculate_hallucination_score(issues)
        
        return {
            'hallucination_detected': hallucination_score > 0.3,
            'hallucination_score': hallucination_score,
            'issues': issues,
            'severity': self._get_severity_level(hallucination_score)
        }
    
    def _detect_unsupported_claims(
        self,
        output: str,
        sources: List[Dict[str, Any]]
    ) -> bool:
        """Detect claims not supported by source content"""
        # This is a simplified check
        # In production, you might use NLI models or semantic similarity
        
        # Extract key technical terms from output
        output_terms = set(re.findall(r'\b[A-Z][A-Za-z0-9_-]{3,}\b', output))
        
        # Extract terms from sources
        source_terms = set()
        for source in sources:
            content = source.get('content', '')
            source_terms.update(re.findall(r'\b[A-Z][A-Za-z0-9_-]{3,}\b', content))
        
        # Check if output has many terms not in sources
        unsupported_terms = output_terms - source_terms
        
        # If more than 30% of technical terms are unsupported, flag it
        if len(output_terms) > 0:
            unsupported_ratio = len(unsupported_terms) / len(output_terms)
            return unsupported_ratio > 0.3
        
        return False
    
    def _calculate_hallucination_score(self, issues: List[Dict[str, Any]]) -> float:
        """Calculate overall hallucination score"""
        if not issues:
            return 0.0
        
        severity_weights = {
            'critical': 1.0,
            'high': 0.7,
            'medium': 0.4,
            'low': 0.2
        }
        
        total_score = sum(severity_weights.get(issue['severity'], 0.5) for issue in issues)
        
        # Normalize to 0-1 range
        normalized_score = min(total_score / 2.0, 1.0)
        
        return normalized_score
    
    def _get_severity_level(self, score: float) -> str:
        """Get severity level from score"""
        if score >= 0.7:
            return 'critical'
        elif score >= 0.5:
            return 'high'
        elif score >= 0.3:
            return 'medium'
        else:
            return 'low'


# Global instances
_guardrails: Optional[Guardrails] = None
_hallucination_detector: Optional[HallucinationDetector] = None


def get_guardrails() -> Guardrails:
    """Get or create global guardrails instance"""
    global _guardrails
    if _guardrails is None:
        _guardrails = Guardrails()
    return _guardrails


def get_hallucination_detector() -> HallucinationDetector:
    """Get or create global hallucination detector"""
    global _hallucination_detector
    if _hallucination_detector is None:
        _hallucination_detector = HallucinationDetector()
    return _hallucination_detector
