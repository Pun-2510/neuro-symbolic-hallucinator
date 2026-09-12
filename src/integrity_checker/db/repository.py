"""Repository — CRUD helpers cho ORM models."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from datetime import datetime, timezone

from integrity_checker.db.models import (
    CitationCache,
    CitationRecord,
    EssayRecord,
    Session,
    User,
    VerdictRecord,
)
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
        def _serialize_authors(authors):
            """Convert Author objects (or other non-JSON types) to plain strings."""
            if not authors:
                return "[]"
            out = []
            for a in authors:
                if isinstance(a, str):
                    out.append(a)
                elif hasattr(a, "last_name"):
                    # Author object - extract name parts
                    parts = [a.last_name]
                    if getattr(a, "first_name", None):
                        parts.append(a.first_name)
                    if getattr(a, "middle_name", None):
                        parts.append(a.middle_name)
                    out.append(" ".join(p for p in parts if p))
                else:
                    out.append(str(a))
            return json.dumps(out, ensure_ascii=False)

        records = [
            CitationRecord(
                essay_id=essay_id,
                raw_text=c.raw_text,
                citation_type=c.citation_type.value if hasattr(c.citation_type, "value") else str(c.citation_type),
                style=c.style.value if hasattr(c.style, "value") else str(c.style),
                authors=_serialize_authors(c.authors),
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
                # v1.2 fields
                mapping_status=v.mapping_status.value if v.mapping_status else "matched",
                mapping_confidence=v.mapping_confidence,
                style_penalty=getattr(v, "style_penalty", None),
                domain_exception=getattr(v, "domain_exception", False),
                is_overridden=v.is_overridden,
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

    # -- Users --

    def get_user_by_username(self, username: str) -> User | None:
        return self.session.query(User).filter(User.username == username).first()

    def create_user(self, username: str, password_hash: str, role: str) -> User:
        user = User(username=username, password_hash=password_hash, role=role)
        self.session.add(user)
        self.session.flush()
        return user

    def update_user(self, user_id: int, **kwargs) -> User | None:
        user = self.session.get(User, user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        self.session.flush()
        return user

    def delete_user(self, user_id: int) -> bool:
        user = self.session.get(User, user_id)
        if not user:
            return False
        self.session.delete(user)
        self.session.flush()
        return True

    def get_all_users(self) -> list[User]:
        return list(self.session.query(User).all())

    # -- Sessions --

    def create_session(self, user_id: int, token: str, expires_at: datetime) -> Session:
        session = Session(user_id=user_id, token=token, expires_at=expires_at)
        self.session.add(session)
        self.session.flush()
        return session

    def get_session_by_token(self, token: str) -> Session | None:
        return self.session.query(Session).filter(Session.token == token).first()

    def delete_session(self, token: str) -> bool:
        session = self.get_session_by_token(token)
        if not session:
            return False
        self.session.delete(session)
        self.session.flush()
        return True

    # -- Essays with user_id --

    def create_essay_with_user(self, filename: str, num_pages: int, user_id: int) -> EssayRecord:
        essay = EssayRecord(filename=filename, num_pages=num_pages, user_id=user_id)
        self.session.add(essay)
        self.session.flush()
        return essay

    def update_essay_pipeline_output(
        self, essay_id: int, style_profile: dict | None = None, cis: dict | None = None
    ) -> None:
        """Persist full pipeline output (style_profile + cis) into essay row."""
        essay = self.session.get(EssayRecord, essay_id)
        if not essay:
            return
        if style_profile is not None:
            essay.style_profile_json = json.dumps(style_profile, ensure_ascii=False, default=str)
        if cis is not None:
            essay.cis_json = json.dumps(cis, ensure_ascii=False, default=str)
        self.session.flush()

    def get_user_essays(self, user_id: int) -> list[EssayRecord]:
        return list(
            self.session.query(EssayRecord)
            .filter(EssayRecord.user_id == user_id)
            .order_by(EssayRecord.uploaded_at.desc())
            .all()
        )

    def get_all_essays(self) -> list[EssayRecord]:
        return list(
            self.session.query(EssayRecord)
            .order_by(EssayRecord.uploaded_at.desc())
            .all()
        )

    # -- Citation Cache --

    def get_cache_entry(self, cache_key: str, source: str) -> CitationCache | None:
        return self.session.query(CitationCache).filter(
            CitationCache.cache_key == cache_key,
            CitationCache.source == source
        ).first()

    def save_cache_entry(
        self, cache_key: str, source: str, raw_response: str, matched_fields: str | None = None
    ) -> CitationCache:
        entry = CitationCache(
            cache_key=cache_key,
            source=source,
            raw_response=raw_response,
            matched_fields=matched_fields,
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def update_cache_hit(self, cache_key: str) -> None:
        entry = self.session.query(CitationCache).filter(CitationCache.cache_key == cache_key).first()
        if entry:
            entry.last_hit_at = datetime.now(timezone.utc)
            entry.hit_count = (entry.hit_count or 0) + 1
            self.session.flush()

    def get_cache_stats(self) -> dict:
        total = self.session.query(CitationCache).count()
        by_source = {}
        for src in ["crossref", "openalex", "semantic_scholar", "arxiv"]:
            count = self.session.query(CitationCache).filter(CitationCache.source == src).count()
            by_source[src] = count
        total_hits = sum(
            (e.hit_count or 0) for e in self.session.query(CitationCache).all()
        )
        return {
            "total": total,
            "by_source": by_source,
            "total_hits": total_hits,
            "avg_hit_count": total_hits / total if total > 0 else 0,
        }

    def clear_cache(self) -> int:
        count = self.session.query(CitationCache).delete()
        self.session.flush()
        return count