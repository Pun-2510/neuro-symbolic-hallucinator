# Session Summary - Week 9 (2026-09-22 to 2026-09-23)

## Mục tiêu tuần này

Hoàn thiện MVP, tích hợp Local Database với FTS5, remove disk cache.

## ✅ Đã hoàn thành

### 1. Local Database với FTS5
- Thêm `data/local_papers.db` với 83,541 ACL papers
- FTS5 search cho fast fuzzy lookups
- Auto-sync papers từ API vào DB

### 2. Remove Disk Cache System
- Deleted `src/integrity_checker/retrieval/cache.py`
- Deleted `src/integrity_checker/api/routes/cache.py`
- Updated all references từ `used_cache` → `used_local_db`
- Simplified architecture

### 3. API Key Integration
- OpenAlex API key: `GLKkBdc2RIdSRyqZvFL1fn` (user provided)
- Rate limits: Crossref 3/s, OpenAlex 50/s
- Contact email: `iannwendii@gmail.com`

### 4. Bug Fixes
- Crossref author parsing (`'str' object has no attribute 'last_name'`)
- Known papers static method
- Rate limiter initialization

## 📊 Test Results

| File | Citations | CIS | Verified | Source |
|------|-----------|-----|----------|--------|
| 2608.13966v1.pdf | 112 | **97.5** | 107 | crossref+openalex |
| VietDepression | 35 | **100.0** | 35 | local_db (ACL) |
| thesis.pdf | 27 | **~100** | 27 | local_db (ACL) |

## 🔧 Files Changed

```
Modified (15 files):
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
  - README.md
  - CHECKPOINT_2026-09-23.md

Deleted (2 files):
  - src/integrity_checker/retrieval/cache.py
  - src/integrity_checker/api/routes/cache.py
```

## 📋 Còn cần làm

### High Priority
1. Real GROBID Docker integration
2. Error analysis - 2-3 unresolved citations in 2608.13966
3. Ground truth dataset annotation

### Medium Priority
1. Implement baselines B0-B5
2. Performance optimization
3. Crossref API key (optional)

### Low Priority
1. Write thesis Chapter 1-6
2. User manual finalization
3. Video demo

## Git Commits

- `6c17868` - fix: Add FTS5 search to Local DB lookup
- `dc26979` - fix: Add OpenAlex API key + Crossref author parsing fix
- `5fb3b9c` - feat: Update API rate limits và email configuration
- (pending) - feat: Remove disk cache system

## Notes

- API key đã được lưu trong `.env` - **KHÔNG commit**
- Local DB tự động populate khi chạy
- FTS5 search giúp giảm API calls đáng kể
