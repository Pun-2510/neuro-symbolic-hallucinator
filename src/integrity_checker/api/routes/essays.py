"""Essays endpoints — upload PDF và analyze."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_current_user, get_db, get_pipeline, require_admin
from integrity_checker.api.progress import get_tracker
from integrity_checker.billing.plans import ensure_user_quota_current, get_user_plan_policy
from integrity_checker.config import PROJECT_ROOT, is_test_runtime
from integrity_checker.db.models import CitationRecord, User, VerdictRecord
from integrity_checker.db.repository import Repository
from integrity_checker.models.api_schemas import CitationSchema, EssayUploadResponse
from integrity_checker.pipeline.integrity_pipeline import IntegrityPipeline

router = APIRouter()

UPLOADS_DIR = PROJECT_ROOT / "data" / "essays" / "uploads"


def _get_persisted_upload_path(essay_id: int, ext: str | None = None) -> Path:
    """Return persistent path on disk for an uploaded essay PDF or DOCX."""
    if ext in (".pdf", ".docx"):
        return UPLOADS_DIR / f"{essay_id}{ext}"
    docx_candidate = UPLOADS_DIR / f"{essay_id}.docx"
    if docx_candidate.is_file():
        return docx_candidate
    return UPLOADS_DIR / f"{essay_id}.pdf"


# ---------------------------------------------------------------------------
# Background pipeline task
# ---------------------------------------------------------------------------

async def _run_pipeline_task(
    essay_id: int,
    tmp_path: str,
    user_id: int,
    pipeline: IntegrityPipeline,
    cleanup_file: bool = True,
) -> None:
    """Background task: run full pipeline and persist results to DB.

    This function lives at module level so it can be registered with
    FastAPI's BackgroundTasks — it receives its own DB session via
    ``get_session()`` to avoid carrying the request's session across
    thread/async boundaries.
    """
    from integrity_checker.db.session import get_session
    from integrity_checker.logging import get_logger

    logger = get_logger(__name__)
    tracker = get_tracker()

    def _progress_to_threadlocal(step_key: str, step_index: int, stats: dict) -> None:
        """Called from the worker thread — tracker.update is thread-safe via
        its own lock, so cross-thread updates are fine."""
        tracker.update(
            essay_id,
            step=step_key,
            step_index=step_index,
            **stats,
        )

    try:
        # Offload heavy CPU work to the default executor so the event loop
        # stays free to serve other requests (status polls, etc.).
        # run_in_executor requires a sync callable; we wrap run_async in a
        # sync runner that creates its own event loop in the worker thread.
        loop = asyncio.get_running_loop()

        def _run_pipeline_sync() -> Any:
            return asyncio.run(
                pipeline.run_async(
                    tmp_path,
                    essay_id=essay_id,
                    progress_callback=_progress_to_threadlocal,
                )
            )

        report = await loop.run_in_executor(None, _run_pipeline_sync)

        # Persist to DB using a fresh session BEFORE marking tracker complete
        session = get_session()
        try:
            repo = Repository(session)
            # Update essay with page count (may have been 0 on creation)
            essay = repo.get_essay(essay_id)
            if essay:
                essay.num_pages = report.num_pages

            # Persist every extracted occurrence/entry so the Citations and
            # References tabs reflect the real document, not the deduped
            # verification set. Clear any partial rows from an interrupted run first.
            session.query(CitationRecord).filter(CitationRecord.essay_id == essay_id).delete()
            session.query(VerdictRecord).filter(VerdictRecord.essay_id == essay_id).delete()
            repo.add_citations(essay_id, report.extracted_citations)
            repo.add_verdicts(essay_id, report.verdicts)

            # Persist full pipeline output for GET /report
            style_profile_dict = None
            if report.style_profile:
                sp = report.style_profile
                if isinstance(sp, dict):
                    evidence = sp.get("evidence", {}) if isinstance(sp.get("evidence"), dict) else {}
                    style_profile_dict = {
                        "style": sp.get("style", "UNKNOWN"),
                        "confidence": sp.get("confidence", 0.0),
                        "apa_count": sp.get("apa_count", 0),
                        "ieee_count": sp.get("ieee_count", 0),
                        "mixed_count": sp.get("mixed_count", 0),
                        "numeric_count": sp.get("numeric_count", 0),
                        "features": evidence.get("features", {}),
                        "ratios": evidence.get("ratios", {}),
                        "explanation": evidence.get("explanation", ""),
                    }
                else:
                    style_profile_dict = {
                        "style": sp.style.value if hasattr(sp.style, "value") else str(sp.style),
                        "confidence": sp.confidence,
                        "apa_count": getattr(sp, "apa_count", 0),
                        "ieee_count": getattr(sp, "ieee_count", 0),
                        "mixed_count": getattr(sp, "mixed_count", 0),
                        "numeric_count": getattr(sp, "numeric_count", 0),
                        "features": getattr(sp, "evidence", {}).get("features", {}) if hasattr(sp, "evidence") else {},
                        "ratios": getattr(sp, "evidence", {}).get("ratios", {}) if hasattr(sp, "evidence") else {},
                        "explanation": getattr(sp, "evidence", {}).get("explanation", "") if hasattr(sp, "evidence") else "",
                    }

            cis_dict = None
            if report.cis:
                cis_obj = report.cis
                if isinstance(cis_obj, dict):
                    components = cis_obj.get("components", {})
                    if not isinstance(components, dict):
                        components = {}
                    cis_dict = {
                        "score": cis_obj.get("score", 0.0),
                        "components": components,
                        "weights_used": cis_obj.get("weights_used", {}) or {},
                        "num_citations": cis_obj.get("num_citations", 0),
                        "num_unresolved": cis_obj.get("num_unresolved", 0),
                        "disclaimer": cis_obj.get("disclaimer", ""),
                    }
                else:
                    comp = cis_obj.components
                    if not isinstance(comp, dict):
                        comp = {
                            attr: getattr(comp, attr)
                            for attr in dir(comp)
                            if not attr.startswith("_")
                            and not callable(getattr(comp, attr, None))
                            and attr in [
                                "verified_ratio",
                                "metadata_accuracy",
                                "in_text_bib_consistency",
                                "format_consistency",
                                "identifier_validity",
                            ]
                        }
                    cis_dict = {
                        "score": cis_obj.score,
                        "components": comp,
                        "weights_used": getattr(cis_obj, "weights_used", {}) or {},
                        "num_citations": getattr(cis_obj, "num_citations", 0),
                        "num_unresolved": getattr(cis_obj, "num_unresolved", 0),
                        "disclaimer": getattr(cis_obj, "disclaimer", ""),
                    }

            repo.update_essay_pipeline_output(
                essay_id,
                style_profile=style_profile_dict,
                cis=cis_dict,
            )
            repo.commit()
        finally:
            session.close()

        tracker.complete(essay_id)
        logger.info(f"Pipeline complete for essay {essay_id}")

    except Exception as exc:
        logger.exception(f"Pipeline failed for essay {essay_id}: {exc}")
        raw_err = str(exc)
        safe_err = (
            "Transient database disk I/O error"
            if "disk I/O error" in raw_err
            else "Analysis failed due to an internal processing error."
        )
        tracker.fail(essay_id, safe_err)
    finally:
        if cleanup_file:
            Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Upload security constants & helpers
# ---------------------------------------------------------------------------

MAX_PDF_UPLOAD_BYTES = int(os.getenv("MAX_PDF_UPLOAD_BYTES", str(25 * 1024 * 1024)))
_UPLOAD_CHUNK_SIZE = 64 * 1024


def _sanitize_upload_filename(raw_name: str) -> str:
    """Strip path traversal components and control characters from uploaded filename."""
    base = Path(raw_name.replace("\\", "/")).name
    cleaned = "".join(ch for ch in base if ch >= " " and ch != "\x7f").strip()
    lower = cleaned.lower()
    ext = ".docx" if lower.endswith(".docx") else ".pdf"
    if not cleaned or cleaned.startswith("."):
        cleaned = f"essay{cleaned}" if lower.endswith((".pdf", ".docx")) else f"document{ext}"
    if len(cleaned) > 200:
        stem = cleaned[: -len(ext)][: 200 - len(ext)]
        cleaned = f"{stem}{ext}"
    return cleaned


async def _read_pdf_upload_bounded(file: UploadFile, max_bytes: int | None = None) -> bytes:
    """Read upload stream in chunks, aborting immediately if size exceeds max_bytes."""
    limit = max_bytes if max_bytes is not None else MAX_PDF_UPLOAD_BYTES
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413,
                detail=f"PDF file too large. Maximum allowed size is {max(1, limit // (1024 * 1024))}MB.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=EssayUploadResponse)
async def upload_essay(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    class_id: int | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pipeline: IntegrityPipeline = Depends(get_pipeline),
) -> EssayUploadResponse:
    """Upload PDF or DOCX → save → return essay_id immediately.

    The actual analysis runs in the background and the ProcessingScreen
    polls ``GET /essays/{id}/status`` for live progress.
    """
    raw_filename = (file.filename or "").strip()
    lower_name = raw_filename.lower()
    if not raw_filename or not lower_name.endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files allowed")
    upload_ext = ".docx" if lower_name.endswith(".docx") else ".pdf"

    ensure_user_quota_current(current_user)
    policy = get_user_plan_policy(current_user)

    # Respect module-level MAX_PDF_UPLOAD_BYTES if monkeypatched in tests (< 25MB),
    # otherwise enforce the user's subscription plan file size limit.
    default_env_bytes = 25 * 1024 * 1024
    effective_max_bytes = (
        min(policy.max_file_size_bytes, MAX_PDF_UPLOAD_BYTES)
        if MAX_PDF_UPLOAD_BYTES != default_env_bytes
        else policy.max_file_size_bytes
    )

    safe_filename = _sanitize_upload_filename(raw_filename)
    content = await _read_pdf_upload_bounded(file, max_bytes=effective_max_bytes)

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded document file is empty")
    if upload_ext == ".pdf":
        if b"%PDF-" not in content[:1024]:
            raise HTTPException(status_code=400, detail="Invalid PDF file: missing %PDF- header")
    else:
        if not content.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=400,
                detail="Invalid DOCX file: missing OOXML PK archive header",
            )

    # Enforce monthly upload quota for the user's subscription tier
    used_uploads = int(current_user.monthly_uploads_used or 0)
    if used_uploads >= policy.max_uploads_per_month:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Monthly upload quota reached ({used_uploads}/{policy.max_uploads_per_month} documents "
                f"on the {policy.name} plan). Please upgrade to Pro or Ultra to continue analyzing manuscripts."
            ),
        )

    # Enforce per-document page limit if readable by PyMuPDF
    detected_pages = 0
    if upload_ext == ".pdf":
        try:
            import fitz

            with fitz.open(stream=content, filetype="pdf") as pdf_doc:
                detected_pages = len(pdf_doc)
        except Exception:
            detected_pages = 0

    if detected_pages > policy.max_pages_per_pdf:
        raise HTTPException(
            status_code=402,
            detail=(
                f"PDF page limit exceeded ({detected_pages} pages uploaded; maximum allowed on "
                f"the {policy.name} plan is {policy.max_pages_per_pdf} pages). Please upgrade to Pro or Ultra."
            ),
        )

    repo = Repository(db)
    if class_id is not None:
        cls = repo.get_class(class_id)
        if not cls:
            raise HTTPException(status_code=404, detail="Class not found")
        if current_user.role == "teacher" and cls.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your class")
        if current_user.role == "user":
            enrolled_ids = {c.id for c in repo.list_classes_for_student(current_user.id)}
            if class_id not in enrolled_ids:
                raise HTTPException(status_code=403, detail="Not enrolled in this class")

    # Create essay record immediately (num_pages=0 until pipeline fills it)
    essay = repo.create_essay_with_user(
        filename=safe_filename,
        num_pages=detected_pages,
        user_id=current_user.id,
        class_id=class_id,
    )
    current_user.monthly_uploads_used = used_uploads + 1
    repo.commit()

    if is_test_runtime():
        with tempfile.NamedTemporaryFile(delete=False, suffix=upload_ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        cleanup_file = True
    else:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        persisted_path = _get_persisted_upload_path(essay.id, ext=upload_ext)
        persisted_path.write_bytes(content)
        tmp_path = str(persisted_path)
        cleanup_file = False

    # Initialize real-time progress tracker so GET /status returns something useful
    tracker = get_tracker()
    tracker.init(essay.id)

    # Register background pipeline — runs after response is sent to client
    background_tasks.add_task(
        _run_pipeline_task,
        essay.id,
        tmp_path,
        current_user.id,
        pipeline,
        cleanup_file,
    )

    return EssayUploadResponse(
        essay_id=essay.id,
        filename=essay.filename,
        num_pages=0,  # Updated by background task once pipeline finishes
        num_citations=0,
        citations=[],
        summary={"status": "processing"},
    )


@router.get("/{essay_id}/status")
def get_essay_status(
    essay_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return real-time pipeline progress for the ProcessingScreen.

    Returns a snapshot of the in-memory ProgressState.  If the tracker has no
    entry (task finished or server restarted), falls back to checking the DB:
    - Verdicts written → status=completed
    - No verdicts yet → auto-resume if uploaded PDF is on disk, else processing
    """
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")

    persisted_pdf = _get_persisted_upload_path(essay_id)

    if not repo.can_user_access_essay(current_user, essay):
        raise HTTPException(status_code=403, detail="Access denied")

    tracker = get_tracker()
    state = tracker.get(essay_id)

    if state is not None:
        # Auto-retry at most once if a prior background run failed solely due to transient sqlite I/O error
        if (
            state.status == "failed"
            and state.error
            and "disk I/O error" in state.error
            and not is_test_runtime()
            and persisted_pdf.is_file()
            and tracker.can_auto_retry(essay_id)
        ):
            resumed_state = tracker.init(essay_id, is_retry=True)
            background_tasks.add_task(
                _run_pipeline_task,
                essay.id,
                str(persisted_pdf),
                essay.user_id or current_user.id,
                get_pipeline(),
                False,
            )
            return resumed_state.to_snapshot()
        return state.to_snapshot()

    # No tracker entry — fall back to DB state
    verdicts = repo.get_verdicts(essay_id)
    if verdicts or essay.cis_json is not None:
        extracted = repo.get_citations(essay_id)
        # Pipeline completed (possibly via cache hit or prior run)
        return {
            "status": "completed",
            "step": "done",
            "step_index": 7,
            "total_steps": 8,
            "message": "Analysis complete",
            "citations_found": sum(c.citation_type in {"in_text", "numeric"} for c in extracted),
            "references_found": sum(c.citation_type == "reference_list" for c in extracted),
            "linked": sum(v.mapping_status == "matched" for v in verdicts),
            "sources_queried": {},
            "elapsed_seconds": 0.0,
            "finished_at": None,
            "error": None,
        }

    # Server restarted before background analysis finished: auto-resume at most once
    # if the uploaded PDF is persisted on disk.
    persisted_pdf = _get_persisted_upload_path(essay_id)
    if not is_test_runtime() and persisted_pdf.is_file() and tracker.can_auto_retry(essay_id):
        resumed_state = tracker.init(essay_id, is_retry=True)
        background_tasks.add_task(
            _run_pipeline_task,
            essay.id,
            str(persisted_pdf),
            essay.user_id or current_user.id,
            get_pipeline(),
            False,
        )
        return resumed_state.to_snapshot()

    # No tracker and no verdicts — either queued or server restarted mid-run
    return {
        "status": "processing",
        "step": "parsing",
        "step_index": 0,
        "total_steps": 8,
        "message": "Processing...",
        "citations_found": 0,
        "references_found": 0,
        "linked": 0,
        "sources_queried": {},
        "elapsed_seconds": 0.0,
        "finished_at": None,
        "error": None,
    }


