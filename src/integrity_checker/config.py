"""Cấu hình ứng dụng — load từ YAML + .env, validate qua Pydantic Settings.

Module này là single source of truth cho mọi threshold / weight / path.
Mọi module khác chỉ import `get_settings()` và dùng — KHÔNG đọc file trực tiếp.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------- Sub-configs ----------


class AppConfig(BaseModel):
    name: str = "Essay Integrity Checker"
    version: str = "0.1.0"
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

    @field_validator("*", mode="before")
    @classmethod
    def _coerce_path(cls, v: Any) -> Any:
        return Path(v) if isinstance(v, str) else v


class ExtractionConfig(BaseModel):
    parser: str = "hybrid"  # mupdf | pdfplumber | hybrid
    fallback_to_ocr: bool = False
    min_text_length: int = 50


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


class RetrievalConfig(BaseModel):
    sources: SourceToggleConfig = Field(default_factory=SourceToggleConfig)
    per_source_top_k: int = 5
    parallel: bool = True
    cache: CacheConfig = Field(default_factory=CacheConfig)
    rate_limits: RateLimitsConfig = Field(default_factory=RateLimitsConfig)
    contact_email: str = "student@tdtu.edu.vn"


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


class LogicConfig(BaseModel):
    abstention_low: float = 0.4
    abstention_high: float = 0.6
    require_consensus_for_verified: int = 2
    require_consensus_for_metadata_error: int = 1


class CISWeightsConfig(BaseModel):
    verified_ratio: float = 0.45
    metadata_accuracy: float = 0.25
    in_text_bib_consistency: float = 0.15
    format_consistency: float = 0.10
    identifier_validity: float = 0.05

    @field_validator("*")
    @classmethod
    def _check_sum(cls, v: float) -> float:
        # Validate tổng = 1.0 sẽ làm ở root config
        return v


class CISConfig(BaseModel):
    weights: CISWeightsConfig = Field(default_factory=CISWeightsConfig)


class DisclaimerConfig(BaseModel):
    short: str = "Decision-support only — not a final grade."
    long: str = (
        "Hệ thống này chỉ hỗ trợ giảng viên rà soát trích dẫn. Kết quả là gợi ý "
        "dựa trên bằng chứng từ các cơ sở dữ liệu học thuật công khai. "
        "Giảng viên là người ra quyết định cuối cùng. "
        "Hệ thống KHÔNG tự động kết luận gian lận học thuật."
    )


class OutOfScopeConfig(BaseModel):
    """Danh sách các capability NGOÀI phạm vi — để tránh scope creep."""

    items: list[str] = Field(default_factory=lambda: [
        "Chấm điểm content / organization / language / vocabulary / mechanics",
        "AES rubric (QWK, holistic scoring)",
        "Phát hiện đạo văn",
        "Phát hiện toàn bộ văn bản do AI tạo",
        "Tự động kết luận gian lận học thuật",
        "Claim-level verification toàn diện",
        "OCR scanned PDF (mở rộng)",
        "Sách / ISBN (mở rộng)",
        "Google Scholar / SerpAPI (bị loại)",
        "GROBID (mở rộng, đã có adapter slot)",
    ])


# ---------- Root ----------


class Settings(BaseSettings):
    """Toàn bộ config của hệ thống."""

    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    matching: MatchingConfig = Field(default_factory=MatchingConfig)
    logic: LogicConfig = Field(default_factory=LogicConfig)
    cis: CISConfig = Field(default_factory=CISConfig)
    disclaimer: DisclaimerConfig = Field(default_factory=DisclaimerConfig)
    out_of_scope: list[str] = Field(
        default_factory=lambda: [
            "Chấm điểm content / organization / language / vocabulary / mechanics",
            "AES rubric (QWK, holistic scoring)",
            "Phát hiện đạo văn",
            "Phát hiện toàn bộ văn bản do AI tạo",
            "Tự động kết luận gian lận học thuật",
            "Claim-level verification toàn diện",
            "OCR scanned PDF (mở rộng)",
            "Sách / ISBN (mở rộng)",
            "Google Scholar / SerpAPI (bị loại)",
            "GROBID (mở rộng, đã có adapter slot)",
        ]
    )

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

    # Normalize out_of_scope: YAML có thể là list[str] trực tiếp
    if "out_of_scope" in yaml_data and isinstance(yaml_data["out_of_scope"], list):
        yaml_data["out_of_scope"] = yaml_data["out_of_scope"]

    return Settings(config_file=config_file, **yaml_data)