"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from integrity_checker.config import get_settings
from integrity_checker.models.api_schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=settings.app.version,
        disclaimer=settings.disclaimer.short,
    )