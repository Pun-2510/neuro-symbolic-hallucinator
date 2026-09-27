"""Essays endpoints — upload PDF và analyze."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_current_user, get_db, get_pipeline, require_admin
from integrity_checker.api.progress import get_tracker
from integrity_checker.db.models import User
from integrity_checker.db.repository import Repository
from integrity_checker.models.api_schemas import CitationSchema, EssayUploadResponse
from integrity_checker.pipeline.integrity_pipeline import IntegrityPipeline

router = APIRouter()


# ---------------------------------------------------------------------------
# Background pipeline task
# ---------------------------------------------------------------------------

async def _run_pipeline_task(
    essay_id: int,
    tmp_path: str,
    user_id: int,
    pipeline: IntegrityPipeline,
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
        loop = asyncio.get_event_loop()

        def _run_pipeline_sync() -> Any:
            return asyncio.run(
                pipeline.run_async(
                    tmp_path,
                    essay_id=essay_id,
                    progress_callback=_progress_to_threadlocal,
                )
            )

        report = await loop.run_in_executor(None, _run_pipeline_sync)
        tracker.complete(essay_id)

        # Persist to DB using a fresh session
        session = get_session()
        try:
            repo = Repository(session)
            # Update essay with page count (may have been 0 on creation)
            essay = repo.get_essay(essay_id)
            if essay:
                essay.num_pages = report.num_pages

            repo.add_citations(essay_id, [v.citation for v in report.verdicts])
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
        tracker.fail(essay_id, str(exc))
    finally:
        # Always clean up the temp file
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=EssayUploadResponse)
async def upload_essay(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pipeline: IntegrityPipeline = Depends(get_pipeline),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> EssayUploadResponse:
    """Upload PDF → save → return essay_id immediately.

    The actual analysis runs in the background and the ProcessingScreen
    polls ``GET /essays/{id}/status`` for live progress.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Create essay record immediately (num_pages=0 until pipeline fills it)
    repo = Repository(db)
    essay = repo.create_essay_with_user(
        filename=file.filename,
        num_pages=0,
        user_id=current_user.id,
    )
    repo.commit()

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return real-time pipeline progress for the ProcessingScreen.

    Returns a snapshot of the in-memory ProgressState.  If the tracker has no
    entry (task finished or server restarted), falls back to checking the DB:
    - Verdicts written → status=completed
    - No verdicts yet → status=queued/processing
    """
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")

    if current_user.role != "admin" and essay.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    tracker = get_tracker()
    state = tracker.get(essay_id)

    if state is not None:
        return state.to_snapshot()

    # No tracker entry — fall back to DB state
    verdicts = repo.get_verdicts(essay_id)
    if verdicts:
        # Pipeline completed (possibly via cache hit or prior run)
        return {
            "status": "completed",
            "step": "done",
            "step_index": 7,
            "total_steps": 8,
            "message": "Analysis complete",
            "citations_found": essay.num_pages,
            "references_found": 0,
            "linked": 0,
            "sources_queried": {},
            "elapsed_seconds": 0.0,
            "finished_at": None,
            "error": None,
        }

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
    repo = Repository(db)

    grouped = repo.get_all_essays_deduped()
    if current_user.role != "admin":
        grouped = [
            (essay, dupes)
            for essay, dupes in grouped
            if essay.user_id == current_user.id
        ]

    return [
        {
            "id": e.id,
            "filename": e.filename,
            "num_pages": e.num_pages,
            "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
            "user_id": e.user_id,
            "duplicate_ids": dupes,
        }
        for e, dupes in grouped
    ]


@router.get("/all", response_model=list[dict])
def list_all_essays(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all essays (admin only), collapsing duplicate uploads."""
    repo = Repository(db)
    grouped = repo.get_all_essays_deduped()

    return [
        {
            "id": e.id,
            "filename": e.filename,
            "num_pages": e.num_pages,
            "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
            "user_id": e.user_id,
            "duplicate_ids": dupes,
        }
        for e, dupes in grouped
    ]


@router.get("/{essay_id}")
async def get_essay(
    essay_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Lấy essay + verdicts từ DB."""
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")

    # Ownership check
    if current_user.role != "admin" and essay.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": essay.id,
        "filename": essay.filename,
        "num_pages": essay.num_pages,
        "uploaded_at": essay.uploaded_at.isoformat() if essay.uploaded_at else None,
        "user_id": essay.user_id,
    }


@router.delete("/{essay_id}")
async def delete_essay(
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

    # Clean up progress tracker
    get_tracker().clear(essay_id)

    db.delete(essay)
    db.commit()

    return {"message": f"Essay {essay_id} deleted"}
