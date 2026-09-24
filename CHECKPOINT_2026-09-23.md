# Checkpoint - 2026-09-23

## ✅ Đã hoàn thành

### 1. Remove Disk Cache System
- **Issue**: Disk cache redundant with Local DB (FTS5)
- **Action**: 
  - Deleted `src/integrity_checker/retrieval/cache.py`
  - Deleted `src/integrity_checker/api/routes/cache.py`
  - Removed `CacheConfig` from `config.py`
  - Updated all `used_cache` → `used_local_db` terminology
  - Cleaned `data/cache/*.json` files
- **Impact**: Simplified architecture, faster cold starts

### 2. Add OpenAlex API Key Support
- **Files**: `src/integrity_checker/retrieval/openalex_client.py`
- **Action**: Added `OPENALEX_API_KEY` env variable support
- **Impact**: Higher rate limits (50 req/s vs 10 req/s)

### 3. Fix Crossref Author Parsing
- **File**: `src/integrity_checker/retrieval/crossref_client.py`
- **Issue**: `'str' object has no attribute 'last_name'`
- **Action**: Handle both `Author` objects and plain strings

### 4. Update Rate Limits
- **File**: `configs/config.yaml`
- **Changes**:
  - Crossref: 3 req/s (polite pool)
  - OpenAlex: 50 req/s (with API key)

### 5. Update Contact Email
- **Changes**: `student@tdtu.edu.vn` → `iannwendii@gmail.com`
- **Impact**: Better polite pool access

### 6. Fix Known Papers Static Method
- **File**: `src/integrity_checker/retrieval/retrieval_orchestrator.py`
- **Issue**: `RetrievalOrchestrator.is_known_paper()` not found
- **Action**: Added static method wrapper

## 📊 Test Results (After Cache Removal)

| File | Citations | CIS | Verified | Sources |
|------|-----------|-----|----------|---------|
| 2608.13966v1.pdf | 112 | **97.5** | 107 | crossref+openalex |
| VietDepression | 35 | **100.0** | 35 | local_db (77%) |
| thesis.pdf | 27 | **~100** | 27 | local_db (100%) |
| Scenario A | 12 | varies | 9 | known_papers |
| Scenario B | 10 | varies | 5 | local_db |

## 🔧 Current Architecture

```
PDF → GROBID/PyMuPDF → Citation Extractor → Local DB (FTS5)
                                              ↓
                              Crossref + OpenAlex + Semantic Scholar
                                              ↓
                                    Neuro-Symbolic Rules → CIS
```

## 📋 Còn cần làm cho MVP

### High Priority
- [ ] Real GROBID Docker integration
- [ ] Error analysis on unresolved citations
- [ ] Dataset annotation (ground truth)

### Medium Priority
- [ ] Implement baselines B0-B5
- [ ] Performance optimization (batch API calls)
- [ ] Error handling improvements

### Low Priority
- [ ] Write thesis Chapter 1-6
- [ ] User manual finalization
- [ ] Video demo

## 🔑 Key Files Changed

```
Modified:
  - src/integrity_checker/config.py
  - src/integrity_checker/retrieval/crossref_client.py
  - src/integrity_checker/retrieval/openalex_client.py
  - src/integrity_checker/retrieval/retrieval_orchestrator.py
  - src/integrity_checker/pipeline/integrity_pipeline.py
  - src/integrity_checker/models/validation.py
  - src/integrity_checker/logic/rules.py
  - src/integrity_checker/logic/neuro_symbolic_checker.py
  - src/integrity_checker/api/main.py
  - configs/config.yaml

Deleted:
  - src/integrity_checker/retrieval/cache.py
  - src/integrity_checker/api/routes/cache.py
```
