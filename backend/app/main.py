from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis
from qdrant_client import AsyncQdrantClient
import logging

from app.config import settings
from app.db import create_all_tables, engine

logger = logging.getLogger(__name__)


# ─── Lifespan: startup + shutdown ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──────────────────────────────────────────
    logger.info("TITAN AI OS starting up...")

    # 1. Create DB tables
    await create_all_tables()
    logger.info("PostgreSQL tables verified")

    # 2. Verify Redis connection
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    await redis_client.ping()
    app.state.redis = redis_client
    logger.info("Redis connected")

    # 3. Verify Qdrant connection
    qdrant_kwargs = {"host": settings.qdrant_host, "port": settings.qdrant_port}
    if settings.qdrant_api_key:
        qdrant_kwargs["api_key"] = settings.qdrant_api_key
        qdrant_kwargs["https"] = True
    qdrant_client = AsyncQdrantClient(**qdrant_kwargs)
    await qdrant_client.get_collections()
    app.state.qdrant = qdrant_client
    logger.info("Qdrant connected")

    logger.info("TITAN AI OS is ONLINE")
    yield

    # ── SHUTDOWN ─────────────────────────────────────────
    await redis_client.aclose()
    await qdrant_client.close()
    await engine.dispose()
    logger.info("TITAN AI OS shutdown complete")


# ─── App Initialization ───────────────────────────────────────────────────────
app = FastAPI(
    title="TITAN AI OS",
    description="Enterprise-grade Autonomous AI Operating System",
    version="0.1.0-mvp",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Returns system health status for all connected services."""
    checks = {}

    # Redis
    try:
        await app.state.redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Qdrant
    try:
        await app.state.qdrant.get_collections()
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = f"error: {e}"

    # PostgreSQL
    try:
        from sqlalchemy import text
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    all_healthy = all(v == "ok" for v in checks.values())

    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content={
            "status": "healthy" if all_healthy else "degraded",
            "version": "0.1.0-mvp",
            "app": settings.app_name,
            "env": settings.app_env,
            "services": checks,
        }
    )


@app.get("/", tags=["System"])
async def root():
    return {"message": "TITAN AI OS API is running", "docs": "/docs"}


# ─── Routers ──────────────────────────────────────────────────────────────────
from app.auth.router import router as auth_router
from app.chat.router import router as chat_router

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
