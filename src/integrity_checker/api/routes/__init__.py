"""FastAPI routers."""

from integrity_checker.api.routes import auth, essays, health, report, verdicts

__all__ = ["auth", "essays", "health", "report", "verdicts"]