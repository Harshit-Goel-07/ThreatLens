"""
Semantic chunking for ThreatLens
Context-aware chunking that preserves document structure
"""

import logging
from typing import List, Dict, Any, Optional
import re

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Semantic chunking with context preservation"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(
        self, 
        text: str, 
        metadata: Optional[Dict[str, Any]] = None,
        preserve_structure: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Chunk text while preserving semantic boundaries
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks
            preserve_structure: Whether to preserve document structure
            
        Returns:
            List of chunk dictionaries with content and metadata
        """
        if preserve_structure:
            return self._chunk_with_structure(text, metadata)
        else:
            return self._chunk_simple(text, metadata)
    
    def _chunk_with_structure(
        self, 
        text: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Chunk text preserving structure (paragraphs, sections)"""
        chunks = []
        
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph exceeds chunk size
            if len(current_chunk) + len(para) > self.chunk_size:
                # Save current chunk if not empty
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk, 
                        chunk_index, 
                        metadata
                    ))
                    chunk_index += 1
                
                # If paragraph itself is larger than chunk size, split it
                if len(para) > self.chunk_size:
                    para_chunks = self._split_large_paragraph(para)
                    for pc in para_chunks:
                        chunks.append(self._create_chunk(
                            pc, 
                            chunk_index, 
                            metadata
                        ))
                        chunk_index += 1
                    current_chunk = ""
                else:
                    # Start new chunk with overlap from previous
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_chunk = overlap_text + para
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        # Add final chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                current_chunk, 
                chunk_index, 
                metadata
            ))
        
        return chunks
    
    def _chunk_simple(
        self, 
        text: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Simple fixed-size chunking with overlap"""
        chunks = []
        text_length = len(text)
        chunk_index = 0
        
        start = 0
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            
            # Try to break at sentence boundary
            if end < text_length:
                # Look for sentence ending
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start:
                    end = sentence_end + 1
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(self._create_chunk(
                    chunk_text, 
                    chunk_index, 
                    metadata
                ))
                chunk_index += 1
            
            # Move start position with overlap
            start = end - self.chunk_overlap
        
        return chunks
    
    def _split_large_paragraph(self, paragraph: str) -> List[str]:
        """Split a large paragraph into smaller chunks"""
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from end of chunk"""
        if len(text) <= self.chunk_overlap:
            return text
        
        # Try to get complete sentences for overlap
        overlap_start = len(text) - self.chunk_overlap
        sentence_start = text.rfind('.', 0, overlap_start)
        
        if sentence_start > 0:
            return text[sentence_start + 1:].strip() + "\n\n"
        else:
            return text[-self.chunk_overlap:] + "\n\n"
    
    def _create_chunk(
        self, 
        content: str, 
        index: int, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create chunk dictionary"""
        chunk = {
            "content": content,
            "chunk_index": index,
            "char_count": len(content),
            "metadata": metadata or {}
        }
        return chunk


class MITREChunker(SemanticChunker):
    """Specialized chunker for MITRE ATT&CK techniques"""
    
    def chunk_technique(self, technique_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk MITRE technique preserving structure"""
        chunks = []
        
        # Main technique description (always keep together)
        main_content = f"""
Technique: {technique_data.get('name', 'Unknown')}
ID: {technique_data.get('id', 'Unknown')}
Tactic: {technique_data.get('tactic', 'Unknown')}

Description:
{technique_data.get('description', '')}
"""
        
        chunks.append({
            "content": main_content.strip(),
            "chunk_index": 0,
            "chunk_type": "main_description",
            "metadata": {
                "technique_id": technique_data.get('id'),
                "technique_name": technique_data.get('name'),
                "tactic": technique_data.get('tactic')
            }
        })
        
        # Detection methods (if available)
        if technique_data.get('detection'):
            detection_content = f"""
Technique: {technique_data.get('name')}
Detection Methods:
{technique_data.get('detection')}
"""
            chunks.append({
                "content": detection_content.strip(),
                "chunk_index": 1,
                "chunk_type": "detection",
                "metadata": {
                    "technique_id": technique_data.get('id'),
                    "technique_name": technique_data.get('name')
                }
            })
        
        # Mitigation strategies (if available)
        if technique_data.get('mitigation'):
            mitigation_content = f"""
Technique: {technique_data.get('name')}
Mitigation Strategies:
{technique_data.get('mitigation')}
"""
            chunks.append({
                "content": mitigation_content.strip(),
                "chunk_index": 2,
                "chunk_type": "mitigation",
                "metadata": {
                    "technique_id": technique_data.get('id'),
                    "technique_name": technique_data.get('name')
                }
            })
        
        return chunks


class CVEChunker(SemanticChunker):
    """Specialized chunker for CVE entries"""
    
    def chunk_cve(self, cve_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk CVE entry preserving all critical information"""
        # CVEs should generally stay as single chunks to preserve context
        content = f"""
CVE ID: {cve_data.get('cve_id', 'Unknown')}
Severity: {cve_data.get('severity', 'Unknown')} (CVSS: {cve_data.get('cvss_score', 'N/A')})
Published: {cve_data.get('published_date', 'Unknown')}

Description:
{cve_data.get('description', '')}

Affected Products:
{cve_data.get('affected_products', 'Not specified')}

Mitigation:
{cve_data.get('mitigation', 'See vendor advisory')}
"""
        
        return [{
            "content": content.strip(),
            "chunk_index": 0,
            "chunk_type": "cve_entry",
            "metadata": {
                "cve_id": cve_data.get('cve_id'),
                "severity": cve_data.get('severity'),
                "cvss_score": cve_data.get('cvss_score')
            }
        }]


class PlaybookChunker(SemanticChunker):
    """Specialized chunker for SOC playbooks"""
    
    def chunk_playbook(self, playbook_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk playbook by procedure steps"""
        chunks = []
        
        # Overview chunk
        overview = f"""
Playbook: {playbook_data.get('title', 'Unknown')}
Incident Type: {playbook_data.get('incident_type', 'Unknown')}
Severity: {playbook_data.get('severity', 'Unknown')}

Description:
{playbook_data.get('description', '')}
"""
        chunks.append({
            "content": overview.strip(),
            "chunk_index": 0,
            "chunk_type": "overview",
            "metadata": {
                "playbook_id": playbook_data.get('playbook_id'),
                "incident_type": playbook_data.get('incident_type')
            }
        })
        
        # Procedure steps (each step as separate chunk)
        procedures = playbook_data.get('procedures', [])
        for idx, procedure in enumerate(procedures):
            proc_content = f"""
Playbook: {playbook_data.get('title')}
Step {idx + 1}: {procedure.get('title', '')}

{procedure.get('description', '')}

Actions:
{procedure.get('actions', '')}
"""
            chunks.append({
                "content": proc_content.strip(),
                "chunk_index": idx + 1,
                "chunk_type": "procedure_step",
                "metadata": {
                    "playbook_id": playbook_data.get('playbook_id'),
                    "step_number": idx + 1,
                    "step_title": procedure.get('title')
                }
            })
        
        return chunks
