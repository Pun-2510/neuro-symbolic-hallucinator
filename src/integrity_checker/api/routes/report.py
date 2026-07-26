"""Report endpoint — export JSON / CSV / PDF."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db
from integrity_checker.config import get_settings
from integrity_checker.db.repository import Repository
from integrity_checker.models.api_schemas import AnalysisReportSchema, CISSchema, VerdictSchema

router = APIRouter()


@router.get("/{essay_id}/report")
async def get_report(
    essay_id: int,
    format: str = "json",
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export report theo format: json | csv."""
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")
    verdicts = repo.get_verdicts(essay_id)

    if format == "csv":
        return _csv_response(essay.filename, verdicts)
    if format == "json":
        return _json_response(essay.filename, essay, verdicts)
    raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


def _csv_response(filename: str, verdicts: list) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["citation_raw", "label", "confidence", "reasoning", "triggered_rules"])
    for v in verdicts:
        writer.writerow([
            v.citation_raw,
            v.label,
            f"{v.confidence:.4f}",
            v.reasoning,
            v.triggered_rules,
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}.report.csv"'
        },
    )


def _json_response(filename: str, essay, verdicts: list) -> StreamingResponse:
    settings = get_settings()
    payload = {
        "essay": {
            "id": essay.id,
            "filename": essay.filename,
            "num_pages": essay.num_pages,
            "uploaded_at": essay.uploaded_at.isoformat() if essay.uploaded_at else None,
        },
        "verdicts": [
            {
                "citation_raw": v.citation_raw,
                "label": v.label,
                "confidence": v.confidence,
                "reasoning": v.reasoning,
                "triggered_rules": json.loads(v.triggered_rules or "[]"),
                "mismatched_fields": json.loads(v.mismatched_fields or "[]"),
                "features": json.loads(v.features or "{}"),
            }
            for v in verdicts
        ],
        "disclaimer": settings.disclaimer.long,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return StreamingResponse(
        iter([body]),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}.report.json"'
        },
    )