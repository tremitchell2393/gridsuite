"""
GridSuite API — application entrypoint.

Run locally with: `uvicorn app.main:app --reload`
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Supply chain intelligence platform API",
    version="0.1.0",
    docs_url="/docs",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
def health_check():
    """Basic liveness check — used by uptime monitoring."""
    return {"status": "ok", "app": settings.APP_NAME, "environment": settings.ENVIRONMENT}
