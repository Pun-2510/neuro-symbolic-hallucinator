"""Repository — CRUD helpers cho ORM models."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from integrity_checker.db.models import CitationRecord, EssayRecord, VerdictRecord
from integrity_checker.models.citation import Citation
from integrity_checker.models.validation import CitationVerdict


class Repository:
    """Thin wrapper quanh Session — methods domain-specific."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # -- Essays --

    def create_essay(self, filename: str, num_pages: int) -> EssayRecord:
        essay = EssayRecord(filename=filename, num_pages=num_pages)
        self.session.add(essay)
        self.session.flush()
        return essay

    def get_essay(self, essay_id: int) -> EssayRecord | None:
        return self.session.get(EssayRecord, essay_id)

    # -- Citations --

    def add_citations(self, essay_id: int, citations: list[Citation]) -> list[CitationRecord]:
        records = [
            CitationRecord(
                essay_id=essay_id,
                raw_text=c.raw_text,
                citation_type=c.citation_type.value,
                style=c.style.value,
                authors=json.dumps(c.authors, ensure_ascii=False),
                year=c.year,
                title=c.title,
                venue=c.venue,
                doi=c.doi,
                url=c.url,
                page_num=c.page_num,
                confidence=c.confidence,
            )
            for c in citations
        ]
        self.session.add_all(records)
        self.session.flush()
        return records

    # -- Verdicts --

    def add_verdicts(self, essay_id: int, verdicts: list[CitationVerdict]) -> None:
        records = [
            VerdictRecord(
                essay_id=essay_id,
                citation_raw=v.citation.raw_text,
                label=v.label.value,
                confidence=v.confidence,
                reasoning=v.reasoning,
                triggered_rules=json.dumps(v.triggered_rules, ensure_ascii=False),
                mismatched_fields=json.dumps(v.mismatched_fields, ensure_ascii=False),
                features=json.dumps(
                    {
                        "title_sim_fuzzy": v.features.title_sim_fuzzy,
                        "title_sim_semantic": v.features.title_sim_semantic,
                        "author_jaccard": v.features.author_jaccard,
                        "year_distance": v.features.year_distance,
                        "doi_exact_match": v.features.doi_exact_match,
                        "source_consensus": v.features.source_consensus,
                    },
                    ensure_ascii=False,
                ),
            )
            for v in verdicts
        ]
        self.session.add_all(records)
        self.session.flush()

    def get_verdicts(self, essay_id: int) -> list[VerdictRecord]:
        return list(
            self.session.query(VerdictRecord)
            .filter(VerdictRecord.essay_id == essay_id)
            .all()
        )

    # -- commit --

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()