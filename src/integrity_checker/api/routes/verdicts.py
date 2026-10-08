"""Verdicts endpoint — list verdict + override của 1 essay."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db, get_current_user
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
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> list[VerdictSchema]:
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")

    # SECURITY: Ownership check
    current_user = get_current_user(authorization, db) if authorization else None
    if current_user and current_user.role != "admin" and essay.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

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
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> VerdictSchema:
    """Override a verdict's label/status.

    Persists the override to DB and returns updated verdict.
    """
    repo = Repository(db)

    # SECURITY: Ownership check
    current_user = get_current_user(authorization, db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")
    if current_user.role != "admin" and essay.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Parse verdict_id from string
    try:
        v_id = int(verdict_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid verdict_id")

    # Update DB
    updated = repo.update_verdict(
        verdict_id=v_id,
        new_label=body.new_label,
        override_note=body.reason,
        new_mapping_status=body.new_mapping_status,
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Verdict not found")

    # Commit
    repo.commit()

    # Return updated verdict
    return VerdictSchema(
        citation_id=str(updated.id),
        citation_raw=updated.citation_raw,
        label=updated.label,
        confidence=updated.confidence,
        reasoning=updated.reasoning,
        triggered_rules=json.loads(updated.triggered_rules or "[]"),
        mismatched_fields=json.loads(updated.mismatched_fields or "[]"),
        matched_sources=[],
        mapping_status=updated.mapping_status or "matched",
        mapping_confidence=updated.mapping_confidence or 0.0,
        style_penalty=updated.style_penalty,
        domain_exception=bool(updated.domain_exception),
        is_overridden=bool(updated.is_overridden),
    )
