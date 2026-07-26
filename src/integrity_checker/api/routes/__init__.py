"""FastAPI routers."""

from integrity_checker.api.routes import essays, health, report, verdicts

__all__ = ["essays", "health", "report", "verdicts"]