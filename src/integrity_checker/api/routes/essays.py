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
        fname_only = Path(essay.filename).name
        direct_root = PROJECT_ROOT / fname_only
        if direct_root.is_file() and direct_root.suffix.lower() == ".pdf":
            pdf_path = direct_root
        else:
            for candidate_dir in (
                PROJECT_ROOT / "data" / "demo",
                PROJECT_ROOT / "data" / "essays",
                PROJECT_ROOT / "style_corpora",
                PROJECT_ROOT / "vn_legal_reports",
                PROJECT_ROOT / "20-theses",
                PROJECT_ROOT / "tdtu_github_reports",
                PROJECT_ROOT / "TDTU-MidtermReport",
            ):
                if candidate_dir.is_dir():
                    matches = list(candidate_dir.rglob(fname_only))
                    if matches and matches[0].suffix.lower() == ".pdf":
                        pdf_path = matches[0]
                        break

    import html as _html
    import re as _re

    citations = repo.get_citations(essay_id)
    verdicts = repo.get_verdicts(essay_id)

    def _find_rects_for_query(page_obj, q_str: str) -> list:
        q_s = (q_str or "").strip()
        if not q_s:
            return []
        q_no_num = _re.sub(r"^\s*(?:\[\d+\]|\d+[\.\)])\s*", "", q_s).strip()
        # For bibliography entries (> 40 chars), match full text block(s) on the page so wrapped lines are included
        if len(q_s) > 40:
            blocks = page_obj.get_text("blocks")
            prefix_low = q_no_num[:58].lower()
            raw_prefix_low = q_s[:58].lower()
            matched_block_rects = []
            for b_i, b in enumerate(blocks):
                b_txt = _re.sub(r"\s+", " ", (b[4] or "").strip())
                b_txt_low = b_txt.lower()
                b_no_num_low = _re.sub(r"^\s*(?:\[\d+\]|\d+[\.\)])\s*", "", b_txt_low).strip()
                if len(b_no_num_low) < 22:
                    continue
                cmp_len = min(len(prefix_low), len(b_no_num_low))
                raw_cmp_len = min(len(raw_prefix_low), len(b_txt_low))
                if (prefix_low and b_no_num_low.startswith(prefix_low[:cmp_len])) or (
                    raw_prefix_low and b_txt_low.startswith(raw_prefix_low[:raw_cmp_len])
                ):
                    matched_block_rects.append(fitz.Rect(b[:4]))
                    # Check if the immediately following block is a hanging-indent continuation of this reference
                    if b_i + 1 < len(blocks):
                        b_next = blocks[b_i + 1]
                        if b_next[0] > b[0] + 8 and 0 <= (b_next[1] - b[3]) <= 16:
                            matched_block_rects.append(fitz.Rect(b_next[:4]))
            if matched_block_rects:
                return matched_block_rects
        for cand_q in (
            q_s[:68],
            q_no_num[:60],
            q_no_num[:34],
        ):
            if cand_q and len(cand_q) >= 3:
                found_r = page_obj.search_for(cand_q)
                if found_r:
                    return found_r
        # Try quoted title or sentence segment
        m_quote = _re.search(r"[\"\u201c]([^\"\u201d]{8,65})[\"\u201d]", q_no_num)
        if m_quote:
            found_r = page_obj.search_for(m_quote.group(1)[:48])
            if found_r:
                return found_r
        # Try leading bracket number [N] if present on this page
        m_num = _re.match(r"^\s*(\[\d+\])", q_s)
        if m_num:
            # Check if there is an in-text citation on this page with that [N]
            for cit_rec in citations:
                if (cit_rec.page_num or 1) == page_num and m_num.group(1) in (cit_rec.raw_text or ""):
                    ctx_s = (getattr(cit_rec, "context", None) or "").strip()
                    if ctx_s:
                        found_r = page_obj.search_for(ctx_s[:48])
                        if found_r:
                            return found_r
                    found_r = page_obj.search_for(m_num.group(1))
                    if found_r:
                        return found_r
        # Try first author surname / distinctive token (>= 4 chars) only for short in-text queries
        if len(q_s) <= 40:
            m_tok = _re.search(r"[A-Za-zÀ-ỹ]{4,}", q_no_num)
            if m_tok and m_tok.group(0).lower() not in {"luật", "nghị", "định", "quốc", "chính", "thông", "quyết"}:
                found_r = page_obj.search_for(m_tok.group(0))
                if found_r:
                    return found_r
        return []

    if pdf_path.is_file():
        import numpy as _np

        doc = fitz.open(str(pdf_path))
        try:
            target_idx = max(0, min(len(doc) - 1, page_num - 1))
            page = doc[target_idx]

            # 1. Collect all text regions for suspected_hallucination & metadata_error citations on this page
            # so we ONLY color the text glyphs in RED ("chỉ tô đỏ text thôi, không đóng khung xung quanh")
            all_red_text_rects: list[fitz.Rect] = []
            ref_records_sorted = sorted(
                [c for c in citations if getattr(c, "citation_type", "") == "reference_list"],
                key=lambda c: c.id,
            )
            ref_link_by_raw = {
                (r.raw_text or "").strip(): f"ref-{i + 1:04d}"
                for i, r in enumerate(ref_records_sorted)
            }
            for v_idx, v in enumerate(verdicts, start=1):
                v_lbl = (v.label or "").lower()
                if v_lbl not in ("suspected_hallucination", "metadata_error"):
                    continue
                err_rects = _find_rects_for_query(page, v.citation_raw or "")
                ref_tag = ref_link_by_raw.get((v.citation_raw or "").strip())
                if ref_tag:
                    for cit_rec in citations:
                        if getattr(cit_rec, "citation_type", "") == "reference_list":
                            continue
                        if (cit_rec.page_num or 1) != (target_idx + 1):
                            continue
                        link_json_s = getattr(cit_rec, "citation_link_json", None) or ""
                        if ref_tag in link_json_s:
                            raw_in_text = (cit_rec.raw_text or "").strip()
                            if raw_in_text:
                                err_rects.extend(_find_rects_for_query(page, raw_in_text))
                all_red_text_rects.extend(err_rects[:14])

            # 2. Check the active query selected by the user
            active_non_err_rects: list[fitz.Rect] = []
            if highlight and highlight.strip():
                q = highlight.strip()
                rects = _find_rects_for_query(page, q)
                is_active_err = False
                q_low = q.lower()
                for v in verdicts:
                    v_raw_low = (v.citation_raw or "").lower()
                    if (q_low in v_raw_low or v_raw_low[:35] in q_low) and (v.label or "").lower() in (
                        "suspected_hallucination",
                        "metadata_error",
                    ):
                        is_active_err = True
                        break
                if rects:
                    if is_active_err:
                        all_red_text_rects.extend(rects[:12])
                    else:
                        active_non_err_rects.extend(rects[:12])

            scale = 1.5
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            if all_red_text_rects or active_non_err_rects:
                arr = _np.frombuffer(pix.samples, dtype=_np.uint8).reshape(pix.height, pix.width, 3).copy()
                # Recolor ONLY the text pixels inside all_red_text_rects to red (#dc2626) without any box/border
                for r in all_red_text_rects:
                    x0 = max(0, int((r.x0 - 1.5) * scale))
                    y0 = max(0, int((r.y0 - 1.5) * scale))
                    x1 = min(pix.width, int((r.x1 + 1.5) * scale))
                    y1 = min(pix.height, int((r.y1 + 1.5) * scale))
                    if x1 <= x0 or y1 <= y0:
                        continue
                    roi = arr[y0:y1, x0:x1].astype(_np.float32)
                    darkness = _np.clip((255.0 - roi.mean(axis=2)) / 255.0, 0.0, 1.0)
                    mask = darkness > 0.06
                    if _np.any(mask):
                        # Map dark text pixels smoothly to vivid red RGB(220, 38, 38) while keeping white background pure white
                        boosted = _np.clip(darkness * 1.15, 0.0, 1.0)
                        roi[:, :, 0] = _np.where(mask, 255.0 - boosted * (255.0 - 220.0), roi[:, :, 0])
                        roi[:, :, 1] = _np.where(mask, 255.0 - boosted * (255.0 - 28.0), roi[:, :, 1])
                        roi[:, :, 2] = _np.where(mask, 255.0 - boosted * (255.0 - 28.0), roi[:, :, 2])
                        arr[y0:y1, x0:x1] = _np.clip(roi, 0, 255).astype(_np.uint8)
                # Recolor active non-error query text to indigo RGB(67, 56, 202) without any box/border
                for r in active_non_err_rects:
                    x0 = max(0, int((r.x0 - 1.5) * scale))
                    y0 = max(0, int((r.y0 - 1.5) * scale))
                    x1 = min(pix.width, int((r.x1 + 1.5) * scale))
                    y1 = min(pix.height, int((r.y1 + 1.5) * scale))
                    if x1 <= x0 or y1 <= y0:
                        continue
                    roi = arr[y0:y1, x0:x1].astype(_np.float32)
                    darkness = _np.clip((255.0 - roi.mean(axis=2)) / 255.0, 0.0, 1.0)
                    mask = darkness > 0.06
                    if _np.any(mask):
                        boosted = _np.clip(darkness * 1.15, 0.0, 1.0)
                        roi[:, :, 0] = _np.where(mask, 255.0 - boosted * (255.0 - 67.0), roi[:, :, 0])
                        roi[:, :, 1] = _np.where(mask, 255.0 - boosted * (255.0 - 56.0), roi[:, :, 1])
                        roi[:, :, 2] = _np.where(mask, 255.0 - boosted * (255.0 - 202.0), roi[:, :, 2])
                        arr[y0:y1, x0:x1] = _np.clip(roi, 0, 255).astype(_np.uint8)
                recolored_pix = fitz.Pixmap(fitz.csRGB, pix.width, pix.height, arr.tobytes(), False)
                png_bytes = recolored_pix.tobytes("png")
            else:
                png_bytes = pix.tobytes("png")
        finally:
            doc.close()
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={"Cache-Control": "no-store"},
        )

    # Dynamic high-DPI virtual page preview for .docx or synthetic/seeded essays without raw PDF on disk
    doc = fitz.open()
    try:
        page = doc.new_page(width=595, height=842)
        page.insert_text(
            fitz.Point(48, 52),
            f"CITRA Document Inspector  |  {essay.filename}",
            fontsize=11,
            fontname="helv",
            color=(0.12, 0.16, 0.28),
        )
        page.insert_text(
            fitz.Point(48, 68),
            f"Virtual Page Reconstruction — Page {max(1, page_num)} of {max(1, essay.num_pages or 1)} (Red Text = Flagged Errors & Hallucinations)",
            fontsize=8.5,
            color=(0.38, 0.43, 0.54),
        )

        hl_q = (highlight or "").strip().lower()
        hl_tok = ""
        if hl_q:
            m_tok = _re.search(r"[a-zA-ZÀ-ỹ]{4,}", hl_q)
            if m_tok:
                hl_tok = m_tok.group(0).lower()

        # Render verdicts and citations cleanly with text-only red coloring for errors & hallucinations
        y = 96.0
        items_to_draw: list[tuple[str, str, str]] = []
        for v_idx, v in enumerate(verdicts, start=1):
            if len(items_to_draw) >= 8:
                break
            v_lbl = (v.label or "unresolved").lower()
            v_raw = (v.citation_raw or "").strip()
            items_to_draw.append((v_raw[:240], v_lbl, v_raw.lower()))
        if not items_to_draw:
            for idx, c in enumerate(citations[:8], start=1):
                ctx = (getattr(c, "context", None) or c.raw_text or "").strip()
                items_to_draw.append((f"[{idx}] {ctx[:220]}", "verified", ctx.lower()))

        for block_text, item_lbl, match_low in items_to_draw[:8]:
            is_halluc = item_lbl == "suspected_hallucination"
            is_meta_err = item_lbl == "metadata_error"

            # Only color the text in red — do NOT draw any box or border frame around it
            if is_halluc:
                badge_html = '<span style="color: #dc2626; font-weight: bold;">[NGUỒN BỊA ĐẶT / SUSPECTED HALLUCINATION]</span> '
                text_color = "#dc2626"
                font_weight = "600"
            elif is_meta_err:
                badge_html = '<span style="color: #dc2626; font-weight: bold;">[LỖI METADATA / METADATA ERROR]</span> '
                text_color = "#dc2626"
                font_weight = "600"
            elif item_lbl in ("verified", "resource"):
                badge_html = '<span style="color: #15803d; font-weight: bold;">[VERIFIED]</span> '
                text_color = "#1e293b"
                font_weight = "normal"
            else:
                badge_html = f'<span style="color: #475569; font-weight: bold;">[{_html.escape(item_lbl.upper())}]</span> '
                text_color = "#1e293b"
                font_weight = "normal"

            page.insert_htmlbox(
                fitz.Rect(48, y, 548, y + 66),
                f'<div style="font-family: serif; font-size: 9.2pt; color: {text_color}; font-weight: {font_weight}; line-height: 1.4;">{badge_html}{_html.escape(block_text)}</div>',
            )
            y += 74.0
            if y > 755:
                break

        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        png_bytes = pix.tobytes("png")
    finally:
        doc.close()

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=120"},
    )
