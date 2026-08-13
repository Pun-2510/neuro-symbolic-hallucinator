"""FastAPI app factory + startup."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from integrity_checker.api.routes import auth, essays, health, report, verdicts
from integrity_checker.config import get_settings
from integrity_checker.db.session import init_db
from integrity_checker.logging import configure_logging, get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """App factory — dễ test."""
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title="Essay Integrity Checker API",
        description=(
            "Citation-only validation. Decision-support for lecturers — "
            "KHÔNG tự động kết luận gian lận học thuật."
        ),
        version=settings.app.version,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Init DB (MVP)
    init_db()
    logger.info("Database initialized")

    # Mount routes
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(essays.router, prefix="/api/essays", tags=["essays"])
    app.include_router(verdicts.router, prefix="/api/essays", tags=["verdicts"])
    app.include_router(report.router, prefix="/api/essays", tags=["report"])

    return app


# Module-level app cho uvicorn
app = create_app()