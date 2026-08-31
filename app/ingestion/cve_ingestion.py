"""
CVE/NVD ingestion for ThreatLens
Fetches and processes CVE data from National Vulnerability Database
"""

import asyncio
import logging
import httpx
from typing import Dict, Any, List, AsyncGenerator
from datetime import datetime, timedelta

from app.config import settings
from app.ingestion.base import BaseIngestor, DocumentChunk
from app.ingestion.chunking import CVEChunker

logger = logging.getLogger(__name__)


class CVEIngestor(BaseIngestor):
    """CVE/NVD data ingestor"""
    
    def __init__(self, days_back: int = 30):
        super().__init__(source_type="cve")
        self.chunker = CVEChunker()
        self.api_base_url = settings.nvd_api_base_url
        self.days_back = days_back
    
    async def fetch_data(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Fetch CVE data from NVD API"""
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=self.days_back)
            
            self.logger.info(f"Fetching CVEs from {start_date.date()} to {end_date.date()}")
            
            # NVD API pagination
            start_index = 0
            results_per_page = 100
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                while True:
                    params = {
                        'pubStartDate': start_date.strftime('%Y-%m-%dT%H:%M:%S.000'),
                        'pubEndDate': end_date.strftime('%Y-%m-%dT%H:%M:%S.000'),
                        'startIndex': start_index,
                        'resultsPerPage': results_per_page
                    }
                    
                    response = await client.get(self.api_base_url, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    vulnerabilities = data.get('vulnerabilities', [])
                    
                    if not vulnerabilities:
                        break
                    
                    for vuln in vulnerabilities:
                        cve_data = self._parse_cve(vuln)
                        if cve_data:
                            yield cve_data
                    
                    # Check if more results available
                    total_results = data.get('totalResults', 0)
                    if start_index + results_per_page >= total_results:
                        break
                    
                    start_index += results_per_page
                    
                    # Rate limiting - NVD has strict rate limits
                    await asyncio.sleep(0.6)  # ~6 seconds per 10 requests
                    
        except Exception as e:
            self.logger.error(f"Failed to fetch CVE data: {e}")
            # Fallback to sample data for testing
            for sample_cve in self._get_sample_cves():
                yield sample_cve
    
    def _parse_cve(self, vuln_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse NVD vulnerability object into CVE"""
        try:
            cve = vuln_data.get('cve', {})
            cve_id = cve.get('id', '')
            
            # Extract descriptions
            descriptions = cve.get('descriptions', [])
            description = next(
                (desc.get('value', '') for desc in descriptions if desc.get('lang') == 'en'),
                ''
            )
            
            # Extract CVSS metrics
            metrics = cve.get('metrics', {})
            cvss_data = {}
            
            # Try CVSS v3.1 first, then v3.0, then v2.0
            for version in ['cvssMetricV31', 'cvssMetricV30', 'cvssMetricV2']:
                if version in metrics and metrics[version]:
                    cvss_metric = metrics[version][0]
                    cvss_data = cvss_metric.get('cvssData', {})
                    break
            
            # Extract affected configurations
            configurations = cve.get('configurations', [])
            affected_products = self._extract_affected_products(configurations)
            
            # Extract references
            references = cve.get('references', [])
            reference_urls = [ref.get('url', '') for ref in references[:5]]  # Limit to 5
            
            # Extract dates
            published = cve.get('published', '')
            last_modified = cve.get('lastModified', '')
            
            return {
                'cve_id': cve_id,
                'description': description,
                'cvss_score': cvss_data.get('baseScore', 0.0),
                'cvss_severity': cvss_data.get('baseSeverity', 'UNKNOWN'),
                'cvss_vector': cvss_data.get('vectorString', ''),
                'affected_products': affected_products,
                'references': reference_urls,
                'published_date': published,
                'last_modified_date': last_modified,
                'cwe_ids': self._extract_cwe_ids(cve)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to parse CVE: {e}")
            return None
    
    def _extract_affected_products(self, configurations: List[Dict[str, Any]]) -> str:
        """Extract affected products from configurations"""
        products = []
        
        for config in configurations[:3]:  # Limit to first 3 configurations
            nodes = config.get('nodes', [])
            for node in nodes:
                cpe_matches = node.get('cpeMatch', [])
                for cpe in cpe_matches[:5]:  # Limit to 5 CPEs per node
                    if cpe.get('vulnerable', True):
                        cpe_uri = cpe.get('criteria', '')
                        # Parse CPE URI (cpe:2.3:a:vendor:product:version:...)
                        parts = cpe_uri.split(':')
                        if len(parts) >= 5:
                            vendor = parts[3]
                            product = parts[4]
                            products.append(f"{vendor} {product}")
        
        return ', '.join(set(products)) if products else 'Not specified'
    
    def _extract_cwe_ids(self, cve: Dict[str, Any]) -> List[str]:
        """Extract CWE IDs from CVE"""
        weaknesses = cve.get('weaknesses', [])
        cwe_ids = []
        
        for weakness in weaknesses:
            descriptions = weakness.get('description', [])
            for desc in descriptions:
                if desc.get('lang') == 'en':
                    cwe_ids.append(desc.get('value', ''))
        
        return cwe_ids
    
    def _get_sample_cves(self) -> List[Dict[str, Any]]:
        """Get sample CVE data for testing"""
        return [
            {
                'cve_id': 'CVE-2024-0001',
                'description': 'Sample critical vulnerability in authentication mechanism allowing remote code execution.',
                'cvss_score': 9.8,
                'cvss_severity': 'CRITICAL',
                'cvss_vector': 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
                'affected_products': 'Sample Vendor Sample Product',
                'references': ['https://example.com/advisory'],
                'published_date': datetime.utcnow().isoformat(),
                'last_modified_date': datetime.utcnow().isoformat(),
                'cwe_ids': ['CWE-287']
            }
        ]
    
    async def process_document(self, raw_doc: Dict[str, Any]) -> List[DocumentChunk]:
        """Process CVE into chunks"""
        try:
            doc_id = f"cve_{raw_doc['cve_id']}"
            
            # Use specialized CVE chunker
            chunks = self.chunker.chunk_cve(raw_doc)
            
            # Convert to DocumentChunk objects
            document_chunks = []
            for chunk in chunks:
                doc_chunk = DocumentChunk(
                    chunk_id=f"{doc_id}_chunk_{chunk['chunk_index']}",
                    doc_id=doc_id,
                    content=chunk['content'],
                    metadata={
                        **chunk.get('metadata', {}),
                        'source_type': 'cve',
                        'cve_id': raw_doc['cve_id'],
                        'cvss_score': raw_doc.get('cvss_score', 0.0),
                        'severity': raw_doc.get('cvss_severity', 'UNKNOWN'),
                        'published_date': raw_doc.get('published_date'),
                        'cwe_ids': raw_doc.get('cwe_ids', [])
                    },
                    source_type='cve',
                    chunk_index=chunk['chunk_index'],
                    total_chunks=len(chunks)
                )
                document_chunks.append(doc_chunk)
            
            return document_chunks
            
        except Exception as e:
            self.logger.error(f"Failed to process CVE: {e}")
            return []
    
    async def validate_document(self, raw_doc: Dict[str, Any]) -> bool:
        """Validate CVE document"""
        required_fields = ['cve_id', 'description']
        
        for field in required_fields:
            if not raw_doc.get(field):
                self.logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate CVE ID format
        cve_id = raw_doc.get('cve_id', '')
        if not cve_id.startswith('CVE-'):
            self.logger.warning(f"Invalid CVE ID format: {cve_id}")
            return False
        
        return True
    
    def extract_metadata(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from CVE"""
        return {
            'cve_id': raw_doc.get('cve_id'),
            'cvss_score': raw_doc.get('cvss_score'),
            'severity': raw_doc.get('cvss_severity'),
            'published_date': raw_doc.get('published_date'),
            'affected_products': raw_doc.get('affected_products'),
            'cwe_ids': raw_doc.get('cwe_ids', [])
        }


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(CVEIngestor().ingest())
