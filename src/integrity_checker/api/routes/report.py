"""Report endpoint — export JSON / CSV (v1.2 schema)."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db
from integrity_checker.config import get_settings
from integrity_checker.db.repository import Repository

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
    # v1.2 CSV: include both integrity + source layers
    writer.writerow([
        "citation_raw", "label", "confidence",
        "mapping_status", "mapping_confidence",
        "reasoning", "triggered_rules", "mismatched_fields",
        "is_overridden", "style_penalty", "domain_exception"
    ])
    for v in verdicts:
        writer.writerow([
            v.citation_raw,
            v.label,
            f"{v.confidence:.4f}",
            v.mapping_status or "matched",
            f"{v.mapping_confidence:.4f}",
            v.reasoning,
            v.triggered_rules,
            v.mismatched_fields,
            "1" if v.is_overridden else "0",
            f"{v.style_penalty:.4f}" if v.style_penalty else "",
            "1" if v.domain_exception else "0",
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

    # Build linking summary
    linking_summary = {
        "matched": 0,
        "missing_reference": 0,
        "uncited_reference": 0,
        "in_text_mismatch": 0,
        "duplicate_reference": 0,
        "ambiguous_mapping": 0,
        "style_inconsistent": 0,
        "unresolved": 0,
    }
    verdict_list = []
    for v in verdicts:
        status = v.mapping_status or "matched"
        linking_summary[status] = linking_summary.get(status, 0) + 1

        verdict_list.append({
            "citation_id": f"v{v.id}",
            "citation_raw": v.citation_raw,
            # Integrity layer
            "mapping_status": status,
            "mapping_confidence": v.mapping_confidence,
            "style_penalty": v.style_penalty,
            "domain_exception": bool(v.domain_exception),
            # Source layer
            "label": v.label,
            "confidence": v.confidence,
            "reasoning": v.reasoning,
            "triggered_rules": json.loads(v.triggered_rules or "[]"),
            "mismatched_fields": json.loads(v.mismatched_fields or "[]"),
            "features": json.loads(v.features or "{}"),
            # Override
            "is_overridden": bool(v.is_overridden),
            "override_note": v.override_note,
        })

    # Simple CIS estimation from verdicts
    total = len(verdicts)
    verified = sum(1 for v in verdicts if v.label == "verified")
    cis_score = round((verified / total * 100) if total > 0 else 0, 1)

    payload = {
        "essay": {
            "id": essay.id,
            "filename": essay.filename,
            "num_pages": essay.num_pages,
            "uploaded_at": essay.uploaded_at.isoformat() if essay.uploaded_at else None,
        },
        "num_citations": total,
        "style_profile": None,  # Not stored in DB, needs pipeline output
        "linking_summary": linking_summary,
        "verdicts": verdict_list,
        "cis": {
            "score": cis_score,
            "components": {
                "verified_ratio": verified / total if total > 0 else 0,
                "metadata_accuracy": 0,
                "in_text_bib_consistency": linking_summary["matched"] / total if total > 0 else 0,
                "format_consistency": 0,
                "identifier_validity": 0,
            },
            "num_citations": total,
            "num_unresolved": sum(1 for v in verdicts if v.label == "unresolved"),
        },
        "disclaimer": settings.disclaimer.long,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return StreamingResponse(
        iter([body]),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}.report.json"'
        },
    )