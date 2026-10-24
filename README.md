<div align="center">

# CITRA — Verify Every Citation. Trace Every Source.

**Explainable Neuro-Symbolic Citation & Source Integrity Verification Platform · GROBID TEI-XML · Federated Scholarly Retrieval · Hybrid ML Calibration**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=0B0B0A)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![GROBID](https://img.shields.io/badge/GROBID-0.8.0_TEI--XML-E34F26?style=for-the-badge)](https://github.com/kermitt2/grobid)
[![Sentence-BERT](https://img.shields.io/badge/SBERT-MiniLM--L6--v2-FF6F00?style=for-the-badge)](https://sbert.net)
[![SQLite FTS5](https://img.shields.io/badge/ACL_Anthology-127K+_Papers_FTS5-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://aclanthology.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Pytest](https://img.shields.io/badge/Unit_Tests-1%2C251_Passed-0A0A0A?style=for-the-badge&logo=pytest&logoColor=00E676)](./tests/unit)

*An editorial-grade academic citation debugger and thesis integrity verification workspace engineered for researchers, instructors, and university committees — combining structural PDF parsing, smart domain-aware retrieval across 8 scholarly databases, and transparent 5-stage Neuro-Symbolic decision traces.*

[Visual Demo](#-visual-demo--ui-walkthrough) · [Feature Matrix](#-complete-feature-matrix) · [Neuro-Symbolic Architecture](#-neuro-symbolic-architecture--cis-scoring) · [Quick Start](#-quick-start--deployment) · [Demo Credentials](#-default-demo-credentials) · [API & Docs](#-api-reference-overview)

</div>

---

![CITRA Landing Hero — Light Mode](./docs/screenshots/01-landing-light.png)

---

## 📖 Table of Contents

1. [Overview & Brand Philosophy](#-overview--brand-philosophy)
2. [Visual Demo & UI Walkthrough](#-visual-demo--ui-walkthrough)
3. [Complete Feature Matrix](#-complete-feature-matrix)
4. [Neuro-Symbolic Architecture & CIS Scoring](#-neuro-symbolic-architecture--cis-scoring)
5. [Real-World Evaluation & Benchmark Metrics](#-real-world-evaluation--benchmark-metrics)
6. [Tech Stack](#-tech-stack)
7. [Repository Structure](#-repository-structure)
8. [Quick Start & Deployment](#-quick-start--deployment)
9. [Default Demo Credentials](#-default-demo-credentials)
10. [Docker Services & Port Matrix](#-docker-services--port-matrix)
11. [API Reference & Automated Testing](#-api-reference--automated-testing)
12. [Documentation Index & Contributors](#-documentation-index--contributors)

---

## 🏛️ Overview & Brand Philosophy

**CITRA** (*Essay Integrity Checker v2.0*) is a full-stack academic citation verification and bibliographic debugging platform developed as a Capstone Graduation Thesis (*Đồ án Tốt nghiệp CNTT*) at **Ton Duc Thang University (TDTU)**.

Large Language Models (LLMs) frequently hallucinate plausible-sounding references, conflate author lists, or fabricate publication years (`METADATA_ERROR` / `HALLUCINATION`). Meanwhile, traditional similarity checkers (e.g., Turnitin) measure text overlap rather than verifying whether cited references actually exist in canonical scholarly registries or whether in-text citations map cleanly to the bibliography.

### Design Philosophy — *SourceLogic Scholarly (Explainable Precision Minimal)*
- **Two-Layer Separation of Concerns**: Strictly decouples **Layer 1: In-Text Citation Mapping** (`MATCHED`, `AMBIGUOUS`, `MISSING_IN_BIBLIOGRAPHY`) from **Layer 2: Reference Entry Validation** (`VERIFIED`, `METADATA_ERROR`, `UNVERIFIED_EXTERNAL`, `HALLUCINATION`), eliminating double-counting when a reference is cited multiple times.
- **No Black-Box Verdicts**: Every reference entry exposes a **5-Stage Neuro-Symbolic Logic Trace** (`Stage 1: Structural Parse` → `Stage 2: Multi-Source Retrieval` → `Stage 3: 8D Feature Vector` → `Stage 4: Symbolic & ML Scorer` → `Stage 5: Calibrated Verdict`), side-by-side canonical vs. cited diffs, and one-click BibTeX/APA fixes.
- **Three Role-Based Portals**:
  1. **Researcher / Student Workspace (`/dashboard`, `/verification/report/:id`)**: Upload single or batch PDF/DOCX manuscripts, inspect citation errors in a split-pane IDE, and export corrected bibliographies.
  2. **Teacher Cohort Classroom (`/teacher/classes`, `/teacher/pending`)**: Manage thesis cohorts via join codes, review flagged submissions, and override contested AI verdicts with human-in-the-loop audit notes.
  3. **Admin Platform Control (`/admin/system`, `/admin/users`, `/admin/audit-logs`)**: Monitor external API latencies, verdict telemetry distributions, user role assignments, and immutable system audit trails.
- **Decision-Support Compliance**: All reports and exports include a mandatory bilingual compliance notice affirming that CITRA is a decision-support tool and final academic evaluation rests with qualified faculty.

---

## 📸 Visual Demo & UI Walkthrough

> All screenshots below are captured directly from the live running platform (`1440×900 @ 2x Retina`) inspecting real undergraduate and research manuscripts.

### 1. Editorial Landing Page — Adaptive Light & Dark Mode
High-contrast academic typography (*Newsreader* serif display, *Plus Jakarta Sans* UI, and *JetBrains Mono* telemetry) with instant theme switching.

| Light Mode (`SourceLogic Ivory`) | Dark Mode (`SourceLogic Obsidian`) |
| :---: | :---: |
| ![Landing Light Mode](./docs/screenshots/01-landing-light.png) | ![Landing Dark Mode](./docs/screenshots/02-landing-dark.png) |

---

### 2. Verification Workspace & Multi-Manuscript Batch Queue
Upload individual PDF/DOCX manuscripts with customizable citation styles (Auto-detect, IEEE, APA 7th, Vancouver, Harvard, TDTU) or process entire thesis cohorts in parallel with real-time Server-Sent Events (SSE) progress streaming.

| Workspace Dashboard (`/dashboard`) | Batch Verification Queue (`/batch-upload`) |
| :---: | :---: |
| ![Workspace Dashboard](./docs/screenshots/03-dashboard-light.png) | ![Batch Upload Queue](./docs/screenshots/04-batch-upload.png) |

---

### 3. Citation Debugger IDE — Hallucination Detection & Side-by-Side Metadata Diff
The split-pane **Reference Inspector** highlights exact discrepancies between the manuscript's bibliography and canonical scholarly records from Crossref, Semantic Scholar, OpenAlex, ArXiv, and ACL Anthology.

| Hallucinated / Fabricated Reference (`HALLUCINATION`) | Venue / Year / Author Mismatch (`METADATA_ERROR`) |
| :---: | :---: |
| ![Hallucination Inspector](./docs/screenshots/05-verification-report.png) | ![Metadata Diff Inspector](./docs/screenshots/06-reference-inspector.png) |

---

### 4. 5-Stage Neuro-Symbolic Logic Trace & Inline Document Context
Inspect every intermediate signal in the 5-stage pipeline (`S_title`, `S_author`, `S_year`, `S_venue`, `S_doi`, `HybridMLScorer` probability, and symbolic rule overrides) alongside the exact paragraph context where each citation appears in the manuscript.

| 5-Stage Neuro-Symbolic Logic Trace (`/trace`) | Split-Pane Document Context Stream (`/document`) |
| :---: | :---: |
| ![Neuro-Symbolic Logic Trace](./docs/screenshots/07-logic-trace.png) | ![Document Context Inspector](./docs/screenshots/09-document-inspector.png) |

---

### 5. Bidirectional Consistency Matrix & Teacher Cohort Classroom
Detect orphaned bibliography entries (`uncited_references`) and dangling in-text citations (`MISSING_IN_BIBLIOGRAPHY`), or manage entire thesis defense classes from the instructor portal.

| Citation ↔ Reference Consistency (`/consistency`) | Teacher Cohort Classroom (`/teacher/classes/1`) |
| :---: | :---: |
| ![Consistency Check](./docs/screenshots/08-consistency-check.png) | ![Teacher Classroom](./docs/screenshots/10-teacher-classroom.png) |

---

### 6. Admin Platform Telemetry & Verdict Distribution
Real-time health checks across GROBID, SQLite FTS5, and external scholarly APIs alongside system-wide verdict distributions and audit trails.

<div align="center">

![Admin System Health](./docs/screenshots/11-admin-system-health.png)

</div>

---

## ✨ Complete Feature Matrix

| Domain | Capability | Implementation Details |
| :--- | :--- | :--- |
| **Document Parsing** | **Multi-Modal PDF & DOCX Extraction** | **GROBID 0.8.0 TEI-XML** deep structural parsing with automatic **PyMuPDF (`fitz`)** + `python-docx` fallback; supports Vietnamese & English section headers (`Tài liệu tham khảo`, `References`, `Bibliography`). |
| **Citation Formats** | **11 Citation Styles + Vietnamese Legal Docs** | Auto-detects **IEEE** (`[1]`, `[1]-[3]`), **APA** (`(Smith et al., 2020)`), **Vancouver**, **Harvard**, **MLA**, **Chicago**, **ACM**, **Nature**, **Springer**, **Footnotes**, and **Vietnamese Legal Documents** (`Luật số`, `Nghị định`, `Thông tư` per TDTU standards). |
| **Smart Retrieval** | **Domain-Aware 8-Source Federated Search** | Local **ACL Anthology SQLite FTS5** (`127,498+` papers) + **Crossref**, **OpenAlex**, **Semantic Scholar**, **ArXiv**, **PubMed**, **DBLP**, and **Docear** with dynamic domain routing (`general`, `cs_ai`, `biomedical`), global concurrency semaphores, and SQLite response caching. |
| **Neuro-Symbolic Verification** | **8D Feature Vector + Hybrid ML + Symbolic Rules** | Computes 8 normalized similarity features (`title`, `author`, `year`, `venue`, `doi`, `arxiv`, `shingle`, `number_jaccard`), feeds a **Random Forest + Platt Scaling** scorer, and applies deterministic symbolic guardrails. |
| **Scoring Engine** | **5-Component Citation Integrity Score (`CIS`)** | Weighted composite score (`0–100`) combining Reference Validity (`35%`), Citation Mapping (`25%`), Metadata Accuracy (`15%`), Format Compliance (`15%`), and Bibliography Hygiene (`10%`) with critical failure caps. |
| **Interactive IDE** | **4 Specialized Inspection Views** | **Bibliography Table** (side-by-side diff), **Logic Trace** (5-stage Neuro-Symbolic pipeline), **Consistency Matrix** (dangling & orphan detection), and **Document Context** (inline sentence highlights + SBERT semantic relevance). |
| **Role-Based Portals** | **User, Teacher, and Admin Workflows** | JWT authentication, **Batch SSE Upload**, **Classroom Management** (`join_code`, cohort analytics), **Teacher Verdict Overrides**, and **Admin System Telemetry & Audit Logs**. |
| **Export & Reporting** | **Multi-Format Compliance Exports** | One-click export of full verification reports to **JSON**, **CSV**, **PDF**, and **DOCX** (`src/integrity_checker/reporting/exporter.py`). |

---

## 🧠 Neuro-Symbolic Architecture & CIS Scoring

### End-to-End Verification Pipeline

```
Manuscript (PDF / DOCX)
   │
   ├─► 1. Structural Extraction (GROBID TEI-XML + PyMuPDF / DOCX Fallback)
   │      ├── Extract raw_references[] (Deduped & Normalized Bibliography)
   │      ├── Extract raw_citations[] (In-Text Markers + Surrounding Context Paragraphs)
   │      └── Detect Citation Style Profile (IEEE / APA / Vancouver / TDTU Legal)
   │
   ├─► 2. Layer 1 — In-Text Citation ↔ Bibliography Linker (CitationLinker)
   │      ├── Maps every in-text marker [k] or (Author, Year) to ReferenceEntry
   │      ├── Assigns CitationMappingStatus: MATCHED | AMBIGUOUS | MISSING_IN_BIBLIOGRAPHY
   │      └── Computes Uncited / Orphan Reference Set (uncited_references[])
   │
   ├─► 3. Layer 2 — Smart Multi-Source Candidate Retrieval (ReferenceVerifier)
   │      ├── Pre-Screening: Web/URL Resource ([Online], GitHub, Docs) & VN Legal Classifier
   │      ├── Tier 0: Exact Identifier Lookup (DOI via Crossref/OpenAlex, ArXiv ID via ArXiv API)
   │      ├── Tier 1: Domain-Prioritized Primary Search (ACL FTS5 + Crossref + OpenAlex / PubMed / DBLP)
   │      └── Tier 2: Fallback Deep Search (Semantic Scholar, ArXiv, Docear) with Early-Exit Threshold (≥0.90)
   │
   ├─► 4. Neuro-Symbolic Candidate Matching & Calibration (CandidateMatcher)
   │      ├── Neural / Fuzzy 8D Features: SBERT Cosine + Token RapidFuzz + shingle_sim + number_jaccard
   │      ├── HybridMLScorer: Random Forest Probability + Platt Scaling Calibration
   │      └── Symbolic Guardrails: Preprint-to-Published Year Relaxation, Cross-Work Collision Veto
   │
   └─► 5. Validation Verdict & Composite CIS Calculation (CISCalculator)
          ├── Assigns ValidationLabel: VERIFIED | METADATA_ERROR | UNVERIFIED_EXTERNAL | HALLUCINATION
          └── Generates 5-Component Citation Integrity Score (0–100) + Actionable Recommendations
```

### Two-Layer Output Taxonomy

#### Layer 1: In-Text Citation Mapping (`CitationMappingStatus`)
| Status | Meaning | Impact on CIS |
| :--- | :--- | :--- |
| `MATCHED` | In-text citation marker resolves uniquely to a bibliography entry (`[k]` or `(Author, Year)`). | Full credit in `S_mapping` (`25%`). |
| `AMBIGUOUS` | Multiple bibliography entries share identical `(Author, Year)` keys without disambiguating `a/b` suffixes. | Partial credit (`0.5×`) + remediation prompt. |
| `MISSING_IN_BIBLIOGRAPHY` | Dangling in-text citation whose target key does not exist in the reference list. | Penalizes `S_mapping` + triggers critical alert. |

#### Layer 2: Bibliography Reference Validation (`ValidationLabel`)
| Verdict Label | Decision Criteria | Semantic Meaning |
| :--- | :--- | :--- |
| `VERIFIED` | Exact title/author/year/venue match (`overall_score ≥ 0.85`) or verified Preprint → Published version (`year_diff ≤ 2`, `title_sim ≥ 0.92`, `author_sim ≥ 0.85`). | Authentic scholarly publication with accurate bibliographic metadata. |
| `METADATA_ERROR` | Real paper found (`title_sim ≥ 0.85`), but the citation contains wrong publication year, missing/swapped authors, or mismatched venue/DOI. | Source exists, but bibliographic fields require correction (side-by-side diff provided). |
| `UNVERIFIED_EXTERNAL` | Non-scholarly web URL (`[Online]`, GitHub, WHO/CDC reports, documentation) or Vietnamese Legal Document (`Luật`, `Nghị định`). | Valid non-indexed external resource; excluded from hallucination penalty. |
| `HALLUCINATION` | No scholarly record matches across all 8 databases (`best_sim < 0.70`), or severe cross-work chimeric fabrication (`title` from Paper A + `authors` from Paper B). | High-risk fabricated or non-existent reference. |

### 5-Component Citation Integrity Score (`CIS`) Formula

$$\text{CIS} = 100 \times \left( 0.35 \cdot S_{\text{validity}} + 0.25 \cdot S_{\text{mapping}} + 0.15 \cdot S_{\text{metadata}} + 0.15 \cdot S_{\text{format}} + 0.10 \cdot S_{\text{hygiene}} \right)$$

- **Critical Failure Caps**:
  - If fabricated references exceed **30%** of the bibliography (`hallucination_rate > 0.30`), `CIS` is hard-capped at **`45.0`** (`CRITICAL`).
  - If bibliography extraction fails completely while in-text citations exist, `CIS` is capped at **`25.0`**.

---

## 📊 Real-World Evaluation & Benchmark Metrics

### Live Verification Results Across Real Manuscripts (`reports/*.json`)

All 5 benchmark PDFs in the repository root were verified end-to-end with live multi-source scholarly retrieval (`use_report_cache=False`):

| Manuscript | Citation Style | In-Text Citations | Bibliography Entries | Verified | Metadata Error | Unverified External | Hallucination | **CIS Score** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`523H0054_NguyenBaoMinh_523H0157_DinhDucMinh.pdf`** | IEEE | 10 (`100%` matched) | 10 | **10** | 0 | 0 | 0 | **100.00 / 100** (`EXCELLENT`) |
| **`TranThanhPhuoc_523H0002_523H0054.pdf`** | IEEE | 14 (`100%` matched) | 15 (1 uncited) | **14** | 0 | 1 (`URL`) | 0 | **99.30 / 100** (`EXCELLENT`) |
| **`VietDepression_Research_Article.pdf`** | IEEE | 28 (`100%` matched) | 28 | **28** | 0 | 0 | 0 | **98.93 / 100** (`EXCELLENT`) |
| **`VietDepression_for_Detecting_Depression...pdf`** | APA | 66 (`97%` matched) | 28 | **28** | 0 | 0 | 0 | **96.21 / 100** (`EXCELLENT`) |
| **`thesis.pdf`** *(Full Graduation Thesis)* | IEEE | 33 (`100%` matched) | 25 | **18** | **1** (`[24]`) | **5** (`Web/Docs`) | **1** (`[3]`) | **87.05 / 100** (`GOOD`) |

> **Deep-Dive Case Study on `thesis.pdf`**:
> - **`[24] Chawla, N. V. et al. (2008). SMOTE...` → `METADATA_ERROR`**: Canonical paper was published in **2002** in *Journal of Artificial Intelligence Research (JAIR)*, whereas the manuscript cited year **2008**.
> - **`[3] Stanley, K. O. et al. (2024). Real-Time Strategy Game AI...` → `HALLUCINATION`**: No paper with this title/author/year combination exists in any scholarly database.
> - **`[9], [10], [12], [17], [18]` → `UNVERIFIED_EXTERNAL`**: Documentation and software web resources (`OpenRA Wiki`, `ZeroTier Docs`, `Setupad Blog`) accurately separated from scholarly hallucinations.

---

## 🛠️ Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend (`web/`)** | React 18.3, TypeScript 5.8, Vite 6, Tailwind CSS 3.4, Radix UI Primitives, Lucide Icons, Newsreader + Plus Jakarta Sans + JetBrains Mono |
| **Backend API (`src/integrity_checker/api/`)** | Python 3.11+, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.0, JWT Auth (`python-jose`, `passlib[bcrypt]`), Server-Sent Events (SSE) |
| **Document Parsing & NLP** | GROBID 0.8.0 (TEI-XML REST Service), PyMuPDF (`fitz`), `python-docx`, `RapidFuzz`, `ftfy`, `langdetect` |
| **Neuro-Symbolic & ML Engine** | `sentence-transformers` (`all-MiniLM-L6-v2`), `scikit-learn` (Random Forest + Platt Scaling `CalibratedClassifierCV`), 8D Feature Engineering |
| **Scholarly Knowledge & APIs** | SQLite FTS5 (`127,498+` ACL Anthology papers), Crossref, OpenAlex, Semantic Scholar, ArXiv, PubMed (NCBI Entrez), DBLP, Docear |
| **Testing & DevOps** | Pytest (`1,251` unit tests), Playwright E2E, Docker & Docker Compose |

---

## 📂 Repository Structure

```text
essay-integrity-checker/
├── docker-compose.yml                  # Orchestrates web (:5173), api (:8000), and grobid (:8070)
├── Dockerfile                          # Python 3.11 + FastAPI + Sentence-BERT backend image
├── pyproject.toml                      # Python package dependencies & CLI entrypoint (`essay-check`)
├── CLAUDE.md                           # AI / Developer architectural quick-reference
├── README.md                           # Project documentation (this file)
├── src/
│   └── integrity_checker/
│       ├── api/                        # FastAPI routers (upload, batch SSE, auth, classes, admin, exports)
│       ├── clients/                    # Async HTTP clients (Crossref, OpenAlex, S2, ArXiv, PubMed, DBLP, Docear, GROBID)
│       ├── db/                         # SQLAlchemy ORM models (User, Essay, Class, AuditLog) & SQLite session
│       ├── ingestion/                  # GROBID TEI-XML parser, PyMuPDF & DOCX structural extractors
│       ├── knowledge/                  # Local ACL Anthology SQLite FTS5 builder & query client
│       ├── models/                     # Core dataclasses (ReferenceEntry, CitationUsage, ValidationLabel, CISBreakdown)
│       ├── ml/                         # HybridMLScorer (Random Forest + Platt Calibration) & training pipeline
│       ├── reporting/                  # Multi-format report exporters (JSON, CSV, PDF, DOCX) & CLI formatters
│       ├── scoring/                    # 5-component CIS calculator & critical failure cap logic
│       ├── verification/               # CitationLinker, ReferenceVerifier, CandidateMatcher, ContextChecker, StyleDetector
│       ├── config.py                   # Centralized settings & environment configuration
│       └── pipeline.py                 # Main IntegrityPipeline orchestrator
├── web/                                # React 18 + TypeScript + Tailwind CSS frontend (`CITRA`)
│   ├── src/
│   │   ├── components/                 # Shared UI primitives, Navbar, ThemeToggle, StatusBadges
│   │   ├── pages/                      # Landing, Dashboard, BatchUpload, VerificationReport, LogicTrace,
│   │   │                               # ConsistencyCheck, DocumentInspector, Teacher*, Admin*
│   │   └── services/                   # Typed API client & authentication context
│   └── package.json
├── scripts/                            # Dataset ingest (`ingest_acl.py`), benchmark runners, ML training scripts
├── tests/
│   ├── unit/                           # 1,251 fast isolated unit tests across all modules
│   ├── integration/                    # Full-pipeline integration tests
│   └── evaluation/                     # 2,500-sample benchmark evaluation suite & baseline comparators
├── docs/                               # Deep-dive architecture, roadmap, and TDTU reference standards
│   └── screenshots/                    # High-resolution live UI screenshots
└── reports/                            # Verified JSON audit reports for the 5 benchmark PDFs
```

---

## 🚀 Quick Start & Deployment

### Option 1: Full-Stack Docker Compose (Recommended)

Launch the entire 3-service stack (**React Web UI**, **FastAPI Backend**, and **GROBID 0.8.0 Server**) with a single command:

```bash
# 1. Clone the repository
git clone https://github.com/iannwendy/essay-integrity-checker.git
cd essay-integrity-checker

# 2. Copy environment configuration
cp .env.example .env

# 3. Build and start all services
docker compose up -d --build
```

Once running:
- **CITRA Web Application**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **GROBID TEI-XML Health Check**: [http://localhost:8070/api/isalive](http://localhost:8070/api/isalive)

---

### Option 2: Local Development (Python `.venv` + Vite Dev Server)

#### 1. Start GROBID (via Docker) & Backend API
```bash
# Start GROBID container on port 8070
docker compose up -d grobid

# Create virtual environment and install package in editable mode
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Launch FastAPI server on port 8000
uvicorn integrity_checker.api.main:app --reload --port 8000
```

#### 2. Start React Frontend (`web/`)
```bash
cd web
npm install
npm run dev
# Open http://localhost:5173
```

---

### Option 3: Command-Line Interface (`essay-check`)

Run verification directly from the terminal on any PDF or DOCX manuscript:

```bash
# Verify a single PDF and export structured JSON report
essay-check thesis.pdf --output reports/thesis_report.json

# Force fresh verification (bypass report cache) with verbose logging
essay-check TranThanhPhuoc_523H0002_523H0054.pdf --no-cache -v
```

---

### Option 4: Building the Local ACL Anthology FTS5 Knowledge Base (Optional)

If you have the ACL Anthology Parquet dataset (`acl-publication-info.74k.v2.parquet`), build the local `127K+` paper SQLite FTS5 index for sub-millisecond offline NLP/CS verification:

```bash
python scripts/ingest_acl.py \
  --parquet data/acl-publication-info.74k.v2.parquet \
  --db data/knowledge.db
```

---

## 🔐 Default Demo Credentials

The database automatically seeds three role-based accounts on startup (`src/integrity_checker/db/session.py`) so you can immediately explore every portal:

| Role | Email | Password | Portal Access |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@example.com` | `admin123` | Full access to **Workspace**, **Teacher Classroom**, and **Admin Control** (`/admin/system`, `/admin/users`, `/admin/audit-logs`) |
| **Teacher / Advisor** | `teacher@example.com` | `teacher123` | **Workspace**, **Batch Upload**, **My Classes** (`/teacher/classes`), and **Pending Reviews** (`/teacher/pending`) |
| **Student / Researcher** | `user@example.com` | `user123` | Standard **Verification Workspace** (`/dashboard`), **Batch Upload**, and **Report History** (`/history`) |

---

## 🐳 Docker Services & Port Matrix

| Container Name | Service | Image / Build | Host Port | Internal Port | Purpose |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `integrity-web` | `web` | `node:20-alpine` (Vite React TS) | `5173` | `5173` | Interactive CITRA Frontend IDE & Role Portals |
| `integrity-api` | `api` | `Dockerfile` (Python 3.11 + FastAPI) | `8000` | `8000` | Neuro-Symbolic Pipeline, REST/SSE API, SQLite ORM & FTS5 |
| `essay-check-grobid` | `grobid` | `lfoppiano/grobid:0.8.0` | `8070` | `8070` | Deep CRF/BiLSTM Structural PDF-to-TEI-XML Parsing |

---

## 🔌 API Reference & Automated Testing

### Key REST & SSE Endpoints (`/api/*`)

| Method | Endpoint | Description |
| :---: | :--- | :--- |
| `POST` | `/api/auth/token` | Authenticate user and issue JWT Bearer token |
| `POST` | `/api/verify` | Upload & verify a single PDF/DOCX manuscript (`style`, `class_id`) |
| `POST` | `/api/verify/batch/stream` | Multi-manuscript batch verification with real-time **SSE progress events** |
| `GET` | `/api/history` | List verified manuscripts for the current user |
| `GET` | `/api/essays/{id}` | Retrieve full two-layer verification report (`ReferenceEntry[]`, `CitationUsage[]`, `CISBreakdown`) |
| `GET` | `/api/essays/{id}/export?format=pdf\|docx\|csv\|json` | Download formatted compliance audit report |
| `POST` | `/api/teacher/classes` | Create a thesis cohort classroom with auto-generated `join_code` |
| `POST` | `/api/teacher/essays/{id}/override` | Teacher human-in-the-loop override for a reference validation label |
| `GET` | `/api/admin/system-health` | Live telemetry across GROBID, SQLite FTS5, and external scholarly APIs |

### Running the Automated Test Suite

The repository includes **1,251 fast, isolated unit tests** covering extraction, style detection, 8-source smart retrieval, 8D feature matching, symbolic rules, CIS calculation, and API endpoints:

```bash
# Run the complete unit test suite (1,251 passed)
pytest tests/unit/ -q

# Run specific verification module tests
pytest tests/unit/test_reference_verifier.py tests/unit/test_candidate_matcher.py -v

# Run frontend TypeScript & production build check
cd web && npm run build
```

---

## 📚 Documentation Index & Contributors

### Architectural & Engineering Documentation (`docs/`)
- [**`CLAUDE.md`**](./CLAUDE.md) — Developer & AI Agent quick-reference guide to the v2.0 architecture.
- [**`docs/DEVELOPER_QUICKSTART.md`**](./docs/DEVELOPER_QUICKSTART.md) — Environment setup, configuration variables, and debugging recipes.
- [**`docs/NEURO_SYMBOLIC_ANALYSIS_AND_DESIGN_PHASES.md`**](./docs/NEURO_SYMBOLIC_ANALYSIS_AND_DESIGN_PHASES.md) — Detailed specification of the Two-Layer Data Model, 8D Feature Vector, and Neuro-Symbolic scoring rules.
- [**`docs/THESIS_PIPELINE_ANALYSIS_AND_FIX_PLAN.md`**](./docs/THESIS_PIPELINE_ANALYSIS_AND_FIX_PLAN.md) — Root-cause analysis and engineering fixes for real-world thesis verification.
- [**`docs/SOURCELOGIC_CONCEPT.md`**](./docs/SOURCELOGIC_CONCEPT.md) — Design system specification for the *SourceLogic Scholarly* UI.
- [**`docs/ROLES_PLAN.md`**](./docs/ROLES_PLAN.md) — Role-Based Access Control (User / Teacher / Admin) & classroom workflow architecture.
- [**`docs/IMPLEMENTATION_ROADMAP.md`**](./docs/IMPLEMENTATION_ROADMAP.md) — Phased implementation history from v1.0 prototype to v2.0 production platform.
- [**`docs/reference/tai_lieu_tham_khao_TDTU.md`**](./docs/reference/tai_lieu_tham_khao_TDTU.md) — Ton Duc Thang University (TDTU) official citation and bibliography formatting guidelines.

### 👥 Contributors — Capstone Graduation Thesis (ĐATN)
**Faculty of Information Technology — Ton Duc Thang University (TDTU)**

| Full Name | Student ID | Role |
| :--- | :---: | :--- |
| **Nguyễn Bảo Minh** | `523H0054` | Co-Author · Neuro-Symbolic Pipeline, Multi-Source Retrieval & Full-Stack Engineering |
| **Trần Gia Thành** | `523H0096` | Co-Author · Citation Extraction, ML Calibration, Benchmark Evaluation & Frontend IDE |
| **ThS. Võ Thị Kim Anh** | *Advisor (GVHD)* | Thesis Supervisor · Faculty of Information Technology, Ton Duc Thang University |

---

<div align="center">

**CITRA — Academic Source Verification Workspace**  
*Built with precision for scholarly integrity at Ton Duc Thang University (TDTU).*

</div>
