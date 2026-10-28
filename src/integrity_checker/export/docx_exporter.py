"""DOCX export functionality for analysis reports."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH


def _set_cell_background(cell, hex_color: str) -> None:
    """Apply background shading color (e.g. 'FEE2E2') to a python-docx table cell."""
    try:
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
        cell._tc.get_or_add_tcPr().append(shading)
    except Exception:
        pass


def export_report_to_docx(
    filename: str,
    cis_score: float,
    num_citations: int,
    num_verified: int,
    num_metadata_error: int,
    num_suspected: int,
    num_unresolved: int,
    num_resource: int,
    verdicts: list[dict],
    generated_at: str | None = None,
    *,
    cis_components: dict[str, float] | None = None,
    linking_summary: dict[str, int] | None = None,
    style_profile: dict | None = None,
) -> bytes:
    """Generate a DOCX report from analysis results.

    Args:
        filename: Name of the analyzed essay
        cis_score: Citation Integrity Score (0-100)
        num_citations: Total number of citations
        num_verified: Number of verified citations
        num_metadata_error: Number with metadata errors
        num_suspected: Number of suspected hallucinations
        num_unresolved: Number of unresolved citations
        num_resource: Number of URL/Resource citations
        verdicts: List of verdict dictionaries
        generated_at: Timestamp string

    Returns:
        bytes: DOCX file content
    """
    doc = Document()

    # Title
    title = doc.add_heading("Essay Integrity Check Report", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Metadata
    doc.add_paragraph()
    meta = doc.add_paragraph()
    meta.add_run("Essay: ").bold = True
    meta.add_run(filename)
    meta = doc.add_paragraph()
    meta.add_run("Generated: ").bold = True
    meta.add_run(generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    meta = doc.add_paragraph()
    meta.add_run("System: ").bold = True
    meta.add_run("Essay Integrity Checker (DATN)")

    # CIS Score Section
    doc.add_heading("Citation Integrity Score (CIS)", level=1)

    score_para = doc.add_paragraph()
    score_run = score_para.add_run(f"{cis_score:.2f}%")
    score_run.font.size = Pt(36)
    score_run.font.bold = True

    # Determine score color
    if cis_score >= 90:
        score_run.font.color.rgb = RGBColor(34, 197, 94)  # Green
    elif cis_score >= 70:
        score_run.font.color.rgb = RGBColor(234, 179, 8)  # Yellow
    else:
        score_run.font.color.rgb = RGBColor(239, 68, 68)  # Red

    doc.add_paragraph("(Score represents percentage of citations that passed integrity verification)")

    if style_profile and isinstance(style_profile, dict) and style_profile.get("style"):
        sp_para = doc.add_paragraph()
        sp_para.add_run("Detected Citation Style: ").bold = True
        conf_pct = float(style_profile.get("confidence", 0.0) or 0.0) * 100.0
        sp_para.add_run(f"{style_profile.get('style')} ({conf_pct:.0f}% confidence)")

    if cis_components and isinstance(cis_components, dict):
        doc.add_heading("5-Component CIS Formula Breakdown", level=2)
        comp_table = doc.add_table(rows=1, cols=3)
        comp_table.style = "Table Grid"
        comp_hdr = comp_table.rows[0].cells
        comp_hdr[0].text = "CIS Component"
        comp_hdr[1].text = "Weight"
        comp_hdr[2].text = "Score"
        for cell in comp_hdr:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True

        comp_rows = [
            ("Verified Ratio (Layer 2)", "35%", float(cis_components.get("verified_ratio", 0.0) or 0.0)),
            ("Metadata Accuracy (Author/Year/Title)", "25%", float(cis_components.get("metadata_accuracy", 0.0) or 0.0)),
            ("In-Text ↔ Bibliography Consistency (Layer 1)", "20%", float(cis_components.get("in_text_bib_consistency", 0.0) or 0.0)),
            ("Citation Style Consistency", "10%", float(cis_components.get("format_consistency", 0.0) or 0.0)),
            ("Identifier Validity (DOI / CrossRef)", "10%", float(cis_components.get("identifier_validity", 0.0) or 0.0)),
        ]
        for label_txt, weight_txt, val in comp_rows:
            r_cells = comp_table.add_row().cells
            r_cells[0].text = label_txt
            r_cells[1].text = weight_txt
            r_cells[2].text = f"{val * 100.0:.1f}%"

    if linking_summary and isinstance(linking_summary, dict):
        doc.add_heading("Layer 1: In-Text ↔ Bibliography Linking Summary", level=2)
        link_table = doc.add_table(rows=1, cols=2)
        link_table.style = "Table Grid"
        lh = link_table.rows[0].cells
        lh[0].text = "Mapping Status"
        lh[1].text = "Count"
        for cell in lh:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
        for k, v_cnt in linking_summary.items():
            rc = link_table.add_row().cells
            rc[0].text = k.replace("_", " ").title()
            rc[1].text = str(v_cnt)

    # Summary Statistics
    doc.add_heading("Summary Statistics", level=1)

    stats_table = doc.add_table(rows=8, cols=2)
    stats_table.style = "Table Grid"

    stats_data = [
        ("Total Citations", str(num_citations)),
        ("Verified", f"{num_verified} ({num_verified * 100 / max(num_citations, 1):.1f}%)"),
        ("Metadata Error", f"{num_metadata_error} ({num_metadata_error * 100 / max(num_citations, 1):.1f}%)"),
        ("Suspected Hallucination", f"{num_suspected} ({num_suspected * 100 / max(num_citations, 1):.1f}%)"),
        ("Unresolved", f"{num_unresolved} ({num_unresolved * 100 / max(num_citations, 1):.1f}%)"),
        ("URL/Resource", f"{num_resource} ({num_resource * 100 / max(num_citations, 1):.1f}%)"),
        ("", ""),
        ("Citation Integrity Score", f"{cis_score:.2f}%"),
    ]

    for i, (label, value) in enumerate(stats_data):
        row = stats_table.rows[i]
        row.cells[0].text = label
        row.cells[1].text = value
        if label == "Citation Integrity Score":
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.bold = True

    # Verdicts Detail Section
    doc.add_heading("Citation Verdicts", level=1)

    if verdicts:
        # Verdicts table
        table = doc.add_table(rows=1, cols=4)
        table.style = "Table Grid"

        # Header row
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Citation"
        hdr_cells[1].text = "Type"
        hdr_cells[2].text = "Label"
        hdr_cells[3].text = "Confidence"

        for cell in hdr_cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True

        # Data rows
        for v in verdicts:
            row_cells = table.add_row().cells
            raw_cit = str(v.get("citation_raw", "") or "")
            mismatched = v.get("mismatched_fields") or []
            rules = v.get("triggered_rules") or []
            lbl_lower = str(v.get("label", "") or "").lower()
            details_suffix = ""
            if rules or mismatched:
                parts = []
                if rules:
                    parts.append(f"Rules: {', '.join(str(r) for r in rules)}")
                if mismatched:
                    parts.append(f"Mismatched: {', '.join(str(m) for m in mismatched)}")
                details_suffix = f"\n[{' | '.join(parts)}]"
            row_cells[0].text = raw_cit + details_suffix
            row_cells[1].text = str(v.get("mapping_status") or v.get("citation_type", "unknown"))
            row_cells[2].text = str(v.get("label", "UNKNOWN")).upper()
            row_cells[3].text = f"{float(v.get('confidence', 0) or 0):.2f}"

            if lbl_lower == "suspected_hallucination":
                for cell in row_cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.color.rgb = RGBColor(220, 38, 38)
                            run.font.bold = True
            elif lbl_lower == "metadata_error":
                for cell in row_cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.color.rgb = RGBColor(220, 38, 38)
                for paragraph in row_cells[2].paragraphs:
                    for run in paragraph.runs:
                        run.font.bold = True
            elif lbl_lower in ("verified", "resource"):
                for paragraph in row_cells[2].paragraphs:
                    for run in paragraph.runs:
                        run.font.color.rgb = RGBColor(22, 163, 74)
                        run.font.bold = True

        # Deep Neuro-Symbolic Evidence & Remediation Section for Flagged / Detailed Verdicts
        detailed_items = [
            v
            for v in verdicts
            if v.get("reasoning")
            or v.get("triggered_rules")
            or v.get("mismatched_fields")
            or (v.get("features") or {}).get("best_evidence_sentence")
        ]
        if detailed_items:
            doc.add_heading("Neuro-Symbolic Diagnostic Trace & Evidence", level=1)
            for idx, v in enumerate(detailed_items, 1):
                p = doc.add_paragraph()
                lbl_str = str(v.get("label", "UNKNOWN")).upper()
                lbl_lower = lbl_str.lower()
                r_num = p.add_run(f"[{idx}] {v.get('citation_raw', '')}\n")
                r_num.bold = True
                if lbl_lower in ("suspected_hallucination", "metadata_error"):
                    r_num.font.color.rgb = RGBColor(220, 38, 38)
                map_str = str(v.get("mapping_status", "matched"))
                r_verdict = p.add_run(
                    f"Verdict: {lbl_str} (Confidence: {float(v.get('confidence', 0) or 0):.2f}) | Layer-1 Mapping: {map_str}\n"
                )
                if lbl_lower in ("suspected_hallucination", "metadata_error"):
                    r_verdict.font.color.rgb = RGBColor(220, 38, 38)
                    r_verdict.bold = True
                rules = v.get("triggered_rules") or []
                if rules:
                    p.add_run(f"Triggered Symbolic Rules: {', '.join(str(r) for r in rules)}\n")
                mismatched = v.get("mismatched_fields") or []
                if mismatched:
                    r_mm = p.add_run(f"Mismatched Metadata Fields: {', '.join(str(m) for m in mismatched)}\n")
                    r_mm.font.color.rgb = RGBColor(185, 28, 28)
                if v.get("reasoning"):
                    p.add_run(f"Diagnostic Reasoning: {v.get('reasoning')}\n")
                feats = v.get("features") if isinstance(v.get("features"), dict) else {}
                ev_sent = feats.get("best_evidence_sentence")
                if ev_sent:
                    p.add_run(f"SBERT Best Evidence Sentence: \"{ev_sent}\"\n")
                intent = feats.get("citation_intent")
                stance = feats.get("citation_stance")
                if intent or stance:
                    p.add_run(
                        f"Discourse Analysis: Intent={intent or 'background'}, Stance={stance or 'neutral'}\n"
                    )

        # 1-Click Auto-Remediated Bibliography & BibTeX Section
        try:
            from integrity_checker.export.bibliography_formatter import build_remediated_bibliography

            rem_data = build_remediated_bibliography(essay_id=0, verdicts=verdicts, style="apa")
            rem_entries = rem_data.get("entries") or []
            if rem_entries:
                doc.add_heading("Auto-Remediated Bibliography & BibTeX Studio", level=1)
                for e in rem_entries:
                    p_rem = doc.add_paragraph()
                    e_lbl = str(e.get("label", "")).lower()
                    if e.get("is_hallucination") or e_lbl == "suspected_hallucination":
                        r_warn = p_rem.add_run(
                            f"[{e['index']}] [CẢNH BÁO ĐỎ — SUSPECTED HALLUCINATION / NGUỒN BỊA ĐẶT: CẦN LOẠI BỎ]\n"
                        )
                        r_warn.bold = True
                        r_warn.font.color.rgb = RGBColor(220, 38, 38)
                        r_orig = p_rem.add_run(f"Original in Manuscript: {e.get('original_raw', '')}\n")
                        r_orig.font.color.rgb = RGBColor(220, 38, 38)
                    elif e.get("is_error") or e_lbl == "metadata_error":
                        r_fix = p_rem.add_run(
                            f"[{e['index']}] [METADATA ERROR AUTO-REPAIRED — Repaired fields: {', '.join(e.get('diff_fields') or ['metadata'])}]\n"
                        )
                        r_fix.bold = True
                        r_fix.font.color.rgb = RGBColor(185, 28, 28)
                        r_before = p_rem.add_run(f"Before (Error): {e.get('original_raw', '')}\n")
                        r_before.font.color.rgb = RGBColor(220, 38, 38)
                        r_after = p_rem.add_run(f"After (Standardized APA): {e.get('apa', '')}\n")
                        r_after.bold = True
                        r_after.font.color.rgb = RGBColor(22, 163, 74)
                        r_bib = p_rem.add_run(f"BibTeX:\n{e.get('bibtex', '')}")
                        r_bib.font.size = Pt(8.5)
                    else:
                        r_ok = p_rem.add_run(f"[{e['index']}] [VERIFIED & STANDARDIZED]\n")
                        r_ok.bold = True
                        r_ok.font.color.rgb = RGBColor(22, 163, 74)
                        p_rem.add_run(f"{e.get('apa', '')}\n")
                        r_bib = p_rem.add_run(f"BibTeX:\n{e.get('bibtex', '')}")
                        r_bib.font.size = Pt(8.5)
        except Exception:
            pass

    else:
        doc.add_paragraph("No citation verdicts available.")

    # Legend
    doc.add_heading("Label Legend", level=1)

    legend_table = doc.add_table(rows=6, cols=2)
    legend_table.style = "Table Grid"

    legend_data = [
        ("VERIFIED", "Citation verified successfully through academic databases"),
        ("METADATA_ERROR", "Citation found but metadata (author, title, year) doesn't match"),
        ("SUSPECTED_HALLUCINATION", "Citation appears to be fabricated or non-existent"),
        ("UNRESOLVED", "Insufficient evidence to determine citation validity"),
        ("RESOURCE", "Citation is a URL/web resource (not academic paper)"),
        ("", ""),
    ]

    for i, (label, desc) in enumerate(legend_data):
        if i >= len(legend_table.rows):
            break
        row = legend_table.rows[i]
        row.cells[0].text = label
        row.cells[1].text = desc
        if label == "VERIFIED":
            row.cells[0].paragraphs[0].runs[0].font.color.rgb = RGBColor(34, 197, 94)
        elif label == "METADATA_ERROR":
            row.cells[0].paragraphs[0].runs[0].font.color.rgb = RGBColor(234, 179, 8)
        elif label == "SUSPECTED_HALLUCINATION":
            row.cells[0].paragraphs[0].runs[0].font.color.rgb = RGBColor(239, 68, 68)

    # Disclaimer
    doc.add_paragraph()
    disclaimer = doc.add_paragraph()
    disclaimer_run = disclaimer.add_run(
        "DISCLAIMER: This report is a decision-support tool only. "
        "Final judgment on citation integrity requires expert human review. "
        "The system may produce false positives or false negatives."
    )
    disclaimer_run.font.size = Pt(9)
    disclaimer_run.font.italic = True

    # Save to bytes
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
