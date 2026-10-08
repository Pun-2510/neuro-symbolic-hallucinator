"""Report endpoint — export JSON / CSV / PDF (v1.2 schema)."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from html import escape
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db, get_current_user
from integrity_checker.api.progress import get_tracker
from integrity_checker.config import get_settings
from integrity_checker.db.repository import Repository
from integrity_checker.pipeline.integrity_pipeline import _serialize_citation_link

router = APIRouter()


@router.get("/{essay_id}/report")
async def get_report(
    essay_id: int,
    format: str = "json",
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export report theo format: json | csv | pdf."""
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")

    # SECURITY: Ownership check
    current_user = get_current_user(authorization, db) if authorization else None
    if current_user and current_user.role != "admin" and essay.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # If the pipeline is still running, return 425 so the frontend knows to keep polling.
    tracker = get_tracker()
    state = tracker.get(essay_id)
    if state is not None and state.status == "processing":
        return JSONResponse(
            status_code=425,
            content={"detail": "Analysis in progress", "retry_after": 3},
            headers={"Retry-After": "3"},
        )

    verdicts = repo.get_verdicts(essay_id)

    if format == "csv":
        return _csv_response(essay.filename, verdicts)
    if format == "json":
        return _json_response(essay.filename, essay, verdicts, repo.get_citations(essay_id))
    if format == "pdf":
        return _pdf_response(essay.filename, essay, verdicts)
    raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


def _deserialize_citation_link_json(json_str: str | None) -> dict[str, Any] | None:
    """Read citation_link_json column (v1.8) into the FIRST link's dict."""
    links = _deserialize_citation_links_json(json_str)
    return links[0] if links else None


def _deserialize_citation_links_json(json_str: str | None) -> list[dict[str, Any]]:
    """Read citation_link_json column into a LIST of link dicts (v1.9).

    v1.8 stored a single object; rows written before that upgrade must keep
    working, so a bare dict is read as a one-element list. Returns ``[]`` when
    the column is NULL/empty/unparseable.
    """
    if not json_str:
        return []
    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


def _serialize_extracted_citation(c) -> dict[str, Any]:
    """One row of the API's ``extracted_citations`` payload.

    Reads the linking layer persisted in v1.8 on ``CitationRecord``, preferring
    the in-memory attributes of a freshly produced report. Emits BOTH the
    lossless ``citation_links`` list (v1.9 — an occurrence may cite several
    references, "[9, 10]") and the single ``citation_link`` scalar so older
    consumers keep working.
    """
    all_links = _deserialize_citation_links_json(
        getattr(c, "citation_link_json", None)
    )
    # A freshly produced report holds live CitationLink objects that are richer
    # than the persisted subset, so prefer them when present.
    live_links = getattr(c, "citation_links", None)
    if live_links:
        all_links = [_serialize_citation_link(link) for link in live_links]
    elif not all_links:
        live_one = _serialize_citation_link(getattr(c, "citation_link", None))
        if live_one:
            all_links = [live_one]

    first_link = all_links[0] if all_links else None
    return {
        "id": c.id,
        "raw_text": c.raw_text,
        "citation_type": c.citation_type,
        "style": c.style,
        "page_num": c.page_num,
        "confidence": c.confidence,
        # NEW v1.7/v1.8 — linking layer for UI Citations tab.
        "mapping_status": getattr(c, "mapping_status", None)
        or (first_link or {}).get("status"),
        "mapping_confidence": getattr(c, "mapping_confidence", 0.0),
        # v1.9 — the lossless LIST; the scalar below is kept for older readers.
        "citation_links": all_links,
        "citation_link": _serialize_citation_link(getattr(c, "citation_link", None))
        or first_link,
    }


def _compute_in_text_citation_index(
    citations: list,
) -> tuple[dict[str, dict[str, Any]], dict[int, str]]:
    """Index in-text citations by their link's reference_id.

    Returns:
        in_text_by_ref: maps ``ref-NNNN`` → {count, pages[]} (de-duped pages).
        ref_link_by_record_id: maps a reference CitationRecord.id → the
            ``ref-NNNN`` string used by the linker for the same position in
            the bibliography (so the frontend can look up "Ref #3" given
            ``citation_link.reference_id``).
    """
    in_text_by_ref: dict[str, dict[str, Any]] = {}
    for c in citations:
        if c.citation_type not in {"in_text", "numeric"}:
            continue
        # v1.9 — one occurrence may cite SEVERAL references ("[9, 10]"), so
        # every link must be counted. Reading only link_dict[0] left ref #9
        # with a "cited in text" count that was short by one.
        for link_dict in _deserialize_citation_links_json(
            getattr(c, "citation_link_json", None)
        ):
            ref_link_id = link_dict.get("reference_id")
            if not ref_link_id:
                continue
            entry = in_text_by_ref.setdefault(
                ref_link_id, {"count": 0, "pages": []}
            )
            entry["count"] += 1
            if getattr(c, "page_num", 0):
                entry["pages"].append(c.page_num)

    # Map each reference DB row (insertion order = bibliography order) to the
    # synthetic ``ref-NNNN`` id the linker uses for it.
    #
    # The linker numbers references 1-BASED — ``_run_linking`` does
    # ``f"ref-{idx + 1:04d}"`` over the bibliography — so row i is ``ref-(i+1)``.
    # This must match, otherwise every ``cited_in_text_count`` / ``cited_on_pages``
    # lands on the neighbouring reference (off by one).
    ref_records_sorted = sorted(
        [c for c in citations if c.citation_type == "reference_list"],
        key=lambda c: c.id,
    )
    ref_link_by_record_id = {
        r.id: f"ref-{i + 1:04d}" for i, r in enumerate(ref_records_sorted)
    }

    return in_text_by_ref, ref_link_by_record_id


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