def _serialize_essay_summary(
    repo: Repository,
    e: Any,
    dupes: list[int],
    verdicts_by_essay: dict[int, list[VerdictRecord]] | None = None,
    in_text_counts_by_essay: dict[int, int] | None = None,
) -> dict[str, Any]:
    """Serialize essay summary with aggregated CIS and citation counts."""
    import json

    verdicts = (
        verdicts_by_essay.get(e.id, [])
        if verdicts_by_essay is not None
        else repo.get_verdicts(e.id)
    )
    if in_text_counts_by_essay is not None:
        in_text_count = in_text_counts_by_essay.get(e.id, 0)
    else:
        citations = repo.get_citations(e.id)
        in_text_count = sum(1 for c in citations if c.citation_type in {"in_text", "numeric"})
    num_citations = in_text_count or len(verdicts)
    num_verdicts = len(verdicts)
    num_verified = sum(1 for v in verdicts if v.label == "verified" or v.is_overridden)

    cis_score: float | None = None
    if e.cis_json:
        try:
            cis_dict = json.loads(e.cis_json)
            if isinstance(cis_dict, dict) and cis_dict.get("score") is not None:
                cis_score = float(cis_dict["score"])
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    if cis_score is None and verdicts:
        academic = [v for v in verdicts if v.label != "resource"]
        if academic:
            verified_academic = sum(1 for v in academic if v.label == "verified")
            cis_score = round((verified_academic / len(academic)) * 100.0, 1)

    return {
        "id": e.id,
        "filename": e.filename,
        "num_pages": e.num_pages,
        "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
        "user_id": e.user_id,
        "duplicate_ids": dupes,
        "cis_score": cis_score,
        "num_citations": num_citations,
        "num_verdicts": num_verdicts,
        "num_verified": num_verified,
    }


