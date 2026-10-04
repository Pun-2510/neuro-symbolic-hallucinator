"""FastAPI app factory + startup."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from integrity_checker.api.routes import auth, cache, essays, export, health, report, users, verdicts
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

    # Ensure avatars directory exists before mounting
    from pathlib import Path

    avatars_dir = Path("data/avatars")
    avatars_dir.mkdir(parents=True, exist_ok=True)

    # Serve uploaded avatars (user-uploaded profile pictures)
    # Use HTML5Mode fallback so 404s return index.html instead of error
    app.mount(
        "/api/avatars",
        StaticFiles(directory=str(avatars_dir), html=True),
        name="avatars",
    )
    logger.info("Avatar static mount registered at /api/avatars")

    # Mount routes
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(cache.router, prefix="/api/cache", tags=["cache"])
    app.include_router(users.router, prefix="/api/users", tags=["users"])
    app.include_router(essays.router, prefix="/api/essays", tags=["essays"])
    app.include_router(verdicts.router, prefix="/api/essays", tags=["verdicts"])
    app.include_router(report.router, prefix="/api/essays", tags=["report"])
    app.include_router(export.router, prefix="/api/export", tags=["export"])

    return app


# Module-level app cho uvicorn
app = create_app()
