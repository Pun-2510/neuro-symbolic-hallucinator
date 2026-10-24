# CLAUDE.md — CITRA (`SourceLogic`) · Essay Integrity Checker

## Purpose

Engineering reference and architectural guide for AI coding assistants and contributors working on **CITRA (`SourceLogic` — Essay Integrity Checker)**.

## Project Overview

**CITRA (`SourceLogic`)** is an explainable **Neuro-Symbolic Citation & Source Integrity Verification Platform** for academic manuscripts, theses, and research papers.

- **Version:** v2.0 (Phase 5 Complete — 2026-10-24)
- **Unit & Integration Tests:** `1,251 passed, 0 failed`
- **Role-Based Web Workspace:** Student / Researcher (`Workspace`), Teacher (`Classroom`), Administrator (`Control`)
- **Decision-Support Principle:** All outputs are strictly decision-support signals for academic reviewers; the system never automatically concludes academic misconduct.

## Repository Architecture

```text
essay-integrity-checker/
├── src/integrity_checker/
│   ├── api/                  # FastAPI backend routes (auth, essays, report, verdicts, classes, admin)
│   ├── config.py             # Centralized Pydantic settings (YAML + environment variables)
│   ├── database/             # Local SQLite + FTS5 paper knowledge base (127K+ ACL & scholarly papers)
│   ├── db/                   # Application database (SQLAlchemy: Users, Classes, Essays, Citations, Verdicts, AuditLogs)
│   ├── evaluation/           # Metrics, Baselines (B0–B4), 2,500-sample Benchmark & Ablation Runner
│   ├── export/               # Multi-format report exporters (JSON, CSV, PDF, DOCX, Class CSV/ZIP)
│   ├── extraction/           # Hybrid PDF parsing (PyMuPDF + GROBID TEI XML + 11 modular regex styles)
│   ├── linking/              # Bidirectional in-text <-> bibliography CitationLinker (7 link statuses)
│   ├── logic/                # NeuroSymbolicChecker, SymbolicRules, HybridMLScorer, PlattCalibration, CISCalculator
│   ├── matching/             # RapidFuzz lexical, Sentence-BERT semantic, AuthorMatcher, VenueNormalizer
│   ├── models/               # Pydantic & dataclass domain models
│   ├── pipeline/             # IntegrityPipeline end-to-end orchestrator
│   └── retrieval/            # Domain-routed multi-source retrieval + Active HTTP/DOI LinkValidator
├── web/                      # React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui frontend
├── configs/                  # YAML configurations (default, Docker, production)
├── docs/                     # Architectural specs, test plans, research reports & UI screenshots
└── tests/                    # 1,251 unit, integration & E2E tests
```

## Two-Layer Orthogonal Output Model

### Layer 1: Citation <-> Reference Linking (`CitationMappingStatus`)
- `MATCHED` — In-text citation linked to a bibliography entry
- `MISSING_REFERENCE` — In-text citation has no matching bibliography entry
- `UNCITED_REFERENCE` — Bibliography entry is never cited in the body text
- `IN_TEXT_MISMATCH` — Linked but author/year metadata diverges between body and bibliography
- `DUPLICATE_REFERENCE` — Duplicate entries in the reference list
- `AMBIGUOUS_MAPPING` — Multiple candidate references match the same in-text citation
- `STYLE_INCONSISTENT` — Citation formatting deviates from the document's dominant style

### Layer 2: Scholarly Source Verification (`ValidationLabel`)
| Label | Badge Color | Meaning |
| :--- | :--- | :--- |
| `VERIFIED` | Emerald (`#10B981`) | Confirmed across scholarly databases with matching metadata |
| `METADATA_ERROR` | Amber (`#F59E0B`) | Work exists, but cited year, author, venue, or title has discrepancies |
| `SUSPECTED_HALLUCINATION` | Red (`#EF4444`) | Fabricated DOI/URL, non-existent work across all scholarly indices, or severe content mismatch |
| `UNRESOLVED` | Slate (`#64748B`) | Insufficient evidence to verify or refute (abstention zone) |
| `RESOURCE` | Violet (`#8B5CF6`) | Non-article web/API documentation, software repositories, or legal statutes |

## Smart Multi-Source Retrieval Tiering

`RetrievalOrchestrator` routes citations by domain signals and identifier availability:
1. **Tier 0 (Instant Local):** Known Seminal Papers Whitelist + SQLite FTS5 Local Database (`data/local_papers.db`)
2. **Tier 1 (Primary Scholarly APIs):**
   - **Crossref REST API** — Exact DOI resolution & bibliographic search
   - **OpenAlex REST API** — Broad scholarly graph & inverted-index abstract reconstruction
   - **DBLP Search API** — Computer Science, AI, ML, NLP venues & CoRR
   - **arXiv Atom API** — Direct arXiv ID & preprint verification
   - **OpenLibrary + Google Books API** — Textbooks, monographs & multi-edition books
   - **Europe PMC REST API** — PubMed/MEDLINE, biomedical, clinical, psychology & life sciences
3. **Tier 2 (Fallback):** **SerpAPI (Google Scholar)** when primary tiers return no high-confidence match
4. **Active Link & DOI Validator (`LinkValidator`):** Asynchronous `HEAD`/`GET` reachability checks for URLs and DOIs (`R-DEAD-LINK`, `R-URL-UNREACHABLE`).

## Common Commands

```bash
# Run full unit test suite (1,251 tests)
.venv/bin/python -m pytest tests/unit/ -q

# Run pipeline on a PDF and output JSON report to reports/<stem>.json
.venv/bin/python -m integrity_checker.pipeline.integrity_pipeline thesis.pdf

# Launch full Docker stack (GROBID :8070 + FastAPI :8000 + React Web :5173)
docker compose up -d --build
```
