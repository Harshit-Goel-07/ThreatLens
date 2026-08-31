"""
SOC Playbook ingestion for ThreatLens
Processes incident response playbooks in markdown and JSON formats
"""

import logging
import json
import re
from typing import Dict, Any, List, AsyncGenerator
from pathlib import Path
from datetime import datetime

from app.config import settings
from app.ingestion.base import BaseIngestor, DocumentChunk
from app.ingestion.chunking import PlaybookChunker

logger = logging.getLogger(__name__)


class PlaybookIngestor(BaseIngestor):
    """SOC playbook data ingestor"""
    
    def __init__(self, playbook_directory: str = "data/playbooks"):
        super().__init__(source_type="playbooks")
        self.chunker = PlaybookChunker()
        self.playbook_directory = Path(playbook_directory)
    
    async def fetch_data(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Fetch playbooks from directory"""
        try:
            if not self.playbook_directory.exists():
                self.logger.warning(f"Playbook directory not found: {self.playbook_directory}")
                # Yield sample playbooks for testing
                for sample_playbook in self._get_sample_playbooks():
                    yield sample_playbook
                return
            
            # Process JSON playbooks
            for playbook_file in self.playbook_directory.glob("*.json"):
                try:
                    with open(playbook_file, 'r', encoding='utf-8') as f:
                        playbook = json.load(f)
                        yield self._parse_json_playbook(playbook, playbook_file.stem)
                except Exception as e:
                    self.logger.error(f"Failed to read playbook {playbook_file}: {e}")
            
            # Process Markdown playbooks
            for playbook_file in self.playbook_directory.glob("*.md"):
                try:
                    with open(playbook_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        yield self._parse_markdown_playbook(content, playbook_file.stem)
                except Exception as e:
                    self.logger.error(f"Failed to read playbook {playbook_file}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to fetch playbooks: {e}")
            raise
    
    def _parse_json_playbook(self, playbook_data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Parse JSON format playbook"""
        return {
            'playbook_id': playbook_data.get('id', filename),
            'title': playbook_data.get('title', filename),
            'description': playbook_data.get('description', ''),
            'incident_type': playbook_data.get('incident_type', 'general'),
            'severity': playbook_data.get('severity', 'MEDIUM'),
            'phase': playbook_data.get('phase', 'response'),
            'procedures': playbook_data.get('procedures', []),
            'checklists': playbook_data.get('checklists', []),
            'escalation_criteria': playbook_data.get('escalation_criteria', []),
            'author': playbook_data.get('author', 'Unknown'),
            'version': playbook_data.get('version', '1.0'),
            'tags': playbook_data.get('tags', []),
            'created_at': playbook_data.get('created_at', datetime.utcnow().isoformat())
        }
    
    def _parse_markdown_playbook(self, content: str, filename: str) -> Dict[str, Any]:
        """Parse Markdown format playbook"""
        # Extract title (first # heading)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else filename
        
        # Extract metadata from frontmatter if present
        metadata = self._extract_frontmatter(content)
        
        # Extract sections
        sections = self._extract_markdown_sections(content)
        
        # Parse procedures from numbered lists or steps
        procedures = self._extract_procedures_from_markdown(content)
        
        return {
            'playbook_id': metadata.get('id', filename),
            'title': title,
            'description': sections.get('description', sections.get('overview', '')),
            'incident_type': metadata.get('incident_type', 'general'),
            'severity': metadata.get('severity', 'MEDIUM'),
            'phase': metadata.get('phase', 'response'),
            'procedures': procedures,
            'checklists': sections.get('checklist', []),
            'escalation_criteria': sections.get('escalation', []),
            'author': metadata.get('author', 'Unknown'),
            'version': metadata.get('version', '1.0'),
            'tags': metadata.get('tags', []),
            'created_at': metadata.get('created_at', datetime.utcnow().isoformat())
        }
    
    def _extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """Extract YAML frontmatter from markdown"""
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not frontmatter_match:
            return {}
        
        # Simple key-value parsing (not full YAML)
        metadata = {}
        for line in frontmatter_match.group(1).split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()
        
        return metadata
    
    def _extract_markdown_sections(self, content: str) -> Dict[str, str]:
        """Extract sections from markdown"""
        sections = {}
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            # Check for section header
            header_match = re.match(r'^##\s+(.+)$', line)
            if header_match:
                # Save previous section
                if current_section:
                    sections[current_section.lower()] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = header_match.group(1)
                current_content = []
            elif current_section:
                current_content.append(line)
        
        # Save last section
        if current_section:
            sections[current_section.lower()] = '\n'.join(current_content).strip()
        
        return sections
    
    def _extract_procedures_from_markdown(self, content: str) -> List[Dict[str, Any]]:
        """Extract procedure steps from markdown"""
        procedures = []
        
        # Look for numbered lists or step sections
        step_pattern = r'(?:^|\n)(?:##\s+)?(?:Step\s+)?(\d+)[.:\s]+(.+?)(?=\n(?:##\s+)?(?:Step\s+)?\d+[.:\s]|\Z)'
        matches = re.finditer(step_pattern, content, re.DOTALL | re.MULTILINE)
        
        for match in matches:
            step_num = match.group(1)
            step_content = match.group(2).strip()
            
            # Split into title and description
            lines = step_content.split('\n', 1)
            title = lines[0].strip()
            description = lines[1].strip() if len(lines) > 1 else ''
            
            procedures.append({
                'step': int(step_num),
                'title': title,
                'description': description,
                'actions': description  # For compatibility
            })
        
        return procedures
    
    def _get_sample_playbooks(self) -> List[Dict[str, Any]]:
        """Get sample playbooks for testing"""
        return [
            {
                'playbook_id': 'PB-PHISHING-001',
                'title': 'Phishing Email Response',
                'description': 'Standard operating procedure for responding to reported phishing emails',
                'incident_type': 'phishing',
                'severity': 'MEDIUM',
                'phase': 'analysis',
                'procedures': [
                    {
                        'step': 1,
                        'title': 'Initial Triage',
                        'description': 'Review the reported email and assess legitimacy',
                        'actions': '1. Check sender address\n2. Analyze email headers\n3. Inspect links and attachments'
                    },
                    {
                        'step': 2,
                        'title': 'Threat Analysis',
                        'description': 'Determine if email is malicious',
                        'actions': '1. Scan attachments with AV\n2. Check URLs against threat intel\n3. Review similar incidents'
                    },
                    {
                        'step': 3,
                        'title': 'Containment',
                        'description': 'Prevent further spread if malicious',
                        'actions': '1. Block sender domain\n2. Remove email from all mailboxes\n3. Update email filters'
                    },
                    {
                        'step': 4,
                        'title': 'User Communication',
                        'description': 'Notify affected users',
                        'actions': '1. Send security alert\n2. Provide guidance\n3. Request additional reports'
                    }
                ],
                'checklists': ['Email headers analyzed', 'Attachments scanned', 'Users notified'],
                'escalation_criteria': ['Credentials compromised', 'Malware executed', 'Data exfiltration detected'],
                'author': 'SOC Team',
                'version': '1.0',
                'tags': ['phishing', 'email', 'social-engineering'],
                'created_at': datetime.utcnow().isoformat()
            },
            {
                'playbook_id': 'PB-MALWARE-001',
                'title': 'Malware Infection Response',
                'description': 'Procedure for responding to confirmed malware infections',
                'incident_type': 'malware',
                'severity': 'HIGH',
                'phase': 'containment',
                'procedures': [
                    {
                        'step': 1,
                        'title': 'Isolate System',
                        'description': 'Immediately isolate infected system',
                        'actions': '1. Disconnect from network\n2. Disable wireless\n3. Document system state'
                    },
                    {
                        'step': 2,
                        'title': 'Identify Malware',
                        'description': 'Determine malware type and capabilities',
                        'actions': '1. Collect samples\n2. Analyze with sandbox\n3. Check threat intel'
                    },
                    {
                        'step': 3,
                        'title': 'Eradication',
                        'description': 'Remove malware from system',
                        'actions': '1. Run AV scan\n2. Remove persistence mechanisms\n3. Verify removal'
                    },
                    {
                        'step': 4,
                        'title': 'Recovery',
                        'description': 'Restore system to normal operation',
                        'actions': '1. Patch vulnerabilities\n2. Reset credentials\n3. Monitor for reinfection'
                    }
                ],
                'checklists': ['System isolated', 'Malware identified', 'IOCs documented', 'System cleaned'],
                'escalation_criteria': ['Ransomware detected', 'Data exfiltration', 'Lateral movement observed'],
                'author': 'SOC Team',
                'version': '1.0',
                'tags': ['malware', 'incident-response', 'containment'],
                'created_at': datetime.utcnow().isoformat()
            }
        ]
    
    async def process_document(self, raw_doc: Dict[str, Any]) -> List[DocumentChunk]:
        """Process playbook into chunks"""
        try:
            doc_id = f"playbook_{raw_doc['playbook_id']}"
            
            # Use specialized playbook chunker
            chunks = self.chunker.chunk_playbook(raw_doc)
            
            # Convert to DocumentChunk objects
            document_chunks = []
            for chunk in chunks:
                doc_chunk = DocumentChunk(
                    chunk_id=f"{doc_id}_chunk_{chunk['chunk_index']}",
                    doc_id=doc_id,
                    content=chunk['content'],
                    metadata={
                        **chunk.get('metadata', {}),
                        'source_type': 'playbooks',
                        'playbook_id': raw_doc['playbook_id'],
                        'incident_type': raw_doc['incident_type'],
                        'severity': raw_doc['severity'],
                        'phase': raw_doc['phase'],
                        'tags': raw_doc.get('tags', [])
                    },
                    source_type='playbooks',
                    chunk_index=chunk['chunk_index'],
                    total_chunks=len(chunks)
                )
                document_chunks.append(doc_chunk)
            
            return document_chunks
            
        except Exception as e:
            self.logger.error(f"Failed to process playbook: {e}")
            return []
    
    async def validate_document(self, raw_doc: Dict[str, Any]) -> bool:
        """Validate playbook document"""
        required_fields = ['playbook_id', 'title', 'incident_type']
        
        for field in required_fields:
            if not raw_doc.get(field):
                self.logger.warning(f"Missing required field: {field}")
                return False
        
        return True
    
    def extract_metadata(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from playbook"""
        return {
            'playbook_id': raw_doc.get('playbook_id'),
            'title': raw_doc.get('title'),
            'incident_type': raw_doc.get('incident_type'),
            'severity': raw_doc.get('severity'),
            'phase': raw_doc.get('phase'),
            'author': raw_doc.get('author'),
            'version': raw_doc.get('version'),
            'tags': raw_doc.get('tags', [])
        }


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(PlaybookIngestor().ingest())
