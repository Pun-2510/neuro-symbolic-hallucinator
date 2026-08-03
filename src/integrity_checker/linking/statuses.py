"""Citation mapping statuses — v1.2 §3.2.2.

Bảy trạng thái tách rời hoàn toàn khỏi ValidationLabel (source verification).
Lớp integrity ≠ lớp source. Một citation có thể vừa MATCHED (link OK)
vừa bị METADATA_ERROR (sai năm) — đây là 2 chiều phân tích khác nhau.

Reference:
    v1.2 §3.2.2 (Hai lớp nhãn và trạng thái)
    v1.2 §3.5 (Nhận diện kiểu trích dẫn và đối chiếu hai chiều)
    config.linking.statuses.enabled (in configs/config.example.yaml)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CitationMappingStatus(str, Enum):
    """7 trạng thái mapping in-text ↔ reference entry (v1.2 §3.2.2).

    BẮT BUỘC dùng đúng giá trị này (lowercase) để serialize/UI.
    """

    MATCHED = "matched"
    MISSING_REFERENCE = "missing_reference"
    UNCITED_REFERENCE = "uncited_reference"
    IN_TEXT_MISMATCH = "in_text_mismatch"
    DUPLICATE_REFERENCE = "duplicate_reference"
    AMBIGUOUS_MAPPING = "ambiguous_mapping"
    STYLE_INCONSISTENT = "style_inconsistent"

    @property
    def color(self) -> str:
        """Màu badge trên UI (hex). Cố ý khác bảng màu 4 ValidationLabel."""
        return {
            CitationMappingStatus.MATCHED: "#16a34a",                # xanh
            CitationMappingStatus.MISSING_REFERENCE: "#dc2626",        # đỏ
            CitationMappingStatus.UNCITED_REFERENCE: "#ea580c",       # cam
            CitationMappingStatus.IN_TEXT_MISMATCH: "#ca8a04",        # vàng
            CitationMappingStatus.DUPLICATE_REFERENCE: "#9333ea",     # tím
            CitationMappingStatus.AMBIGUOUS_MAPPING: "#6b7280",       # xám
            CitationMappingStatus.STYLE_INCONSISTENT: "#0891b2",      # cyan
        }[self]

    @property
    def is_integrity_issue(self) -> bool:
        """True nếu trạng thái này BIỂU THỊ vấn đề về tính nhất quán nội bộ.

        Dùng cho CIS weight penalty (config.cis.rubric_penalty).
        MATCHED và trạng thái trung tính (chưa phân loại) → False.
        """
        return self in {
            CitationMappingStatus.MISSING_REFERENCE,
            CitationMappingStatus.UNCITED_REFERENCE,
            CitationMappingStatus.IN_TEXT_MISMATCH,
            CitationMappingStatus.DUPLICATE_REFERENCE,
            CitationMappingStatus.AMBIGUOUS_MAPPING,
            CitationMappingStatus.STYLE_INCONSISTENT,
        }


@dataclass
class CitationLink:
    """Một quan hệ in-text ↔ reference entry.

    Một in-text occurrence gộp nhiều citation (e.g. (Smith, 2020; Doe, 2021))
    được tách thành nhiều CitationLink — mỗi link ứng với 1 reference entry.

    Attributes:
        occurrence_id: id ổn định cho in-text occurrence (vd: 'occ-0001').
        reference_id: id ổn định cho reference entry (vd: 'ref-0007').
            None nếu MISSING_REFERENCE.
        status: CitationMappingStatus.
        confidence: 0.0-1.0. Dùng cho rule ordering + CIS penalty.
        method: cách quyết định (vd: 'exact_author_year', 'numeric_index',
            'normalized_title_fuzzy', 'manual_review').
        evidence: dict bằng chứng giải thích (vd: {'author': 'Smith',
            'year': '2020', 'page': 5, 'context': '...'}).
        page: trang PDF nơi xuất hiện in-text (1-indexed).
        section: section name (vd: 'body', 'introduction').
    """

    occurrence_id: str
    reference_id: Optional[str]
    status: CitationMappingStatus
    confidence: float
    method: str = "unknown"
    evidence: dict = field(default_factory=dict)
    page: int = 0
    section: str = ""


@dataclass
class CitationOccurrence:
    """Wrapper cho in-text occurrence từ CitationExtractor.

    CitationExtractor hiện trả Citation với citation_type=IN_TEXT/NUMERIC.
    Wrapper này cung cấp thêm occurrence_id ổn định + parsed keys
    (author, year, numeric_index) để Linker so khớp.
    """

    occurrence_id: str
    raw_text: str
    page: int
    section: str = ""
    context: str = ""

    # Parsed keys (ít nhất 1 trong các trường này có dữ liệu)
    authors: list[str] = field(default_factory=list)       # last names
    year: Optional[str] = None
    year_suffix: Optional[str] = None                      # 'a', 'b' cho 2024a/2024b
    numeric_index: Optional[int] = None                    # cho IEEE-like [12]
    numeric_indices: list[int] = field(default_factory=list)  # cho [1,2,3] hoặc [1-5]
    doi: Optional[str] = None
    raw_style_hint: str = "unknown"                        # APA / IEEE / unknown


@dataclass
class ReferenceEntry:
    """Wrapper cho reference entry từ ReferenceListParser.

    Parser hiện trả Citation với citation_type=REFERENCE_LIST.
    Wrapper này cung cấp thêm:
    - reference_id ổn định
    - normalized title (để duplicate detection)
    - order_index (vị trí trong bibliography)
    - parsed fields chuẩn hoá (chữ thường, bỏ dấu câu)
    """

    reference_id: str
    raw_text: str
    order_index: int
    page: int = 0

    authors: list[str] = field(default_factory=list)
    year: Optional[str] = None
    year_suffix: Optional[str] = None
    title: Optional[str] = None
    title_normalized: Optional[str] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None


@dataclass
class StyleProfile:
    """Document-level citation style — v1.2 §3.5.

    Hiện Type=APA-like / IEEE-like / MIXED / UNKNOWN với confidence.
    Field thêm:
        apa_count: số marker author-year tìm được.
        numeric_count: số marker numeric tìm được.
    """

    style: str = "UNKNOWN"     # APA-like | IEEE-like | MIXED | UNKNOWN
    confidence: float = 0.0
    apa_count: int = 0
    numeric_count: int = 0
    evidence: dict = field(default_factory=dict)


@dataclass
class LinkingResult:
    """Đầu ra aggregate của CitationLinker.link().

    Attributes:
        links: list[CitationLink] — quan hệ in-text ↔ reference.
        uncited_reference_ids: list reference_id không có occurrence
            hợp lệ trong thân bài (sau loại trừ exclude_sections).
        duplicate_reference_ids: list reference_id bị DuplicateDetector
            đánh dấu (chuyển từ external call). Mỗi nhóm trùng → 1 id canonical,
            các id còn lại nằm trong groups.
        ambiguous_mapping_ids: list occurrence_id không map được chắc chắn.
    """

    links: list[CitationLink] = field(default_factory=list)
    uncited_reference_ids: list[str] = field(default_factory=list)
    duplicate_reference_ids: list[str] = field(default_factory=list)
    ambiguous_mapping_ids: list[str] = field(default_factory=list)

    # Thống kê — optional, dùng cho UI/Report
    counts_by_status: dict[str, int] = field(default_factory=dict)

    def has_integrity_issues(self) -> bool:
        """True nếu có bất kỳ trạng thái nào KHÔNG phải MATCHED/STYLE_INCONSISTENT."""
        return any(
            link.status
            not in (
                CitationMappingStatus.MATCHED,
                CitationMappingStatus.STYLE_INCONSISTENT,
            )
            for link in self.links
        )
