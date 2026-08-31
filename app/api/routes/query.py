"""
Query endpoints for ThreatLens RAG system.

All endpoints require authentication (API key or JWT). Errors are sanitised by
the global exception handlers; query history is persisted best-effort.
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.dependencies import Principal, get_current_principal
from app.config import settings
from app.database.models import QueryHistory
from app.database.postgres import session_scope
from app.retrieval.rag_pipeline import get_rag_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()

_ALLOWED_SOURCE_TYPES = {"mitre", "cve", "logs", "playbooks"}


class QueryRequest(BaseModel):
    """Request model for RAG queries."""
    query: str = Field(min_length=1, max_length=settings.max_query_length)
    top_k: int = Field(default=10, ge=1, le=50)
    rerank_top_k: int = Field(default=5, ge=1, le=20)
    source_types: Optional[List[str]] = None  # mitre, cve, logs, playbooks
    filters: Optional[Dict[str, Any]] = None
    stream: bool = False


class QueryResponse(BaseModel):
    """Response model for RAG queries."""
    success: bool
    answer: str = ""
    sources: List[Dict[str, Any]] = []
    confidence_score: float = 0.0
    token_count: Optional[int] = None
    response_time_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    issues: Optional[List[str]] = None


def _validate_source_types(source_types: Optional[List[str]]) -> Optional[List[str]]:
    if not source_types:
        return None
    invalid = [s for s in source_types if s not in _ALLOWED_SOURCE_TYPES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source_types: {invalid}. "
            f"Allowed: {sorted(_ALLOWED_SOURCE_TYPES)}",
        )
    return source_types


async def _persist_history(
    principal: Principal, query: str, response: Dict[str, Any]
) -> None:
    """Best-effort persistence of a completed query for analytics."""
    if not response.get("success"):
        return
    try:
        async with session_scope() as session:
            session.add(
                QueryHistory(
                    session_id=principal.subject or "anonymous",
                    user_query=query,
                    retrieved_docs=[
                        s.get("doc_id") for s in response.get("sources", [])
                    ],
                    llm_response=response.get("answer", ""),
                    response_time_ms=response.get("response_time_ms"),
                    token_count=response.get("token_count"),
                    groundedness_score=response.get("confidence_score"),
                    hallucination_detected=bool(
                        response.get("metadata", {})
                        .get("validation", {})
                        .get("hallucination_detected", False)
                    ),
                )
            )
    except Exception as exc:  # noqa: BLE001 - analytics must not break queries
        logger.warning("Failed to persist query history: %s", exc)


async def _run_query(request: QueryRequest, principal: Principal) -> QueryResponse:
    source_types = _validate_source_types(request.source_types)
    rag_pipeline = get_rag_pipeline()
    response = await rag_pipeline.query(
        query=request.query,
        top_k=request.top_k,
        rerank_top_k=request.rerank_top_k,
        source_types=source_types,
        filters=request.filters,
    )
    if not response.get("success") and response.get("error") == "Input validation failed":
        raise HTTPException(
            status_code=400,
            detail={"message": "Input validation failed", "issues": response.get("issues", [])},
        )
    await _persist_history(principal, request.query, response)
    return QueryResponse(**response)


@router.post("/query", response_model=QueryResponse)
async def rag_query(
    request: QueryRequest, principal: Principal = Depends(get_current_principal)
):
    """Main RAG query endpoint."""
    logger.info("Processing query (len=%d)", len(request.query))
    return await _run_query(request, principal)


@router.post("/query/stream")
async def rag_query_stream(
    request: QueryRequest, principal: Principal = Depends(get_current_principal)
):
    """Streaming RAG query endpoint (Server-Sent Events)."""
    source_types = _validate_source_types(request.source_types)
    rag_pipeline = get_rag_pipeline()
    logger.info("Processing streaming query (len=%d)", len(request.query))

    async def generate():
        try:
            async for chunk in rag_pipeline.query_stream(
                query=request.query,
                top_k=request.top_k,
                rerank_top_k=request.rerank_top_k,
                source_types=source_types,
                filters=request.filters,
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception:  # noqa: BLE001
            logger.exception("SSE stream failed")
            err = {"type": "error", "error": "Internal server error", "error_id": uuid.uuid4().hex}
            yield f"data: {json.dumps(err)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/alert/explain", response_model=QueryResponse)
async def explain_alert(
    request: QueryRequest, principal: Principal = Depends(get_current_principal)
):
    """Explain a security alert."""
    response = await get_rag_pipeline().explain_alert(
        alert_description=request.query, top_k=request.top_k
    )
    await _persist_history(principal, request.query, response)
    return QueryResponse(**response)


@router.post("/cve/lookup", response_model=QueryResponse)
async def lookup_cve(
    request: QueryRequest, principal: Principal = Depends(get_current_principal)
):
    """Lookup CVE information."""
    response = await get_rag_pipeline().lookup_cve(
        cve_query=request.query, top_k=request.top_k
    )
    await _persist_history(principal, request.query, response)
    return QueryResponse(**response)


@router.post("/incident/guidance", response_model=QueryResponse)
async def incident_response_guidance(
    request: QueryRequest, principal: Principal = Depends(get_current_principal)
):
    """Get incident response guidance."""
    response = await get_rag_pipeline().get_incident_response_guidance(
        incident_description=request.query, top_k=request.top_k
    )
    await _persist_history(principal, request.query, response)
    return QueryResponse(**response)


@router.post("/threat/intel", response_model=QueryResponse)
async def threat_intelligence(
    request: QueryRequest, principal: Principal = Depends(get_current_principal)
):
    """Query threat intelligence."""
    response = await get_rag_pipeline().threat_intelligence_query(
        threat_query=request.query, top_k=request.top_k
    )
    await _persist_history(principal, request.query, response)
    return QueryResponse(**response)
