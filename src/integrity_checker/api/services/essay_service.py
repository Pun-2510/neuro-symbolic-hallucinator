"""EssayService — orchestration giữa API + pipeline + DB."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from integrity_checker.db.repository import Repository
from integrity_checker.models.validation import CitationVerdict
from integrity_checker.pipeline.integrity_pipeline import IntegrityPipeline


class EssayService:
    """Service layer — wrap pipeline + persistence."""

    def __init__(self, db: Session, pipeline: IntegrityPipeline | None = None) -> None:
        self.db = db
        self.repo = Repository(db)
        self.pipeline = pipeline or IntegrityPipeline()

    async def upload_and_analyze(self, pdf_bytes: bytes, filename: str) -> tuple[int, list[CitationVerdict]]:
        """Upload → analyze → persist. Returns (essay_id, verdicts)."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            loop = asyncio.get_event_loop()
            report = await loop.run_in_executor(None, self.pipeline.run, tmp_path, 0)

            essay = self.repo.create_essay(filename=filename, num_pages=report.num_pages)
            self.repo.add_citations(essay.id, [v.citation for v in report.verdicts])
            self.repo.add_verdicts(essay.id, report.verdicts)
            self.repo.commit()
            return essay.id, report.verdicts
        finally:
            Path(tmp_path).unlink(missing_ok=True)