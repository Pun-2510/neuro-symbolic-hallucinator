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
from pathlib import Path
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
        url: URL nếu có.
        raw_reference: raw text từ <note type="raw_reference">.
        raw_xml: lưu xml string để debug / re-parse.
    """

    id: str
    authors: list[GrobidAuthor] = field(default_factory=list)
    title: Optional[str] = None
    year: Optional[str] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    raw_reference: str = ""
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
            filename = Path(pdf_path).name if pdf_path else "document.pdf"
            files = {"input": (filename, f, "application/pdf")}
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
    title_el = header.find(f".//{_TEI}title[@level='a']")
    if title_el is None:
        title_el = header.find(f".//{_TEI}title")
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


_CONTINUATION_START_RE = re.compile(
    r"^(?:"
    r"EBSCOhost|JSTOR|ProQuest|PubMed|ScienceDirect|ResearchGate|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z.]*\s+(?:19|20)\d{2}\b|"
    r"(?:vol\.|no\.|pp?\.)\s*\d+|"
    r"https?://doi\.org/|doi:\s*10\."
    r")",
    re.IGNORECASE,
)

_BOOK_PUBLISHER_SUFFIX_RE = re.compile(
    r"(?:"
    r",\s*edited\s+by\s+[^,]+,\s*(?P<ed_pub>[A-Z][A-Za-z&\s]+)$|"
    r"\.\s+(?P<pub>"
    r"Zondervan(?:\s+Academic)?|Baker\s+Academic|Baker\s+Publishing(?:\s+Group)?|"
    r"Crossway|Brazos\s+Press|HarperOne(?:\s*,\s*an\s+imprint\s+of\s+Harper(?:\s*Collins)?)?|"
    r"Harper\s*Collins(?:\s+Publishers)?|InterVarsity\s+Press|IVP(?:\s+Academic|\s+Books)?|"
    r"Waterbrook(?:\s+Press)?|Convergent(?:\s+Books)?|B&H(?:\s+Publishing(?:\s+Group)?|\s+Academic)?|"
    r"Holman\s+Bible\s+Publishers|Farrar,\s*Straus\s+and\s+Giroux|Penguin(?:\s+Random\s+House)?|"
    r"Cambridge\s+University\s+Press|Oxford\s+University\s+Press|Routledge|Sage|Bloomsbury|"
    r"Eerdmans|Westminster\s+John\s+Knox(?:\s+Press)?|Thomas\s+Nelson|Moody\s+Publishers|"
    r"Project\s+Gutenberg"
    r")(?:\s*,\s*an\s+imprint\s+of\s+[^.]+)?$"
    r")",
    re.IGNORECASE,
)


def _normalize_raw_ref_text(raw_ref_text: str) -> str:
    """Repair line-wrapped URLs and percent-encoded fragments in raw reference text."""
    if not raw_ref_text:
        return ""
    text = re.sub(r"\s+", " ", raw_ref_text).strip()
    # Join broken percent-encoding across line wraps: "% 20" or "%F0... %9F..."
    text = re.sub(r"%\s+([0-9A-Fa-f]{2})", r"%\1", text)
    text = re.sub(r"(%[0-9A-Fa-f]{2}[0-9A-Za-z_%~:-]*)\s+(%[0-9A-Fa-f]{2})", r"\1\2", text)
    # Join domain broken across line wrap right after dot: "https://doi. org/..." -> "https://doi.org/..."
    text = re.sub(
        r"((?:https?://|www\.)[a-z0-9-]+)\.\s+((?:org|com|edu|gov|net|io|int)/)",
        r"\1.\2",
        text,
        flags=re.IGNORECASE,
    )
    # Join URL paths broken after '/' or '-' before a lowercase slug/path
    text = re.sub(
        r"((?:https?://|www\.)[^\s]+[/\-])\s+([a-z0-9_~%#][^\s]*)",
        r"\1\2",
        text,
    )
    return text


def _extract_url_and_doi_from_raw(
    raw_ref_text: str, bibl=None
) -> tuple[Optional[str], Optional[str]]:
    """Extract clean URL and DOI from TEI element or raw_reference text."""
    doi: Optional[str] = None
    url: Optional[str] = None

    if bibl is not None:
        doi_el = bibl.find(f".//{_TEI}idno[@type='DOI']")
        if doi_el is not None and doi_el.text:
            doi = doi_el.text.strip().rstrip(".,;")
        for ptr_el in bibl.findall(f".//{_TEI}ptr"):
            target = (ptr_el.get("target") or "").strip()
            if target and not target.startswith("#"):
                if "doi.org/" in target.lower():
                    m_doi = re.search(r"10\.\d{4,9}/[^\s\"<>]+", target)
                    if m_doi and not doi:
                        doi = m_doi.group(0).rstrip(".,;")
                else:
                    url = target.rstrip(".,;")

    if raw_ref_text:
        if not doi:
            m_doi = re.search(r"\b(10\.\d{4,9}/[^\s\"<>]+)", raw_ref_text)
            if m_doi:
                doi = m_doi.group(1).rstrip(".,;)")

        if not url:
            # Explicit http(s):// or www. URL
            for m_url in re.finditer(r"(?:https?://|www\.)[^\s\"<>]+", raw_ref_text):
                cand = m_url.group(0).rstrip(".,;)")
                if "doi.org/" in cand.lower():
                    continue
                if cand.lower().startswith("www."):
                    cand = "https://" + cand
                url = cand
                break

        if not url:
            # Bare domain with path (common in MLA 9th ed.: e.g. fightthenewdrug.org/...)
            m_bare = re.search(
                r"\b((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
                r"(?:com|org|edu|gov|net|io|co\.uk|ac\.uk)/[^\s\"<>]+)",
                raw_ref_text,
                re.IGNORECASE,
            )
            if m_bare:
                cand = m_bare.group(1).rstrip(".,;)")
                if "doi.org/" not in cand.lower():
                    url = "https://" + cand

    if url:
        url = re.sub(
            r"[\(\[](?:ac-?\s*cessed|re-?\s*trieved)\b.*$",
            "",
            url,
            flags=re.IGNORECASE,
        )
        # Strip any accidental trailing quote or punctuation
        url = url.rstrip(".,;)'\"\u2019\u201d")
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        host_m = re.match(r"^https?://([^/\s]+)", url, re.IGNORECASE)
        if not host_m or ("." not in host_m.group(1) and host_m.group(1).lower() != "localhost"):
            url = None

    return url, doi


def _split_merged_raw_reference(raw_ref_text: str) -> list[str]:
    """Split a GROBID raw_reference when it accidentally glues 2 MLA entries."""
    if not raw_ref_text:
        return []
    text = _normalize_raw_ref_text(raw_ref_text)

    # Case 1: Entry 1 ends with "Accessed DD Mon. YYYY." followed by optional author + quoted title
    m1 = re.match(
        r"^(.+?\bAccessed\s+\d{1,2}\s+[A-Za-z.]+\s+(?:19|20)\d{2}\.)\s+((?:[A-Z][A-Za-z0-9.\s'\u2019-]{1,40}\.\s+)?[\"\u201c][A-Z].+)$",
        text,
    )
    if m1:
        return [m1.group(1).strip(), m1.group(2).strip()]

    # Case 2: Book entry ending with "YYYY." or URL followed by a quoted web entry with URL
    m2 = re.match(
        r"^(.+?(?:\b(?:19|20)\d{2}\.|https?://\S+\.))\s+((?:[A-Z][A-Za-z0-9.\s'\u2019-]{1,40}\.\s+)?[\"\u201c][^\"\u201d]+[\"\u201d]\s+[A-Z].*(?:https?://|www\.|\b[a-z0-9-]+\.(?:com|org|edu|gov|net)/).*)$",
        text,
    )
    if m2:
        return [m2.group(1).strip(), m2.group(2).strip()]

    return [text]


def _parse_raw_bib_segment(raw_seg: str, entry_id: str) -> GrobidBibEntry:
    """Parse a single raw bibliography segment that was split from a multi-entry biblStruct."""
    seg = _normalize_raw_ref_text(raw_seg)
    url, doi = _extract_url_and_doi_from_raw(seg)

    authors: list[GrobidAuthor] = []
    title: Optional[str] = None
    venue: Optional[str] = None
    year: Optional[str] = None

    # Extract year (prefer non-Accessed year if present, else Accessed year)
    non_accessed = re.sub(
        r"\bAccessed\s+\d{1,2}\s+[A-Za-z.]+\s+(?:19|20)\d{2}\.?",
        "",
        seg,
        flags=re.IGNORECASE,
    )
    years = re.findall(r"\b((?:19|20)\d{2})\b", non_accessed)
    if years:
        year = years[0]
    else:
        acc_years = re.findall(r"\b((?:19|20)\d{2})\b", seg)
        if acc_years:
            year = acc_years[-1]

    # Check if starts with optional Site/Author + quoted title: [Goodreads.] "Title." Site, URL
    q_m = re.match(
        r"^(?:([A-Z][A-Za-z0-9.\s'\u2019-]{1,40})\.\s+)?[\"\u201c]([^\"\u201d]{2,200}?)[\"\u201d]\s*([A-Za-z0-9][^,]+)?",
        seg,
    )
    if q_m:
        lead_author = (q_m.group(1) or "").strip().rstrip(".")
        title = q_m.group(2).strip().rstrip(".,")
        if q_m.group(3):
            venue = q_m.group(3).strip().rstrip(".")
        auth_label = lead_author or venue
        if auth_label:
            authors.append(GrobidAuthor(full_name=auth_label, first_name=None, last_name=auth_label))
    else:
        # MLA Author: "Surname, Firstname. Title. [Edited by ..., Publisher,] Year"
        mla_m = re.match(
            r"^([A-Z][A-Za-z'\u2019-]+),\s*([A-Z][A-Za-z.\s-]*?\.)\s+([^.]+)\.",
            seg,
        )
        if mla_m:
            sn = mla_m.group(1).strip()
            fn = mla_m.group(2).strip().rstrip(".")
            authors.append(
                GrobidAuthor(full_name=f"{sn}, {fn}", first_name=fn, last_name=sn)
            )
            title = mla_m.group(3).strip().rstrip(".")

    return GrobidBibEntry(
        id=entry_id,
        authors=authors,
        title=title,
        year=year,
        venue=venue,
        doi=doi,
        url=url,
        raw_reference=seg,
        raw_xml="",
    )


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

        # Raw reference note (if provided by GROBID)
        raw_ref_el = bibl.find(f".//{_TEI}note[@type='raw_reference']")
        raw_ref_text = (
            _normalize_raw_ref_text("".join(raw_ref_el.itertext()).strip())
            if raw_ref_el is not None
            else ""
        )

        # If GROBID glued multiple bibliography entries into a single <biblStruct>,
        # split and parse each segment separately.
        split_segments = _split_merged_raw_reference(raw_ref_text)
        if len(split_segments) > 1:
            for seg_idx, seg_text in enumerate(split_segments):
                seg_id = entry_id if seg_idx == 0 else f"{entry_id}_{seg_idx}"
                entries.append(_parse_raw_bib_segment(seg_text, seg_id))
            continue

        # Authors
        raw_authors: list[tuple[str, str]] = []
        for author_el in bibl.findall(f".//{_TEI}author"):
            pers = author_el.find(f"{_TEI}persName")
            if pers is None:
                org = author_el.find(f"{_TEI}orgName")
                if org is not None and org.text and org.text.strip():
                    raw_authors.append((org.text.strip(), ""))
                continue
            surname = pers.find(f"{_TEI}surname")
            forenames = [
                f.text.strip()
                for f in pers.findall(f"{_TEI}forename")
                if f.text and f.text.strip()
            ]
            sn = surname.text.strip() if surname is not None and surname.text else ""
            fn = " ".join(forenames)

            # Skip or fix standalone generational suffixes parsed as separate authors (e.g. "III, Tremper Longman")
            if sn.lower().rstrip(".") in {"iii", "ii", "iv", "jr", "sr"}:
                if fn:
                    # Keep fn as a pending forename for the next author node
                    raw_authors.append(("", fn))
                continue
            if (
                sn
                and not fn
                and raw_authors
                and not raw_authors[-1][0]
                and raw_authors[-1][1]
            ):
                fn = raw_authors.pop()[1]

            # Fix GROBID splitting hyphenated Vietnamese initials into surname
            # e.g. forename="D H", surname=".-C. Nguyen" -> fn="D H.-C.", sn="Nguyen"
            if sn:
                hyph_m = re.match(r"^(\.?-[A-ZÀ-Ý]\.?)\s+(.+)$", sn)
                if hyph_m:
                    fn = f"{fn}{hyph_m.group(1)}".strip()
                    sn = hyph_m.group(2).strip()

            # Merge with previous author if GROBID split a hyphenated given name
            # across two <author> nodes: prev has sn="" & fn="L T", current has fn="-V" & sn="Pham"
            if (
                fn.startswith("-")
                and sn
                and raw_authors
                and not raw_authors[-1][0]
                and raw_authors[-1][1]
            ):
                prev_fn = raw_authors.pop()[1]
                fn = f"{prev_fn}{fn}"

            raw_authors.append((sn, fn))

        authors: list[GrobidAuthor] = []
        for sn, fn in raw_authors:
            if not sn and not fn:
                continue
            # Skip obvious non-author artifacts from GROBID on body text
            if f"{sn} {fn}".strip().lower() in ("cls token",):
                continue
            authors.append(
                GrobidAuthor(
                    full_name=f"{sn}, {fn}".strip(", "),
                    first_name=fn or None,
                    last_name=sn or None,
                )
            )

        # Recover corporate/organization author from raw_reference when GROBID
        # omitted <author> (e.g. "American Psychiatric Association. (2022)...",
        # "Dictionary.com (2026, March 12)...", "Fight the New Drug. 'Is Reading...'",
        # or "'Erotica Sub-Genres...' Shameless Book Deals, ...").
        if not authors and raw_ref_text:
            org_m = re.match(
                r"^(?:\[\s*\d+\s*\]\s*)?([A-Z][A-Za-z0-9.\s&'\u2019-]{2,80}?)\.?\s*(?:\((?:19|20)\d{2}|\.\s*[\"\u201c])",
                raw_ref_text,
            )
            if org_m:
                org_name = org_m.group(1).strip().rstrip(".")
                authors.append(
                    GrobidAuthor(full_name=org_name, first_name=None, last_name=org_name)
                )
            else:
                anon_m = re.match(
                    r"^[\"\u201c][^\"\u201d]{3,200}[\"\u201d]\s*([A-Z][A-Za-z0-9.\s&'\u2019-]{2,50}?),",
                    raw_ref_text,
                )
                if anon_m:
                    site_name = anon_m.group(1).strip().rstrip(".")
                    authors.append(
                        GrobidAuthor(full_name=site_name, first_name=None, last_name=site_name)
                    )

        # Title (article-level first, then monograph-level, skipping empty <title/> tags)
        title: str | None = None
        for xpath in (
            f".//{_TEI}title[@level='a']",
            f".//{_TEI}title[@level='m']",
            f".//{_TEI}title",
        ):
            for cand_el in bibl.findall(xpath):
                cand_text = "".join(cand_el.itertext()).strip()
                if cand_text:
                    title = cand_text
                    break
            if title:
                break

        # Discard bogus URL fragment / anchor placed into <title> by GROBID
        if title and re.match(r"^(?:#|https?://|www\.|%[0-9A-Fa-f]{2})", title, re.I):
            title = None

        # Fallback: check <note> (excluding raw_reference) when <title/> is empty
        # (e.g. Flanagan [2020] where GROBID puts "JavaScript: The Definitive Guide, 7th Edition" in <note>)
        if not title:
            for note_el in bibl.findall(f"{_TEI}note"):
                if note_el.get("type") == "raw_reference":
                    continue
                note_text = "".join(note_el.itertext()).strip()
                if (
                    len(note_text) > 5
                    and not re.match(r"^(?:\d+(?:st|nd|rd|th)|th)\s+ed", note_text, re.I)
                    and not re.match(r"^(?:#|https?://|www\.)", note_text, re.I)
                ):
                    title = note_text
                    break

        # Year
        year_el = bibl.find(f".//{_TEI}date[@type='published']")
        if year_el is None:
            year_el = bibl.find(f".//{_TEI}date")
        year: str | None = None
        if year_el is not None:
            when = year_el.get("when")
            if when and re.match(r"^(?:19|20)\d{2}", when):
                year = when[:4]

        # Some PDFs use author-year suffixes (``2018a. Title``).  GROBID can
        # occasionally attach that prefix to the analytic title and omit the
        # date element.  Recover the year/suffix and remove the artefact so
        # linking and metadata comparison see the actual title.
        if title:
            prefix = re.match(r"^(19|20)\d{2}([a-z])?\.\s+", title, re.I)
            if prefix:
                if year is None:
                    year = prefix.group(0)[:4]
                title = title[prefix.end():].strip()

        # Venue (journal-level title) — dùng .// để tìm trong <monogr>
        venue_el = bibl.find(f".//{_TEI}title[@level='j']")
        venue = "".join(venue_el.itertext()).strip() if venue_el is not None else None

        # Extract URL and DOI (including from raw_reference)
        url, doi = _extract_url_and_doi_from_raw(raw_ref_text, bibl)

        # Merge continuation <biblStruct> fragments into the previous entry
        # (e.g. "EBSCOhost, https://doi.org/..." or "Dec. 2015, pp. 183-205, https://doi.org/...")
        if (
            entries
            and title is None
            and raw_ref_text
            and _CONTINUATION_START_RE.match(raw_ref_text)
        ):
            prev = entries[-1]
            if doi and not prev.doi:
                prev.doi = doi
            if year and not prev.year:
                prev.year = year
            if url and not prev.url:
                prev.url = url
            prev.raw_reference = f"{prev.raw_reference} {raw_ref_text}".strip()
            continue

        # Recover quoted title from raw_reference when GROBID missed the title
        # or put the website/container name (e.g. "Project Gutenberg") as the monograph title
        if raw_ref_text:
            q_match = re.search(r"[\"\u201c]([^\"\u201d]{3,220}?)[\"\u201d]", raw_ref_text)
            if q_match:
                q_title = q_match.group(1).strip().rstrip(".,")
                if not title or (
                    title.lower() != q_title.lower()
                    and f'"{title}' not in raw_ref_text
                    and f"\u201c{title}" not in raw_ref_text
                    and len(title.split()) <= 4
                ):
                    if title and not venue:
                        venue = title
                    title = q_title

        # Fix unquoted IEEE/APA/MLA book entries where GROBID places the book title
        # into <author> inside <monogr> and leaves title=None or sets title to the series/publisher
        if bibl.find(f"{_TEI}analytic") is None and raw_ref_text:
            # Determine where the author segment ends in raw_ref_text:
            # either at "(YYYY)" or after the first author block in MLA ("Surname, Firstname.")
            auth_head_end = None
            yr_parens = re.search(r"\(\s*(?:19|20)\d{2}", raw_ref_text)
            if yr_parens:
                auth_head_end = yr_parens.start()
            else:
                mla_head = re.match(
                    r"^(?:III,\s*)?[A-Z][A-Za-z'\u2019-]+,\s*"
                    r"(?:"
                    r"[A-Z][a-zA-Z.\s-]+?,\s*and\s+(?:[A-Z]\.\s*|[A-Z][a-zA-Z-]+\s+)+[A-Z][a-zA-Z'\u2019-]+\."
                    r"|(?:[A-Z]\.\s*){1,3}"
                    r"|[A-Z][a-zA-Z-]+(?:\.|\s+(?:[A-Z]\.\s*){1,2})"
                    r")\s*",
                    raw_ref_text,
                )
                if mla_head:
                    auth_head_end = mla_head.end()

            had_removed_authors = False
            if auth_head_end is not None and len(authors) >= 2:
                auth_prefix = raw_ref_text[:auth_head_end].lower()
                kept_authors: list[GrobidAuthor] = []
                removed_authors: list[GrobidAuthor] = []
                for auth in authors:
                    ln = (auth.last_name or "").lower().strip()
                    if ln and ln in auth_prefix:
                        kept_authors.append(auth)
                    else:
                        removed_authors.append(auth)
                if kept_authors and removed_authors:
                    authors = kept_authors
                    had_removed_authors = True

            # If title is still None (or GROBID placed the book title into <author> and set title to the publisher/note), recover from raw_ref_text
            if (
                not title
                or had_removed_authors
                or title.lower() in {"project gutenberg", "goodreads", "holman bible publishers"}
                or title.lower().startswith(("cambridge university press", "oxford university press", "holman bible"))
            ):
                old_title = title
                if yr_parens:
                    after_yr = re.sub(
                        r"^\(\s*(?:19|20)\d{2}[^)]*\)\.\s*",
                        "",
                        raw_ref_text[yr_parens.start():],
                    )
                    m_title = re.match(r"^([^.]{3,180})\.", after_yr)
                    if m_title:
                        title = m_title.group(1).strip()
                elif auth_head_end is not None:
                    after_auth = raw_ref_text[auth_head_end:].strip()
                    m_title = re.match(r"^([^.]{2,180})\.", after_auth)
                    if m_title:
                        title = m_title.group(1).strip()
                if (
                    old_title
                    and title != old_title
                    and not venue
                    and not old_title.lower().startswith(("cambridge university press,", "https://", "http://"))
                ):
                    venue = old_title

            # Also support IEEE "B. Settles, Active Learning. Synthesis Lectures..."
            if len(authors) >= 2:
                last_auth = authors[-1]
                if (
                    last_auth.first_name
                    and last_auth.last_name
                    and len(last_auth.first_name) > 2
                    and len(last_auth.last_name) > 2
                ):
                    candidate_book_title = f"{last_auth.first_name} {last_auth.last_name}"
                    if re.search(
                        rf",\s*{re.escape(candidate_book_title)}\.\s+",
                        raw_ref_text,
                        re.IGNORECASE,
                    ):
                        authors.pop()
                        if title and not venue:
                            venue = title
                        title = candidate_book_title

        # Strip book publisher or ", edited by ..., Publisher" glued to the end of title
        if title:
            pub_m = _BOOK_PUBLISHER_SUFFIX_RE.search(title)
            if pub_m:
                extracted_pub = (pub_m.group("ed_pub") or pub_m.group("pub") or "").strip()
                title = title[:pub_m.start()].strip().rstrip(".,")
                if extracted_pub and (not venue or venue.lower().startswith(title.lower())):
                    venue = extracted_pub

        # Recover numbered biblical book title (e.g. "1 Corinthians", "2 Corinthians") when GROBID dropped the leading number
        if title == "Corinthians" and raw_ref_text:
            m_cor = re.search(r"\b([12]\s+Corinthians)\b", raw_ref_text)
            if m_cor:
                title = m_cor.group(1)
                if venue and venue.startswith("Corinthians."):
                    venue = venue[len("Corinthians."):].strip()

        # Clean percent-encoded URL fragments and trailing blog/site names from title
        if title:
            title = re.sub(r"\.\s*[^\s.]*%[0-9A-Fa-f]{2}.*$", "", title).strip()
            if (
                ". " in title
                and raw_ref_text
                and re.search(r"\(\s*(?:19|20)\d{2},\s*[A-Za-z]+", raw_ref_text)
            ):
                t_parts = [p.strip() for p in title.split(". ") if p.strip()]
                if len(t_parts) >= 2:
                    title = t_parts[0]
                    if not venue:
                        venue = t_parts[1]

        # Recover book publisher into venue from raw_ref_text if venue is still None
        if not venue and raw_ref_text:
            pub_raw_m = re.search(
                r"\b(Zondervan(?:\s+Academic)?|Baker\s+Academic|Baker\s+Publishing(?:\s+Group)?|"
                r"Crossway(?:\s+Books)?|Brazos\s+Press|HarperOne|Harper\s*Collins(?:\s+Publishers)?|"
                r"InterVarsity\s+Press|IVP\s+Books|Waterbrook\s+Press|Convergent\s+Books|"
                r"B&H\s+Publishing|Holman\s+Bible\s+Publishers|Farrar,\s*Straus\s+and\s+Giroux|"
                r"Cambridge\s+University\s+Press|Oxford\s+University\s+Press|Project\s+Gutenberg)\b",
                raw_ref_text,
                re.IGNORECASE,
            )
            if pub_raw_m:
                venue = pub_raw_m.group(1).strip()

        # For malformed two-column references GROBID may put the continuation
        # of the author list in <analytic>/<title>, while the real title is in
        # the monograph title (e.g. Warstadt et al.).
        if title and re.search(r",\s*(?:and\s+)?[^.]+\b(?:Bowman|Manning)\b", title):
            monogr_title = bibl.find(f".//{_TEI}title[@level='m']")
            if monogr_title is not None and "".join(monogr_title.itertext()).strip():
                title = "".join(monogr_title.itertext()).strip()

        # Recover year from raw_ref_text if GROBID missed <date>
        if not year and raw_ref_text:
            non_accessed = re.sub(
                r"\bAccessed\s+\d{1,2}\s+[A-Za-z.]+\s+(?:19|20)\d{2}\.?",
                "",
                raw_ref_text,
                flags=re.IGNORECASE,
            )
            yr_matches = re.findall(r"\b((?:19|20)\d{2})\b", non_accessed)
            if yr_matches:
                year = yr_matches[0]
            else:
                acc_matches = re.findall(r"\b((?:19|20)\d{2})\b", raw_ref_text)
                if acc_matches:
                    year = acc_matches[-1]

        # Raw XML for debug
        raw = tostring(bibl, encoding="unicode")

        entries.append(GrobidBibEntry(
            id=entry_id,
            authors=authors,
            title=title,
            year=year,
            venue=venue,
            doi=doi,
            url=url,
            raw_reference=raw_ref_text,
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
