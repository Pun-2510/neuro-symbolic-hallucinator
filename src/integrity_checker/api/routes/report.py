"""Report endpoint — export JSON / CSV / PDF (v1.2 schema)."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
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
    """Export report theo format: json | csv | pdf."""
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")
    verdicts = repo.get_verdicts(essay_id)

    if format == "csv":
        return _csv_response(essay.filename, verdicts)
    if format == "json":
        return _json_response(essay.filename, essay, verdicts)
    if format == "pdf":
        return _pdf_response(essay.filename, essay, verdicts)
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


def _pdf_response(filename: str, essay, verdicts: list) -> StreamingResponse:
    """Generate PDF report with 2-layer analysis."""
    settings = get_settings()
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

    verdict_data = [["#", "Citation Raw", "Source Status", "Mapping Status", "Confidence"]]

    for i, v in enumerate(verdicts[:50], 1):  # Limit to 50 citations per page
        source_status = _format_label(v.label)
        mapping_status = _format_mapping_status(v.mapping_status or "matched")
        confidence = f"{v.confidence * 100:.0f}%"

        # Truncate long citation text
        raw_text = v.citation_raw[:50] + "..." if len(v.citation_raw) > 50 else v.citation_raw
        verdict_data.append([
            str(i),
            raw_text,
            source_status,
            mapping_status,
            confidence,
        ])

    verdict_table = Table(verdict_data, colWidths=[1 * cm, 6 * cm, 3 * cm, 3 * cm, 2 * cm])
    verdict_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),  # Left align citation text
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        # Color coding for source status
        ('BACKGROUND', (2, 1), (2, -1), colors.HexColor('#dcfce7')),  # Default green
    ]))
    elements.append(verdict_table)

    if len(verdicts) > 50:
        elements.append(Paragraph(
            f"<i>Showing first 50 of {len(verdicts)} citations. See JSON/CSV export for full list.</i>",
            body_style
        ))

    elements.append(Spacer(1, 1 * cm))

    # Disclaimer
    elements.append(Paragraph("Disclaimer", heading_style))
    elements.append(Paragraph(settings.disclaimer.long, body_style))

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