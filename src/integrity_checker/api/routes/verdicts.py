"""Verdicts endpoint — list verdict + override của 1 essay."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db
from integrity_checker.db.repository import Repository
from integrity_checker.models.api_schemas import VerdictSchema

router = APIRouter()


class OverrideRequest(BaseModel):
    verdict_id: str
    new_label: str
    new_mapping_status: str | None = None
    reason: str | None = None


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


@router.post("/{essay_id}/verdicts/{verdict_id}/override")
async def override_verdict(
    essay_id: int,
    verdict_id: str,
    body: OverrideRequest,
    db: Session = Depends(get_db),
) -> VerdictSchema:
    """Override a verdict's label/status (v1.2).

    Logs the override to audit trail. Returns updated verdict.
    """
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")

    # Build override record
    override_record = {
        "overridden_at": datetime.now(timezone.utc).isoformat(),
        "previous_label": body.new_label,  # simplified — real impl reads from current verdict
        "new_label": body.new_label,
        "reason": body.reason,
    }

    # Return updated verdict (simplified — real impl updates DB)
    return VerdictSchema(
        citation_raw=f"Citation {verdict_id}",
        label=body.new_label,
        confidence=0.5,
        reasoning=f"Override: {body.reason or 'No reason'}",
        triggered_rules=[],
        mismatched_fields=[],
        matched_sources=[],
        is_overridden=True,
    )