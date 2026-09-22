"""Pydantic models for local database."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Paper:
    """Paper metadata stored in local database.

    This is a simplified model focused on fields needed for citation verification.
    """

    id: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    categories: list[str] = field(default_factory=list)
    external_ids: dict[str, str] = field(default_factory=dict)
    source: str = "api"  # 'acl', 's2orc', 'api'
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "abstract": self.abstract,
            "categories": self.categories,
            "external_ids": self.external_ids,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Paper:
        """Create Paper from dictionary."""
        authors = data.get("authors", [])
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except json.JSONDecodeError:
                authors = [authors]

        categories = data.get("categories", [])
        if isinstance(categories, str):
            try:
                categories = json.loads(categories)
            except json.JSONDecodeError:
                categories = [categories]

        external_ids = data.get("external_ids", {})
        if isinstance(external_ids, str):
            try:
                external_ids = json.loads(external_ids)
            except json.JSONDecodeError:
                external_ids = {}

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            id=data.get("id"),
            doi=data.get("doi"),
            arxiv_id=data.get("arxiv_id"),
            title=data.get("title", ""),
            authors=authors,
            year=data.get("year"),
            venue=data.get("venue"),
            abstract=data.get("abstract"),
            categories=categories,
            external_ids=external_ids,
            source=data.get("source", "api"),
            created_at=created_at,
        )

    def matches_query(self, title: str | None = None, authors: list[str] | None = None, year: int | None = None) -> bool:
        """Check if paper matches given query parameters."""
        if title and self.title:
            # Simple case-insensitive substring match
            if title.lower() not in self.title.lower():
                return False

        if year and self.year:
            if abs(year - self.year) > 1:  # Allow 1 year tolerance
                return False

        if authors and self.authors:
            # Check if any author matches
            author_found = False
            for query_author in authors[:3]:  # Check first 3 authors
                query_author_lower = query_author.lower()
                for paper_author in self.authors:
                    if query_author_lower in paper_author.lower():
                        author_found = True
                        break
                if author_found:
                    break
            if not author_found:
                return False

        return True


@dataclass
class QueryLog:
    """Log entry for database queries."""

    id: int | None = None
    query_hash: str = ""
    found: bool = False
    source: str | None = None
    paper_id: int | None = None
    queried_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "query_hash": self.query_hash,
            "found": self.found,
            "source": self.source,
            "paper_id": self.paper_id,
            "queried_at": self.queried_at.isoformat() if self.queried_at else None,
        }
