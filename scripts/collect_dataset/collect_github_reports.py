#!/usr/bin/env python3
"""
Collect public student reports / essays / theses (PDFs) from GitHub repositories.
Prioritizes Ton Duc Thang University (TDTU) student project reports and Vietnamese
university reports/theses shared publicly on GitHub.

Usage:
    .venv/bin/python scripts/collect_dataset/collect_github_reports.py \
        --output data/tdtu_github_reports \
        --n 100
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

import fitz  # PyMuPDF
import requests

GITHUB_API = "https://api.github.com"
RAW_GITHUB = "https://raw.githubusercontent.com"

# TDTU-focused search queries (prioritizing TDTU student IDs across cohorts & faculties)
SEARCH_QUERIES = [
    # Unsearched / partially searched TDTU student ID prefixes first
    "52300",
    "51800",
    "524H",
    "52400",
    "51700",
    "517H",
    "42100",
    "42000",
    "41900",
    "42200",
    "41800",
    "72100",
    "72000",
    "504070",
    "503073",
    "504044",
    "502045",
    "SOA TDTU",
    "NLP TDTU",
    "ML TDTU",
    "DIP TDTU",
    "BigData TDTU",
    "CNPM TDTU",
    # Previously searched TDTU queries (will also check pages 2-3 & newly discovered owners)
    "52100",
    "52200",
    "52000",
    "51900",
    "523H",
    "522H",
    "521H",
    "520H",
    "519H",
    "518H",
    "522K",
    "521K",
    "TDTU Final",
    "TDTU Midterm",
    "TDTU Report",
    "TDTU Project",
    "TDTU Essay",
    "TDTU",
    "Ton Duc Thang",
]

# Paths/filenames to exclude (non-reports: labs, slides, resumes, Unity/SDK docs, etc.)
EXCLUDE_PATH_RE = re.compile(
    r"("
    r"node_modules|vendor|assets/|third[_-]?party|packages/|site-packages|"
    r"textmesh|shader|polyspace|misra|turnitin|rulebook|manual|datasheet|"
    r"resume|cv[_.-]|certificate|bangdiem|bang_diem|score|transcript|"
    r"slide|presentation|poster|pitch|banner|brochure|"
    r"syllabus|de_bai|debai|de-bai|huong_dan|huongdan|guideline|rubric|template|"
    r"lab\s*0?\d|exercise|baitap|bai_tap|tutorial|cheat[_-]?sheet|checklist"
    r")",
    re.IGNORECASE,
)

# Positive filename/path indicators for student reports/essays/theses
INCLUDE_PATH_RE = re.compile(
    r"("
    r"report|baocao|bao_cao|bao-cao|báo\s*cáo|"
    r"tieuluan|tieu_luan|tieu-luan|tiểu\s*luận|"
    r"khoaluan|khoa_luan|khóa\s*luận|luanvan|luận\s*văn|"
    r"doan|do_an|do-an|đồ\s*án|datn|kltn|lvtn|btl|"
    r"midterm|final|giuaky|giua_ky|cuoiky|cuoi_ky|"
    r"essay|thesis|dissertation|paper|document|doc/|docs/|nop_bai|"
    r"5\d{2}[h0k]\d{4}"
    r")",
    re.IGNORECASE,
)

TDTU_STUDENT_ID_RE = re.compile(r"\b(5\d{2}[H0K]\d{4})\b", re.IGNORECASE)
TDTU_HEADER_RE = re.compile(
    r"^([ivx0-9]+\s*\|\s*)?("
    r"TỔNG\s+LIÊN\s+ĐOÀN\s+LAO\s+ĐỘNG\s+VIỆT\s+NAM|"
    r"VIETNAM\s+GENERAL\s+CONFEDERATION\s+OF\s+LABOU?R"
    r")",
    re.IGNORECASE,
)
TDTU_TEXT_RE = re.compile(
    r"(ton\s+duc\s+thang|tôn\s+đức\s+thắng|\btdtu\b|5\d{2}[h0k]\d{4})",
    re.IGNORECASE,
)
REF_SECTION_RE = re.compile(
    r"(tài\s+liệu\s+tham\s+khảo|danh\s+mục\s+tham\s+khảo|\breferences\b|\bbibliography\b)",
    re.IGNORECASE,
)


def get_github_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token.strip()
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        return None


def api_get(session: requests.Session, url: str, params: dict | None = None) -> dict | list | None:
    for attempt in range(1, 5):
        try:
            resp = session.get(url, params=params, timeout=25)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (403, 429):
                reset = int(resp.headers.get("X-RateLimit-Reset", 0))
                wait = max(reset - int(time.time()) + 2, 10 * attempt) if reset else 15 * attempt
                wait = min(wait, 65)
                print(f"  [rate-limit] Waiting {wait}s for {url}...")
                time.sleep(wait)
                continue
            return None
        except Exception as e:
            print(f"  [warn] API error ({url}): {e}")
            time.sleep(2 * attempt)
    return None


def download_raw_file(session: requests.Session, full_name: str, branch: str, path: str) -> bytes | None:
    encoded_path = "/".join(quote(part, safe="") for part in path.split("/"))
    url = f"{RAW_GITHUB}/{full_name}/{quote(branch, safe='')}/{encoded_path}"
    for attempt in range(1, 4):
        try:
            resp = session.get(url, timeout=45)
            if resp.status_code == 200 and resp.content.startswith(b"%PDF"):
                return resp.content
            return None
        except Exception:
            time.sleep(2 * attempt)
    return None


def inspect_pdf_bytes(pdf_bytes: bytes, min_pages: int = 5, max_pages: int = 250) -> dict | None:
    """Validate that the PDF is a real multi-page report/essay/thesis (not slides or a 1-page prompt)."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return None

    try:
        if doc.is_encrypted or len(doc) < min_pages or len(doc) > max_pages:
            return None

        num_pages = len(doc)
        # Check aspect ratio of first few pages to filter out landscape slides (width > height * 1.15)
        landscape_pages = 0
        sample_check = min(5, num_pages)
        for i in range(sample_check):
            rect = doc[i].rect
            if rect.width > rect.height * 1.15:
                landscape_pages += 1
        if landscape_pages >= (sample_check // 2 + 1):
            return None  # Presentation slides

        # Extract text from first 4 pages and last 5 pages
        first_pages_text = "\n".join(doc[i].get_text("text") for i in range(min(4, num_pages)))
        last_pages_text = "\n".join(
            doc[i].get_text("text") for i in range(max(0, num_pages - 6), num_pages)
        )
        combined_sample = first_pages_text + "\n" + last_pages_text

        if len(combined_sample.strip()) < 600:
            return None  # Scanned image without text layer or near-empty PDF

        is_tdtu = bool(TDTU_TEXT_RE.search(first_pages_text))
        student_ids = sorted(set(m.upper() for m in TDTU_STUDENT_ID_RE.findall(first_pages_text)))
        has_references = bool(REF_SECTION_RE.search(last_pages_text) or REF_SECTION_RE.search(first_pages_text))

        # Extract a clean snippet from page 1 for title/preview
        p1_lines = [line.strip() for line in first_pages_text.splitlines() if line.strip()]
        preview = " | ".join(p1_lines[:8])[:250]

        if not TDTU_HEADER_RE.search(preview):
            return None

        return {
            "num_pages": num_pages,
            "is_tdtu": is_tdtu,
            "student_ids": student_ids,
            "has_references": has_references,
            "preview": preview,
        }
    finally:
        doc.close()


def safe_filename(index: int, repo_full_name: str, pdf_path: str, is_tdtu: bool) -> str:
    prefix = "tdtu" if is_tdtu else "vn_uni"
    repo_slug = re.sub(r"[^a-zA-Z0-9]+", "_", repo_full_name).strip("_")
    stem = Path(pdf_path).stem
    stem_slug = re.sub(r"[^a-zA-Z0-9]+", "_", stem).strip("_")
    name = f"{index:03d}_{prefix}_{repo_slug}_{stem_slug}"[:110]
    return f"{name}.pdf"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collect student report PDFs from GitHub API")
    p.add_argument("--output", "-o", default="data/tdtu_github_reports", help="Output directory")
    p.add_argument("--n", type=int, default=100, help="Target number of PDF reports to collect")
    p.add_argument("--min-pages", type=int, default=5, help="Minimum PDF page count")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "metadata.json"

    token = get_github_token()
    session = requests.Session()
    session.headers.update({
        "Accept": "application/vnd.github+json",
        "User-Agent": "EssayIntegrityChecker-DatasetCollector/1.0",
    })
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
        print("✓ Authenticated with GitHub API token")
    else:
        print("! Running without GitHub token (rate limits will be lower)")

    # Load existing manifest if resuming
    collected: list[dict] = []
    seen_sha256: set[str] = set()
    seen_blob_shas: set[str] = set()
    seen_repos: set[str] = set()
    discovered_tdtu_owners: set[str] = set()

    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in existing:
                fpath = out_dir / item["filename"]
                if fpath.exists():
                    collected.append(item)
                    seen_sha256.add(item["sha256"])
                    if item.get("blob_sha"):
                        seen_blob_shas.add(item["blob_sha"])
            print(f"Resuming with {len(collected)} already downloaded PDFs in {out_dir}")
        except Exception as e:
            print(f"Could not load existing manifest: {e}")

    def process_repo(repo_obj: dict) -> None:
        nonlocal collected
        if len(collected) >= args.n:
            return
        full_name = repo_obj.get("full_name")
        if not full_name or full_name in seen_repos or repo_obj.get("fork"):
            return
        seen_repos.add(full_name)

        branch = repo_obj.get("default_branch") or "main"
        tree_data = api_get(
            session,
            f"{GITHUB_API}/repos/{full_name}/git/trees/{quote(branch, safe='')}?recursive=1",
        )
        if not isinstance(tree_data, dict):
            return

        tree = tree_data.get("tree", [])
        if not isinstance(tree, list):
            return

        # Limit max PDFs taken from a single repository to avoid one repo dominating (max 6 per repo)
        taken_from_repo = 0
        for node in tree:
            if len(collected) >= args.n or taken_from_repo >= 6:
                break
            if node.get("type") != "blob":
                continue
            path = node.get("path", "")
            size = node.get("size", 0) or 0
            blob_sha = node.get("sha", "")

            if not path.lower().endswith(".pdf"):
                continue
            if size < 90_000 or size > 25_000_000:
                continue
            if blob_sha and blob_sha in seen_blob_shas:
                continue
            if EXCLUDE_PATH_RE.search(path):
                continue
            if not (INCLUDE_PATH_RE.search(path) or INCLUDE_PATH_RE.search(full_name)):
                continue

            pdf_bytes = download_raw_file(session, full_name, branch, path)
            if not pdf_bytes:
                continue

            file_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
            if file_sha256 in seen_sha256:
                if blob_sha:
                    seen_blob_shas.add(blob_sha)
                continue

            info = inspect_pdf_bytes(pdf_bytes, min_pages=args.min_pages)
            if not info:
                if blob_sha:
                    seen_blob_shas.add(blob_sha)
                continue

            # Prioritize TDTU or reports with student IDs or reference sections
            is_tdtu = True
            idx = max((item["id"] for item in collected), default=0) + 1
            fname = safe_filename(idx, full_name, path, is_tdtu)
            out_path = out_dir / fname
            out_path.write_bytes(pdf_bytes)

            seen_sha256.add(file_sha256)
            if blob_sha:
                seen_blob_shas.add(blob_sha)
            taken_from_repo += 1

            owner = full_name.split("/")[0]
            if is_tdtu:
                discovered_tdtu_owners.add(owner)

            record = {
                "id": idx,
                "filename": fname,
                "repo": full_name,
                "branch": branch,
                "repo_path": path,
                "size_kb": len(pdf_bytes) // 1024,
                "num_pages": info["num_pages"],
                "is_tdtu": is_tdtu,
                "student_ids": info["student_ids"],
                "has_references": info["has_references"],
                "preview": info["preview"],
                "sha256": file_sha256,
                "blob_sha": blob_sha,
                "raw_url": f"{RAW_GITHUB}/{full_name}/{branch}/{path}",
            }
            collected.append(record)
            tag = "TDTU" if is_tdtu else "UNI "
            ref_tag = "+Refs" if info["has_references"] else "     "
            print(
                f"[{len(collected):03d}/{args.n:03d}] [{tag}] [{ref_tag}] "
                f"{fname} ({info['num_pages']}p, {record['size_kb']}KB)"
            )
            manifest_path.write_text(
                json.dumps(collected, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    checked_owners: set[str] = set()

    # Build dynamic query list starting with discovered 8-char TDTU student IDs
    discovered_sids = sorted({sid for item in collected for sid in item.get("student_ids", [])})
    dynamic_queries = discovered_sids + [q for q in SEARCH_QUERIES if q not in discovered_sids]

    for query in dynamic_queries:
        if len(collected) >= args.n:
            break
        print(f"\n=== Searching GitHub repositories: '{query}' ===")
        for page in (1, 2):
            if len(collected) >= args.n:
                break
            data = api_get(
                session,
                f"{GITHUB_API}/search/repositories",
                params={"q": query, "per_page": 50, "page": page},
            )
            if not isinstance(data, dict):
                break
            items = data.get("items", [])
            if not items:
                break
            for repo_obj in items:
                if len(collected) >= args.n:
                    break
                process_repo(repo_obj)

            # Expand discovered TDTU students' other public repositories!
            new_owners = list(discovered_tdtu_owners - checked_owners)
            for owner in new_owners:
                if len(collected) >= args.n:
                    break
                checked_owners.add(owner)
                user_repos = api_get(
                    session,
                    f"{GITHUB_API}/users/{owner}/repos",
                    params={"per_page": 50, "type": "owner", "sort": "updated"},
                )
                if isinstance(user_repos, list):
                    for urepo in user_repos:
                        if len(collected) >= args.n:
                            break
                        process_repo(urepo)

            if len(items) < 50:
                break
            time.sleep(1.5)

    tdtu_count = sum(1 for r in collected if r["is_tdtu"])
    ref_count = sum(1 for r in collected if r["has_references"])
    print("\n" + "=" * 65)
    print(f"Done! Collected {len(collected)} PDF reports in: {out_dir}")
    print(f"  - TDTU reports: {tdtu_count}/{len(collected)}")
    print(f"  - With References/Bibliography section: {ref_count}/{len(collected)}")
    print(f"  - Manifest saved to: {manifest_path}")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
