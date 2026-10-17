"""System health endpoint (admin only) — Phase 4."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db, require_admin
from integrity_checker.db.models import User, VerdictRecord
from integrity_checker.db.repository import Repository

router = APIRouter()


@router.get("/health")
def get_system_health(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    repo = Repository(db)
    users = repo.get_all_users()
    essays = repo.get_all_essays()
    verdicts = db.query(VerdictRecord).all()
    label_counts: dict[str, int] = {}
    for v in verdicts:
        label_counts[v.label] = label_counts.get(v.label, 0) + 1
    cache_stats = repo.get_cache_stats()
    return {
        "status": "ok",
        "totals": {
            "users": len(users),
            "admins": sum(1 for u in users if u.role == "admin"),
            "teachers": sum(1 for u in users if u.role == "teacher"),
            "students": sum(1 for u in users if u.role == "user"),
            "essays": len(essays),
            "verdicts": len(verdicts),
        },
        "verdict_label_counts": label_counts,
        "cache_stats": cache_stats,
    }
