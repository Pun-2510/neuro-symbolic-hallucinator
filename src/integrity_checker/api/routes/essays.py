"""Essays endpoints — upload PDF và analyze."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_current_user, get_db, get_pipeline, require_admin
from integrity_checker.db.models import User
from integrity_checker.db.repository import Repository
from integrity_checker.models.api_schemas import CitationSchema, EssayUploadResponse
from integrity_checker.pipeline.integrity_pipeline import IntegrityPipeline

router = APIRouter()


@router.post("", response_model=EssayUploadResponse)
async def upload_essay(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pipeline: IntegrityPipeline = Depends(get_pipeline),
) -> EssayUploadResponse:
    """Upload PDF → parse → extract → validate (chạy end-to-end)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    # Lưu tạm
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Chạy pipeline (offload executor để không block event loop)
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(None, pipeline.run, tmp_path, 0)

        # Persist with user_id
        repo = Repository(db)
        essay = repo.create_essay_with_user(
            filename=file.filename,
            num_pages=report.num_pages,
            user_id=current_user.id
        )
        repo.add_citations(essay.id, [v.citation for v in report.verdicts])
        repo.add_verdicts(essay.id, report.verdicts)

        # Lưu full pipeline output (style_profile + cis) để GET /report trả về đầy đủ
        style_profile_dict = None
        if report.style_profile:
            sp = report.style_profile
            if isinstance(sp, dict):
                # Pipeline trả dict — normalize về cấu trúc chuẩn
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
                # Object → convert
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
                # Convert components nếu là dict-like object (e.g., CISComponents dataclass)
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
                components = cis_obj.components
                if not isinstance(components, dict):
                    # CISComponents dataclass with attributes
                    components = {
                        attr: getattr(components, attr)
                        for attr in dir(components)
                        if not attr.startswith("_") and not callable(getattr(components, attr, None))
                        and attr in ["verified_ratio", "metadata_accuracy", "in_text_bib_consistency", "format_consistency", "identifier_validity"]
                    }
                cis_dict = {
                    "score": cis_obj.score,
                    "components": components,
                    "weights_used": getattr(cis_obj, "weights_used", {}) or {},
                    "num_citations": getattr(cis_obj, "num_citations", 0),
                    "num_unresolved": getattr(cis_obj, "num_unresolved", 0),
                    "disclaimer": getattr(cis_obj, "disclaimer", ""),
                }

        repo.update_essay_pipeline_output(
            essay.id,
            style_profile=style_profile_dict,
            cis=cis_dict,
        )
        repo.commit()

        def _author_to_str(a):
            """Convert Author object or string to plain string."""
            if isinstance(a, str):
                return a
            if hasattr(a, "last_name"):
                parts = [a.last_name]
                if getattr(a, "first_name", None):
                    parts.append(a.first_name)
                if getattr(a, "middle_name", None):
                    parts.append(a.middle_name)
                return " ".join(p for p in parts if p)
            return str(a)

        citations = [
            CitationSchema(
                raw_text=v.citation.raw_text,
                citation_type=v.citation.citation_type.value if hasattr(v.citation.citation_type, "value") else str(v.citation.citation_type),
                style=v.citation.style.value if hasattr(v.citation.style, "value") else str(v.citation.style),
                authors=[_author_to_str(a) for a in (v.citation.authors or [])],
                year=v.citation.year,
                title=v.citation.title,
                venue=v.citation.venue,
                doi=v.citation.doi,
                url=v.citation.url,
                page_num=v.citation.page_num,
                confidence=v.citation.confidence,
            )
            for v in report.verdicts
        ]

        return EssayUploadResponse(
            essay_id=essay.id,
            filename=essay.filename,
            num_pages=essay.num_pages,
            num_citations=report.num_citations,
            citations=citations,
            summary={
                "cis_score": report.cis.score if report.cis else None,
                "num_unresolved": report.cis.num_unresolved if report.cis else 0,
            },
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.get("", response_model=list[dict])
def list_essays(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List essays for current user (or all for admin)."""
    repo = Repository(db)

    if current_user.role == "admin":
        essays = repo.get_all_essays()
    else:
        essays = repo.get_user_essays(current_user.id)

    return [
        {
            "id": e.id,
            "filename": e.filename,
            "num_pages": e.num_pages,
            "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
            "user_id": e.user_id,
        }
        for e in essays
    ]


@router.get("/all", response_model=list[dict])
def list_all_essays(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all essays (admin only)."""
    repo = Repository(db)
    essays = repo.get_all_essays()

    return [
        {
            "id": e.id,
            "filename": e.filename,
            "num_pages": e.num_pages,
            "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
            "user_id": e.user_id,
        }
        for e in essays
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

    db.delete(essay)
    db.commit()

    return {"message": f"Essay {essay_id} deleted"}