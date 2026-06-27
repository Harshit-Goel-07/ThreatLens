"""
Health check endpoints for Security Copilot
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_async_session, check_postgres_health
from app.retrieval.vector_store import check_qdrant_health

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "security-copilot",
        "version": "0.1.0"
    }


@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_async_session)):
    """Detailed health check with service status"""
    postgres_healthy = await check_postgres_health()
    qdrant_healthy = await check_qdrant_health()
    
    overall_status = "healthy" if postgres_healthy and qdrant_healthy else "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "security-copilot",
        "version": "0.1.0",
        "services": {
            "postgres": {
                "status": "healthy" if postgres_healthy else "unhealthy",
                "description": "PostgreSQL metadata database"
            },
            "qdrant": {
                "status": "healthy" if qdrant_healthy else "unhealthy", 
                "description": "Qdrant vector database"
            }
        }
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_async_session)):
    """Readiness check for Kubernetes/liveness probes"""
    postgres_healthy = await check_postgres_health()
    qdrant_healthy = await check_qdrant_health()
    
    if postgres_healthy and qdrant_healthy:
        return {"status": "ready"}
    else:
        return {"status": "not_ready"}
