"""Local database module for paper metadata storage.

This module provides a local SQLite database to cache paper metadata,
reducing API calls to external services (Crossref, OpenAlex, Semantic Scholar).

Usage:
    from integrity_checker.database import LocalDatabase

    db = LocalDatabase()
    paper = db.find_by_doi("10.48550/arXiv.1706.03762")
    if not paper:
        # Query API, then add to DB
        db.add_paper(paper_data)
"""

from __future__ import annotations

from .local_db import LocalDatabase
from .models import Paper, QueryLog

__all__ = ["LocalDatabase", "Paper", "QueryLog"]
