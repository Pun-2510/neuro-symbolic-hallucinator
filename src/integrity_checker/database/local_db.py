"""Local SQLite database for paper metadata storage.

This module provides a local database to cache paper metadata from:
1. ACL Anthology (NLP papers)
2. S2ORC (broad academic papers)
3. API queries (auto-sync)

The database uses SQLite with FTS5 for full-text search.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from .models import Paper, QueryLog
from .schemas import INIT_STATEMENTS

# Default database path
DEFAULT_DB_PATH = Path("./data/local_papers.db")


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
        """Initialize database schema if not exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_conn() as conn:
            for stmt in INIT_STATEMENTS:
                conn.executescript(stmt)
            conn.commit()

    @contextmanager
    def _get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
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
            Paper ID if successful, None if failed
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO papers (doi, arxiv_id, title, authors, year, venue,
                                   abstract, categories, external_ids, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doi) DO UPDATE SET
                    title = excluded.title,
                    authors = excluded.authors,
                    year = excluded.year,
                    venue = excluded.venue,
                    abstract = excluded.abstract,
                    categories = excluded.categories,
                    external_ids = excluded.external_ids,
                    source = excluded.source,
                    created_at = excluded.created_at
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
            return cursor.lastrowid

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

        # Normalize DOI
        doi = doi.strip().lower()
        if doi.startswith("https://doi.org/"):
            doi = doi[16:]
        elif doi.startswith("http://doi.org/"):
            doi = doi[15:]
        elif doi.startswith("doi.org/"):
            doi = doi[9:]

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

        # Normalize arXiv ID
        arxiv_id = arxiv_id.strip()
        if arxiv_id.startswith("https://arxiv.org/abs/"):
            arxiv_id = arxiv_id[21:]
        elif arxiv_id.startswith("http://arxiv.org/abs/"):
            arxiv_id = arxiv_id[22:]
        elif arxiv_id.startswith("arxiv:"):
            arxiv_id = arxiv_id[6:]

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
            # Build FTS query
            fts_query = f'"{title}"'

            if year:
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
        authors: list[str] | None = None,
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
        conditions = []
        params = []

        if title:
            conditions.append("title LIKE ?")
            params.append(f"%{title}%")

        if year:
            conditions.append("year BETWEEN ? AND ?")
            params.extend([year - 1, year + 1])

        if authors:
            # Search in authors field (JSON array)
            author_condition = " OR ".join(["authors LIKE ?" for _ in authors])
            conditions.append(f"({author_condition})")
            params.extend([f"%{a}%" for a in authors])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT * FROM papers
            WHERE {where_clause}
            ORDER BY year DESC
            LIMIT ?
        """
        params.append(limit)

        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [Paper.from_dict(dict(row)) for row in rows]

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
            return cursor.lastrowid or 0

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with stats
        """
        with self._get_conn() as conn:
            # Count papers
            total_papers = conn.execute(
                "SELECT COUNT(*) FROM papers"
            ).fetchone()[0]

            # Count by source
            source_counts = conn.execute(
                """
                SELECT source, COUNT(*) as count
                FROM papers
                GROUP BY source
                ORDER BY count DESC
                """
            ).fetchall()

            # Count queries
            total_queries = conn.execute(
                "SELECT COUNT(*) FROM query_log"
            ).fetchone()[0]

            hit_rate = conn.execute(
                """
                SELECT
                    CAST(SUM(found) AS FLOAT) / COUNT(*) * 100
                FROM query_log
                """
            ).fetchone()[0] or 0

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

            return {
                "total_papers": total_papers,
                "source_counts": {row[0]: row[1] for row in source_counts},
                "total_queries": total_queries,
                "hit_rate_percent": round(hit_rate, 2),
                "recent_queries": [dict(row) for row in recent_queries],
            }

    # ==================== Bulk Operations ====================

    def add_papers_bulk(self, papers: list[Paper]) -> int:
        """Add multiple papers in a single transaction.

        Args:
            papers: List of papers to add

        Returns:
            Number of papers added
        """
        with self._get_conn() as conn:
            data = [
                (
                    p.doi,
                    p.arxiv_id,
                    p.title,
                    json.dumps(p.authors),
                    p.year,
                    p.venue,
                    p.abstract,
                    json.dumps(p.categories),
                    json.dumps(p.external_ids),
                    p.source,
                    datetime.now().isoformat(),
                )
                for p in papers
            ]

            conn.executemany(
                """
                INSERT INTO papers (doi, arxiv_id, title, authors, year, venue,
                                   abstract, categories, external_ids, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doi) DO UPDATE SET
                    title = excluded.title,
                    authors = excluded.authors,
                    year = excluded.year,
                    venue = excluded.venue,
                    abstract = excluded.abstract,
                    categories = excluded.categories,
                    external_ids = excluded.external_ids,
                    source = excluded.source
                """,
                data,
            )
            conn.commit()
            return len(papers)

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
            return count
