"""Local SQLite database for paper metadata storage.

This module provides a local database to cache paper metadata from:
1. ACL Anthology (NLP papers)
2. S2ORC (broad academic papers)
3. API queries (auto-sync)

The database uses SQLite with FTS5 for full-text search.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from integrity_checker.retrieval.normalization import (
    author_keys,
    normalize_arxiv_id,
    normalize_doi,
    title_similarity,
    title_tokens,
    year_key,
)

from .models import Paper, QueryLog
from .schemas import INIT_STATEMENTS

# Default database path (project root / data / local_papers.db)
DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "local_papers.db"

_DB_CACHE_LOCK = threading.Lock()
_INITIALIZED_DB_INODES: dict[str, int] = {}
_STATS_CACHE: dict[str, tuple[float, int, int, int, dict[str, Any]]] = {}
_STATS_CACHE_TTL_SECONDS = 3600.0
_MUTATION_VERSION = 0


def _bump_mutation_version() -> None:
    global _MUTATION_VERSION
    with _DB_CACHE_LOCK:
        _MUTATION_VERSION += 1


def _title_key(title: str | None) -> str:
    """Case/punctuation-insensitive key for exact-ish title comparison.

    Only used to look a row up in the curated ``known_papers`` table — it is
    deliberately stricter than :func:`title_similarity`, which is tuned for
    candidate ranking and treats containment as a near-match.
    """
    if not title:
        return ""
    text = title.casefold()
    text = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in text)
    return " ".join(text.split())


def _known_papers_metadata() -> dict[tuple[str, str], dict]:
    """Load the curated seminal-paper table lazily.

    The table lives in ``retrieval.retrieval_orchestrator``, which imports
    from the retrieval layer.  Importing it at module load time would create a
    cycle once retrieval starts depending on the database package, so the
    lookup is deferred until dedupe actually needs it.
    """
    from integrity_checker.retrieval.retrieval_orchestrator import _KNOWN_PAPERS

    return _KNOWN_PAPERS


class LocalDatabase:
    """Local SQLite database for paper metadata.

    Features:
        - FTS5 full-text search on title, authors, abstract
        - Fast lookup by DOI, arXiv ID
        - Query logging for analytics
        - Thread-safe connections
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Defaults to ./data/local_papers.db
        """
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema if not exists (cached per file inode)."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_key = str(self.db_path.resolve())
        try:
            if self.db_path.is_file():
                stat = self.db_path.stat()
                if stat.st_size > 0:
                    with _DB_CACHE_LOCK:
                        if _INITIALIZED_DB_INODES.get(resolved_key) == stat.st_ino:
                            return
        except OSError:
            pass

        with self._get_conn() as conn:
            for stmt in INIT_STATEMENTS:
                conn.executescript(stmt)
            # ``PRAGMA journal_mode`` returns a row, so it must be a query (not
            # part of a script). Use DELETE mode for Docker VirtioFS compatibility.
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.commit()

        try:
            stat = self.db_path.stat()
            if stat.st_size > 0:
                with _DB_CACHE_LOCK:
                    _INITIALIZED_DB_INODES[resolved_key] = stat.st_ino
        except OSError:
            pass

    @contextmanager
    def _get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection with row factory and in-memory FTS5 cache."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA cache_size=-16000")
        conn.execute("PRAGMA temp_store=MEMORY")
        try:
            yield conn
        finally:
            conn.close()

    # ==================== Basic CRUD ====================

    def add_paper(self, paper: Paper) -> int | None:
        """Add or update a paper in the database.

        Args:
            paper: Paper object to add

        Returns:
            Canonical paper row ID if successful, None if failed.

        Note:
            ``ON CONFLICT(doi) DO UPDATE`` keeps the *existing* row id in
            SQLite, so ``cursor.lastrowid`` is not reliable for conflict
            updates.  We resolve the row id explicitly so that provenance
            (``query_log.paper_id``, ``candidate.paper_id``) always points at
            the row that actually holds the metadata.
        """
        paper.doi = normalize_doi(paper.doi)
        paper.arxiv_id = normalize_arxiv_id(paper.arxiv_id)

        # SQLite UNIQUE permits multiple NULL values.  API results without a
        # DOI would therefore be inserted repeatedly on every run.  Reuse an
        # existing metadata record before attempting the insert.
        if not paper.doi:
            existing = self._find_existing_metadata_paper(paper)
            if existing is not None:
                if paper.abstract and paper.abstract.strip() and not (existing.abstract and existing.abstract.strip()):
                    with self._get_conn() as conn:
                        conn.execute(
                            "UPDATE papers SET abstract = ? WHERE id = ?",
                            (paper.abstract.strip(), existing.id),
                        )
                        conn.commit()
                    _bump_mutation_version()
                return existing.id

        # Guard against UNIQUE(arxiv_id) IntegrityError when a paper with the
        # same arxiv_id already exists under a different (or NULL) DOI.
        if paper.arxiv_id:
            existing_arxiv = self.find_by_arxiv_id(paper.arxiv_id)
            if existing_arxiv is not None:
                if not paper.doi or normalize_doi(existing_arxiv.doi) != paper.doi:
                    if paper.abstract and paper.abstract.strip() and not (existing_arxiv.abstract and existing_arxiv.abstract.strip()):
                        with self._get_conn() as conn:
                            conn.execute(
                                "UPDATE papers SET abstract = ? WHERE id = ?",
                                (paper.abstract.strip(), existing_arxiv.id),
                            )
                            conn.commit()
                        _bump_mutation_version()
                    return existing_arxiv.id

        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO papers (doi, arxiv_id, title, authors, year, venue,
                                   abstract, categories, external_ids, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doi) DO UPDATE SET
                    title = CASE
                        WHEN excluded.title IS NULL OR TRIM(excluded.title) = ''
                            THEN papers.title ELSE excluded.title END,
                    authors = CASE
                        WHEN excluded.authors IN ('[]', '') OR excluded.authors IS NULL
                            THEN papers.authors ELSE excluded.authors END,
                    year = COALESCE(excluded.year, papers.year),
                    venue = COALESCE(NULLIF(excluded.venue, ''), papers.venue),
                    abstract = COALESCE(NULLIF(excluded.abstract, ''), papers.abstract),
                    categories = CASE
                        WHEN excluded.categories IN ('[]', '') OR excluded.categories IS NULL
                            THEN papers.categories ELSE excluded.categories END,
                    external_ids = CASE
                        WHEN excluded.external_ids IN ('{}', '') OR excluded.external_ids IS NULL
                            THEN papers.external_ids ELSE excluded.external_ids END,
                    source = CASE
                        WHEN excluded.source IN ('local_db', 'known_papers')
                             AND papers.source NOT IN ('local_db', 'known_papers')
                            THEN papers.source
                        WHEN papers.source = 'acl' AND excluded.source <> 'acl'
                            THEN papers.source
                        ELSE excluded.source END,
                    created_at = papers.created_at
                """,
                (
                    paper.doi,
                    paper.arxiv_id,
                    paper.title,
                    json.dumps(paper.authors),
                    paper.year,
                    paper.venue,
                    paper.abstract,
                    json.dumps(paper.categories),
                    json.dumps(paper.external_ids),
                    paper.source,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            _bump_mutation_version()

            # Resolve the actual row id for query provenance.  A conflict
            # update keeps the original row id, so re-read it rather than
            # trusting ``cursor.lastrowid``.
            if paper.doi:
                row = conn.execute(
                    "SELECT id FROM papers WHERE doi = ? COLLATE NOCASE",
                    (paper.doi,),
                ).fetchone()
                return int(row["id"]) if row else None
            if paper.arxiv_id:
                row = conn.execute(
                    "SELECT id FROM papers WHERE arxiv_id = ? COLLATE NOCASE",
                    (paper.arxiv_id,),
                ).fetchone()
                if row:
                    return int(row["id"])
            if cursor.lastrowid:
                return cursor.lastrowid
            return None

    def _find_existing_metadata_paper(self, paper: Paper) -> Paper | None:
        """Find an existing no-DOI record using normalized metadata."""
        if not paper.title:
            return None
        candidates = self.fuzzy_search(
            title=paper.title,
            authors=paper.authors,
            year=paper.year,
            limit=20,
        )
        for candidate in candidates:
            if title_similarity(paper.title, candidate.title) < 0.90:
                continue
            query_year = year_key(paper.year)
            if query_year and candidate.year and abs(query_year - candidate.year) > 1:
                continue
            query_authors = author_keys(paper.authors)
            candidate_authors = author_keys(candidate.authors)
            if query_authors and candidate_authors and not query_authors & candidate_authors:
                continue
            return candidate
        return None

    def get_paper(self, paper_id: int) -> Paper | None:
        """Get paper by ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM papers WHERE id = ?", (paper_id,)
            ).fetchone()
            return Paper.from_dict(dict(row)) if row else None

    # ==================== Lookup Methods ====================

    def find_by_doi(self, doi: str | None) -> Paper | None:
        """Find paper by DOI.

        Args:
            doi: DOI to search for

        Returns:
            Paper if found, None otherwise
        """
        if not doi:
            return None

        doi = normalize_doi(doi)
        if not doi:
            return None

        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM papers WHERE doi = ? COLLATE NOCASE", (doi,)
            ).fetchone()
            return Paper.from_dict(dict(row)) if row else None

    def find_by_arxiv_id(self, arxiv_id: str | None) -> Paper | None:
        """Find paper by arXiv ID.

        Args:
            arxiv_id: arXiv ID to search for (e.g., "1706.03762")

        Returns:
            Paper if found, None otherwise
        """
        if not arxiv_id:
            return None

        arxiv_id = normalize_arxiv_id(arxiv_id)
        if not arxiv_id:
            return None

        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM papers WHERE arxiv_id = ? COLLATE NOCASE", (arxiv_id,)
            ).fetchone()
            return Paper.from_dict(dict(row)) if row else None

    def search_by_title(
        self,
        title: str,
        limit: int = 10,
        year: int | None = None,
        author: str | None = None,
    ) -> list[Paper]:
        """Search papers by title using FTS5.

        Args:
            title: Title to search for
            limit: Maximum results to return
            year: Optional year filter
            author: Optional author filter

        Returns:
            List of matching papers
        """
        with self._get_conn() as conn:
            tokens = title_tokens(title)
            if not tokens:
                return []
            # Match all meaningful words instead of the raw title string.
            # This tolerates terminal punctuation and Unicode dash variants.
            fts_query = " AND ".join(f'"{token}"' for token in tokens)

            if year and author:
                query = """
                    SELECT p.*, bm25(papers_fts) as rank
                    FROM papers_fts
                    JOIN papers p ON papers_fts.rowid = p.id
                    WHERE papers_fts MATCH ? AND p.year = ? AND p.authors LIKE ?
                    ORDER BY rank
                    LIMIT ?
                """
                rows = conn.execute(
                    query, (fts_query, year, f"%{author}%", limit)
                ).fetchall()
            elif year:
                query = """
                    SELECT p.*, bm25(papers_fts) as rank
                    FROM papers_fts
                    JOIN papers p ON papers_fts.rowid = p.id
                    WHERE papers_fts MATCH ? AND p.year = ?
                    ORDER BY rank
                    LIMIT ?
                """
                rows = conn.execute(query, (fts_query, year, limit)).fetchall()
            elif author:
                query = """
                    SELECT p.*, bm25(papers_fts) as rank
                    FROM papers_fts
                    JOIN papers p ON papers_fts.rowid = p.id
                    WHERE papers_fts MATCH ? AND p.authors LIKE ?
                    ORDER BY rank
                    LIMIT ?
                """
                rows = conn.execute(query, (fts_query, f"%{author}%", limit)).fetchall()
            else:
                query = """
                    SELECT p.*, bm25(papers_fts) as rank
                    FROM papers_fts
                    JOIN papers p ON papers_fts.rowid = p.id
                    WHERE papers_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """
                rows = conn.execute(query, (fts_query, limit)).fetchall()

            return [Paper.from_dict(dict(row)) for row in rows]

    def fuzzy_search(
        self,
        title: str | None = None,
        authors: list[str] | str | None = None,
        year: int | None = None,
        limit: int = 10,
    ) -> list[Paper]:
        """Fuzzy search for papers by title/authors/year.

        This method is used when exact lookup fails and we need
        to find potential matches.

        Args:
            title: Title to search
            authors: List of authors
            year: Publication year
            limit: Maximum results

        Returns:
            List of matching papers
        """
        query_authors = author_keys(authors)
        query_year = year_key(year)
        query_tokens = title_tokens(title)

        # FTS narrows the 80k+ ACL rows efficiently.  If an old database was
        # created before FTS was populated, fall back to a broad title query.
        rows: list[sqlite3.Row] = []
        with self._get_conn() as conn:
            if query_tokens:
                fts_query = " AND ".join(f'"{token}"' for token in query_tokens)
                rows = conn.execute(
                    """
                    SELECT p.*
                    FROM papers_fts
                    JOIN papers p ON papers_fts.rowid = p.id
                    WHERE papers_fts MATCH ?
                    LIMIT ?
                    """,
                    (fts_query, max(limit * 20, 50)),
                ).fetchall()

            if not rows and len(query_tokens) >= 3:
                # Fallback if first token lost a hyphen (e.g. "Scikitlearn" vs "Scikit-learn")
                sub_fts = " AND ".join(f'"{token}"' for token in query_tokens[1:])
                rows = conn.execute(
                    """
                    SELECT p.*
                    FROM papers_fts
                    JOIN papers p ON papers_fts.rowid = p.id
                    WHERE papers_fts MATCH ?
                    LIMIT ?
                    """,
                    (sub_fts, max(limit * 20, 50)),
                ).fetchall()

            if not rows and title:
                first_token = query_tokens[0] if query_tokens else str(title)
                rows = conn.execute(
                    "SELECT * FROM papers WHERE lower(title) LIKE ? LIMIT ?",
                    (f"%{first_token.casefold()}%", max(limit * 20, 50)),
                ).fetchall()

        papers = [Paper.from_dict(dict(row)) for row in rows]
        scored: list[tuple[float, Paper]] = []
        for paper in papers:
            score = title_similarity(title, paper.title) if title else 0.0
            if title and score < 0.70:
                continue

            candidate_authors = author_keys(paper.authors)
            author_match = bool(query_authors & candidate_authors)
            if query_authors and candidate_authors and not author_match:
                # A title containing generic words such as "transfer learning"
                # is not enough to identify a paper.  Require the first author
                # whenever both sides provide author metadata.
                continue

            if query_year and paper.year:
                distance = abs(query_year - paper.year)
                if distance > 3:
                    continue
                score += max(0.0, 0.08 - distance * 0.02)
            if author_match:
                score += 0.08
            scored.append((score, paper))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [paper for _, paper in scored[:limit]]

    # ==================== Query Logging ====================

    def log_query(
        self,
        query_params: dict[str, Any],
        found: bool,
        source: str,
        paper_id: int | None = None,
    ) -> int:
        """Log a database query for analytics.

        Args:
            query_params: Parameters used for the query
            found: Whether a paper was found
            source: Source of the result ('local_db', 'api')
            paper_id: ID of found paper (if any)

        Returns:
            Log entry ID
        """
        # Create hash of query params for deduplication
        param_str = json.dumps(query_params, sort_keys=True)
        query_hash = hashlib.md5(param_str.encode()).hexdigest()

        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO query_log (query_hash, found, source, paper_id, queried_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    query_hash,
                    1 if found else 0,
                    source,
                    paper_id,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            _bump_mutation_version()
            return cursor.lastrowid or 0

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics with Read-Through RAM Cache + Event Invalidation.

        Returns:
            Dictionary with stats
        """
        resolved_key = str(self.db_path.resolve())
        now_mono = time.monotonic()
        mtime_ns = 0
        file_size = 0
        try:
            if self.db_path.is_file():
                stat = self.db_path.stat()
                mtime_ns = stat.st_mtime_ns
                file_size = stat.st_size
        except OSError:
            pass

        with _DB_CACHE_LOCK:
            cached = _STATS_CACHE.get(resolved_key)
            if cached is not None:
                cached_at, c_mtime, c_size, c_ver, payload = cached
                if (
                    now_mono - cached_at < _STATS_CACHE_TTL_SECONDS
                    and c_mtime == mtime_ns
                    and c_size == file_size
                    and c_ver == _MUTATION_VERSION
                ):
                    return copy.deepcopy(payload)

        with self._get_conn() as conn:
            # Count by source (uses covering index idx_papers_source, avoiding 245MB table scan)
            source_counts = conn.execute(
                """
                SELECT source, COUNT(*) as count
                FROM papers
                GROUP BY source
                ORDER BY count DESC
                """
            ).fetchall()
            total_papers = sum(int(row[1]) for row in source_counts)

            # Count queries + hit rate in a single pass
            q_row = conn.execute(
                """
                SELECT
                    COUNT(*),
                    CAST(SUM(found) AS FLOAT) / COUNT(*) * 100
                FROM query_log
                """
            ).fetchone()
            total_queries = q_row[0] if q_row else 0
            hit_rate = (q_row[1] if q_row and q_row[1] is not None else 0) or 0

            # Recent queries
            recent_queries = conn.execute(
                """
                SELECT l.*, p.title
                FROM query_log l
                LEFT JOIN papers p ON l.paper_id = p.id
                ORDER BY l.queried_at DESC
                LIMIT 10
                """
            ).fetchall()

            result = {
                "total_papers": total_papers,
                "source_counts": {row[0]: row[1] for row in source_counts},
                "total_queries": total_queries,
                "hit_rate_percent": round(hit_rate, 2),
                "recent_queries": [dict(row) for row in recent_queries],
            }

        with _DB_CACHE_LOCK:
            _STATS_CACHE[resolved_key] = (
                now_mono,
                mtime_ns,
                file_size,
                _MUTATION_VERSION,
                copy.deepcopy(result),
            )
        return result

    # ==================== Bulk Operations ====================

    def add_papers_bulk(self, papers: list[Paper]) -> int:
        """Add multiple papers safely with DOI/arXiv normalization and conflict guards.

        Args:
            papers: List of papers to add

        Returns:
            Number of papers added
        """
        added = 0
        for p in papers:
            self.add_paper(p)
            added += 1
        return added

    def get_all_papers(self, limit: int = 100, offset: int = 0) -> list[Paper]:
        """Get all papers with pagination.

        Args:
            limit: Maximum papers to return
            offset: Number of papers to skip

        Returns:
            List of papers
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM papers ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [Paper.from_dict(dict(row)) for row in rows]

    def delete_all(self) -> int:
        """Delete all papers (for testing/reset).

        Returns:
            Number of papers deleted
        """
        with self._get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            conn.execute("DELETE FROM papers")
            conn.execute("DELETE FROM query_log")
            conn.commit()
            _bump_mutation_version()
            return count

    # ==================== Maintenance ====================

    def dedupe(self) -> dict[str, int]:
        """Remove duplicate/empty rows and rebuild the FTS index.

        Crossref/OpenAlex sync can insert several rows for the same work when
        the DOI is missing or differs only by URL prefix.  This routine:

        1. Deletes rows without a usable title.
        2. Removes DOI duplicates, preferring the row referenced by
           ``query_log.paper_id`` and the smallest ``id`` otherwise.
        3. Removes remaining ``(normalized title, year)`` duplicates.
        4. Folds ``known_papers`` seed rows onto the live row that carries the
           curated DOI (title-only matches are never folded).
        5. Rebuilds the FTS5 index so the search table matches ``papers``.

        Returns:
            Counts keyed by ``removed_empty_title``, ``removed_doi_duplicates``,
            ``removed_title_duplicates``, ``removed_known_paper_duplicates``
            and ``total_removed``.
        """
        removed_empty = 0
        removed_doi = 0
        removed_title = 0
        removed_known_papers = 0

        with self._get_conn() as conn:
            # 1. Drop rows with no usable title.
            cursor = conn.execute(
                "DELETE FROM papers WHERE title IS NULL OR TRIM(title) = ''"
            )
            removed_empty = cursor.rowcount or 0

            # 2. DOI duplicates.  Keep the row that is referenced by the query
            #    log (has provenance) and, as a tie-breaker, the lowest id.
            dup_dois = conn.execute(
                """
                SELECT doi
                FROM papers
                WHERE doi IS NOT NULL AND TRIM(doi) <> ''
                GROUP BY lower(doi)
                HAVING COUNT(*) > 1
                """
            ).fetchall()
            for row in dup_dois:
                doi = row["doi"]
                candidates = conn.execute(
                    """
                    SELECT p.id,
                           (SELECT COUNT(*) FROM query_log q
                            WHERE q.paper_id = p.id) AS refs
                    FROM papers p
                    WHERE lower(p.doi) = lower(?)
                    ORDER BY refs DESC, p.id ASC
                    """,
                    (doi,),
                ).fetchall()
                keep_id = candidates[0]["id"]
                drop_ids = [c["id"] for c in candidates[1:]]
                if not drop_ids:
                    continue
                placeholders = ",".join("?" for _ in drop_ids)
                # Re-point provenance to the surviving row before deleting.
                conn.execute(
                    f"UPDATE query_log SET paper_id = ? WHERE paper_id IN ({placeholders})",
                    (keep_id, *drop_ids),
                )
                cursor = conn.execute(
                    f"DELETE FROM papers WHERE id IN ({placeholders})",
                    tuple(drop_ids),
                )
                removed_doi += cursor.rowcount or 0

            # 3. Remaining (title, year) duplicates without a DOI.
            dup_titles = conn.execute(
                """
                SELECT lower(TRIM(title)) AS norm_title, COALESCE(year, -1) AS y
                FROM papers
                GROUP BY norm_title, y
                HAVING COUNT(*) > 1
                """
            ).fetchall()
            for row in dup_titles:
                candidates = conn.execute(
                    """
                    SELECT p.id,
                           (SELECT COUNT(*) FROM query_log q
                            WHERE q.paper_id = p.id) AS refs
                    FROM papers p
                    WHERE lower(TRIM(p.title)) = ?
                      AND COALESCE(p.year, -1) = ?
                    ORDER BY refs DESC, p.id ASC
                    """,
                    (row["norm_title"], row["y"]),
                ).fetchall()
                keep_id = candidates[0]["id"]
                drop_ids = [c["id"] for c in candidates[1:]]
                if not drop_ids:
                    continue
                placeholders = ",".join("?" for _ in drop_ids)
                conn.execute(
                    f"UPDATE query_log SET paper_id = ? WHERE paper_id IN ({placeholders})",
                    (keep_id, *drop_ids),
                )
                cursor = conn.execute(
                    f"DELETE FROM papers WHERE id IN ({placeholders})",
                    tuple(drop_ids),
                )
                removed_title += cursor.rowcount or 0

            # 4. Fold curated ``known_papers`` rows onto the canonical live
            #     row, matched by the *curated DOI* only (never by title).
            #
            #     The curated table is authoritative: its DOI lives in code
            #     (``_KNOWN_PAPERS``), not in the ``papers.doi`` column, so
            #     comparing the DB column alone would leave the seed rows
            #     looking like distinct papers forever.  We resolve the DOI
            #     from the curated entry and collapse the seed row onto the
            #     live row that carries it.
            #
            #     A title-based fallback is deliberately NOT used.  A title
            #     match cannot prove two rows are the same work here: the ACL
            #     corpus republishes the same title across years/venues (e.g.
            #     "Adam" the 2015 ICLR paper vs. an unrelated 2014 EMNLP
            #     "A Fast and Accurate Dependency Parser" row that shares the
            #     title of the known-paper entry but has a different DOI).
            #     Only a shared DOI is strong enough evidence, so entries
            #     whose curated DOI is absent from the DB are left untouched.
            curated_titles = {
                _title_key(info["title"]): info
                for info in _known_papers_metadata().values()
            }

            known_rows = conn.execute(
                "SELECT id, title, doi, year FROM papers WHERE source = 'known_papers'"
            ).fetchall()
            for known in known_rows:
                curated_doi = normalize_doi(known["doi"]) if known["doi"] else None
                if not curated_doi:
                    info = curated_titles.get(_title_key(known["title"]))
                    if not info or not info.get("doi"):
                        continue
                    curated_doi = normalize_doi(info["doi"])
                if not curated_doi:
                    continue

                target = conn.execute(
                    "SELECT id FROM papers "
                    "WHERE source <> 'known_papers' "
                    "AND doi IS NOT NULL AND lower(doi) = ? LIMIT 1",
                    (curated_doi,),
                ).fetchone()
                if target is None:
                    continue

                keep_id = target["id"]
                conn.execute(
                    "UPDATE query_log SET paper_id = ? WHERE paper_id = ?",
                    (keep_id, known["id"]),
                )
                cursor = conn.execute(
                    "DELETE FROM papers WHERE id = ?", (known["id"],)
                )
                removed_known_papers += cursor.rowcount or 0

            conn.commit()

            # 5. Rebuild FTS to match the deduped table.
            conn.execute("INSERT INTO papers_fts(papers_fts) VALUES('rebuild')")
            conn.commit()
            _bump_mutation_version()

        return {
            "removed_empty_title": removed_empty,
            "removed_doi_duplicates": removed_doi,
            "removed_title_duplicates": removed_title,
            "removed_known_paper_duplicates": removed_known_papers,
            "total_removed": (
                removed_empty + removed_doi + removed_title + removed_known_papers
            ),
        }
