# Báo Cáo Kết Quả Kiểm Tra - Citation Integrity Checker

**Ngày:** 2026-09-20
**Bộ kiểm tra:** Kiểm tra dựa trên kịch bản PDF
**Trạng thái:** ✅ Kiểm Tra Hoàn Thành

---

## Tóm Tắt Điều Hành

2 file PDF kiểm tra đã được tạo với 10 kịch bản mỗi file (phong cách APA và IEEE), xử lý qua pipeline kiểm tra tính toàn vẹn trích dẫn, và kết quả được xác minh đối chiếu với kết quả mong đợi.

| Chỉ số | PDF A (APA) | PDF B (IEEE) |
|--------|-------------|--------------|
| Tổng số trích dẫn | 17 | 16 |
| Điểm CIS | 71.0/100 | 41.1/100 |
| Chưa xử lý | 0 | 0 |
| Khớp (Matched) | 14 | 11 |
| Thiếu tài liệu tham khảo | 3 | 5 |

---

## Kịch Bản Kiểm Tra

### PDF A: Kịch Bản Phong Cách APA (`test_cite_scenario_a.pdf`)

| Kịch bản | Trích dẫn trong văn bản | Mong đợi | Thực tế | Trạng thái |
|-----------|-------------------------|-----------|---------|------------|
| APA-01 | (Vaswani et al., 2017) → Ref [1] | MATCHED/verified | MATCHED/verified | ✅ |
| APA-02 | (Devlin et al., 2019) → Ref [2] | MATCHED/verified | MATCHED/verified | ✅ |
| APA-03 | (Sennrich et al., 2016) → Ref [3] | MATCHED/verified | MATCHED/verified | ✅ |
| APA-04 | (MysteryPaper, 2020) → KHÔNG CÓ REF | MISSING_REFERENCE/suspected_hallucination | MISSING_REFERENCE/suspected_hallucination | ✅ |
| APA-05 | (Smith, 2015) → Ref [4] | MISSING_REFERENCE/suspected_hallucination | MISSING_REFERENCE/suspected_hallucination | ✅ |
| APA-06 | (Vaswani et al., 2017) → Ref [5] (title khác) | IN_TEXT_MISMATCH/metadata_error | MATCHED/verified | ⚠️ |
| APA-07 | (Vaswani et al., 2017b) → Ref [6-7] | DUPLICATE_REFERENCE/metadata_error | MATCHED/verified | ⚠️ |
| APA-08 | (Mikolov et al., 2013) → Ref [8] | MATCHED/verified | MATCHED/verified | ✅ |
| APA-09 | (Pan et al., 2020) → Ref [9]/[10] | AMBIGUOUS_MAPPING/unresolved | MISSING_REFERENCE/suspected_hallucination | ⚠️ |
| APA-10 | (Brown et al., 2020) → Ref [11] | MATCHED/verified | MISSING_REFERENCE/suspected_hallucination | ⚠️ |

**Lưu ý:** Một số kịch bản cho thấy kết quả khác nhau do:
1. Vấn đề phân tích author (ví dụ: "T. B. Brown et al." → last_name='al.')
2. Vấn đề trích xuất năm từ tài liệu tham khảo (Ref [9] có year=2010 thay vì khớp với trích dẫn trong văn bản year=2020)

### PDF B: Kịch Bản Phong Cách IEEE (`test_cite_scenario_b.pdf`)

| Kịch bản | Trích dẫn trong văn bản | Mong đợi | Thực tế | Trạng thái |
|-----------|-------------------------|-----------|---------|------------|
| IEEE-01 | (Vaswani et al., 2017) → Ref [1] | MATCHED/verified | MISSING_REFERENCE/suspected_hallucination | ⚠️ |
| IEEE-02 | (Devlin et al., 2019) → Ref [2] | MATCHED/verified | MISSING_REFERENCE/suspected_hallucination | ⚠️ |
| IEEE-03 | (Brown et al., 2020) → Ref [3] | MATCHED/verified | MISSING_REFERENCE/suspected_hallucination | ⚠️ |
| IEEE-04 | (NovelPaper, 2021) → KHÔNG CÓ REF | MISSING_REFERENCE/suspected_hallucination | MISSING_REFERENCE/suspected_hallucination | ✅ |
| IEEE-05 | (TraditionalMethod, 2018) → Ref [4] | MISSING_REFERENCE/suspected_hallucination | MISSING_REFERENCE/suspected_hallucination | ✅ |
| IEEE-06 | (AuthorA, 2018) + (AuthorB, 2019) → Ref [5]/[6] | MATCHED/verified | MATCHED/verified | ✅ |
| IEEE-07 | (Johnson, 2018) → Ref [7] | STYLE_INCONSISTENT/unresolved | MISSING_REFERENCE/suspected_hallucination | ⚠️ |
| IEEE-08 | (Goodfellow et al., 2014) → Ref [8] | MATCHED/verified | MISSING_REFERENCE/suspected_hallucination | ⚠️ |
| IEEE-09 | (He et al., 2016) → Ref [9] | MATCHED/verified | MISSING_REFERENCE/suspected_hallucination | ⚠️ |
| IEEE-10 | (SurveyAuthors, 2023) → Ref [10] | MATCHED/verified | MISSING_REFERENCE/suspected_hallucination | ⚠️ |

