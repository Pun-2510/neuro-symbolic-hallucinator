# Annotation Guideline — 4 nhãn Citation Integrity

> Áp dụng cho gold dataset. Mọi annotator đọc kỹ file này trước khi gán nhãn.

## Quyết định cốt lõi

**Citation-only**, KHÔNG chấm full tiểu luận. Chỉ gán nhãn cho citation ở **reference list section** (References / Bibliography / Works Cited / Tài liệu tham khảo).

## 4 nhãn

### 1. `verified`
- Nguồn tồn tại trong ít nhất 1 cơ sở dữ liệu uy tín (Crossref / OpenAlex / Semantic Scholar / arXiv).
- **Title** khớp (≥90% theo fuzzy/semantic).
- **Author(s)** khớp ít nhất 1 tên họ.
- **Year** chênh lệch ≤1 năm.
- **DOI** (nếu có) resolve được.

### 2. `metadata_error`
- Nguồn có thật, NHƯNG một hoặc nhiều trường bị sai:
  - Year lệch >1 năm.
  - Title bị biến dạng (typo / paraphrase / sai từ quan trọng).
  - Author sai tên / thiếu / thừa.
  - Venue sai.
  - DOI sai (VD: gõ nhầm).

### 3. `suspected_hallucination`
- Không tìm thấy candidate nào qua cả 4 nguồn (Crossref + OpenAlex + Semantic Scholar + arXiv).
- API trả 200 OK (không phải lỗi mạng).
- Đặc điểm gợi ý: DOI có pattern hợp lệ nhưng resolve 404, journal "lạ", author "lạ", title có vẻ AI-generated.

### 4. `unresolved`
- Không đủ bằng chứng để kết luận:
  - API lỗi / timeout.
  - Title quá chung chung, không thể phân biệt với paper khác.
  - Quá ít thông tin (chỉ có author mà không có title/year/DOI).
  - Dữ liệu mâu thuẫn giữa các nguồn.

## Quy trình gán nhãn

1. **2 SV cùng annotate độc lập** trên cùng 1 batch (50–100 citation đầu tiên).
2. Tính **Cohen's kappa** để đo IAA — target ≥0.7 (substantial agreement).
3. Nếu kappa <0.7, thảo luận những case disagree → cập nhật guideline → annotate lại batch tiếp theo.
4. Sau khi đạt IAA ≥0.7, 2 SV chia nhau annotate phần còn lại.
5. Mỗi citation cần 1 nhãn cuối cùng (resolved disputes).

## Lưu nhãn trong file nào?

- File seed (stub): `data/ground_truth/gold_dataset.json` (do `scripts/gen_gold_dataset.py` tạo).
- File thật: cùng schema, nhưng 2 cột `annotator_A`, `annotator_B` + cột `final` sau khi resolve.

## Edge cases

| Tình huống | Nhãn |
|---|---|
| Citation không có DOI nhưng có title + author khớp chính xác qua OpenAlex | `verified` |
| Citation có DOI nhưng DOI không resolve, title match qua OpenAlex | `verified` (DOI dù là fallback) |
| Citation dùng author "Anonymous" hoặc "Unknown" | `metadata_error` (thiếu thông tin thiết yếu) |
| Citation chỉ có URL (không DOI), URL trỏ tới arXiv abstract | `verified` nếu abstract match, `suspected_hallucination` nếu 404 |
| Citation có DOI nhưng resolve đến paper KHÁC (không liên quan) | `suspected_hallucination` (DOI bịa) |
| Citation ở in-text không có trong reference list | (KHÔNG gán nhãn — chỉ gán cho reference list entry) |

## Disclaimer

Hệ thống là **decision-support**, không tự động kết luận gian lận. Khi giảng viên dùng hệ thống, họ có thể override nhãn của hệ thống — những override này cần được log vào `audit_logs` trong DB.