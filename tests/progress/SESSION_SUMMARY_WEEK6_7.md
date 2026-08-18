# Session Summary — Tuần 6–7 (v1.2, ngày 2026-08-10 → 2026-08-17)

> **Ngày:** 2026-08-10 → 2026-08-17 (Asia/Ho_Chi_Minh)
> **Người thực hiện:** Claude (Claude Opus 5, 1M context) + User (Nguyễn Bảo Minh, 523H0054)
> **Project:** Essay Integrity Checker — Đồ án tốt nghiệp TDTU
> **Giai đoạn:** v1.2 §5.2 — Tuần 6–7 "Full-text audit (Tầng 1 + Tầng 2)"

---

## 1. Mục tiêu phiên

Triển khai các module extraction mới theo đặc tả v1.2:
- Phân vùng văn bản PDF (body / bibliography / appendix / footnote).
- Trích + chuẩn hoá author name APA / IEEE / Vancouver.
- GROBID adapter (TEI XML parser + HTTP client).
- StyleDetector (document-level style profile).
- Mở rộng ReferenceListParser để parse APA + IEEE + Vancouver.

---

## 2. Công việc hoàn thành

### 2.1 Module mới

| Ngày | Module | File mới | Tests | Status |
|---|---|---|---|---|
| 2026-08-10 | `extraction/section_segmenter.py` | `src/integrity_checker/extraction/section_segmenter.py` | 15/15 | ✅ |
| 2026-08-12 | `matching/author_parser.py` | `src/integrity_checker/matching/author_parser.py` | 27/27 | ✅ |
| 2026-08-15 | `extraction/grobid_parser.py` | `src/integrity_checker/extraction/grobid_parser.py` | 15/15 | ✅ |
| 2026-08-17 | `extraction/style_detector.py` | `src/integrity_checker/extraction/style_detector.py` | 12/12 | ✅ |

### 2.2 Module mở rộng

| Ngày | Module mở rộng | Tests | Status |
|---|---|---|---|
| 2026-08-13 | `extraction/reference_parser.py` — thêm IEEE + Vancouver parsers + title extraction | 15/17 (2 deferred) | ✅ + 2 backlog |

### 2.3 Citation model mở rộng (backward compatible)

`src/integrity_checker/models/citation.py` được thêm 4 field mới:

```python
title: Optional[str] = None
title_normalized: Optional[str] = None  # lowercase + no punctuation
numeric_index: Optional[int] = None     # IEEE bracket index
year_suffix: Optional[str] = None       # APA 2020a/2020b
order_index: Optional[int] = None       # position in bib
```

Update signature `Citation.__init__` để chấp nhận các field mới — không phá các code cũ.

---

## 3. Quyết định kỹ thuật đáng chú ý

### 3.1 Defusedxml cho GROBID TEI

**Vấn đề:** Python stdlib `xml.etree.ElementTree` vulnerable với XXE / billion-laughs attacks. GROBID trả TEI XML nên cần parser an toàn.

**Fix:** Dùng `defusedxml.ElementTree.fromstring()`. Mình đã catch `EntitiesForbidden` riêng để clean error_message (chỉ log type, không leak system_id URL attack).

```python
try:
    root = fromstring(tei_xml)
except ParseError as exc:
    return GrobidOutput(is_available=False,
                       error_message=f"parse error: {type(exc).__name__}")
except Exception as exc:
    logger.warning("TEI parse error: %s", type(exc).__name__)
    return GrobidOutput(is_available=False,
                       error_message=f"parse error: {type(exc).__name__}")
```

### 3.2 StyleDetector body + bib split

Phân loại document-level style cần kết hợp tín hiệu từ cả body + bibliography. Nếu 1 trong 2 rỗng, dùng cái còn lại (không nhân 0.5 chia cho 0):

```python
if bib_total == 0:
    ratios["apa_combined"] = ratios["body_apa"]
    ratios["ieee_combined"] = ratios["body_ieee"]
elif body_total == 0:
    ratios["apa_combined"] = ratios["bib_apa"]
    ratios["ieee_combined"] = ratios["bib_ieee"]
else:
    ratios["apa_combined"] = (ratios["body_apa"] + ratios["bib_apa"]) / 2
```

### 3.3 GROBID HTTP client injectable

Để test mà không cần GROBID Docker thật, `call_grobid_fulltext()` nhận `http_post_fn` parameter:

