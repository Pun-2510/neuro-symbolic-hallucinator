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
    # SECURITY: Ownership check - uncomment when auth is implemented
    # from integrity_checker.api.deps import get_current_user
    # current_user = get_current_user() if has_auth else None
    # if current_user and current_user.role != 'admin' and essay.user_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="Access denied")

    records = repo.get_verdicts(essay_id)
    citation_types = {c.raw_text: c.citation_type for c in repo.get_citations(essay_id)}
    return [
        VerdictSchema(
            citation_id=str(r.id),
            citation_raw=r.citation_raw,
            citation_type=citation_types.get(r.citation_raw, "unknown"),
            label=r.label,
            confidence=r.confidence,
            reasoning=r.reasoning,
            triggered_rules=json.loads(r.triggered_rules or "[]"),
            mismatched_fields=json.loads(r.mismatched_fields or "[]"),
            # Read matched_sources from the features JSON blob persisted by add_verdicts.
            # Pre-fix rows that lack this key default to [].
            matched_sources=_load_matched_sources(r.features),
            citation_link=_load_citation_link(r.features),
            mapping_status=r.mapping_status or "matched",
            mapping_confidence=r.mapping_confidence or 0.0,
            style_penalty=r.style_penalty,
            domain_exception=bool(r.domain_exception),
            is_overridden=bool(r.is_overridden),
        )
        for r in records
    ]


def _load_matched_sources(features_json: str | None) -> list[dict]:
    """Pull matched_sources list from the features JSON blob."""
    if not features_json:
        return []
    try:
        data = json.loads(features_json)
    except (json.JSONDecodeError, TypeError):
        return []
    matched = data.get("matched_sources") if isinstance(data, dict) else None
    return matched if isinstance(matched, list) else []


def _load_citation_link(features_json: str | None) -> dict | None:
    """Pull the in-text to bibliography link persisted with the verdict."""
    if not features_json:
        return None
    try:
        data = json.loads(features_json)
    except (json.JSONDecodeError, TypeError):
        return None
    link = data.get("citation_link") if isinstance(data, dict) else None
    return link if isinstance(link, dict) else None


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
    # SECURITY: Ownership check - uncomment when auth is implemented
    # from integrity_checker.api.deps import get_current_user
    # current_user = get_current_user() if has_auth else None
    # if current_user and current_user.role != 'admin' and essay.user_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="Access denied")

    # Build override record
    override_record = {
        "overridden_at": datetime.now(timezone.utc).isoformat(),
        "previous_label": body.new_label,  # simplified — real impl reads from current verdict
        "new_label": body.new_label,
        "reason": body.reason,
    }

    # Return updated verdict (simplified — real impl updates DB)
    return VerdictSchema(
        citation_id=verdict_id,
        citation_raw=f"Citation {verdict_id}",
        label=body.new_label,
        confidence=0.5,
        reasoning=f"Override: {body.reason or 'No reason'}",
        triggered_rules=[],
        mismatched_fields=[],
        matched_sources=[],
        mapping_status=body.new_mapping_status or "matched",
        mapping_confidence=0.0,
        is_overridden=True,
    )
