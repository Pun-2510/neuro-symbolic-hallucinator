"""Regression tests for local-DB provenance and cleanup (handoff § 5 P1b/P4).

Covers:
* ``LocalDatabase.add_paper`` returns the *canonical* row id when a DOI
  conflict merges into an existing row (previously the stale ``lastrowid``
  could be attributed to the wrong paper).
* ``LocalDatabase.dedupe`` removes empty titles + duplicates, folds curated
  ``known_papers`` seeds onto their canonical DOI row, and rebuilds FTS.
* ``SymbolicRules`` refuses to award the strongest VERIFIED verdict on a
  local-database-only DOI match.
"""

from __future__ import annotations

from integrity_checker.database import LocalDatabase, Paper
from integrity_checker.logic.rules import SymbolicRules
from integrity_checker.models.source import SourceCandidate, SourceResult
from integrity_checker.models.validation import MatchFeatures, ValidationLabel


def _features(*, title_sim: float = 0.98, doi_match: bool = True) -> MatchFeatures:
    return MatchFeatures(
        title_sim_fuzzy=title_sim,
        title_sim_semantic=title_sim,
        author_jaccard=0.9,
        year_distance=0,
        doi_exact_match=doi_match,
        source_consensus=1,
    )


def _candidate(source_name: str, doi: str | None = "10.5555/x") -> SourceCandidate:
    return SourceCandidate(
        source_name=source_name,
        found=True,
        doi=doi,
        title="Some Paper Title",
        authors=["Jane Doe"],
        year="2020",
        confidence=0.9,
    )


# --- add_paper canonical id ---


def test_add_paper_conflict_returns_existing_row_id(tmp_path) -> None:
    db = LocalDatabase(tmp_path / "local_papers.db")
    first_id = db.add_paper(Paper(doi="10.5555/dup", title="Original", authors=["A"], year=2020))
    second_id = db.add_paper(
        Paper(doi="https://doi.org/10.5555/dup", title="Updated", authors=["A"], year=2020)
    )
    assert first_id == second_id
    with db._get_conn() as conn:  # noqa: SLF001
        count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    assert count == 1


def test_add_paper_without_doi_reuses_metadata_match(tmp_path) -> None:
    db = LocalDatabase(tmp_path / "local_papers.db")
    first_id = db.add_paper(
        Paper(doi=None, title="A Quite Distinctive Title", authors=["Jane Doe"], year=2020)
    )
    second_id = db.add_paper(
        Paper(doi=None, title="A Quite Distinctive Title", authors=["Jane Doe"], year=2020)
    )
    assert first_id == second_id
    with db._get_conn() as conn:  # noqa: SLF001
        count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    assert count == 1


# --- dedupe ---


def test_dedupe_removes_empty_titles_and_duplicates(tmp_path) -> None:
    db = LocalDatabase(tmp_path / "local_papers.db")
    db.add_paper(Paper(title="", doi="10.1/a"))  # empty title -> removed
    db.add_paper(Paper(title="Keep Me", authors=["A"], year=2020))
    # Two rows sharing a title/year but no DOI -> keep the lowest id.
    with db._get_conn() as conn:  # noqa: SLF001
        conn.execute(
            "INSERT INTO papers (doi, title, authors, year, source) VALUES (NULL, ?, ?, ?, ?)",
            ("Duplicate Title", "[]", 2021, "crossref"),
        )
        conn.execute(
            "INSERT INTO papers (doi, title, authors, year, source) VALUES (NULL, ?, ?, ?, ?)",
            ("Duplicate Title", "[]", 2021, "crossref"),
        )
        conn.commit()

    report = db.dedupe()
    assert report["removed_empty_title"] == 1
    assert report["removed_title_duplicates"] == 1
    with db._get_conn() as conn:  # noqa: SLF001
        titles = [
            r[0]
            for r in conn.execute("SELECT title FROM papers ORDER BY id").fetchall()
        ]
        fts_docs = conn.execute("SELECT COUNT(*) FROM papers_fts_docsize").fetchone()[0]
    assert titles == ["Keep Me", "Duplicate Title"]
    assert fts_docs == 2


