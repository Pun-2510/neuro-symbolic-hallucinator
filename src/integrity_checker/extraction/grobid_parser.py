"""GROBID adapter — parse TEI XML trả về từ GROBID service (v1.2 §3.4).

GROBID là Java service của Hugues Genthial, trích xuất metadata từ PDF:
    - Header: title, authors, abstract
    - Body sections
    - Citations (in-text + bibliography) với coordinates
    - References (full TEI XML)

Mục tiêu v1.2:
    - Wrapper quanh GROBID HTTP API (POST /api/processFulltextDocument,
      /api/processHeaderDocument).
    - Parser TEI XML → GrobidOutput (dataclass tối giản).
    - Cache theo file SHA256.
    - Graceful fallback: nếu GROBID không available → trả GrobidOutput rỗng,
      caller quyết định dùng heuristic hay fail.

References:
    v1.2 §3.4 (PDF → Document full-text extraction)
    v1.2 §5.2 (GROBID Docker setup)
    config.grobid.{enabled, url, timeout_seconds, cache_by_file_sha256}
    https://grobid.readthedocs.io/en/latest/Grobid-service/

Limitations (v1.2):
    - Chỉ parse TEI XML, không gọi HTTP. Caller cần wrap với requests/httpx.
    - TEI schema coverage: header, abstract, body sections, bibliography.
      Figure captions / tables: out-of-scope v1.2.
    - Citation coordinates (PDF bbox): lưu raw, chưa dùng.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from defusedxml.ElementTree import ParseError, fromstring, tostring

from integrity_checker.config import GrobidConfig

logger = logging.getLogger(__name__)


# TEI XML namespace
_TEI_NS = "http://www.tei-c.org/ns/1.0"
_TEI = "{" + _TEI_NS + "}"


@dataclass
class GrobidAuthor:
    """1 author từ TEI header.

    Attributes:
        full_name: "LeCun, Yann" (canonical).
        first_name, last_name, middle_name: parsed.
        email: optional.
        affiliation: optional.
    """

    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    email: Optional[str] = None
    affiliation: Optional[str] = None


@dataclass
class GrobidBibEntry:
    """1 entry từ <listBibl>/<biblStruct>.

    Attributes:
        id: TEI ID (vd '#b0').
        authors: list[GrobidAuthor].
        title: title.
        year: year (4 chars).
        venue: journal/venue (từ <title level="j">).
        doi: DOI.
        raw_xml: lưu xml string để debug / re-parse.
    """

    id: str
    authors: list[GrobidAuthor] = field(default_factory=list)
    title: Optional[str] = None
    year: Optional[str] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    raw_xml: str = ""


@dataclass
class GrobidCitation:
    """1 in-text citation (từ <body>).

    Attributes:
        raw_text: text nguyên gốc (vd "(Smith, 2020)").
        ref_id: TEI ID trỏ đến <biblStruct> (vd '#b0'). None nếu không match.
        page: page number nếu có.
    """

    raw_text: str
    ref_id: Optional[str] = None
    page: Optional[int] = None


@dataclass
class GrobidSection:
    """1 section trong body.

    Attributes:
        section_type: 'abstract' / 'body' / 'bibliography' / 'footnote' /
                      'appendix' / 'unknown'.
        text: text content.
        page_start: optional page number.
    """

    section_type: str
    text: str
    page_start: Optional[int] = None


@dataclass
class GrobidOutput:
    """Output đầy đủ từ GROBID."""

    header: dict = field(default_factory=dict)
    authors: list[GrobidAuthor] = field(default_factory=list)
    abstract: Optional[str] = None
    sections: list[GrobidSection] = field(default_factory=list)
    citations: list[GrobidCitation] = field(default_factory=list)
    bibliography: list[GrobidBibEntry] = field(default_factory=list)
    is_available: bool = True     # False nếu GROBID fail
    error_message: Optional[str] = None
    sha256: Optional[str] = None
    raw_tei_xml: Optional[str] = None  # cache để debug


# --- HTTP client (caller wrap requests/httpx) ---


def call_grobid_fulltext(
    pdf_path: str,
    config: GrobidConfig,
    http_post_fn=None,    # injectable cho testing
) -> str:
    """Gọi GROBID /api/processFulltextDocument trả về TEI XML string.

    Args:
        pdf_path: path to PDF file.
        config: GrobidConfig.
        http_post_fn: optional callable(url, files, data, timeout) -> Response
                      để inject trong tests. Mặc định dùng requests.

    Returns:
        TEI XML string. Rỗng nếu lỗi.
    """
    url = f"{config.url.rstrip('/')}/api/processFulltextDocument"
    timeout = config.timeout_seconds

    if http_post_fn is None:
        try:
            import requests
        except ImportError:
            logger.warning("requests not installed — GROBID disabled")
            return ""

        def _default_post(url, files, data, timeout):
            return requests.post(url, files=files, data=data, timeout=timeout)

        http_post_fn = _default_post

    try:
        with open(pdf_path, "rb") as f:
            files = {"input": (pdf_path, f, "application/pdf")}
            data = {
                "consolidateHeader": str(config.consolidate_header[0]).lower(),
                "consolidateCitations": "0",
                "includeRawCitations": "1",
                "teiCoordinates": "figure,head,biblStruct,snote,formula",
            }
            response = http_post_fn(url, files=files, data=data, timeout=timeout)
        if response.status_code != 200:
            logger.warning("GROBID returned %d", response.status_code)
            return ""
        return response.text
    except Exception as exc:
        logger.warning("GROBID call failed: %s", exc)
        return ""


def compute_sha256(pdf_path: str) -> str:
    """SHA256 hash của file PDF — dùng cho cache."""
    h = hashlib.sha256()
    try:
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except OSError as exc:
        logger.warning("Cannot hash %s: %s", pdf_path, exc)
    return h.hexdigest()


# --- TEI XML parser ---


def parse_tei(tei_xml: str) -> GrobidOutput:
    """Parse TEI XML string → GrobidOutput.

    Robust với malformed XML: nếu parse fail, trả GrobidOutput rỗng
    với error_message.
    """
    if not tei_xml:
        return GrobidOutput(is_available=False, error_message="empty TEI XML")

    try:
        root = fromstring(tei_xml)
    except ParseError as exc:
        return GrobidOutput(
            is_available=False, error_message=f"parse error: {type(exc).__name__}"
        )
    except Exception as exc:  # noqa: BLE001 — defusedxml raises EntitiesForbidden etc.
        # Chỉ log exception type, KHÔNG leak system_id / URL attack.
        logger.warning("TEI parse error: %s", type(exc).__name__)
        return GrobidOutput(
            is_available=False, error_message=f"parse error: {type(exc).__name__}"
        )

    out = GrobidOutput(raw_tei_xml=tei_xml, sha256=compute_sha256_hash(tei_xml))

    # Header → title + abstract + authors
    header = root.find(f".//{_TEI}teiHeader")
    if header is not None:
        out.header = _extract_header(header)
        out.authors = _extract_authors(header)
        out.abstract = _extract_abstract(header)

    # Body sections
    out.sections = _extract_sections(root)

    # In-text citations + bibliography
    out.citations = _extract_citations(root)
    out.bibliography = _extract_bibliography(root)

    return out


def compute_sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_header(header: ET.Element) -> dict:
    """Trích title + DOI + journal từ teiHeader/fileDesc."""
    result: dict = {}
    title_el = header.find(f".//{_TEI}title[@level='a']") or header.find(f".//{_TEI}title")
    if title_el is not None:
        result["title"] = "".join(title_el.itertext()).strip()

    doi_el = header.find(f".//{_TEI}idno[@type='DOI']")
    if doi_el is not None and doi_el.text:
        result["doi"] = doi_el.text.strip()

    journal_el = header.find(f".//{_TEI}title[@level='j']")
    if journal_el is not None:
        result["journal"] = "".join(journal_el.itertext()).strip()

    return result


def _extract_authors(header: ET.Element) -> list[GrobidAuthor]:
    """Trích authors từ <teiHeader>/<fileDesc>/<sourceDesc>/<biblStruct>/.../<author>."""
    authors: list[GrobidAuthor] = []
    for author_el in header.findall(f".//{_TEI}author"):
        pers = author_el.find(f"{_TEI}persName")
        if pers is None:
            continue

        surname = pers.find(f"{_TEI}surname")
        forename = pers.find(f"{_TEI}forename")
        email_el = author_el.find(f"{_TEI}email")
        affil_el = author_el.find(f"{_TEI}affiliation")

        surname_t = surname.text.strip() if surname is not None and surname.text else ""
        forename_t = forename.text.strip() if forename is not None and forename.text else ""

        full_name = f"{surname_t}, {forename_t}".strip(", ")
        authors.append(
            GrobidAuthor(
                full_name=full_name,
                first_name=forename_t or None,
                last_name=surname_t or None,
                email=email_el.text.strip() if email_el is not None and email_el.text else None,
                affiliation="".join(affil_el.itertext()).strip() if affil_el is not None else None,
            )
        )
    return authors


def _extract_abstract(header: ET.Element) -> Optional[str]:
    """Trích abstract từ <profileDesc>/<abstract>."""
    abstract_el = header.find(f".//{_TEI}abstract")
    if abstract_el is None:
        return None
    # Abstract có thể chứa nhiều <p> (paragraphs)
    parts = [
        "".join(p.itertext()).strip()
        for p in abstract_el.findall(f"{_TEI}p")
    ]
    if not parts:
        # Fallback: all text
        text = "".join(abstract_el.itertext()).strip()
        return text or None
    return "\n\n".join(parts)


def _extract_sections(root: ET.Element) -> list[GrobidSection]:
    """Trích body sections (consolidated <div> blocks)."""
    sections: list[GrobidSection] = []
    body = root.find(f".//{_TEI}body")
    if body is None:
        return sections

    # Top-level <div> of body
    for div in body.findall(f"{_TEI}div"):
        section_type = _detect_section_type(div)
        # Gộp text từ các <p>
        text = "\n".join(
            "".join(p.itertext()).strip()
            for p in div.findall(f"{_TEI}p")
        ).strip()
        if text:
            sections.append(GrobidSection(section_type=section_type, text=text))
    return sections


def _detect_section_type(div: ET.Element) -> str:
    """Heuristic: đoán section type từ <head> text."""
    head_el = div.find(f"{_TEI}head")
    if head_el is None:
        return "body"
    head_text = "".join(head_el.itertext()).strip().lower()
    if "abstract" in head_text:
        return "abstract"
    if any(kw in head_text for kw in ["appendix", "phụ lục"]):
        return "appendix"
    if any(kw in head_text for kw in ["footnote", "chú thích"]):
        return "footnote"
    return "body"


def _extract_citations(root: ET.Element) -> list[GrobidCitation]:
    """Trích in-text citations từ <body>/<p>/<ref type='bibr'>."""
    citations: list[GrobidCitation] = []
    for ref in root.findall(f".//{_TEI}ref[@type='bibr']"):
        raw_text = "".join(ref.itertext()).strip()
        target = ref.get("target", "")
        if target.startswith("#"):
            ref_id = target[1:]
        else:
            ref_id = None
        citations.append(GrobidCitation(raw_text=raw_text, ref_id=ref_id))
    return citations


def _extract_bibliography(root: ET.Element) -> list[GrobidBibEntry]:
    """Trích <listBibl>/<biblStruct>. Skip entry ở <teiHeader> (chỉ là metadata).

    GROBID trả biblStruct ở 2 nơi:
        - <teiHeader>/<fileDesc>/<sourceDesc> → metadata bài báo
        - <back>/<listBibl> → danh sách references

    Mình chỉ lấy các entry trong <listBibl>.
    """
    entries: list[GrobidBibEntry] = []
    for bibl in root.findall(f".//{_TEI}biblStruct"):
        entry_id = (
            bibl.get("{http://www.w3.org/XML/1998/namespace}id")
            or bibl.get("id")
            or ""
        )
        # Skip entry không có id → likely là header metadata
        if not entry_id:
            continue

        # Authors
        authors: list[GrobidAuthor] = []
        for author_el in bibl.findall(f".//{_TEI}author"):
            pers = author_el.find(f"{_TEI}persName")
            if pers is None:
                continue
            surname = pers.find(f"{_TEI}surname")
            forename = pers.find(f"{_TEI}forename")
            sn = surname.text.strip() if surname is not None and surname.text else ""
            fn = forename.text.strip() if forename is not None and forename.text else ""
            authors.append(
                GrobidAuthor(full_name=f"{sn}, {fn}".strip(", "),
                             first_name=fn or None, last_name=sn or None)
            )

        # Title (article-level) — dùng .// để tìm trong <analytic>
        title_el = (
            bibl.find(f".//{_TEI}title[@level='a']")
            or bibl.find(f".//{_TEI}title")
        )
        title = "".join(title_el.itertext()).strip() if title_el is not None else None

        # Year
        year_el = bibl.find(f".//{_TEI}date[@type='published']") or bibl.find(f".//{_TEI}date")
        year = year_el.get("when", "")[:4] if year_el is not None and year_el.get("when") else None

        # Venue (journal-level title) — dùng .// để tìm trong <monogr>
        venue_el = bibl.find(f".//{_TEI}title[@level='j']")
        venue = "".join(venue_el.itertext()).strip() if venue_el is not None else None

        # DOI
        doi_el = bibl.find(f".//{_TEI}idno[@type='DOI']")
        doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None

        # Raw XML for debug
        raw = tostring(bibl, encoding="unicode")

        entries.append(GrobidBibEntry(
            id=entry_id,
            authors=authors,
            title=title,
            year=year,
            venue=venue,
            doi=doi,
            raw_xml=raw,
        ))
    return entries


# --- Cache helpers ---


def cache_key(pdf_path: str) -> str:
    """Trả SHA256 của PDF để cache TEI XML theo file."""
    return compute_sha256(pdf_path)


def serialize_output(out: GrobidOutput) -> str:
    """Serialize GrobidOutput → JSON string để cache disk."""
    # Convert dataclasses nested → dicts
    def _to_dict(obj):
        if hasattr(obj, "__dataclass_fields__"):
            return {k: _to_dict(v) for k, v in obj.__dict__.items()}
        if isinstance(obj, list):
            return [_to_dict(v) for v in obj]
        return obj

    return json.dumps(_to_dict(out), ensure_ascii=False, indent=2)


def deserialize_output(text: str) -> GrobidOutput:
    """Deserialize JSON → GrobidOutput."""
    if not text:
        return GrobidOutput(is_available=False)
    data = json.loads(text)
    return GrobidOutput(
        header=data.get("header", {}),
        authors=[
            GrobidAuthor(**{k: v for k, v in a.items() if k in GrobidAuthor.__dataclass_fields__})
            for a in data.get("authors", [])
        ],
        abstract=data.get("abstract"),
        sections=[
            GrobidSection(**{k: v for k, v in s.items() if k in GrobidSection.__dataclass_fields__})
            for s in data.get("sections", [])
        ],
        citations=[
            GrobidCitation(**{k: v for k, v in c.items() if k in GrobidCitation.__dataclass_fields__})
            for c in data.get("citations", [])
        ],
        bibliography=[
            GrobidBibEntry(**{k: v for k, v in e.items() if k in GrobidBibEntry.__dataclass_fields__})
            for e in data.get("bibliography", [])
        ],
        is_available=data.get("is_available", True),
        error_message=data.get("error_message"),
        sha256=data.get("sha256"),
    )


# --- Sample TEI (cho test + fallback khi không có GROBID) ---


SAMPLE_TEI = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title level="a">Deep Learning</title>
      </titleStmt>
      <sourceDesc>
        <biblStruct>
          <analytic>
            <author>
              <persName>
                <surname>LeCun</surname>
                <forename>Yann</forename>
              </persName>
            </author>
            <author>
              <persName>
                <surname>Bengio</surname>
                <forename>Yoshua</forename>
              </persName>
            </author>
            <idno type="DOI">10.1038/nature14539</idno>
          </analytic>
        </biblStruct>
      </sourceDesc>
    </fileDesc>
    <profileDesc>
      <abstract>
        <p>Deep learning allows computational models...</p>
      </abstract>
    </profileDesc>
  </teiHeader>
  <text>
    <body>
      <div>
        <head>1. Introduction</head>
        <p>Deep learning <ref type="bibr" target="#b0">(LeCun et al., 2015)</ref> is powerful.</p>
      </div>
      <div>
        <head>References</head>
        <listBibl>
          <biblStruct xml:id="b0">
            <analytic>
              <author><persName><surname>LeCun</surname><forename>Yann</forename></persName></author>
              <author><persName><surname>Bengio</surname><forename>Yoshua</forename></persName></author>
              <title level="a">Deep learning</title>
              <idno type="DOI">10.1038/nature14539</idno>
            </analytic>
            <monogr>
              <title level="j">Nature</title>
              <imprint>
                <date type="published" when="2015">2015</date>
              </imprint>
            </monogr>
          </biblStruct>
        </listBibl>
      </div>
    </body>
  </text>
</TEI>
"""