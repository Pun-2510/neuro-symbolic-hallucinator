# Plan: Local Database cho Essay Integrity Checker

## Context
- Giảng viên yêu cầu xây dựng database lưu trữ references đã được chọn lọc
- Mục tiêu: giảm API calls, tăng tốc độ, và tự động mở rộng database
- Phạm vi: toàn bộ ngành nghề (CS, AI, ML, NLP, CV, etc.)

## Database Strategy

### Data Sources
1. **ACL Anthology** (~20MB BibTeX) - NLP/ML papers chất lượng cao
2. **S2ORC** (filtered by categories) - papers từ multiple domains
3. **Auto-sync** - tự thêm papers mới từ API

### Database Schema (SQLite - đơn giản, không cần server)

```sql
-- papers: core table
CREATE TABLE papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doi TEXT UNIQUE,
    arxiv_id TEXT,
    title TEXT NOT NULL,
    authors TEXT,  -- JSON array string
    year INTEGER,
    venue TEXT,
    abstract TEXT,
    categories TEXT,  -- JSON array string
    external_ids TEXT,  -- JSON object
    source TEXT DEFAULT 'imported',  -- 'acl', 's2orc', 'api'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full-text search index
CREATE VIRTUAL TABLE papers_fts USING fts5(title, authors, abstract, content='papers', content_rowid='id');

-- Query log for analytics
CREATE TABLE query_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT NOT NULL,  -- hash of query params
    found INTEGER DEFAULT 0,
    source TEXT,
    paper_id INTEGER REFERENCES papers(id),
    queried_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Implementation Steps

### Step 1: Database Module
- [ ] `src/integrity_checker/database/local_db.py` - SQLite wrapper
- [ ] `src/integrity_checker/database/models.py` - Pydantic models
- [ ] `src/integrity_checker/database/schemas.py` - Table creation

### Step 2: Import Scripts
- [ ] `scripts/import_acl_anthology.py` - Import ACL papers
- [ ] `scripts/import_s2orc.py` - Import S2ORC (with category filter)
- [ ] `scripts/sync_from_api.py` - Sync new papers from APIs

### Step 3: Integration
- [ ] Update `retrieval_orchestrator.py` - Check local DB first
- [ ] Update `config.py` - Add local_db settings
- [ ] Update `config.yaml` - Add local_db config

### Step 4: Testing
- [ ] Test database creation
- [ ] Test import scripts
- [ ] Test full pipeline integration
- [ ] Test with sample PDF

## Files to Modify/Create

### New Files
1. `src/integrity_checker/database/__init__.py`
2. `src/integrity_checker/database/local_db.py`
3. `src/integrity_checker/database/models.py`
4. `src/integrity_checker/database/schemas.py`
5. `scripts/import_acl_anthology.py`
6. `scripts/import_s2orc.py`
7. `scripts/sync_from_api.py`
8. `scripts/build_local_db.py` (orchestrator)

### Modified Files
1. `src/integrity_checker/retrieval/retrieval_orchestrator.py`
2. `src/integrity_checker/config.py`
3. `configs/config.yaml`
4. `src/integrity_checker/__init__.py` (add database exports)

## Verification

1. Chạy database creation test
2. Import sample data từ ACL Anthology
3. Test retrieval với sample PDF
4. Verify không có 429 errors khi data đã có trong DB
