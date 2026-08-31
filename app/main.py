"""
ThreatLens - FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import auth, health, ingest, query
from app.config import settings
from app.core.cache import close_redis
from app.core.errors import register_exception_handlers
from app.core.limiter import limiter
from app.core.logging_config import configure_logging
from app.core.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from app.database.bootstrap import create_bootstrap_admin
from app.database.postgres import close_postgres, init_postgres
from app.retrieval.vector_store import init_qdrant

configure_logging()
logger = logging.getLogger(__name__)

from app import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting ThreatLens (env=%s)...", settings.environment)
    try:
        await init_postgres()
        await init_qdrant()
        await create_bootstrap_admin()
        logger.info("Initialization complete")
        yield
    finally:
        logger.info("Shutting down ThreatLens...")
        await close_postgres()
        await close_redis()


app = FastAPI(
    title="ThreatLens",
    description="Production-grade RAG-based Security Analysis System for SOC Analysts",
    version=__version__,
    lifespan=lifespan,
    # Interactive docs are disabled in production to reduce attack surface.
    docs_url="/docs" if settings.expose_docs else None,
    redoc_url="/redoc" if settings.expose_docs else None,
    openapi_url="/openapi.json" if settings.expose_docs else None,
)

# --- Rate limiting -----------------------------------------------------------
app.state.limiter = limiter

async def _safe_rate_limit_handler(request, exc):
    detail = getattr(exc, "detail", str(exc))
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=429, content={"detail": f"Rate limit exceeded: {detail}"})

app.add_exception_handler(RateLimitExceeded, _safe_rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

# --- Security & transport middleware ----------------------------------------
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    max_age=600,
)

# --- Error handling ----------------------------------------------------------
register_exception_handlers(app)

# --- Metrics (Prometheus at /metrics) ---------------------------------------
Instrumentator().instrument(app).expose(app, include_in_schema=False)

# --- Routes ------------------------------------------------------------------
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(query.router, prefix="/api/v1", tags=["query"])
app.include_router(ingest.router, prefix="/api/v1", tags=["ingestion"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "ThreatLens API",
        "version": __version__,
        "docs": "/docs" if settings.expose_docs else "disabled",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