def _serialize_essay_summaries_batch(
    repo: Repository,
    grouped: list[tuple[Any, list[int]]],
) -> list[dict[str, Any]]:
    """Batch-load verdicts and in-text citation counts for all canonical essays in 2 queries."""
    if not grouped:
        return []
    from sqlalchemy import func

    essay_ids = [e.id for e, _ in grouped]
    verdicts_by_essay: dict[int, list[VerdictRecord]] = {eid: [] for eid in essay_ids}
    for v in (
        repo.session.query(VerdictRecord)
        .filter(VerdictRecord.essay_id.in_(essay_ids))
        .all()
    ):
        verdicts_by_essay.setdefault(v.essay_id, []).append(v)

    in_text_counts_by_essay = {
        row[0]: int(row[1] or 0)
        for row in repo.session.query(
            CitationRecord.essay_id, func.count(CitationRecord.id)
        )
        .filter(
            CitationRecord.essay_id.in_(essay_ids),
            CitationRecord.citation_type.in_(["in_text", "numeric"]),
        )
        .group_by(CitationRecord.essay_id)
        .all()
    }

    return [
        _serialize_essay_summary(
            repo,
            e,
            dupes,
            verdicts_by_essay=verdicts_by_essay,
            in_text_counts_by_essay=in_text_counts_by_essay,
        )
        for e, dupes in grouped
    ]


