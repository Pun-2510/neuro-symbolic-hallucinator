# Checkpoint - 2026-09-15

## ✅ Đã hoàn thành hôm nay

### 1. Fix TEI XML raw_text trong GROBID parser
- **File**: `src/integrity_checker/extraction/document_parser.py`
- **Vấn đề**: GROBID trả về XML thô trong `raw_text` (e.g., `<ns0:biblStruct...>`)
- **Fix**: Build human-readable `raw_text` từ structured fields (authors, year, title, DOI)
- **Result**: raw_text giờ hiển thị đúng: `"Vaswani, A, Shazeer, N (2017) Attention is all you need..."`

### 2. Fix IEEE `[N]` marker extraction
- **File**: `src/integrity_checker/extraction/citation_extractor.py`
- **Vấn đề**: `[4] Xiao, Y., ...` bị extract thành in-text citation
- **Fix**: Thêm `_is_reference_list_marker()` để filter các marker này

### 3. Fix Essay title filtering
- **Files**: `citation_extractor.py`, `reference_parser.py`
- **Vấn đề**: Tiêu đề essay như "Deep Learning for NLP: A Comprehensive Survey" bị extract nhầm
- **Fix**: Thêm `_is_essay_title()` với regex patterns

### 4. Fix newline trong citations
- **File**: `citation_linker.py`
- **Vấn đề**: `(Vaswani et al.,\n2017)` không extract được author-year
- **Fix**: `_extract_author_year()` normalize newlines

### 5. Fix `Author et al. (Year)` citation format
- **File**: `citation_linker.py`
- **Vấn đề**: Chỉ xử lý được `(Author et al., Year)`, không xử lý `Author et al. (Year)`
- **Fix**: Thêm `_APA_ETAL_YEAR_RE` regex + logic trong `_extract_author_year()`

### 6. Fix reference_list mapping status
- **File**: `pipeline/integrity_pipeline.py`
- **Vấn đề**: Reference entries không có link trong lookup, bị AMBIGUOUS_MAPPING
- **Fix**: Reference list entries được gán `MATCHED` by default

### 7. Fix link lookup normalization
- **File**: `pipeline/integrity_pipeline.py`
- **Vấn đề**: Lookup keys có newlines, lookup fails
- **Fix**: Normalize newlines trong `_build_link_lookup()` và lookup logic

### 8. Add fabricated DOI detection
- **File**: `logic/rules.py`
- **Vấn đề**: DOI giả như `10.1234/ncr.2022.0456` không bị flag
- **Fix**: Thêm `_FABRICATED_DOI_PATTERNS` và `R-FABRICATED-DOI` rule

### 9. Fix arXiv client - replace SDK với direct urllib
- **File**: `src/integrity_checker/retrieval/arxiv_client.py`
- **Vấn đề**: arXiv Python SDK gặp HTTP 429 rate limits + retry exhausted
- **Fix**: 
  - Dùng `urllib` trực tiếp thay vì SDK
  - Parse XML response bằng regex
  - Extract arXiv ID từ DOI field
- **Security**: HTTPS + URL-encode

### 10. Add _split_by_year_fallback
- **File**: `src/integrity_checker/extraction/reference_parser.py`
- **Vấn đề**: Entries không có DOI/URL không split được
- **Fix**: Thêm `_split_by_year_fallback()` method

### 11. Create configs/config.yaml
- **File**: `configs/config.yaml`
- **Nội dung**: GROBID timeout 120s, contact_email, database URL

## 📊 Kết quả - essay_03_comprehensive.pdf

| Metric | Trước | Sau |
|--------|--------|------|
| **CIS Score** | 44.4 | **84.3** |
| Verified | 2 | 19 |
| Suspected Hallucination | 10 | 5 |
| Unresolved | 11 | 1 |

## ❌ Còn lại phải xử lý

### Priority 1: API Rate Limits
1. **Semantic Scholar**: Gặp HTTP 429 rate limits khi chạy nhiều citations
   - Cần implement exponential backoff
   - Hoặc batch requests
2. **arXiv**: Rate limit 429 vẫn xảy ra khi có nhiều requests
   - Đã có retry nhưng cần tăng delay

### Priority 2: Crossref/OpenAlex cho arXiv DOIs
- arXiv DOIs (10.48550/arXiv.XXX) chỉ resolve được qua arXiv API
- Crossref và OpenAlex trả về 404
- Có thể tìm cách map arXiv ID sang Crossref/OpenAlex records

### Priority 3: còn các case unresolved
1. `https://example.com/rag-tech.pdf` - URL không tồn tại
   - Có thể xử lý better error message
2. DOI fabricated được flag đúng nhưng:
   - `10.9999/jmle.2023.4567` → đúng là fabricated
   - `10.1234/ncr.2022.0456` → đúng là fabricated

### Priority 4: Performance
- Semantic matcher model load mỗi lần chạy (~5s)
- Có thể cache model instance
- GROBID timeout 120s có thể giảm nếu server nhanh

### Priority 5: Tests coverage
- Thêm tests cho arXiv DOI extraction
- Thêm tests cho `et al.` format variations
- Thêm tests cho fabricated DOI detection

## 📝 Ghi chú

- Commit history hôm nay: 7 commits
- Tests: 467 passed, 4 skipped
- CIS improvement: +40 điểm (44.4 → 84.3)
