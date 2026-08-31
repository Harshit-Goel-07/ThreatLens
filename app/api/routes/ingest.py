"""
Ingestion endpoints for ThreatLens data sources.

Ingestion mutates the knowledge base, so every endpoint requires *admin*
privileges. Jobs run in the background and their status is tracked in the
``ingestion_jobs`` table.
"""

import logging
import uuid
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import Principal, require_admin
from app.database.models import IngestionJob
from app.database.postgres import session_scope

logger = logging.getLogger(__name__)

router = APIRouter()


class IngestionRequest(BaseModel):
    """Request model for data ingestion."""
    source_type: str = Field(pattern="^(mitre|cve|logs|playbooks)$")
    force_refresh: bool = False
    batch_size: int = Field(default=100, ge=1, le=1000)


class IngestionStatus(BaseModel):
    """Status model for ingestion jobs."""
    job_id: str
    source_type: str
    status: str  # pending, running, completed, failed
    progress: float
    total_items: int
    processed_items: int
    failed_items: int
    error_message: Optional[str] = None


def _build_ingestor(source_type: str):
    from app.ingestion.cve_ingestion import CVEIngestor
    from app.ingestion.log_ingestion import SecurityLogIngestor
    from app.ingestion.mitre_ingestion import MITREIngestor
    from app.ingestion.playbook_ingestion import PlaybookIngestor

    return {
        "mitre": MITREIngestor,
        "cve": CVEIngestor,
        "logs": SecurityLogIngestor,
        "playbooks": PlaybookIngestor,
    }[source_type]()


async def _update_job(job_id: str, **fields) -> None:
    from sqlalchemy import update

    async with session_scope() as session:
        await session.execute(
            update(IngestionJob).where(IngestionJob.job_id == job_id).values(**fields)
        )


async def _run_ingestion_job(job_id: str, source_type: str, batch_size: int) -> None:
    await _update_job(job_id, status="running", progress=0.0)
    try:
        ingestor = _build_ingestor(source_type)
        result = await ingestor.ingest(batch_size=batch_size)
        await _update_job(
            job_id,
            status="completed" if result.success else "failed",
            progress=1.0,
            total_items=result.documents_processed,
            processed_items=result.documents_processed,
            failed_items=len(result.errors),
            error_message="; ".join(result.errors[:5]) if result.errors else None,
        )
        logger.info("Ingestion %s completed: %s chunks", job_id, result.chunks_created)
    except Exception as exc:  # noqa: BLE001 - record failure in job row
        logger.exception("Ingestion job %s failed", job_id)
        await _update_job(job_id, status="failed", error_message=str(exc)[:500])


@router.get("/ingest/sources")
async def list_available_sources(_: Principal = Depends(require_admin)):
    """List available data sources for ingestion."""
    descriptions = {
        "mitre": "MITRE ATT&CK techniques and tactics",
        "cve": "CVE vulnerability database (NVD)",
        "logs": "Security logs (Sysmon, Windows Event, auditd)",
        "playbooks": "SOC incident response playbooks",
    }
    return {
        "sources": [
            {"name": name, "description": desc, "enabled": True}
            for name, desc in descriptions.items()
        ]
    }


@router.post("/ingest", response_model=Dict[str, str])
async def start_ingestion(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
    _: Principal = Depends(require_admin),
):
    """Start data ingestion for the specified source type (admin only)."""
    job_id = f"job_{request.source_type}_{uuid.uuid4().hex[:12]}"
    logger.info("Queuing ingestion job %s for %s", job_id, request.source_type)

    async with session_scope() as session:
        session.add(
            IngestionJob(
                job_id=job_id,
                source_type=request.source_type,
                status="pending",
                progress=0.0,
            )
        )

    background_tasks.add_task(
        _run_ingestion_job, job_id, request.source_type, request.batch_size
    )
    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"Ingestion job queued for {request.source_type}",
    }


@router.get("/ingest/{job_id}", response_model=IngestionStatus)
async def get_ingestion_status(job_id: str, _: Principal = Depends(require_admin)):
    """Get the status of an ingestion job."""
    from sqlalchemy import select

    async with session_scope() as session:
        result = await session.execute(
            select(IngestionJob).where(IngestionJob.job_id == job_id)
        )
        job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")

    return IngestionStatus(
        job_id=job.job_id,
        source_type=job.source_type,
        status=job.status,
        progress=job.progress or 0.0,
        total_items=job.total_items or 0,
        processed_items=job.processed_items or 0,
        failed_items=job.failed_items or 0,
        error_message=job.error_message,
    )
