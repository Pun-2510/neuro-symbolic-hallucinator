"""Export routes (admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db, require_admin
from integrity_checker.db.models import User, VerdictRecord
from integrity_checker.db.repository import Repository

router = APIRouter()


@router.get("/report")
def get_system_report(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get full system report (admin only)."""
    repo = Repository(db)

    # Users summary
    users = repo.get_all_users()
    user_summaries = [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]

    # Essays summary
    essays = repo.get_all_essays()
    essay_summaries = [
        {
            "id": e.id,
            "filename": e.filename,
            "user_id": e.user_id,
            "num_pages": e.num_pages,
            "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
        }
        for e in essays
    ]

    # Verdicts summary
    verdicts = db.query(VerdictRecord).all()
    verdict_counts = {}
    for v in verdicts:
        label = v.label
        verdict_counts[label] = verdict_counts.get(label, 0) + 1

    # Cache stats
    cache_stats = repo.get_cache_stats()

    return JSONResponse({
        "users": {
            "total": len(users),
            "admins": len([u for u in users if u.role == "admin"]),
            "users": len([u for u in users if u.role == "user"]),
            "list": user_summaries,
        },
        "essays": {
            "total": len(essays),
            "list": essay_summaries,
        },
        "verdicts": {
            "total": len(verdicts),
            "by_label": verdict_counts,
        },
        "cache": cache_stats,
    })