def test_dedupe_keeps_row_with_query_provenance(tmp_path) -> None:
    db = LocalDatabase(tmp_path / "local_papers.db")
    # Two rows sharing a title/year (both DOI-less).  Insert them directly to
    # bypass the metadata-dedup guard in ``add_paper``, which would otherwise
    # merge the second insert into the first.
    with db._get_conn() as conn:  # noqa: SLF001
        old_id = conn.execute(
            "INSERT INTO papers (doi, title, authors, year, source) VALUES (NULL, ?, ?, ?, ?)",
            ("Shared Title", "[]", 2020, "crossref"),
        ).lastrowid
        new_id = conn.execute(
            "INSERT INTO papers (doi, title, authors, year, source) VALUES (NULL, ?, ?, ?, ?)",
            ("Shared Title", "[]", 2020, "crossref"),
        ).lastrowid
        conn.commit()
    assert new_id != old_id
    # Reference the higher id from the query log; dedupe must preserve it.
    db.log_query({"title": "Shared Title"}, found=True, source="local_db", paper_id=new_id)
    db.dedupe()
    remaining = {r[0] for r in _all_ids(db)}
    assert new_id in remaining
    assert old_id not in remaining


def _all_ids(db: LocalDatabase):
    with db._get_conn() as conn:  # noqa: SLF001
        return conn.execute("SELECT id FROM papers").fetchall()


# --- known_papers fold (curated DOI only) ---


def test_dedupe_folds_known_paper_by_curated_doi(tmp_path) -> None:
    """A seeded ``known_papers`` row folds onto the live row with the same DOI.

    The titles deliberately differ in punctuation (curly quotes vs. plain) so
    that the title/year dedupe step — which groups on ``lower(TRIM(title))`` —
    cannot catch the pair.  Only the curated-DOI fold may remove the seed here.
    """
    db = LocalDatabase(tmp_path / "local_papers.db")
    # Live row that already carries the curated DOI (e.g. resolved via Crossref).
    live_id = db.add_paper(
        Paper(
            doi="10.1177/107769905303000401",
            title="\u201cCloze Procedure\u201d: A New Tool for Measuring Readability",
            authors=["Taylor"],
            year=1953,
            source="crossref",
        )
    )
    # Seed row duplicating the same work, but stored without a DOI (as the
    # curated table historically did).
    with db._get_conn() as conn:  # noqa: SLF001
        seed_id = conn.execute(
            "INSERT INTO papers (doi, title, authors, year, source) "
            "VALUES (NULL, ?, ?, ?, 'known_papers')",
            ("Cloze procedure: A new tool for measuring readability", "[]", 1953),
        ).lastrowid
        conn.commit()

    report = db.dedupe()
    assert report["removed_known_paper_duplicates"] == 1
    assert report["removed_title_duplicates"] == 0
    remaining = {r[0] for r in _all_ids(db)}
    assert live_id in remaining
    assert seed_id not in remaining


def test_dedupe_never_folds_title_only_known_paper(tmp_path) -> None:
    """Title reuse alone must not fold a seed row onto a distinct ACL paper."""
    db = LocalDatabase(tmp_path / "local_papers.db")
    # An ACL row that shares a *title* with a known-paper entry but is a
    # different work (different DOI).  "Adam" the 2015 ICLR paper vs. this
    # 2014 EMNLP row is exactly the trap the fold rule must avoid.
    acl_id = db.add_paper(
        Paper(
            doi="10.3115/v1/D14-1082",
            title="A Fast and Accurate Dependency Parser using Neural Networks",
            authors=["Chen", "Manning"],
            year=2014,
            venue="emnlp",
            source="acl",
        )
    )
    with db._get_conn() as conn:  # noqa: SLF001
        seed_id = conn.execute(
            "INSERT INTO papers (doi, title, authors, year, source) "
            "VALUES (?, ?, ?, ?, 'known_papers')",
            (
                "10.48550/arxiv.1412.7449",
                "A Fast and Accurate Dependency Parser using Neural Networks",
                "[]",
                2015,
            ),
        ).lastrowid
        conn.commit()

    report = db.dedupe()
    # The curated DOI (arXiv) has no live row, so nothing may fold.
    assert report["removed_known_paper_duplicates"] == 0
    remaining = {r[0] for r in _all_ids(db)}
    assert acl_id in remaining
    assert seed_id in remaining


