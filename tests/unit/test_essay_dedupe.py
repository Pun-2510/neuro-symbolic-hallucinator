"""Regression tests for duplicate-upload collapsing in the app DB (handoff § 5 P5)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from integrity_checker.db.models import Base, CitationRecord, EssayRecord
from integrity_checker.db.repository import Repository


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'app.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_duplicate_filenames_are_collapsed(tmp_path) -> None:
    session = _session(tmp_path)
    repo = Repository(session)
    base_time = datetime(2026, 9, 1, tzinfo=timezone.utc)

    # Three uploads of the same file; only the newest produced citations.
    first = EssayRecord(filename="4.pdf", num_pages=37, uploaded_at=base_time)
    second = EssayRecord(filename="4.pdf", num_pages=37, uploaded_at=base_time + timedelta(days=1))
    third = EssayRecord(filename="4.pdf", num_pages=37, uploaded_at=base_time + timedelta(days=2))
    session.add_all([first, second, third])
    session.commit()

    session.add(
        CitationRecord(essay_id=third.id, raw_text="x", citation_type="reference", style="APA")
    )
    session.commit()

    grouped = repo.get_all_essays_deduped()
    assert len(grouped) == 1
    kept, dupes = grouped[0]
    # The copy that actually produced citations must be kept.
    assert kept.id == third.id
    assert set(dupes) == {first.id, second.id}


def test_distinct_filenames_are_preserved(tmp_path) -> None:
    session = _session(tmp_path)
    repo = Repository(session)
    session.add_all(
        [
            EssayRecord(filename="a.pdf", num_pages=1),
            EssayRecord(filename="b.pdf", num_pages=2),
        ]
    )
    session.commit()
    grouped = repo.get_all_essays_deduped()
    assert len(grouped) == 2
    assert all(dupes == [] for _, dupes in grouped)
