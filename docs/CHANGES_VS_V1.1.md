# Thay đổi từ v1.1 sang v1.2

**Cập nhật:** 2026-09-12  
**Dự án:** Essay Integrity Checker

## 1. Thay đổi phạm vi

v1.1 tập trung vào kiểm tra citation và xác minh reference ở mức cơ bản. v1.2 mở rộng thành pipeline đọc toàn văn nhưng vẫn giữ nguyên nguyên tắc citation-only:

- Không chấm nội dung, ngôn ngữ hay chất lượng toàn bài.
- Không phát hiện đạo văn hoặc tự kết luận gian lận.
- Kết quả là decision-support; giảng viên đưa ra quyết định cuối.

## 2. Kiến trúc

| v1.1 | v1.2 |
|---|---|
| PDF parsing cơ bản | Full-text extraction + phân vùng body/bibliography/appendix |
| GROBID là mở rộng | GROBID adapter và Docker setup nằm trong MVP |
| Mapping một chiều/không rõ | Bidirectional linking giữa in-text citation và reference |
| Style không có output riêng | Document-level style profile: APA-like, IEEE-like, MIXED, UNKNOWN |
| Một nhãn source cho citation | Tách integrity status và source validation label |
| Retrieval stub | Crossref, OpenAlex, Semantic Scholar, arXiv có HTTP implementation, retry và cache |
| CIS có component placeholder | CIS tính consistency từ linker và style profile thật |

## 3. Output schema

v1.2 tách hai lớp:

### Citation integrity

`MATCHED`, `MISSING_REFERENCE`, `UNCITED_REFERENCE`, `IN_TEXT_MISMATCH`, `DUPLICATE_REFERENCE`, `AMBIGUOUS_MAPPING`, `STYLE_INCONSISTENT`, `UNRESOLVED`.

### Source verification

`VERIFIED`, `METADATA_ERROR`, `SUSPECTED_HALLUCINATION`, `UNRESOLVED`.

Report cũng có `style_profile`, `linking_summary`, evidence, triggered rules, matched fields và CIS components.

## 4. Matching và logic

v1.2 bổ sung:

- Author normalization hỗ trợ APA, IEEE, tên nhiều từ, diacritics và particles.
- Venue normalization bằng ISSN, alias dictionary và fuzzy matching.
- Multi-source consensus.
- Fuzzy threshold tuning và abstention band.
- Brier score, ECE và coverage-accuracy.
- Rules cho style inconsistency, ambiguous mapping và domain exception.
- ExplanationGenerator bằng tiếng Việt.

## 5. Ứng dụng web

Web UI v1.2 hiện có:

- Upload PDF và hiển thị tiến trình.
- Dashboard/history.
- Style profile card.
- Citation graph với các chế độ Integrity/Source/Combined.
- Evidence drawer theo từng nguồn.
- Override controls.
- Export JSON/CSV/PDF.
- Authentication cơ bản và layout dùng chung.

## 6. Kiểm thử

Tính đến 2026-09-12:

- Backend test suite: **467 passed, 4 skipped**.
- 4 test skipped là real GROBID Docker mode; mock GROBID integration đã pass.
- Frontend `npm run build`: pass.

## 7. Phần chưa hoàn thành

- Chạy real GROBID Docker trên máy đủ RAM.
- Dataset thật, annotation guideline v2 và IAA giữa hai người annotator.
- Baselines B0–B5 và so sánh định lượng.
- Error analysis và usability study.
- Persist override vào DB và audit log đầy đủ.
- Hardening production: giới hạn upload, kiểm tra magic bytes, CORS allowlist, migrations và ownership tests.

