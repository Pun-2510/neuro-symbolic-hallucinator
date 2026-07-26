"""Essays endpoints — upload PDF và analyze."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db, get_pipeline
from integrity_checker.db.repository import Repository
from integrity_checker.models.api_schemas import CitationSchema, EssayUploadResponse
from integrity_checker.pipeline.integrity_pipeline import IntegrityPipeline

router = APIRouter()


@router.post("", response_model=EssayUploadResponse)
async def upload_essay(
    file: UploadFile = File(...),
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

        # Persist
        repo = Repository(db)
        essay = repo.create_essay(filename=file.filename, num_pages=report.num_pages)
        repo.add_citations(essay.id, [v.citation for v in report.verdicts])
        repo.add_verdicts(essay.id, report.verdicts)
        repo.commit()

        citations = [
            CitationSchema(
                raw_text=v.citation.raw_text,
                citation_type=v.citation.citation_type.value,
                style=v.citation.style.value,
                authors=v.citation.authors,
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


@router.get("/{essay_id}")
async def get_essay(
    essay_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Lấy essay + verdicts từ DB."""
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")
    return {
        "id": essay.id,
        "filename": essay.filename,
        "num_pages": essay.num_pages,
        "uploaded_at": essay.uploaded_at.isoformat() if essay.uploaded_at else None,
    }