"""Verdicts endpoint — list verdict của 1 essay."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db
from integrity_checker.db.repository import Repository
from integrity_checker.models.api_schemas import VerdictSchema

router = APIRouter()


@router.get("/{essay_id}/verdicts")
async def get_verdicts(
    essay_id: int,
    db: Session = Depends(get_db),
) -> list[VerdictSchema]:
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")

    records = repo.get_verdicts(essay_id)
    return [
        VerdictSchema(
            citation_raw=r.citation_raw,
            label=r.label,
            confidence=r.confidence,
            reasoning=r.reasoning,
            triggered_rules=json.loads(r.triggered_rules or "[]"),
            mismatched_fields=json.loads(r.mismatched_fields or "[]"),
            matched_sources=json.loads(r.features or "{}"),
            is_overridden=False,
        )
        for r in records
    ]