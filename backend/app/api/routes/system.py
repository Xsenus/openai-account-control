"""Health and simple system routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from ...config import settings
from ...schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return process health and current UTC timestamp."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        now_utc=datetime.now(timezone.utc),
    )
