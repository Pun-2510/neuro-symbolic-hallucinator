"""Cấu hình ứng dụng — load từ YAML + .env, validate qua Pydantic Settings.

Module này là single source of truth cho mọi threshold / weight / path.
Mọi module khác chỉ import `get_settings()` và dùng — KHÔNG đọc file trực tiếp.

Đồng bộ với đề cương v1.2 (chốt với GVHD 2026-08-03).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------- Sub-configs ----------


class AppConfig(BaseModel):
    name: str = "Essay Integrity Checker"
    version: str = "0.2.0"   # v1.2 spec
    env: str = "development"
    debug: bool = True
    log_level: str = "INFO"


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///./data/app.db"
    echo: bool = False


class PathsConfig(BaseModel):
    data_dir: Path = Path("./data")
    essays_dir: Path = Path("./data/essays")
    cache_dir: Path = Path("./data/cache")
    ground_truth: Path = Path("./data/ground_truth/gold_dataset.json")
    grobid_output_dir: Path = Path("./data/cache/grobid")   # MỚI v1.2

    @field_validator("*", mode="before")
    @classmethod
    def _coerce_path(cls, v: Any) -> Any:
        return Path(v) if isinstance(v, str) else v


# --- Extraction (MỚI v1.2: GROBID section) ---


class GrobidConfig(BaseModel):
    """GROBID service config — MUST-HAVE trong MVP v1.2."""

    enabled: bool = True
    url: str = "http://localhost:8070"
    timeout_seconds: int = 30
    cache_by_file_sha256: bool = True
    consolidate_header: list[str] = Field(
        default_factory=lambda: [
            "abstract",
            "body",
            "bibliography",
            "footnote",
            "appendix",
        ]
    )


class ExtractionConfig(BaseModel):
    # v1.1: mupdf | pdfplumber | hybrid
    # v1.2: thêm grobid_hybrid — GROBID TEI XML + PyMuPDF bounding box
    parser: str = "grobid_hybrid"
    fallback_to_ocr: bool = False
    min_text_length: int = 50
    grobid: GrobidConfig = Field(default_factory=GrobidConfig)


# --- Citation style detection (MỚI v1.2) ---


class StyleFeaturesConfig(BaseModel):
    """Regex features cho style detection."""

    apa_author_year_pattern: str = (
        r"\([A-Z][^()]{0,80},\s*(19|20)\d{2}[a-z]?\)"
    )
    ieee_numeric_pattern: str = r"\[\d+(?:\s*[-,]\s*\d+)*\]"


class StyleOutputConfig(BaseModel):
    classes: list[str] = Field(
        default_factory=lambda: ["APA-like", "IEEE-like", "MIXED", "UNKNOWN"]
    )


class StyleDetectionConfig(BaseModel):
    """Document-level citation style profile (v1.2 §3.5)."""

    min_occurrences_to_classify: int = 5
    mixed_threshold: float = 0.3
    unknown_threshold: float = 0.15
    features: StyleFeaturesConfig = Field(default_factory=StyleFeaturesConfig)
    output: StyleOutputConfig = Field(default_factory=StyleOutputConfig)


# --- Bidirectional linking (MỚI v1.2) ---


class DuplicateDetectionConfig(BaseModel):
    """Duplicate detection trong reference entries."""

    exact_identifier_match: bool = True
    title_year_author_similarity: float = 0.92


class LinkingStatusesConfig(BaseModel):
    enabled: list[str] = Field(
        default_factory=lambda: [
            "MATCHED",
            "MISSING_REFERENCE",
            "UNCITED_REFERENCE",
            "IN_TEXT_MISMATCH",
            "DUPLICATE_REFERENCE",
            "AMBIGUOUS_MAPPING",
            "STYLE_INCONSISTENT",
        ]
    )


class SameAuthorYearResolutionConfig(BaseModel):
    use_title_metadata: bool = True
    use_first_author: bool = True


class LinkingConfig(BaseModel):
    """Bidirectional citation linking (v1.2 §3.5)."""

    exclude_sections: list[str] = Field(
        default_factory=lambda: [
            "references",
            "bibliography",
            "tài liệu tham khảo",
            "appendix",
            "phụ lục",
        ]
    )
    duplicate_detection: DuplicateDetectionConfig = Field(
        default_factory=DuplicateDetectionConfig
    )
    statuses: LinkingStatusesConfig = Field(default_factory=LinkingStatusesConfig)
    same_author_year_resolution: SameAuthorYearResolutionConfig = Field(
        default_factory=SameAuthorYearResolutionConfig
    )


# --- Retrieval (MỚI v1.2: retry config) ---


class SourceToggleConfig(BaseModel):
    crossref: bool = True
    openalex: bool = True
    semantic_scholar: bool = True
    arxiv: bool = True


class RateLimitsConfig(BaseModel):
    crossref_per_sec: float = 50.0
    openalex_per_sec: float = 10.0
    semantic_scholar_per_sec: float = 1.0
    arxiv_per_sec: float = 3.0


class CacheConfig(BaseModel):
    enabled: bool = True
    ttl_seconds: int = 86400
    include_source_in_key: bool = True   # MỚI v1.2 — tránh trộn nhầm giữa các nguồn


class RetryBackoffConfig(BaseModel):
    initial_seconds: float = 1.0
    max_seconds: float = 10.0
    multiplier: float = 2.0


class RetryConfig(BaseModel):
    """Tenacity retry + exponential backoff — MỚI v1.2."""

    enabled: bool = True
    max_attempts: int = 3
    backoff: RetryBackoffConfig = Field(default_factory=RetryBackoffConfig)


class RetrievalConfig(BaseModel):
    sources: SourceToggleConfig = Field(default_factory=SourceToggleConfig)
    per_source_top_k: int = 5
    parallel: bool = True
    cache: CacheConfig = Field(default_factory=CacheConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)   # MỚI v1.2
    rate_limits: RateLimitsConfig = Field(default_factory=RateLimitsConfig)
    contact_email: str = "student@tdtu.edu.vn"


# --- Matching (giữ nguyên v1.1, sẽ tinh chỉnh ở tuần 10–11) ---


class FuzzyConfig(BaseModel):
    token_set_ratio_threshold: float = 0.85
    partial_ratio_threshold: float = 0.80


class MatchingConfig(BaseModel):
    title_sim_verified: float = 0.9
    title_sim_metadata_error: float = 0.6
    author_jaccard_verified: float = 0.5
    year_tolerance: int = 1
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    fuzzy: FuzzyConfig = Field(default_factory=FuzzyConfig)


# --- Logic (MỚI v1.2: new_rules) ---


class NewRulesConfig(BaseModel):
    """Rule IDs mới v1.2 — bổ sung ở tuần 12–13."""

    domain_exception_broken_link: bool = True
    ambiguous_mapping: bool = True
    style_inconsistent_override: bool = False   # không tự sửa; hỏi giảng viên


class LogicConfig(BaseModel):
    abstention_low: float = 0.4
    abstention_high: float = 0.6
    require_consensus_for_verified: int = 2
    require_consensus_for_metadata_error: int = 1
    new_rules: NewRulesConfig = Field(default_factory=NewRulesConfig)


# --- CIS (v1.2 §3.9: weights 35/25/25/10/5) ---


class CISWeightsConfig(BaseModel):
    """Trọng số CIS — v1.2 §3.9.

    Tổng PHẢI = 1.0 (±0.01). Validate qua root model_validator.
    Hai component in_text_bib_consistency + format_consistency
    KHÔNG được là stub — phải tính từ linker + style detector.
    """

    verified_ratio: float = 0.35
    metadata_accuracy: float = 0.25
    in_text_bib_consistency: float = 0.25
    format_consistency: float = 0.10
    identifier_validity: float = 0.05


class RubricPenaltyConfig(BaseModel):
    """Trọng số phạt cho in_text_bib_consistency — v1.2 §3.9."""

    MISSING_REFERENCE: float = 0.20
    UNCITED_REFERENCE: float = 0.10
    IN_TEXT_MISMATCH: float = 0.15
    DUPLICATE_REFERENCE: float = 0.10
    AMBIGUOUS_MAPPING: float = 0.05
    STYLE_INCONSISTENT: float = 0.02


class CISConfig(BaseModel):
    weights: CISWeightsConfig = Field(default_factory=CISWeightsConfig)
    rubric_penalty: RubricPenaltyConfig = Field(default_factory=RubricPenaltyConfig)


# --- Disclaimer & out-of-scope (v1.2) ---


class DisclaimerConfig(BaseModel):
    short: str = "Decision-support only — not a final grade."
    long: str = (
        "Hệ thống này chỉ hỗ trợ giảng viên rà soát tính toàn vẹn trích dẫn "
        "trong tiểu luận. Hai lớp kết quả (đối chiếu in-text ↔ reference entry "
        "và độ tin cậy nguồn) đều là gợi ý dựa trên bằng chứng từ các cơ sở dữ "
        "liệu học thuật công khai (Crossref, OpenAlex, Semantic Scholar, arXiv) "
        "và quy luật Neuro-Symbolic có thể giải thích. Kết luận "
        "`SUSPECTED_HALLUCINATION` chỉ là suspect — không đồng nghĩa nguồn bị "
        "bịa. Giảng viên là người ra quyết định cuối cùng. Hệ thống KHÔNG tự động "
        "kết luận gian lận học thuật, KHÔNG kiểm chứng claim-level, và KHÔNG xem "
        "việc trích cùng một nguồn nhiều lần là 'dư thừa'."
    )


# Default out-of-scope items (v1.2) — được override bởi YAML nếu có
_DEFAULT_OUT_OF_SCOPE: list[str] = [
    "Chấm điểm content / organization / language / vocabulary / mechanics",
    "AES rubric (QWK, holistic scoring)",
    "Phát hiện đạo văn",
    "Phát hiện toàn bộ văn bản do AI tạo",
    "Tự động kết luận gian lận học thuật",
    "Claim-level verification toàn diện",
    "Phán xét việc trích cùng một nguồn nhiều lần là dư thừa",
    "OCR scanned PDF (mở rộng)",
    "Sách / ISBN (mở rộng)",
    "Highlight trực tiếp lên PDF (mở rộng)",
    "Google Scholar / SerpAPI (bị loại)",
]


# ---------- Root ----------


class Settings(BaseSettings):
    """Toàn bộ config của hệ thống."""

    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    style_detection: StyleDetectionConfig = Field(default_factory=StyleDetectionConfig)
    linking: LinkingConfig = Field(default_factory=LinkingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    matching: MatchingConfig = Field(default_factory=MatchingConfig)
    logic: LogicConfig = Field(default_factory=LogicConfig)
    cis: CISConfig = Field(default_factory=CISConfig)
    disclaimer: DisclaimerConfig = Field(default_factory=DisclaimerConfig)
    out_of_scope: list[str] = Field(default_factory=lambda: list(_DEFAULT_OUT_OF_SCOPE))

    # Env override
    contact_email: str = "student@tdtu.edu.vn"
    s2_api_key: str = ""
    config_file: Path | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _validate_weights_sum(self) -> "Settings":
        """CIS weights PHẢI tổng = 1.0 (±0.01). Raise nếu sai."""
        w = self.cis.weights
        s = (
            w.verified_ratio
            + w.metadata_accuracy
            + w.in_text_bib_consistency
            + w.format_consistency
            + w.identifier_validity
        )
        if abs(s - 1.0) >= 0.01:
            raise ValueError(
                f"CIS weights must sum to 1.0 (±0.01), got {s:.4f}. "
                f"Current: {w.model_dump()}"
            )
        return self

    def weights_sum_ok(self) -> bool:
        """Kiểm tra tổng CIS weights = 1.0 (±0.01)."""
        w = self.cis.weights
        s = (
            w.verified_ratio
            + w.metadata_accuracy
            + w.in_text_bib_consistency
            + w.format_consistency
            + w.identifier_validity
        )
        return abs(s - 1.0) < 0.01


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Lazy singleton — load YAML nếu có, merge với env."""
    config_file = Path("configs/config.yaml")
    if not config_file.exists():
        config_file = Path("configs/config.example.yaml")

    yaml_data: dict[str, Any] = {}
    if config_file.exists():
        with config_file.open("r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

    # YAML `out_of_scope` là list[str] trực tiếp — không cần normalize
    return Settings(config_file=config_file, **yaml_data)
