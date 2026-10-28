"""1-Click Bibliography Auto-Remediation & Canonical Reference Formatter (Sprint 3.1).

Transforms extracted / verified references (including METADATA_ERROR entries) into
standardized academic bibliography entries using verified canonical metadata from
Semantic Scholar, OpenAlex, Crossref, PubMed, arXiv, and LocalDB.

Supported output formats:
- `apa`: APA 7th Edition
- `ieee`: IEEE Numeric Style
- `tdtu`: Harvard / TDTU Thesis Guideline Style
- `bibtex`: BibTeX (.bib)
- `ris`: Research Information Systems (.ris)
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any


_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})[a-z]?\b")
_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\]\)\,;]+", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s\]\)\,;]+", re.IGNORECASE)


def _clean_text(val: Any) -> str:
    if not val:
        return ""
    s = str(val).strip()
    return " ".join(s.split())


def _extract_raw_fallback_metadata(raw_text: str) -> dict[str, Any]:
    """Best-effort extraction from raw reference text when no external candidate matched."""
    cleaned = _clean_text(raw_text)
    # Strip leading [N] or N.
    cleaned_no_num = re.sub(r"^\s*(?:\[\d+\]|\d+\.)\s*", "", cleaned)

    year_m = _YEAR_RE.search(cleaned_no_num)
    year = year_m.group(1) if year_m else ""

    doi_m = _DOI_RE.search(cleaned_no_num)
    doi = doi_m.group(0).rstrip(".,;)") if doi_m else ""

    url_m = _URL_RE.search(cleaned_no_num)
    url = url_m.group(0).rstrip(".,;)") if url_m else ""

    authors: list[str] = []
    title = ""
    venue = ""

    # Try Author (Year). Title. Venue.
    apa_m = re.match(
        r"^(?P<authors>[^()]{2,140}?)\s*\(\s*(?:19|20)\d{2}[a-z]?\s*\)[.,]?\s*(?P<rest>.+)$",
        cleaned_no_num,
    )
    if apa_m:
        raw_auth = apa_m.group("authors").strip(" .,;")
        authors = [a.strip() for a in re.split(r"\s*(?:;|&\s+|\band\b)\s*", raw_auth) if a.strip()]
        rest = apa_m.group("rest").strip()
        # Strip trailing DOI/URL
        rest = re.sub(r"\s*(?:https?://\S+|doi:\s*\S+)\s*$", "", rest, flags=re.IGNORECASE).strip()
        parts = [p.strip() for p in rest.split(". ") if p.strip()]
        if parts:
            title = parts[0].strip(" .\"“”'")
            if len(parts) > 1:
                venue = parts[1].strip(" .")
    else:
        # Try quoted title
        q_m = re.search(r"[\"\u201c]([^\"\u201d]{6,220})[\"\u201d]", cleaned_no_num)
        if q_m:
            title = q_m.group(1).strip(" .")
            prefix = cleaned_no_num[: q_m.start()].strip(" .,;")
            if prefix:
                authors = [a.strip() for a in re.split(r"\s*(?:;|,\s+and\s+|\band\b)\s*", prefix) if a.strip()]
        else:
            parts = [p.strip() for p in cleaned_no_num.split(". ") if p.strip()]
            if len(parts) >= 2:
                authors = [parts[0]]
                title = parts[1].strip(" .")
                if len(parts) >= 3:
                    venue = parts[2].strip(" .")
            else:
                title = cleaned_no_num[:160]

    return {
        "title": title,
        "authors": authors,
        "year": str(year) if year else "",
        "venue": venue,
        "doi": doi,
        "url": url,
    }


def _normalize_author_list(raw_authors: Any) -> list[str]:
    if not raw_authors:
        return []
    if isinstance(raw_authors, str):
        items = [a.strip() for a in re.split(r"\s*(?:;|\band\b|&)\s*", raw_authors) if a.strip()]
    elif isinstance(raw_authors, list):
        items = []
        for item in raw_authors:
            if isinstance(item, dict):
                name = item.get("name") or item.get("raw") or item.get("last_name") or ""
                if name:
                    items.append(str(name).strip())
            elif hasattr(item, "raw") or hasattr(item, "last_name"):
                name = getattr(item, "raw", "") or getattr(item, "last_name", "")
                if name:
                    items.append(str(name).strip())
            elif item:
                items.append(str(item).strip())
    else:
        return []
    return [a for a in items if a]


_CORPORATE_AUTHOR_RE = re.compile(
    r"^(?:quốc\s+hội|chính\s+phủ|thủ\s+tướng(?:\s+chính\s+phủ)?|"
    r"bộ\s+[\wÀ-ỹ\s]+|ủy\s+ban[\wÀ-ỹ\s]*|tòa\s+án[\wÀ-ỹ\s]*|"
    r"viện\s+kiểm\s+sát[\wÀ-ỹ\s]*|ngân\s+hàng\s+nhà\s+nước|"
    r"world\s+health\s+organization|united\s+nations|european\s+commission|"
    r"ministry\s+of\s+[\w\s]+|national\s+institute[\w\s]*)\b",
    re.IGNORECASE,
)


def _split_surname_initials(author_str: str) -> tuple[str, str]:
    """Return (Surname, Initials_With_Dots) for a single author string."""
    s = _clean_text(author_str).strip(".,;")
    if not s:
        return ("Unknown", "")
    if _CORPORATE_AUTHOR_RE.search(s):
        return (s, "")
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        surname = parts[0]
        given = parts[1] if len(parts) > 1 else ""
    else:
        tokens = s.split()
        if len(tokens) == 1:
            return (tokens[0], "")
        # Check if trailing token is uppercase initials like "Ackerman JD"
        if re.fullmatch(r"[A-Z]{1,3}", tokens[-1]) and len(tokens[0]) > 1:
            surname = " ".join(tokens[:-1])
            given = " ".join(list(tokens[-1]))
        else:
            surname = tokens[-1]
            given = " ".join(tokens[:-1])

    initials: list[str] = []
    for tok in re.split(r"[\s.]+", given):
        tok = tok.strip()
        if tok and tok[0].isalpha():
            initials.append(f"{tok[0].upper()}.")
    return (surname, " ".join(initials))


def _format_authors_apa(authors: list[str]) -> str:
    if not authors:
        return "Anonymous"
    formatted: list[str] = []
    for a in authors[:20]:
        surname, inits = _split_surname_initials(a)
        formatted.append(f"{surname}, {inits}".strip(", "))
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"


def _format_authors_ieee(authors: list[str]) -> str:
    if not authors:
        return "Anonymous"
    if len(authors) > 6:
        surname, inits = _split_surname_initials(authors[0])
        first = f"{inits} {surname}".strip()
        return f"{first} et al."
    formatted: list[str] = []
    for a in authors:
        surname, inits = _split_surname_initials(a)
        formatted.append(f"{inits} {surname}".strip())
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", and {formatted[-1]}"


def _format_authors_tdtu(authors: list[str]) -> str:
    if not authors:
        return "Anonymous"
    formatted: list[str] = []
    for a in authors[:6]:
        surname, inits = _split_surname_initials(a)
        formatted.append(f"{surname}, {inits}".strip(", "))
    if len(authors) > 6:
        return f"{formatted[0]} et al."
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    return ", ".join(formatted[:-1]) + f" and {formatted[-1]}"


def _make_bibtex_key(authors: list[str], year: str, title: str, index: int) -> str:
    surname = "ref"
    if authors:
        s, _ = _split_surname_initials(authors[0])
        s_ascii = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        s_clean = re.sub(r"[^a-zA-Z0-9]", "", s_ascii).lower()
        if s_clean:
            surname = s_clean
    yr = year if year and year.isdigit() else "nd"
    first_word = "work"
    for w in re.findall(r"[A-Za-z]{4,}", title or ""):
        if w.lower() not in {"with", "from", "that", "this", "using", "based", "study", "analysis"}:
            first_word = w.lower()
            break
    return f"{surname}{yr}{first_word}{index}"


def format_canonical_entry(
    meta: dict[str, Any],
    index: int,
    style: str = "apa",
) -> dict[str, str]:
    """Render a canonical metadata dictionary into APA, IEEE, TDTU, BibTeX, and RIS."""
    title = _clean_text(meta.get("title")) or "Untitled Source"
    authors = _normalize_author_list(meta.get("authors"))
    year = _clean_text(meta.get("year")) or "n.d."
    venue = _clean_text(meta.get("venue"))
    doi = _clean_text(meta.get("doi"))
    if doi.lower().startswith("https://doi.org/"):
        doi = doi[16:].strip()
    elif doi.lower().startswith("doi:"):
        doi = doi[4:].strip()
    url = _clean_text(meta.get("url"))

    # 1. APA 7th
    apa_authors = _format_authors_apa(authors)
    apa_parts = [f"{apa_authors} ({year}). {title.rstrip('.')}."]
    if venue:
        apa_parts.append(f"{venue.rstrip('.')}.")
    if doi:
        apa_parts.append(f"https://doi.org/{doi}")
    elif url:
        apa_parts.append(url)
    apa_str = " ".join(apa_parts)

    # 2. IEEE
    ieee_authors = _format_authors_ieee(authors)
    ieee_parts = [f"[{index}] {ieee_authors}, \"{title.rstrip('.')},\""]
    if venue:
        ieee_parts.append(f"{venue.rstrip('.')},")
    ieee_parts.append(f"{year}.")
    if doi:
        ieee_parts[-1] = f"{year}, doi: {doi}."
    elif url:
        ieee_parts.append(f"[Online]. Available: {url}")
    ieee_str = " ".join(ieee_parts)

    # 3. Harvard / TDTU Standard
    tdtu_authors = _format_authors_tdtu(authors)
    tdtu_parts = [f"{tdtu_authors} ({year}), '{title.rstrip('.')}'"]
    if venue:
        tdtu_parts.append(venue.rstrip("."))
    if doi:
        tdtu_parts.append(f"DOI: {doi}")
    elif url:
        tdtu_parts.append(f"URL: {url}")
    tdtu_str = ", ".join(tdtu_parts) + "."

    # 4. BibTeX
    bib_key = _make_bibtex_key(authors, year, title, index)
    bib_authors = " and ".join(authors) if authors else "Anonymous"
    bib_lines = [
        f"@article{{{bib_key},",
        f"  author = {{{bib_authors}}},",
        f"  title = {{{title}}},",
    ]
    if venue:
        bib_lines.append(f"  journal = {{{venue}}},")
    if year and year != "n.d.":
        bib_lines.append(f"  year = {{{year}}},")
    if doi:
        bib_lines.append(f"  doi = {{{doi}}},")
    if url:
        bib_lines.append(f"  url = {{{url}}},")
    bib_lines.append("}")
    bibtex_str = "\n".join(bib_lines)

    # 5. RIS
    ris_lines = [
        "TY  - JOUR",
        f"TI  - {title}",
    ]
    for a in (authors or ["Anonymous"]):
        surname, inits = _split_surname_initials(a)
        ris_lines.append(f"AU  - {surname}, {inits}".strip(", "))
    if year and year != "n.d.":
        ris_lines.append(f"PY  - {year}")
    if venue:
        ris_lines.append(f"JO  - {venue}")
    if doi:
        ris_lines.append(f"DO  - {doi}")
    if url:
        ris_lines.append(f"UR  - {url}")
    ris_lines.append("ER  - ")
    ris_str = "\n".join(ris_lines)

    by_style = {
        "apa": apa_str,
        "ieee": ieee_str,
        "tdtu": tdtu_str,
        "bibtex": bibtex_str,
        "ris": ris_str,
    }
    selected = by_style.get(style.lower(), apa_str)
    return {
        "remediated_text": selected,
        "apa": apa_str,
        "ieee": ieee_str,
        "tdtu": tdtu_str,
        "bibtex": bibtex_str,
        "ris": ris_str,
    }


def build_remediated_bibliography(
    essay_id: int,
    verdicts: list[Any],
    style: str = "apa",
) -> dict[str, Any]:
    """Generate auto-remediated bibliography entries and diffs for an essay."""
    normalized_style = (style or "apa").strip().lower()
    if normalized_style not in {"apa", "ieee", "tdtu", "bibtex", "ris"}:
        normalized_style = "apa"

    entries: list[dict[str, Any]] = []
    remediated_count = 0

    for idx, v in enumerate(verdicts, start=1):
        raw_text = _clean_text(getattr(v, "citation_raw", "") if not isinstance(v, dict) else v.get("citation_raw", ""))
        label = _clean_text(getattr(v, "label", "") if not isinstance(v, dict) else v.get("label", "")).lower()
        verdict_id = getattr(v, "id", idx) if not isinstance(v, dict) else v.get("citation_id", f"v{idx}")

        mismatched_raw = (
            getattr(v, "mismatched_fields", "")
            if not isinstance(v, dict)
            else v.get("mismatched_fields", [])
        )
        if isinstance(mismatched_raw, str):
            s_raw = mismatched_raw.strip()
            if s_raw.startswith("["):
                try:
                    parsed_mf = json.loads(s_raw)
                    mismatched_fields = (
                        [str(f).strip() for f in parsed_mf if str(f).strip()]
                        if isinstance(parsed_mf, list)
                        else []
                    )
                except (json.JSONDecodeError, TypeError):
                    mismatched_fields = []
            else:
                mismatched_fields = [f.strip() for f in s_raw.split(",") if f.strip()]
        elif isinstance(mismatched_raw, list):
            mismatched_fields = [str(f).strip() for f in mismatched_raw if str(f).strip()]
        else:
            mismatched_fields = []

        features_dict: dict[str, Any] = {}
        if isinstance(v, dict):
            features_dict = v.get("features") if isinstance(v.get("features"), dict) else {}
            matched_sources = v.get("matched_sources") or features_dict.get("matched_sources") or []
        else:
            try:
                features_dict = json.loads(getattr(v, "features", None) or "{}")
            except (json.JSONDecodeError, TypeError):
                features_dict = {}
            matched_sources = features_dict.get("matched_sources", [])

        fallback_meta = _extract_raw_fallback_metadata(raw_text)
        canonical_meta = dict(fallback_meta)
        diff_fields: list[str] = list(mismatched_fields)
        source_used: str | None = None

        # Choose the highest-confidence found source candidate
        # Note: persisted VerdictRecord.features['matched_sources'] entries only contain
        # already-matched candidates and may omit the boolean 'found' key.
        found_candidates = [
            s for s in matched_sources
            if isinstance(s, dict) and s.get("found", True) is not False and s.get("title")
        ]
        if found_candidates:
            best = max(
                found_candidates,
                key=lambda s: float(s.get("score") or s.get("confidence") or 0.0),
            )
            source_used = str(best.get("source_name") or best.get("source") or "scholarly_db")

            cand_title = _clean_text(best.get("title"))
            cand_authors = _normalize_author_list(best.get("authors"))
            cand_year = _clean_text(best.get("year"))
            cand_venue = _clean_text(best.get("venue"))
            cand_doi = _clean_text(best.get("doi"))

            if cand_title:
                if fallback_meta["title"] and cand_title.lower() != fallback_meta["title"].lower():
                    if "title" not in diff_fields:
                        diff_fields.append("title")
                canonical_meta["title"] = cand_title

            if cand_authors:
                if not fallback_meta["authors"] or "authors" in diff_fields or "author" in diff_fields:
                    if "authors" not in diff_fields and fallback_meta["authors"]:
                        diff_fields.append("authors")
                canonical_meta["authors"] = cand_authors

            if cand_year:
                if fallback_meta["year"] and cand_year[:4] != fallback_meta["year"][:4]:
                    if "year" not in diff_fields:
                        diff_fields.append("year")
                elif not fallback_meta["year"]:
                    diff_fields.append("year")
                canonical_meta["year"] = cand_year[:4]

            if cand_venue:
                if not fallback_meta["venue"] or "venue" in diff_fields:
                    if "venue" not in diff_fields and not fallback_meta["venue"]:
                        diff_fields.append("venue")
                canonical_meta["venue"] = cand_venue

            if cand_doi:
                if not fallback_meta["doi"]:
                    if "doi" not in diff_fields:
                        diff_fields.append("doi")
                elif fallback_meta["doi"].lower() != cand_doi.lower():
                    if "doi" not in diff_fields:
                        diff_fields.append("doi")
                canonical_meta["doi"] = cand_doi

        rendered = format_canonical_entry(canonical_meta, index=idx, style=normalized_style)
        was_modified = bool(diff_fields) or label == "metadata_error"
        if was_modified:
            remediated_count += 1

        entries.append(
            {
                "index": idx,
                "verdict_id": str(verdict_id),
                "label": label or "unresolved",
                "source_used": source_used,
                "original_raw": raw_text,
                "remediated_text": rendered["remediated_text"],
                "apa": rendered["apa"],
                "ieee": rendered["ieee"],
                "tdtu": rendered["tdtu"],
                "bibtex": rendered["bibtex"],
                "ris": rendered["ris"],
                "diff_fields": diff_fields,
                "was_modified": was_modified,
                "canonical_metadata": canonical_meta,
            }
        )

    combined_text = "\n\n".join(e["remediated_text"] for e in entries)
    combined_bibtex = "\n\n".join(e["bibtex"] for e in entries)
    combined_ris = "\n\n".join(e["ris"] for e in entries)

    return {
        "essay_id": essay_id,
        "style": normalized_style,
        "total_entries": len(entries),
        "remediated_count": remediated_count,
        "entries": entries,
        "combined_text": combined_text,
        "combined_bibtex": combined_bibtex,
        "combined_ris": combined_ris,
    }