def _json_response(
    filename: str,
    essay,
    verdicts: list,
    citations: list | None = None,
) -> StreamingResponse:
    settings = get_settings()
    citations = citations or []

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
    citation_types = {c.raw_text: c.citation_type for c in citations}
    for v in verdicts:
        status = v.mapping_status or "matched"
        linking_summary[status] = linking_summary.get(status, 0) + 1

        # Reconstruct matched_sources from the features JSON blob (written there by
        # repository.add_verdicts).  If absent (pre-fix rows), fall back to an
        # empty list so the UI never receives undefined.
        features_dict = json.loads(v.features or "{}")
        matched_sources = features_dict.get("matched_sources", [])

        verdict_list.append({
            "citation_id": f"v{v.id}",
            "citation_raw": v.citation_raw,
            "citation_type": citation_types.get(v.citation_raw, "unknown"),
            "citation_link": features_dict.get("citation_link"),
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
            "features": features_dict,
            "matched_sources": matched_sources,
            # Override
            "is_overridden": bool(v.is_overridden),
            "override_note": v.override_note,
        })

    # Ưu tiên dùng CIS đầy đủ từ pipeline (lưu DB) — fallback về simple estimation
    in_text_count = sum(
        1 for c in citations if c.citation_type in {"in_text", "numeric"}
    )
    reference_count = sum(1 for c in citations if c.citation_type == "reference_list")
    total = in_text_count or len(verdicts)
    academic_verdicts = [v for v in verdicts if v.label != "resource"]
    academic_total = len(academic_verdicts)
    verified = sum(1 for v in academic_verdicts if v.label == "verified")

    style_profile_dict = None
    cis_dict = None
    if essay.style_profile_json:
        try:
            style_profile_dict = json.loads(essay.style_profile_json)
        except (json.JSONDecodeError, TypeError):
            pass
    if essay.cis_json:
        try:
            cis_dict = json.loads(essay.cis_json)
        except (json.JSONDecodeError, TypeError):
            pass

    if cis_dict is None:
        # Fallback: simple estimation
        cis_score = round((verified / academic_total * 100) if academic_total > 0 else 0, 1)
        cis_dict = {
            "score": cis_score,
            "components": {
                "verified_ratio": verified / academic_total if academic_total > 0 else 0,
                "metadata_accuracy": 0,
                "in_text_bib_consistency": linking_summary["matched"] / academic_total if academic_total > 0 else 0,
                "format_consistency": 0,
                "identifier_validity": 0,
            },
            "weights_used": {},
            "num_citations": academic_total,
            "num_unresolved": sum(1 for v in academic_verdicts if v.label == "unresolved"),
            "disclaimer": "",
        }

    # v1.2 schema: trả về flat fields (essay_id, filename, num_pages, num_citations)
    # ở top-level để frontend `AnalysisReport` interface map 1-1.
    # Giữ `essay` nested để không phá clients khác (CSV/PDF export, scripts).
    # NEW v1.8 — index in-text citations for the References tab
    # ("cited in text" indicator) and the Citations tab (Linked Reference).
    in_text_by_ref, ref_link_by_record_id = _compute_in_text_citation_index(citations)

    payload = {
        "essay_id": essay.id,
        "filename": essay.filename,
        "num_pages": essay.num_pages,
        "num_citations": total,
        "num_references": reference_count,
        "extracted_citations": [
            _serialize_extracted_citation(c)
            for c in citations
            if c.citation_type in {"in_text", "numeric"}
        ],
        "essay": {
            "id": essay.id,
            "filename": essay.filename,
            "num_pages": essay.num_pages,
            "uploaded_at": essay.uploaded_at.isoformat() if essay.uploaded_at else None,
        },
        "style_profile": style_profile_dict,
        "linking_summary": linking_summary,
        "verdicts": verdict_list,
        "references": [
            {
                "id": c.id,
                "raw_text": c.raw_text,
                "citation_type": c.citation_type,
                "style": c.style,
                "authors": json.loads(c.authors or "[]"),
                "year": c.year,
                "title": c.title,
                "venue": c.venue,
                "doi": c.doi,
                "url": c.url,
                "page_num": c.page_num,
                "confidence": c.confidence,
                # NEW v1.8 — "cited in text" indicator for the References tab
                "cited_in_text_count": in_text_by_ref.get(
                    ref_link_by_record_id.get(c.id, ""), {"count": 0}
                )["count"],
                "cited_on_pages": sorted(set(
                    in_text_by_ref.get(
                        ref_link_by_record_id.get(c.id, ""), {"pages": []}
                    )["pages"]
                )),
            }
            for c in citations
            if c.citation_type == "reference_list"
        ],
        "cis": cis_dict,
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


def _pdf_response(filename: str, essay, verdicts: list) -> StreamingResponse:
    """Generate PDF report with 2-layer analysis."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
    )
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=9,
        spaceAfter=0,
        wordWrap='LTR',
    )
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=table_cell_style,
        textColor=colors.whitesmoke,
        fontName='Helvetica-Bold',
    )

    elements: list[Any] = []

    # Title
    elements.append(Paragraph("Citation Integrity Report", title_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Essay info
    elements.append(Paragraph(f"<b>File:</b> {essay.filename}", body_style))
    elements.append(Paragraph(f"<b>Essay ID:</b> {essay.id}", body_style))
    elements.append(Paragraph(f"<b>Pages:</b> {essay.num_pages}", body_style))
    elements.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Summary stats
    total = len(verdicts)
    verified = sum(1 for v in verdicts if v.label == "verified")
    metadata_error = sum(1 for v in verdicts if v.label == "metadata_error")
    suspected = sum(1 for v in verdicts if v.label == "suspected_hallucination")
    unresolved = sum(1 for v in verdicts if v.label == "unresolved")

    matched = sum(1 for v in verdicts if v.mapping_status == "matched")
    missing_ref = sum(1 for v in verdicts if v.mapping_status == "missing_reference")
    mismatched = sum(1 for v in verdicts if v.mapping_status == "in_text_mismatch")

    elements.append(Paragraph("Summary", heading_style))

    summary_data = [
        ["Metric", "Count", "Percentage"],
        ["Total Citations", str(total), "100%"],
        ["--- Source Layer ---", "", ""],
        ["Verified", str(verified), f"{verified/total*100:.1f}%" if total > 0 else "0%"],
        ["Metadata Error", str(metadata_error), f"{metadata_error/total*100:.1f}%" if total > 0 else "0%"],
        ["Suspected Hallucination", str(suspected), f"{suspected/total*100:.1f}%" if total > 0 else "0%"],
        ["Unresolved", str(unresolved), f"{unresolved/total*100:.1f}%" if total > 0 else "0%"],
        ["--- Integrity Layer ---", "", ""],
        ["Matched", str(matched), f"{matched/total*100:.1f}%" if total > 0 else "0%"],
        ["Missing Reference", str(missing_ref), f"{missing_ref/total*100:.1f}%" if total > 0 else "0%"],
        ["In-Text Mismatch", str(mismatched), f"{mismatched/total*100:.1f}%" if total > 0 else "0%"],
    ]

    summary_table = Table(summary_data, colWidths=[5 * cm, 3 * cm, 3 * cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#dcfce7')),  # Total
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f3f4f6')),  # Separator
        ('BACKGROUND', (0, 7), (-1, 7), colors.HexColor('#f3f4f6')),  # Separator
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Verdict details table
    elements.append(Paragraph("Citation Details", heading_style))

    verdict_data = [[
        Paragraph("#", table_header_style),
        Paragraph("Citation Raw", table_header_style),
        Paragraph("Source Status", table_header_style),
        Paragraph("Mapping Status", table_header_style),
        Paragraph("Confidence", table_header_style),
    ]]

    for i, v in enumerate(verdicts, 1):
        source_status = _format_label(v.label)
        mapping_status = _format_mapping_status(v.mapping_status or "matched")
        confidence = f"{v.confidence * 100:.0f}%"

        verdict_data.append([
            Paragraph(str(i), table_cell_style),
            Paragraph(escape(v.citation_raw), table_cell_style),
            Paragraph(escape(source_status), table_cell_style),
            Paragraph(escape(mapping_status), table_cell_style),
            Paragraph(escape(confidence), table_cell_style),
        ])

    verdict_table = Table(
        verdict_data,
        colWidths=[1 * cm, 6 * cm, 3 * cm, 3 * cm, 2 * cm],
        repeatRows=1,
    )
    verdict_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),  # Left align citation text
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        # Color coding for source status
        ('BACKGROUND', (2, 1), (2, -1), colors.HexColor('#dcfce7')),  # Default green
    ]))
    elements.append(verdict_table)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}.report.pdf"'
        },
    )


def _format_label(label: str) -> str:
    """Format validation label for display."""
    labels = {
        "verified": "Verified",
        "metadata_error": "Metadata Error",
        "suspected_hallucination": "Suspected",
        "unresolved": "Unresolved",
        "resource": "URL Resource",
    }
    return labels.get(label, label.title())


def _format_mapping_status(status: str) -> str:
    """Format mapping status for display."""
    statuses = {
        "matched": "Matched",
        "missing_reference": "Missing Ref",
        "uncited_reference": "Uncited Ref",
        "in_text_mismatch": "Mismatch",
        "duplicate_reference": "Duplicate",
        "ambiguous_mapping": "Ambiguous",
        "style_inconsistent": "Style Issue",
        "unresolved": "Unresolved",
    }
    return statuses.get(status, status.title())
