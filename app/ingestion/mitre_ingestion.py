"""
MITRE ATT&CK ingestion for ThreatLens
Downloads and processes MITRE ATT&CK STIX 2.1 data
"""

import logging
import httpx
import json
from typing import Dict, Any, List, AsyncGenerator
from datetime import datetime

from app.config import settings
from app.ingestion.base import BaseIngestor, DocumentChunk
from app.ingestion.chunking import MITREChunker

logger = logging.getLogger(__name__)


class MITREIngestor(BaseIngestor):
    """MITRE ATT&CK data ingestor"""
    
    def __init__(self):
        super().__init__(source_type="mitre")
        self.chunker = MITREChunker()
        self.data_url = settings.mitre_data_url
    
    async def fetch_data(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Fetch MITRE ATT&CK data from GitHub"""
        try:
            self.logger.info(f"Fetching MITRE ATT&CK data from {self.data_url}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(self.data_url)
                response.raise_for_status()
                
                stix_data = response.json()
                
                # Extract techniques from STIX bundle
                for obj in stix_data.get('objects', []):
                    if obj.get('type') == 'attack-pattern':
                        yield self._parse_technique(obj)
                        
        except Exception as e:
            self.logger.error(f"Failed to fetch MITRE data: {e}")
            raise
    
    def _parse_technique(self, stix_obj: Dict[str, Any]) -> Dict[str, Any]:
        """Parse STIX attack-pattern object into technique"""
        # Extract external references
        external_refs = stix_obj.get('external_references', [])
        mitre_ref = next(
            (ref for ref in external_refs if ref.get('source_name') == 'mitre-attack'),
            {}
        )
        
        # Extract kill chain phases (tactics)
        kill_chain_phases = stix_obj.get('kill_chain_phases', [])
        tactics = [phase.get('phase_name', '') for phase in kill_chain_phases]
        
        # Extract platforms
        platforms = stix_obj.get('x_mitre_platforms', [])
        
        # Extract data sources
        data_sources = stix_obj.get('x_mitre_data_sources', [])
        
        # Extract detection
        detection = stix_obj.get('x_mitre_detection', '')
        
        # Build technique object
        technique = {
            'id': mitre_ref.get('external_id', ''),
            'name': stix_obj.get('name', ''),
            'description': stix_obj.get('description', ''),
            'tactics': tactics,
            'platforms': platforms,
            'data_sources': data_sources,
            'detection': detection,
            'url': mitre_ref.get('url', ''),
            'created': stix_obj.get('created', ''),
            'modified': stix_obj.get('modified', ''),
            'permissions_required': stix_obj.get('x_mitre_permissions_required', []),
            'defenses_bypassed': stix_obj.get('x_mitre_defense_bypassed', []),
            'is_subtechnique': '.' in mitre_ref.get('external_id', '')
        }
        
        return technique
    
    async def process_document(self, raw_doc: Dict[str, Any]) -> List[DocumentChunk]:
        """Process MITRE technique into chunks"""
        try:
            doc_id = f"mitre_{raw_doc['id']}"
            
            # Use specialized MITRE chunker
            chunks = self.chunker.chunk_technique(raw_doc)
            
            # Convert to DocumentChunk objects
            document_chunks = []
            for chunk in chunks:
                doc_chunk = DocumentChunk(
                    chunk_id=f"{doc_id}_chunk_{chunk['chunk_index']}",
                    doc_id=doc_id,
                    content=chunk['content'],
                    metadata={
                        **chunk.get('metadata', {}),
                        'source_type': 'mitre',
                        'chunk_type': chunk.get('chunk_type', 'general'),
                        'technique_id': raw_doc['id'],
                        'technique_name': raw_doc['name'],
                        'tactics': raw_doc.get('tactics', []),
                        'platforms': raw_doc.get('platforms', []),
                        'is_subtechnique': raw_doc.get('is_subtechnique', False)
                    },
                    source_type='mitre',
                    chunk_index=chunk['chunk_index'],
                    total_chunks=len(chunks)
                )
                document_chunks.append(doc_chunk)
            
            return document_chunks
            
        except Exception as e:
            self.logger.error(f"Failed to process MITRE technique: {e}")
            return []
    
    async def validate_document(self, raw_doc: Dict[str, Any]) -> bool:
        """Validate MITRE technique document"""
        required_fields = ['id', 'name', 'description']
        
        for field in required_fields:
            if not raw_doc.get(field):
                self.logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate technique ID format (T1234 or T1234.001)
        technique_id = raw_doc.get('id', '')
        if not technique_id.startswith('T'):
            self.logger.warning(f"Invalid technique ID format: {technique_id}")
            return False
        
        return True
    
    def extract_metadata(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from MITRE technique"""
        return {
            'technique_id': raw_doc.get('id'),
            'technique_name': raw_doc.get('name'),
            'tactics': raw_doc.get('tactics', []),
            'platforms': raw_doc.get('platforms', []),
            'data_sources': raw_doc.get('data_sources', []),
            'is_subtechnique': raw_doc.get('is_subtechnique', False),
            'created': raw_doc.get('created'),
            'modified': raw_doc.get('modified'),
            'url': raw_doc.get('url')
        }
    
    async def get_technique_by_id(self, technique_id: str) -> Dict[str, Any]:
        """Get specific technique by ID"""
        async for technique in self.fetch_data():
            if technique['id'] == technique_id:
                return technique
        return None


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(MITREIngestor().ingest())
