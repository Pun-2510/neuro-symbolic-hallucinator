"""System health endpoint (admin only) — Phase 4."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db, require_admin
from integrity_checker.db.models import EssayRecord, User, VerdictRecord
from integrity_checker.db.repository import Repository

router = APIRouter()


@router.get("/health")
def get_system_health(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    repo = Repository(db)
    role_counts: dict[str, int] = {}
    for role, cnt in (
        db.query(User.role, func.count(User.id)).group_by(User.role).all()
    ):
        if role:
            role_counts[str(role)] = int(cnt or 0)
    total_users = sum(role_counts.values())
    total_essays = int(db.query(func.count(EssayRecord.id)).scalar() or 0)

    label_counts: dict[str, int] = {}
    for label, cnt in (
        db.query(VerdictRecord.label, func.count(VerdictRecord.id))
        .group_by(VerdictRecord.label)
        .all()
    ):
        if label:
            label_counts[str(label)] = int(cnt or 0)
    total_verdicts = sum(label_counts.values())

    cache_stats = repo.get_cache_stats()
    return {
        "status": "ok",
        "totals": {
            "users": total_users,
            "admins": role_counts.get("admin", 0),
            "teachers": role_counts.get("teacher", 0),
            "students": role_counts.get("user", 0),
            "essays": total_essays,
            "verdicts": total_verdicts,
        },
        "verdict_label_counts": label_counts,
        "cache_stats": cache_stats,
    }