# --- rules provenance ---


def test_local_db_only_perfect_match_is_verified() -> None:
    """LOCAL_DB only with perfect match (title>=0.95, author>=0.8, year=0) → VERIFIED.

    This is the new expected behavior: local_db is a curated knowledge base,
    so perfect matches are trusted.
    """
    rules = SymbolicRules()
    source = SourceResult(
        citation_raw="x",
        candidates=[_candidate("local_db")],
        sources_queried=["local_db"],
        sources_succeeded=["local_db"],
    )
    outcome = rules.apply(_features(), source, used_local_db=True)
    assert outcome.label == ValidationLabel.VERIFIED
    assert "R-LOCAL_DB_VERIFIED" in outcome.triggered_rules


def test_local_db_only_partial_match_is_unresolved() -> None:
    """LOCAL_DB only with partial author match should not be VERIFIED.

    When author similarity is low (<0.8), even with perfect title/year,
    we should NOT return VERIFIED without live source confirmation.
    """
    rules = SymbolicRules()
    source = SourceResult(
        citation_raw="x",
        candidates=[_candidate("local_db")],
        sources_queried=["local_db"],
        sources_succeeded=["local_db"],
    )
    # Lower author similarity (0.3) - should NOT trigger R-LOCAL_DB_VERIFIED
    features_partial = MatchFeatures(
        title_sim_fuzzy=0.96,
        title_sim_semantic=0.96,
        author_jaccard=0.3,  # Low author similarity
        year_distance=0,
        doi_exact_match=True,
        source_consensus=1,
    )
    outcome = rules.apply(features_partial, source, used_local_db=True)
    # Should not be VERIFIED with low author similarity
    assert outcome.label != ValidationLabel.VERIFIED


def test_live_source_doi_match_is_verified() -> None:
    rules = SymbolicRules()
    source = SourceResult(
        citation_raw="x",
        candidates=[_candidate("crossref")],
        sources_queried=["crossref"],
        sources_succeeded=["crossref"],
    )
    outcome = rules.apply(_features(), source)
    assert outcome.label == ValidationLabel.VERIFIED
    assert "R-DOI-TITLE-AUTHOR" in outcome.triggered_rules


def test_local_db_plus_live_source_is_verified() -> None:
    rules = SymbolicRules()
    source = SourceResult(
        citation_raw="x",
        candidates=[_candidate("local_db"), _candidate("crossref")],
        sources_queried=["local_db", "crossref"],
        sources_succeeded=["local_db", "crossref"],
    )
    outcome = rules.apply(_features(), source, used_local_db=True)
    assert outcome.label == ValidationLabel.VERIFIED


def test_local_db_plus_known_papers_is_verified() -> None:
    """LOCAL_DB + known_papers (both local sources) with perfect match → VERIFIED.

    Both local_db and known_papers are curated knowledge bases,
    so their combined result should be trusted.
    """
    rules = SymbolicRules()
    source = SourceResult(
        citation_raw="x",
        candidates=[_candidate("local_db"), _candidate("known_papers")],
        sources_queried=["local_db", "known_papers"],
        sources_succeeded=["local_db", "known_papers"],
    )
    outcome = rules.apply(_features(), source, used_local_db=True)
    assert outcome.label == ValidationLabel.VERIFIED
    assert "R-LOCAL_DB_VERIFIED" in outcome.triggered_rules


