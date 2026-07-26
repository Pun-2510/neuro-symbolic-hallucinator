"""Pydantic schemas cho API request/response."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CitationSchema(BaseModel):
    """Citation sau khi extract — trả về cho client."""

    id: Optional[int] = None
    raw_text: str
    citation_type: str
    style: str
    authors: list[str] = Field(default_factory=list)
    year: Optional[str] = None
    title: Optional[str] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    page_num: int = 0
    confidence: float = 0.0


class VerdictSchema(BaseModel):
    """Verdict cho 1 citation — đầu ra chính của API."""

    citation_id: Optional[int] = None
    citation_raw: str
    label: str                                  # ValidationLabel value
    confidence: float
    reasoning: str
    triggered_rules: list[str] = Field(default_factory=list)
    mismatched_fields: list[str] = Field(default_factory=list)
    matched_sources: list[dict] = Field(default_factory=list)
    is_overridden: bool = False


class CISSchema(BaseModel):
    """Citation Integrity Score — KHÔNG phải điểm tiểu luận."""

    score: float                               # 0–100
    components: dict[str, float]
    weights_used: dict[str, float]
    num_citations: int
    num_unresolved: int
    disclaimer: str


class AnalysisReportSchema(BaseModel):
    """Toàn bộ report cho 1 essay."""

    essay_id: int
    filename: str
    num_pages: int
    num_citations: int
    verdicts: list[VerdictSchema]
    cis: CISSchema
    disclaimer: str


class EssayUploadResponse(BaseModel):
    """Response khi upload PDF essay."""

    essay_id: int
    filename: str
    num_pages: int
    num_citations: int
    citations: list[CitationSchema]
    summary: dict


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    disclaimer: str