"""FastAPI routers."""

from integrity_checker.api.routes import auth, essays, health, report, users, verdicts

__all__ = ["auth", "essays", "health", "report", "users", "verdicts"]