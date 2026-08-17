#!/usr/bin/env python3
"""
Upload gold_dataset_annotation.csv to Google Sheets.

Setup:
    1. Go to https://console.cloud.google.com
    2. Create project → Enable Google Sheets API
    3. Credentials → Service Account → download JSON key
    4. Share the Sheet with the service account email
    5. Run: pip install gspread google-auth
    6. Set GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json
    7. python scripts/collect_dataset/upload_to_sheets.py

Usage:
    GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json \
    python scripts/collect_dataset/upload_to_sheets.py \
        --csv data/gold_dataset_annotation.csv \
        --title "DATN Citation Annotation" \
        --email your-email@gmail.com
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Upload CSV to Google Sheets")
    p.add_argument("--csv", "-i", required=True, help="CSV file to upload")
    p.add_argument("--title", "-t", default="Citation Annotation", help="Sheet title")
    p.add_argument("--share", help="Email to share the sheet with")
    p.add_argument("--credentials", default=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
                   help="Path to service account JSON key")
    p.add_argument("--sheet", "-s", default="Sheet1", help="First sheet name")
    return p.parse_args()


def upload_csv_to_sheet(csv_path: str, title: str, share_email: str | None, creds_path: str) -> str:
    """Upload CSV to Google Sheets, return share URL."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    client = gspread.authorize(creds)

    # Read CSV
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    if not rows:
        print("CSV is empty.")
        sys.exit(1)

    headers = list(rows[0].keys())
    data = [headers]
    for row in rows:
        data.append([row.get(h, "") for h in headers])

    # Create spreadsheet
    print(f"Creating spreadsheet: {title!r}")
    sh = client.create(title)

    # Write to first sheet
    ws = sh.sheet1
    ws.clear()
    ws.update(data, value_input_option="USER_ENTERED")
    print(f"  Wrote {len(data)} rows × {len(headers)} columns")

    # Format headers
    ws.format("1:1", {
        "textFormat": {"bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
        "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
        "horizontalAlignment": "CENTER",
    })
    ws.freeze(rows=1)  # Freeze header row

    # Set column widths for readability
    col_widths = {
        "A": 140,  # citation_id
        "B": 80,   # source_paper
        "C": 320,  # citation_raw
        "D": 140,  # doi
        "E": 200,  # crossref_title
        "F": 180,  # crossref_authors
        "G": 80,   # crossref_year
        "H": 120,  # crossref_venue
        "I": 130,  # ground_truth_label
        "J": 160,  # ground_truth_mapping_status
        "K": 80,   # annotator
        "L": 200,  # notes
    }
    for col_letter, width in col_widths.items():
        try:
            ws.col_state(col_letter, desired_width=width)
        except Exception:
            pass  # Some gspread versions don't support col_state

    # Add data validation for ground_truth_label
    try:
        ws.range("I2:I1000").set_data_validation({
            "conditionValues": ["verified", "suspected_hallucination", "metadata_error", "unresolved"],
            "conditionType": "ONE_OF_LIST",
            "strict": True,
        })
        ws.range("J2:J1000").set_data_validation({
            "conditionValues": [
                "matched", "missing_reference", "uncited_reference",
                "in_text_mismatch", "duplicate_reference",
                "ambiguous_mapping", "style_inconsistent", "unresolved"
            ],
            "conditionType": "ONE_OF_LIST",
            "strict": True,
        })
        print("  Added dropdown validation for label columns")
    except Exception as e:
        print(f"  Dropdown validation skipped: {e}")

    # Share
    if share_email:
        print(f"  Sharing with {share_email}...")
        sh.share(share_email, perm_type="user", role="writer")

    url = sh.url
    print(f"\n✅ Done!")
    print(f"   Sheet URL: {url}")
    if share_email:
        print(f"   Shared with: {share_email}")
    print(f"\n   Sheet ID: {sh.id}")

    return url


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        sys.exit(1)

    if not args.credentials:
        print("Error: --credentials or GOOGLE_APPLICATION_CREDENTIALS required.")
        print("Download service account key from Google Cloud Console:")
        print("  https://console.cloud.google.com → APIs & Services → Credentials")
        print("  → Create Credentials → Service Account → Key → JSON")
        print()
        print("Then run:")
        print(f"  GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json \\")
        print(f"  python {__file__} --csv {csv_path} --title 'Citation Annotation'")
        sys.exit(1)

    url = upload_csv_to_sheet(
        str(csv_path),
        args.title,
        args.share,
        args.credentials,
    )
    print(f"\n📋 Open: {url}")


if __name__ == "__main__":
    main()
