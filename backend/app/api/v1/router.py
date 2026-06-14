"""V1 API router — combines all route modules under one prefix."""
from fastapi import APIRouter

from app.api.v1.routes import alerts, auth, ecosystem, forecasts, lanes, signals

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(signals.router)
api_router.include_router(forecasts.router)
api_router.include_router(lanes.router)
api_router.include_router(alerts.router)
api_router.include_router(ecosystem.router)