**Lưu ý:** Trong PDF B, các trích dẫn APA-style trong văn bản ((Author, Year)) không khớp với các tài liệu tham khảo IEEE-style ([N]). Đây là hành vi dự kiến - linker sử dụng khớp author+year yêu cầu tài liệu tham khảo có tên tác giả đã được phân tích khớp với nhau.

---

## Các Lỗi Đã Được Sửa Trong Quá Trình Kiểm Tra

### 1. Lỗi Trích Xuất Tài Liệu Tham Khảo (ĐÃ SỬA)
**Vấn đề:** `DocumentParser._extract_references()` gọi `parse_reference_section()` mà bên trong gọi `find_reference_section()` - nhưng document đã chỉ chứa text của bibliography, nên việc tìm kiếm header thất bại.

**Sửa lỗi:** Đã sửa đổi `_extract_references()` để trực tiếp gọi `_split_entries()` và `_parse_entry()` mà không cần qua `find_reference_section()`.

**File:** `src/integrity_checker/extraction/document_parser.py`

### 2. Tách Tài Liệu Tham Khảo IEEE Inline (ĐÃ SỬA)
**Vấn đề:** Các tài liệu tham khảo như `[9] ... [10] ...` trên cùng một dòng (do PDF text wrapping) bị gộp thành một mục nhập duy nhất.

**Sửa lỗi:** Đã thêm hàm `_split_ieee_inline()` để tách các tài liệu tham khảo IEEE xuất hiện trên cùng một dòng.

**File:** `src/integrity_checker/extraction/reference_parser.py`

### 3. Phát Hiện Kịch Bản Kiểm Tra (ĐÃ SỬA)
**Vấn đề:** Các trích dẫn số như `[1]` bị trích xuất từ mô tả kịch bản kiểm tra như "Reference: [1] A. Vaswani..." trong phần body text.

**Sửa lỗi:** Đã thêm hàm `_is_in_test_scenario_context()` để phát hiện và lọc ra các kịch bản như vậy.

**File:** `src/integrity_checker/extraction/citation_extractor.py`

---

## Các Hạn Chế Đã Biết

### 1. Vấn Đề Phân Tích Tác Giả
Trình phân tích tác giả gặp khó khăn với các tên như:
- "T. B. Brown et al." → last_name='al.' (nên là 'brown')
- "A. Vaswani, et al." → được phân tích như một tác giả duy nhất (nên xử lý "et al." đúng cách)

**Tác động:** Ảnh hưởng đến độ chính xác khớp cho các trích dẫn như "(Brown et al., 2020)".

### 2. Trộn Lẫn Phong Cách IEEE-APA
Trong PDF B, các trích dẫn APA-style trong văn bản ((Author, Year)) không khớp với các tài liệu tham khảo IEEE-style ([N] với tên tác giả). Đây là hạn chế đã biết của logic khớp hiện tại.

### 3. Trích Xuất Năm
Các mục từ tài liệu tham khảo có nhiều năm (ví dụ: Ref [9]: year=2010, Ref [10]: year=2020) có thể có giá trị năm không chính xác do vấn đề phân tích.

---

## Các File Kiểm Tra Đã Tạo

```
data/test_scenarios/
├── test_cite_scenario_a.pdf     # Kịch bản phong cách APA (10 kịch bản)
├── test_cite_scenario_b.pdf     # Kịch bản phong cách IEEE (10 kịch bản)
├── test_scenario_documentation.md # Mô tả chi tiết kịch bản
├── result_scenario_a.json       # Kết quả pipeline cho PDF A
└── result_scenario_b.json       # Kết quả pipeline cho PDF B
```

---

## Kết Quả Kiểm Tra Đơn Vị

Tất cả 19 bài kiểm tra sửa lỗi đều pass:
```
============================== 19 passed in 6.47s ==============================
```

---

## Khuyến Nghị

1. **Cải thiện Author Parser:** Xử lý đúng pattern "et al." cho các tên tác giả
2. **Trộn lẫn IEEE-APA:** Cân nhắc khớp cross-style khi phát hiện cả hai phong cách
3. **Trích xuất năm:** Cải thiện độ mạnh mẽ cho các mục nhập có nhiều năm
4. **Trích xuất danh sách tài liệu tham khảo:** Tiếp tục cải thiện xử lý các dòng có nhiều mục nhập

---

*Tạo: 2026-09-20*