@router.get("", response_model=list[dict])
def list_essays(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List essays for current user (or all for admin).

    Re-uploaded copies of the same file are collapsed into a single entry.
    The underlying duplicate ids are returned in ``duplicate_ids`` so the UI
    can offer cleanup without hiding the fact that they exist.
    """
    from integrity_checker.db.models import Class, ClassMembership

    repo = Repository(db)

    if current_user.role == "admin":
        grouped = repo.get_all_essays_deduped()
    elif current_user.role == "teacher":
        visible_ids = {current_user.id}
        for (student_id,) in (
            db.query(ClassMembership.student_id)
            .join(Class, Class.id == ClassMembership.class_id)
            .filter(Class.teacher_id == current_user.id)
            .all()
        ):
            visible_ids.add(student_id)
        grouped = repo.get_all_essays_deduped(user_ids=list(visible_ids))
    else:
        grouped = repo.get_all_essays_deduped(user_id=current_user.id)

    return _serialize_essay_summaries_batch(repo, grouped)


@router.get("/all", response_model=list[dict])
def list_all_essays(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all essays (admin only), collapsing duplicate uploads."""
    repo = Repository(db)
    grouped = repo.get_all_essays_deduped()

    return _serialize_essay_summaries_batch(repo, grouped)


@router.get("/{essay_id}")
def get_essay(
    essay_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Lấy essay + verdicts từ DB."""
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")

    # Ownership / teacher class check
    if not repo.can_user_access_essay(current_user, essay):
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": essay.id,
        "filename": essay.filename,
        "num_pages": essay.num_pages,
        "uploaded_at": essay.uploaded_at.isoformat() if essay.uploaded_at else None,
        "user_id": essay.user_id,
    }


@router.delete("/{essay_id}")
def delete_essay(
    essay_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa essay (owner hoặc admin)."""
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")

    # Ownership check
    if current_user.role != "admin" and essay.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Clean up progress tracker and persisted PDF / DOCX
    get_tracker().clear(essay_id)
    _get_persisted_upload_path(essay_id, ext=".pdf").unlink(missing_ok=True)
    _get_persisted_upload_path(essay_id, ext=".docx").unlink(missing_ok=True)

    db.delete(essay)
    db.commit()

    return {"message": f"Essay {essay_id} deleted"}


@router.get("/{essay_id}/page-preview/{page_num}")
def get_essay_page_preview(
    essay_id: int,
    page_num: int,
    highlight: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Render an interactive PNG page preview with bounding-box citation highlighting (Sprint 3.3)."""
    import fitz

    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")

    if not repo.can_user_access_essay(current_user, essay):
        raise HTTPException(status_code=403, detail="Access denied")

    pdf_path = _get_persisted_upload_path(essay_id, ext=".pdf")
    if not pdf_path.is_file() and essay.filename:
        for candidate_dir in (
            PROJECT_ROOT / "data" / "demo",
            PROJECT_ROOT / "data" / "essays",
            PROJECT_ROOT / "style_corpora",
        ):
            if candidate_dir.is_dir():
                matches = list(candidate_dir.rglob(Path(essay.filename).name))
                if matches and matches[0].suffix.lower() == ".pdf":
                    pdf_path = matches[0]
                    break

    if pdf_path.is_file():
        doc = fitz.open(str(pdf_path))
        try:
            target_idx = max(0, min(len(doc) - 1, page_num - 1))
            page = doc[target_idx]
            if highlight and highlight.strip():
                q = highlight.strip()
                # Strip leading [N] if full reference string
                q_clean = q
                rects = page.search_for(q_clean[:65])
                if not rects and len(q_clean) > 25:
                    rects = page.search_for(q_clean[:32])
                if not rects:
                    # Try first token / author surname + year
                    import re as _re

                    m_tok = _re.search(r"[A-Za-zÀ-ỹ]{4,}", q_clean)
                    if m_tok:
                        rects = page.search_for(m_tok.group(0))
                if rects:
                    shape = page.new_shape()
                    for r in rects[:12]:
                        padded = fitz.Rect(r.x0 - 2, r.y0 - 1.5, r.x1 + 2, r.y1 + 1.5)
                        shape.draw_rect(padded)
                    shape.finish(
                        color=(0.31, 0.27, 0.90),
                        fill=(0.99, 0.88, 0.28),
                        fill_opacity=0.36,
                        width=1.4,
                    )
                    shape.commit()
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            png_bytes = pix.tobytes("png")
        finally:
            doc.close()
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={"Cache-Control": "private, max-age=120"},
        )

    # Dynamic high-DPI virtual page preview for .docx or synthetic/seeded essays without raw PDF on disk
    doc = fitz.open()
    try:
        page = doc.new_page(width=595, height=842)
        # Header banner
        shape = page.new_shape()
        shape.draw_rect(fitz.Rect(36, 32, 559, 82))
        shape.finish(color=(0.82, 0.85, 0.92), fill=(0.96, 0.97, 0.99), width=1.0)
        shape.commit()

        page.insert_text(
            fitz.Point(48, 54),
            f"CITRA Document Inspector  |  {essay.filename}",
            fontsize=11,
            fontname="helv",
            color=(0.12, 0.16, 0.28),
        )
        page.insert_text(
            fitz.Point(48, 70),
            f"Virtual Page Reconstruction — Page {max(1, page_num)} of {max(1, essay.num_pages or 1)}",
            fontsize=8.5,
            color=(0.38, 0.43, 0.54),
        )

        citations = repo.get_citations(essay_id)
        verdicts = repo.get_verdicts(essay_id)
        page_cits = [c for c in citations if (c.page_num or 1) == page_num] or citations[:8]

        y = 110.0
        for idx, c in enumerate(page_cits[:8], start=1):
            ctx = (getattr(c, "context", None) or c.raw_text or "").strip()
            block_text = f"[{idx}] {ctx[:260]}"
            is_hl = bool(
                highlight
                and (
                    highlight.strip().lower() in ctx.lower()
                    or highlight.strip().lower() in (c.raw_text or "").lower()
                )
            )
            box = fitz.Rect(42, y - 6, 553, y + 66)
            sh = page.new_shape()
            sh.draw_rect(box)
            if is_hl:
                sh.finish(
                    color=(0.31, 0.27, 0.90),
                    fill=(0.99, 0.92, 0.45),
                    fill_opacity=0.42,
                    width=1.8,
                )
            else:
                sh.finish(
                    color=(0.88, 0.90, 0.94),
                    fill=(0.99, 0.99, 1.0),
                    fill_opacity=0.9,
                    width=0.8,
                )
            sh.commit()
            page.insert_textbox(
                fitz.Rect(50, y, 545, y + 62),
                block_text,
                fontsize=9.2,
                color=(0.10, 0.12, 0.18),
            )
            y += 80.0
            if y > 740:
                break

        if not page_cits and verdicts:
            for idx, v in enumerate(verdicts[:7], start=1):
                txt = f"[{idx}] ({v.label.upper()}) {v.citation_raw[:220]}"
                is_hl = bool(highlight and highlight.strip().lower() in v.citation_raw.lower())
                box = fitz.Rect(42, y - 6, 553, y + 58)
                sh = page.new_shape()
                sh.draw_rect(box)
                if is_hl:
                    sh.finish(
                        color=(0.31, 0.27, 0.90),
                        fill=(0.99, 0.92, 0.45),
                        fill_opacity=0.42,
                        width=1.8,
                    )
                else:
                    sh.finish(color=(0.88, 0.90, 0.94), fill=(0.99, 0.99, 1.0), width=0.8)
                sh.commit()
                page.insert_textbox(
                    fitz.Rect(50, y, 545, y + 54),
                    txt,
                    fontsize=9.2,
                    color=(0.10, 0.12, 0.18),
                )
                y += 72.0

        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        png_bytes = pix.tobytes("png")
    finally:
        doc.close()

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=120"},
    )
