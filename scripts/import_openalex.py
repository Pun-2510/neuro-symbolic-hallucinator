#!/usr/bin/env python3
"""
Import papers from OpenAlex to local database.
Usage:
    export OPENALEX_API_KEY="your-key"  # Set in environment
    python scripts/import_openalex.py --field cs --limit 10000
"""

import argparse
import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import requests


def get_openalex_api_key() -> str | None:
    """Get API key from environment variable."""
    return os.environ.get("OPENALEX_API_KEY")


def search_papers(query: str, field: str = None, limit: int = 100, offset: int = 0) -> list[dict]:
    """Search papers on OpenAlex."""
    api_key = get_openalex_api_key()

    base_url = "https://api.openalex.org/works"

    params = {
        "search": query,
        "per-page": min(limit, 200),  # Max 200 per request
        "mailto": "your-email@example.com",  # Required by OpenAlex
        "select": "id,title,authorships,publication_year,doi,primary_location,concepts,abstract_inverted_index",
    }

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if offset:
        params["offset"] = offset

    if field:
        # Filter by domain
        field_map = {
            "cs": "C41008148",  # Machine Learning
            "ai": "C39432304",  # Artificial Intelligence
            "nlp": "C185592680",  # Computational Linguistics
        }
        if field.lower() in field_map:
            params["filter"] = f"concepts.id:{field_map[field.lower()]}"

    response = requests.get(base_url, params=params, headers=headers, timeout=30)

    if response.status_code == 429:
        print("Rate limited. Waiting 60 seconds...")
        time.sleep(60)
        return search_papers(query, field, limit, offset)

    response.raise_for_status()
    return response.json().get("results", [])


def paper_to_dict(work: dict) -> dict:
    """Convert OpenAlex work to paper dict."""
    # Extract authors
    authors = []
    for authorship in work.get("authorships", []):
        author = authorship.get("author", {})
        if author:
            authors.append(author.get("display_name", ""))

    # Extract DOI
    doi = work.get("doi", "").replace("https://doi.org/", "")

    # Extract venue
    venue = ""
    primary_location = work.get("primary_location", {})
    if primary_location:
        source = primary_location.get("source", {})
        if source:
            venue = source.get("display_name", "")

    # Extract concepts
    concepts = []
    for concept in work.get("concepts", []):
        if concept.get("score", 0) > 0.3:
            concepts.append(concept.get("display_name", ""))

    return {
        "doi": doi or None,
        "arxiv_id": None,
        "title": work.get("title", ""),
        "authors": json.dumps(authors),
        "year": work.get("publication_year"),
        "venue": venue,
        "abstract": None,  # Too large to store
        "categories": json.dumps(concepts),
        "external_ids": json.dumps({"openalex": work.get("id", "").replace("https://openalex.org/", "")}),
        "source": "openalex",
        "created_at": datetime.now().isoformat(),
    }


def insert_paper(conn: sqlite3.Connection, paper: dict) -> int | None:
    """Insert paper into database."""
    try:
        cursor = conn.execute(
            """
            INSERT INTO papers (doi, arxiv_id, title, authors, year, venue,
                               abstract, categories, external_ids, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doi) DO UPDATE SET
                title = excluded.title,
                authors = excluded.authors,
                year = excluded.year,
                venue = excluded.venue,
                categories = excluded.categories,
                source = excluded.source,
                created_at = excluded.created_at
            """,
            (
                paper["doi"],
                paper["arxiv_id"],
                paper["title"],
                paper["authors"],
                paper["year"],
                paper["venue"],
                paper["abstract"],
                paper["categories"],
                paper["external_ids"],
                paper["source"],
                paper["created_at"],
            ),
        )
        return cursor.lastrowid
    except Exception as e:
        print(f"Error inserting paper: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Import papers from OpenAlex")
    parser.add_argument("--query", "-q", default="machine learning", help="Search query")
    parser.add_argument("--field", "-f", choices=["cs", "ai", "nlp", "all"], default="cs",
                        help="Field filter")
    parser.add_argument("--limit", "-l", type=int, default=1000, help="Number of papers to import")
    parser.add_argument("--db", "-d", default="data/local_papers.db", help="Database path")
    parser.add_argument("--batch-size", "-b", type=int, default=100, help="Batch size for API calls")

    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return

    # Check API key
    api_key = get_openalex_api_key()
    if api_key:
        print(f"Using API key: {api_key[:8]}...")
    else:
        print("WARNING: No API key set. Using free tier (rate limited)")

    conn = sqlite3.connect(db_path)
    total_imported = 0
    offset = 0

    print(f"Importing papers: query='{args.query}', field={args.field}, limit={args.limit}")

    while total_imported < args.limit:
        batch_size = min(args.batch_size, args.limit - total_imported)

        try:
            print(f"Fetching batch: offset={offset}, size={batch_size}...")
            works = search_papers(args.query, args.field, batch_size, offset)

            if not works:
                print("No more results")
                break

            for work in works:
                paper = paper_to_dict(work)
                if paper["doi"]:  # Only insert papers with DOI
                    insert_paper(conn, paper)
                    total_imported += 1

            conn.commit()
            print(f"Imported: {total_imported}/{args.limit}")

            offset += len(works)

            # Rate limiting
            time.sleep(0.1)  # 10 requests per second

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            time.sleep(5)  # Wait before retry

    conn.close()
    print(f"Done! Total imported: {total_imported}")


if __name__ == "__main__":
    main()