```python
def call_grobid_fulltext(pdf_path, config, http_post_fn=None):
    if http_post_fn is None:
        import requests
        # default
    ...
```

Test mock:
```python
class MockResponse:
    status_code = 200
    text = "<TEI>...</TEI>"

def mock_post(url, files, data, timeout):
    return MockResponse()
```

### 3.4 ReferenceListParser text_preprocessor workaround

TextPreprocessor `_fix_broken_lines()` có false positive: nối `References\nvan der Berg` → `References van der Berg` (rồi regex References không match). Đã workaround bằng **light normalize** trong ReferenceListParser:

```python
# Light normalize: xóa \n sau "References" header, GIỮ \n giữa entries
text = re.sub(r"(?i)(References|Tài liệu tham khảo)\n", r"\1 ", text)
```

Không sửa `_fix_broken_lines()` để tránh phá integration tests.

---

## 4. Các test fail còn lại (backlog)

### 4.1 ReferenceListParser — 2 test case tracked #18

**Test 1: `test_apa_dutch_multi_word`**
- Input: `"van der Berg, J. (2020). A study..."`
- Expected: 1 entry, last-name = `"van der Berg"`
- Actual: `IndexError: list index out of range`
- **Root cause:** Regex `^([A-Z][A-Za-z\s]+(?:,\s*[A-Z]\.\s*)*)\s*\(` không match `"van der"` vì `v` viết thường.

**Test 2: `test_apa_separates_lines`**
- Input: 2 APA entries trên 2 dòng `("Smith, 2020). A study...\nDoe, 2021). Another...")`
- Expected: 2 entries
- Actual: 0 entries (parser không tách được)
- **Root cause:** Light normalize giữ `\n` ở giữa entries, nhưng regex entry boundaries chỉ match start-of-line `^...`.

**Approach mình đã thử (đều fail):**
1. Tăng số entry boundary heuristic (year + period + newline)
2. Lowercase-strip regex (chấp nhận `van`, `de`, `van der`)
3. Tách thử nhiều cách + fallback

**Approach đề xuất (chưa thử):**
- Nếu GROBID khả dụng → dùng `biblStruct` entries trực tiếp (đã có trong `grobid_parser.py`).
- Nếu không → cần ML model (BERT/DistilBERT NER trên reference entries) — push sang tuần 16–17 baseline B5.

---

## 5. Tổng kết

**Trước tuần 6:** 29 unit tests, 8 integration tests (skeleton v1.1).

**Sau tuần 6–7:** **84 unit tests pass, 2 deferred**. Thêm 4 module mới + 1 mở rộng. 5 commit.

**Tasks completed:** #13 (section_segmenter), #14 (GROBID), #15 (author_parser), #16 (ReferenceListParser multi-style + title — có backlog), #17 (style_detector).

**Tasks open:** #18 (ReferenceListParser Dutch + 2-line APA split), #19 (.md docs update — done).

**Tasks pending (chưa start):** #9 (update CIS weights config — đã có sẵn, mark complete), tuần 8 (linking/ scaffold), tuần 8–9 (4 API client thật).

---

## 6. Files changed

```
M  src/integrity_checker/extraction/__init__.py
A  src/integrity_checker/extraction/section_segmenter.py    (15/15 tests)
A  src/integrity_checker/extraction/grobid_parser.py        (15/15 tests)
A  src/integrity_checker/extraction/style_detector.py       (12/12 tests)
A  src/integrity_checker/matching/author_parser.py          (27/27 tests)
M  src/integrity_checker/extraction/reference_parser.py    (15/17 tests)
M  src/integrity_checker/models/citation.py                 (+4 field mới)
A  tests/unit/test_section_segmenter.py
A  tests/unit/test_author_parser.py
A  tests/unit/test_grobid_parser.py
A  tests/unit/test_style_detector.py
M  tests/unit/test_reference_parser.py                       (mở rộng)
A  SESSION_SUMMARY_WEEK6_7.md
M  KNOWN_ISSUES_AND_TODO.md
M  README.md
M  DEVELOPER_QUICKSTART.md
```

---

**Maintained by:** Nguyễn Bảo Minh (523H0054) & Trần Gia Thành (523H0096)
**GVHD:** ThS. Võ Thị Kim Anh
**Đề cương:** v1.2 đã chốt 2026-08-03