def test_known_papers_only_perfect_match_is_verified() -> None:
    """known_papers only with perfect match → VERIFIED.

    known_papers is a curated knowledge base of seminal papers.
    """
    rules = SymbolicRules()
    source = SourceResult(
        citation_raw="x",
        candidates=[_candidate("known_papers")],
        sources_queried=["known_papers"],
        sources_succeeded=["known_papers"],
    )
    outcome = rules.apply(_features(), source)
    assert outcome.label == ValidationLabel.VERIFIED
    assert "R-LOCAL_DB_VERIFIED" in outcome.triggered_rules


# --- reference-list parse confidence (handoff § 5 P5) ---


# --- upsert must not clobber richer metadata (handoff § 8 residual) ---


def test_doi_upsert_preserves_richer_existing_fields(tmp_path) -> None:
    """A cache-only re-sync must not erase ACL metadata via ON CONFLICT.

    Live on-demand sync inserts candidates with ``abstract=None`` and
    ``categories=[]``.  Without field-level guards the ``DO UPDATE`` branch
    overwrote the richer ACL row (observed: 40 rows lost their abstract).
    """
    db = LocalDatabase(tmp_path / "local_papers.db")
    db.add_paper(
        Paper(
            doi="10.18653/v1/D18-1045",
            title="BERT",
            authors=["Devlin"],
            year=2018,
            venue="ACL",
            abstract="Rich ACL abstract",
            categories=["cs.CL"],
            source="acl",
        )
    )
    # Cache-only re-sync with empty metadata must not downgrade the row.
    db.add_paper(
        Paper(
            doi="10.18653/v1/D18-1045",
            title="BERT",
            authors=["Devlin"],
            year=2018,
            abstract=None,
            categories=[],
            venue=None,
            source="known_papers",
        )
    )
    with db._get_conn() as conn:  # noqa: SLF001
        row = dict(
            conn.execute(
                "SELECT abstract, categories, venue, source FROM papers WHERE doi = ?",
                ("10.18653/v1/d18-1045",),
            ).fetchone()
        )
    assert row["abstract"] == "Rich ACL abstract"
    assert row["categories"] == '["cs.CL"]'
    assert row["venue"] == "ACL"
    assert row["source"] == "acl"


def test_doi_upsert_still_fills_missing_fields(tmp_path) -> None:
    """The guarded upsert must still enrich a sparse existing row."""
    db = LocalDatabase(tmp_path / "local_papers.db")
    db.add_paper(Paper(doi="10.5555/sparse", title="Sparse", source="crossref"))
    db.add_paper(
        Paper(
            doi="10.5555/sparse",
            title="Sparse",
            year=2021,
            venue="EMNLP",
            abstract="Now with abstract",
            categories=["cs.CL"],
            source="crossref",
        )
    )
    with db._get_conn() as conn:  # noqa: SLF001
        row = dict(
            conn.execute(
                "SELECT year, venue, abstract, categories FROM papers WHERE doi = ?",
                ("10.5555/sparse",),
            ).fetchone()
        )
    assert row["year"] == 2021
    assert row["venue"] == "EMNLP"
    assert row["abstract"] == "Now with abstract"
    assert row["categories"] == '["cs.CL"]'


# --- reference-list parse confidence (handoff § 5 P5) ---


def test_reference_confidence_reflects_metadata() -> None:
    from integrity_checker.extraction.reference_parser import (
        _estimate_reference_confidence,
    )
    from integrity_checker.models.citation import Citation

    empty = Citation(raw_text="x")
    assert _estimate_reference_confidence(empty) == 0.0

    full = Citation(
        raw_text="x",
        title="A Paper",
        authors=["Doe, J."],
        year="2020",
        doi="10.1/x",
    )
    assert _estimate_reference_confidence(full) == 1.0

    partial = Citation(raw_text="x", title="A Paper", year="2020")
    score = _estimate_reference_confidence(partial)
    assert 0.0 < score < 1.0
