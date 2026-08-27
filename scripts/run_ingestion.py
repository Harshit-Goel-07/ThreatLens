"""
Data ingestion script for Security Copilot
Runs all data ingestors and populates the vector database
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ingestion.mitre_ingestion import MITREIngestor
from app.ingestion.cve_ingestion import CVEIngestor
from app.ingestion.log_ingestion import SecurityLogIngestor
from app.ingestion.playbook_ingestion import PlaybookIngestor
from app.ingestion.embeddings import generate_and_store_embeddings
from app.retrieval.vector_store import COLLECTIONS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def ingest_mitre():
    """Ingest MITRE ATT&CK data"""
    logger.info("=" * 60)
    logger.info("Starting MITRE ATT&CK ingestion...")
    logger.info("=" * 60)
    
    try:
        ingestor = MITREIngestor()
        result = await ingestor.ingest(batch_size=50)
        
        logger.info(f"✓ MITRE ingestion completed")
        logger.info(f"  Documents processed: {result.documents_processed}")
        logger.info(f"  Chunks created: {result.chunks_created}")
        logger.info(f"  Errors: {len(result.errors)}")
        
        return result
    except Exception as e:
        logger.error(f"✗ MITRE ingestion failed: {e}")
        return None


async def ingest_cve():
    """Ingest CVE data"""
    logger.info("=" * 60)
    logger.info("Starting CVE ingestion...")
    logger.info("=" * 60)
    
    try:
        ingestor = CVEIngestor(days_back=30)
        result = await ingestor.ingest(batch_size=50)
        
        logger.info(f"✓ CVE ingestion completed")
        logger.info(f"  Documents processed: {result.documents_processed}")
        logger.info(f"  Chunks created: {result.chunks_created}")
        logger.info(f"  Errors: {len(result.errors)}")
        
        return result
    except Exception as e:
        logger.error(f"✗ CVE ingestion failed: {e}")
        return None


async def ingest_logs():
    """Ingest security logs"""
    logger.info("=" * 60)
    logger.info("Starting security log ingestion...")
    logger.info("=" * 60)
    
    try:
        ingestor = SecurityLogIngestor()
        result = await ingestor.ingest(batch_size=50)
        
        logger.info(f"✓ Log ingestion completed")
        logger.info(f"  Documents processed: {result.documents_processed}")
        logger.info(f"  Chunks created: {result.chunks_created}")
        logger.info(f"  Errors: {len(result.errors)}")
        
        return result
    except Exception as e:
        logger.error(f"✗ Log ingestion failed: {e}")
        return None


async def ingest_playbooks():
    """Ingest SOC playbooks"""
    logger.info("=" * 60)
    logger.info("Starting playbook ingestion...")
    logger.info("=" * 60)
    
    try:
        ingestor = PlaybookIngestor()
        result = await ingestor.ingest(batch_size=50)
        
        logger.info(f"✓ Playbook ingestion completed")
        logger.info(f"  Documents processed: {result.documents_processed}")
        logger.info(f"  Chunks created: {result.chunks_created}")
        logger.info(f"  Errors: {len(result.errors)}")
        
        return result
    except Exception as e:
        logger.error(f"✗ Playbook ingestion failed: {e}")
        return None


async def main():
    """Run all ingestion tasks"""
    logger.info("\n" + "=" * 60)
    logger.info("Security Copilot - Data Ingestion Pipeline")
    logger.info("=" * 60 + "\n")
    
    from app.database.postgres import init_postgres
    from app.retrieval.vector_store import init_qdrant

    await init_postgres()
    await init_qdrant()

    results = {}
    
    # Run ingestion tasks
    results['mitre'] = await ingest_mitre()
    results['cve'] = await ingest_cve()
    results['logs'] = await ingest_logs()
    results['playbooks'] = await ingest_playbooks()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Ingestion Summary")
    logger.info("=" * 60)
    
    total_docs = 0
    total_chunks = 0
    total_errors = 0
    
    for source_type, result in results.items():
        if result:
            total_docs += result.documents_processed
            total_chunks += result.chunks_created
            total_errors += len(result.errors)
            status = "✓ Success"
        else:
            status = "✗ Failed"
        
        logger.info(f"{source_type.upper():12} - {status}")
    
    logger.info("-" * 60)
    logger.info(f"Total documents: {total_docs}")
    logger.info(f"Total chunks: {total_chunks}")
    logger.info(f"Total errors: {total_errors}")
    logger.info("=" * 60 + "\n")
    
    if total_errors > 0:
        logger.warning(f"⚠ Ingestion completed with {total_errors} errors")
    else:
        logger.info("✓ All ingestion tasks completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
