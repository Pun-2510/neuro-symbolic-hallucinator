# Báo Cáo Phân Tích Toàn Diện Pipeline Trên `thesis.pdf` & Kế Hoạch Xử Lý Triệt Để

> **Ngày thực hiện:** 2026-10-23  
> **Đối tượng kiểm thử:** [`thesis.pdf`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/thesis.pdf) (76 trang PDF — báo cáo khóa luận tốt nghiệp mô tả chính hệ thống Essay Integrity Checker)  
> **Báo cáo JSON sinh ra:** [`reports/thesis.json`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/reports/thesis.json) (7.382 dòng)  
> **Chế độ chạy:** `IntegrityPipeline.run_async("thesis.pdf", use_document_parser=True, use_report_cache=False)` với full `DEBUG` logging (`loguru` + stdlib `logging`).

---

## MỤC LỤC

1. [Phần 1: Tổng quan Ground Truth vs. Kết quả thực tế của Pipeline](#phần-1-tổng-quan-ground-truth-vs-kết-quả-thực-tế-của-pipeline)
2. [Phần 2: Toàn bộ Log thực thi & Phân tích 12 lỗi hệ thống qua từng tầng](#phần-2-toàn-bộ-log-thực-thi--phân-tích-12-lỗi-hệ-thống-qua-từng-tầng)
   - [Tầng 0 — Logging Split-Brain (`loguru` vs `logging`)](#1-tầng-0--logging-split-brain-loguru-vs-stdlib-logging)
   - [Tầng 1 — Section Segmentation: Cắt sai toàn bộ ranh giới Body / Bibliography / Appendix](#2-tầng-1--section-segmentation-cắt-sai-toàn-bộ-ranh-giới-body--bibliography--appendix)
   - [Tầng 2 — GROBID & Reference Merging: Mất sạch URL, arXiv ID, hỏng tác giả tổ chức](#3-tầng-2--grobid--reference-merging-mất-sạch-url-arxiv-id-và-hỏng-tên-tác-giả-tổ-chức)
   - [Tầng 3 — Body Citation Extraction: Rơi trích dẫn đầu dòng, bắt nhầm khoảng toán học `[0, 1]` và bảng ví dụ](#4-tầng-3--body-citation-extraction-bỏ-sót-trích-dẫn-đầu-dòng--bắt-nhầm-khoảng-toán-học-0-1-0-100-và-bảng-ví-dụ)
   - [Tầng 4 — Bidirectional Linking ↔ Verdict Mapping: Đứt gãy 100% kết quả liên kết](#5-tầng-4--bidirectional-linking--verdict-mapping-mất-100-kết-quả-liên-kết-trên-verdicts-và-linking_summary)
   - [Tầng 5 — Multi-Source Retrieval: Bão HTTP 429 trên Semantic Scholar & lỗi chọn `best_candidate`](#6-tầng-5--multi-source-retrieval-nghẽn-cổ-chai-semantic-scholar-http-429-storm--chọn-sai-best_candidate)
   - [Tầng 6 — Feature Matching (`author_matcher.py`): Bug `_INITIAL_RE` biến mọi họ 2 chữ cái thành chữ viết tắt](#7-tầng-6--feature-calculation-author_matcherpy-bug-regex-_initial_re-biến-mọi-họ-2-chữ-cái-ji-yu-su-xu-lo-ge-thành-chữ-viết-tắt)
   - [Tầng 7 — Neuro-Symbolic Rules (`rules.py`): 4 mâu thuẫn logic nghiêm trọng trong cây quyết định](#8-tầng-7--neuro-symbolic-rules-rulespy-hàng-loạt-mâu-thuẫn-logic-trong-cây-quyết-định)
   - [Tầng 8 — CIS Scoring (`cis.py`): Điểm thành phần cao/thấp giả tạo](#9-tầng-8--cis-scoring-cispy-điểm-thành-phần-caothấp-giả-tạo-do-không-nhìn-thấy-lỗi-liên-kết)
3. [Phần 3: Bảng đối chiếu chi tiết toàn bộ 37 Body Citations & 34 Verdicts](#phần-3-bảng-đối-chiếu-chi-tiết-toàn-bộ-37-body-citations--34-verdicts)
4. [Phần 4: Đề xuất phương án xử lý triệt để (Root-Cause Fix Plan kèm Code)](#phần-4-đề-xuất-phương-án-xử-lý-triệt-để-root-cause-fix-plan-kèm-code)
5. [Phần 5: Lộ trình thực thi & Kiểm thử chống hồi quy (Regression Testing)](#phần-5-lộ-trình-thực-thi--kiểm-thử-chống-hồi-quy-regression-testing)

---

## PHẦN 1: Tổng quan Ground Truth vs. Kết quả thực tế của Pipeline

### 1.1. Ground Truth của file [`thesis.pdf`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/thesis.pdf) (76 trang PDF)

| Phân vùng thực tế | Trang PDF (1-based) | Trang đánh số trên giấy | Nội dung thực tế |
| :--- | :---: | :---: | :--- |
| **Front Matter** | Trang 1 – 13 | `i` – `xii` | Bìa, Lời cảm ơn, Tóm tắt, Mục lục (trang 9 có dòng `REFERENCES . . . 54`, `APPENDIX . . . 58`), Danh mục hình, Danh mục bảng, Từ viết tắt. |
| **Body (Chapters 1–6)** | Trang 14 – 67 | `1` – `54` | Toàn bộ nội dung chính từ Chapter 1 đến hết Chapter 6. Sử dụng trích dẫn trong bài theo phong cách số IEEE `[1]` đến `[27]`. |
| **Bibliography (`REFERENCES`)** | Trang 68 – 70 | `55` – `57` | Tiêu đề `REFERENCES` ở đầu trang 68. Chứa **đúng 27 mục tài liệu tham khảo** đánh số `[1]` đến `[27]` (kết hợp chỉ số `[N]` của IEEE và thân trích dẫn `Author (Year). Title...` kiểu APA). |
| **Appendix (`APPENDIX`)** | Trang 71 – 76 | `58` – `63` | Tiêu đề `APPENDIX` ở đầu trang 71. Chứa 4 phụ lục: Appendix A (`.env.example`), Appendix B (`docker-compose.yml`), Appendix C (Annotation Guideline), Appendix D (Core Modules). |

> **Lưu ý đặc biệt về dữ liệu trong chính `thesis.pdf`:**  
> Ngay trong 27 tài liệu tham khảo `[1]`–`[27]` của `thesis.pdf`, có một số mục do chính văn bản khóa luận viết sai metadata so với thực tế (ví dụ: `[2] MuPDF` ghi tác giả `Jurtz, P., & Xu, A.` thay vì Jorj X. McKie; `[3] pdfplumber` ghi tác giả `Stanley, C.` thay vì Jeremy Singer-Vine; `[26] FastAPI` ghi tác giả `Richardson, T., & O'Flanagan, S.` thay vì Sebastián Ramírez; `[11] Sentence-BERT` ghi năm `2020` thay vì `2019`; `[13] Ji et al.` và `[14] Sadasivan et al.` ghi sai một số đồng tác giả cuối; `[15] Jin et al. (2024) "Be honest or leave..."` là tên bài không tồn tại trên ACL 2024). Một pipeline chuẩn xác phải **phân biệt rõ**: đâu là tài liệu hợp lệ (`verified`), đâu là tài liệu web (`resource`), đâu là lỗi metadata của tác giả bài viết (`metadata_error`), và đâu là nguồn không tồn tại (`suspected_hallucination`).

### 1.2. Kết quả thực tế hệ thống xuất ra trong [`reports/thesis.json`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/reports/thesis.json)

* **Tổng thời gian thực thi:** ~82 giây (bị treo ~65 giây do retry HTTP 429 từ Semantic Scholar).
* **Phân đoạn trang (`SectionSegmenter`):**
  * `BODY`: Trang 1 – 56 *(sai: cắt mất 11 trang cuối của Chapter 5 & Chapter 6)*.
  * `BIBLIOGRAPHY`: Trang 57 – 63 *(sai hoàn toàn: lấy phần thân bài của Chapter 5 và mục 6.1–6.2 làm mục Tài liệu tham khảo!)*.
  * `APPENDIX`: Trang 64 – 76 *(sai: nuốt trọn mục 6.3–6.5 và toàn bộ mục `REFERENCES` thật ở trang 68–70 vào Phụ lục!)*.
* **Số trích dẫn trích xuất (`extracted_citations`):** 71 mục:
  * **37 `body_citations`:** Bỏ sót 4 trích dẫn thật (`[9]`, `[14]`, `[17]`, `[23]`), bắt nhầm 2 khoảng toán học (`[0, 1]`, `[0, 100]`) và 8 chuỗi ví dụ trong bảng `Table 4.2`.
  * **34 `references`:** Gồm 27 mục từ GROBID (`ref-0001` → `ref-0027`) + **7 mục rác từ nhánh Regex (`ref-0028` → `ref-0034`)** thực chất là các bảng `Table 5.1`–`5.4` và các đoạn văn của Chapter 5 & Chapter 6!
* **Phân bố 34 `verdicts`:**
  * `verified`: **12 / 34** (`[1], [9], [10], [12], [16], [17], [18], [19], [20], [21], [23], [25]`)
  * `metadata_error`: **1 / 34** (`[15]` — bắt nhầm sang một bài báo khác có tác giả không liên quan trên OpenAlex)
  * `resource`: **1 / 34** (**không phải** các tài liệu web `[4]–[8]`, mà là bảng **`Table 5.1`** (`ref-0028`) do chứa chữ `"FastAPI REST API,"`!)
  * `suspected_hallUCINATION`: **0 / 34**
  * `unresolved`: **20 / 34** (gồm 14 tài liệu thật trong `[1]–[27]` và 6 bảng/đoạn văn của Chapter 5 & 6).
* **Tóm tắt liên kết (`linking_summary`):**
  * `matched: 0`, `missing_reference: 6`, `uncited_reference: 0`, `unresolved: 34`.
* **Điểm `CIS`:** `75.91 / 100`
  * `verified_ratio`: `0.3636` (12 / 33)
  * `metadata_accuracy`: `0.9697`
  * `in_text_bib_consistency`: `0.9684`
  * `format_consistency`: `0.9730`
  * `identifier_validity`: `1.0000`

---

## PHẦN 2: Toàn bộ Log thực thi & Phân tích 12 lỗi hệ thống qua từng tầng

### 1. Tầng 0 — Logging Split-Brain (`loguru` vs stdlib `logging`)

* **File liên quan:** [`src/integrity_checker/logging.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logging.py#L14-L52)
* **Hiện tượng:** Khi chạy pipeline với cấu hình mặc định của dự án, log thu được chỉ có 146 dòng từ `loguru` (chỉ hiển thị tầng `IntegrityPipeline` và `RetrievalOrchestrator`). Toàn bộ log của tầng trích xuất PDF, phân đoạn trang (`SectionSegmenter`), lọc mục giả của GROBID (`DocumentParser`), tách mục tài liệu tham khảo (`ReferenceListParser`), liên kết hai chiều (`CitationLinker`) và tính điểm (`CISCalculator`) **biến mất hoàn toàn** khỏi console và file `data/logs/integrity_checker.log`.
* **Nguyên nhân gốc rễ:**
  * Các module [`document_parser.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L42), [`section_segmenter.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/section_segmenter.py#L44), [`reference_parser.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/reference_parser.py#L44), [`citation_linker.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/linking/citation_linker.py#L34), [`cis.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/cis.py#L28) gọi `logger = logging.getLogger(__name__)` (stdlib `logging`).
  * Trong khi đó, [`configure_logging()`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logging.py#L14-L45) chỉ cấu hình `loguru.logger` mà không đăng ký `InterceptHandler` cho `logging.basicConfig()`.

---

### 2. Tầng 1 — Section Segmentation: Cắt sai toàn bộ ranh giới Body / Bibliography / Appendix

* **File liên quan:** [`src/integrity_checker/extraction/section_segmenter.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/section_segmenter.py#L46-L343)
* **Log thực tế khi bật stdlib `DEBUG`:**
  ```text
  DEBUG:integrity_checker.extraction.section_segmenter:Bibliography starts at page 57 (header)
  DEBUG:integrity_checker.extraction.section_segmenter:Appendix starts at page 64
  INFO:integrity_checker.extraction.document_parser:Extracted 7 references from regex
  INFO:integrity_checker.extraction.document_parser:Merged references: 27 GROBID + 7 regex → 34 unique
  ```
* **Giải phẫu chi tiết cách [`SectionSegmenter`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/section_segmenter.py) đã ra quyết định sai:**
  1. **Tại sao trang 57 PDF (đầu Chapter 5, `Table 5.1`) bị nhận nhầm là đầu mục Bibliography?**
     * Trên trang 57 PDF, `Table 5.1` có ô văn bản: `"PDF text extraction (PyMuPDF, pdfplumber), regex reference parser, eight citation styles, style detector"`. Do cột bảng hẹp, PyMuPDF tách văn bản thành 15 dòng đầu trang:
       ```text
       L1: '44'
       L2: 'Table 5.1: Implementation status by subsystem'
       ...
       L9: 'regex'
       L10: 'reference'
       L11: 'parser, eight citation styles, style'
       ```
     * Hàm [`_page_has_bibliography_header`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/section_segmenter.py#L319-L325) quét 15 dòng đầu mỗi trang bằng [`_BIBLIOGRAPHY_HEADER_PATTERNS`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/section_segmenter.py#L46-L61):
       ```python
       _BIBLIOGRAPHY_HEADER_PATTERNS = [
           r"^\s*(?:\d+\.?\s+)?references?\s*$",
           ...
       ]
       ```
     * Vì pattern dùng `references?` (cho phép danh từ số ít `reference`) kết hợp với cờ `re.IGNORECASE`, chữ `'reference'` viết thường nằm một mình ở dòng 10 trong bảng `Table 5.1` khớp hoàn toàn!
     * Và vì [`_find_boundaries`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/section_segmenter.py#L197-L200) dùng `break` ngay tại trang đầu tiên khớp header, hệ thống chốt `bib_start = 56` (trang 57 PDF) và **không bao giờ quét tới trang 68 PDF** (nơi có tiêu đề `'REFERENCES'` thật sự)!
  2. **Tại sao trang 64 PDF (mục `6.3 Directions for Next Steps`) bị nhận nhầm là đầu mục Appendix?**
     * Trên trang 64 PDF, câu văn ở mục 6.3 viết:
       `"Two independent annotation passes will be completed over the citation dataset following\nAppendix C, chance-corrected inter-annotator agreement will be computed"`
     * Dòng 15 của trang 64 bắt đầu bằng: `'Appendix C, chance-corrected inter-annotator agreement will be computed'`.
     * Hàm [`_page_has_appendix_header`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/section_segmenter.py#L327-L333) kiểm tra 15 dòng đầu trang bằng [`_APPENDIX_HEADER_PATTERNS`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/section_segmenter.py#L63-L71):
       ```python
       _APPENDIX_HEADER_PATTERNS = [
           r"^\s*appendix(?:\s+[A-Z0-9]+)?\b.*$",
           ...
       ]
       ```
     * Vì cuối regex là `\b.*$` (chấp nhận mọi ký tự bất kỳ phía sau, kể cả dấu phẩy và cả một mệnh đề câu văn xuôi), dòng 15 của trang 64 bị nhận nhầm là tiêu đề Phụ lục!
* **Hậu quả dây chuyền:**
  * Nhánh Regex (`ReferenceListParser`) chỉ được chạy trên `SectionType.BIBLIOGRAPHY` (trang 57–63), tức là **nhánh Regex không hề nhìn thấy mục `REFERENCES` thật ở trang 68–70**!
  * Thay vào đó, `ReferenceListParser` băm 7 bảng biểu và đoạn văn của Chapter 5 & Chapter 6 (trang 57–63) thành 7 tài liệu tham khảo `Vancouver` (`ref-0028` → `ref-0034`).
  * Còn mục `REFERENCES` thật ở trang 68–70 bị đẩy vào `SectionType.APPENDIX`, khiến `DocumentParser._extract_appendix_citations` trích xuất 25 ký hiệu `[1]`–`[27]` trong `REFERENCES` thành `appendix_citations`!

---

### 3. Tầng 2 — GROBID & Reference Merging: Mất sạch URL, arXiv ID và hỏng tên tác giả tổ chức

* **File liên quan:** [`src/integrity_checker/extraction/grobid_adapter.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_adapter.py#L467-L586), [`src/integrity_checker/extraction/document_parser.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L384-L510)
* **Giải phẫu quyết định của hệ thống:**
  1. **GROBID sinh 73 mục (`b0`–`b72`) do ăn cả Mục lục (Table of Contents):**
     * Trong `thesis.pdf`, các dòng mục lục ở trang 6–9 (`3.1 System Requirements... 22`) bị GROBID parse thành `b0`–`b45`. Hàm [`_is_fake_entry`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L513-L570) đã lọc bỏ `b0`–`b45`, giữ lại `b46`–`b72` (tương ứng với `[1]`–`[27]`).
  2. **Mất sạch `url` và `arXiv ID` khi qua GROBID:**
     * Trong mục `REFERENCES` của `thesis.pdf` (trang 68–69):
       * `[4]` có `Retrieved from https://api.crossref.org/`
       * `[5]` có `Retrieved from https://docs.openalex.org/`
       * `[6]` có `Retrieved from https://api.semanticscholar.org/`
       * `[7]` có `Retrieved from https://www.doi.org/doi-handbook/HTML/`
       * `[8]` có `Retrieved from https://aclanthology.org/`
       * `[14]` có `arXiv:2303.11156.`
     * Khi GROBID parse TEI XML (`grobid_parser.py`), URL trong `<ptr target="..."/>` hoặc văn bản `Retrieved from ...` không được trích xuất vào `GrobidReference`, và [`_synthesize_raw_text`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_adapter.py#L564-L586) chỉ ghép `authors + (year) + title + venue`, làm biến mất hoàn toàn URL và mã `arXiv:2303.11156` khỏi `citation.raw_text` và `citation.url`!
     * Hơn nữa, trong [`DocumentParser._enrich_grobid_ref`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L495-L510):
       ```python
       for attr in ("doi", "volume", "issue", "pages", "venue"):
           if getattr(target, attr) is None and getattr(donor, attr) is not None:
               setattr(target, attr, getattr(donor, attr))
       ```
       Danh sách thuộc tính được làm giàu từ `donor` (regex) sang `target` (GROBID) **thiếu mất `"url"`**!
     * **Hậu quả:** Cả 5 tài liệu web `[4]–[8]` bị mất URL nên `Rule 0 (R-WEB-RESOURCE)` không nhận diện được, bị đẩy đi tìm kiếm như bài báo học thuật và bị chấm `UNRESOLVED` cả 5!
  3. **GROBID tách sai tên tổ chức (`Corporate Author`):**
     * Mục `[6] Allen Institute for AI. (2024). Semantic Scholar Open Research Corpus` bị GROBID hiểu nhầm là tên người (`forename="Allen"`, `surname="Institute"`, cộng thêm tác giả thứ hai `"A I"`), tạo ra `authors = ["Institute, Allen", "A I"]`.
  4. **Gán cứng `style = CitationStyle.APA` cho mọi reference từ GROBID:**
     * Tại [`grobid_adapter.py:537`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_adapter.py#L537), mọi reference do GROBID trả về đều bị gán cứng `style=CitationStyle.APA`, dù thực tế chúng có chỉ số `[1]`–`[27]`.

---

### 4. Tầng 3 — Body Citation Extraction: Bỏ sót trích dẫn đầu dòng & Bắt nhầm khoảng toán học `[0, 1]`, `[0, 100]` và bảng ví dụ

* **File liên quan:** [`src/integrity_checker/extraction/citation_extractor.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/citation_extractor.py#L67-L85), [`src/integrity_checker/extraction/patterns/ieee.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/patterns/ieee.py)
* **Các lỗi cụ thể:**
  1. **Rơi 4 trích dẫn thật `[9]`, `[14]`, `[17]`, `[23]` trong thân bài:**
     * Trong `thesis.pdf`, do căn đều hai bên (justified alignment), 4 ký hiệu trích dẫn nằm ngay đầu dòng mới:
       * Trang 20: `"In the bibliographic domain it has a long history\n[9], and the key insight..."`
       * Trang 21: `"...training and serving infrastructure\n[17], and it is..."` và `"...evaded by simple paraphrasing\n[14]..."`
       * Trang 27: `"...Krippendorff's alpha [22], and\n[23]."`
     * Hàm [`_is_reference_list_marker`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/citation_extractor.py#L67-L85) kiểm tra:
       ```python
       prefix = raw_text[:raw_start]
       if prefix.isspace() or re.search(r"\n\s*$", prefix):
           return True
       ```
       Hàm này không hề nhìn ký tự **phía sau** `[N]`! Trong danh mục tài liệu tham khảo thật, sau `[9]` phải là khoảng trắng và chữ cái viết hoa của tên tác giả (`[9] Fellegi, I. P.`), còn trong thân bài, ngay sau `[9]` là dấu câu (`,`, `.`, `;`) hoặc chữ viết thường (`[9], and`). Vì chỉ nhìn phía trước có `\n`, cả 4 trích dẫn `[9],`, `[17],`, `[14]`, `[23].` đều bị xóa sổ!
  2. **Hậu quả dây chuyền sang `_extract_reference_context`:**
     * Khi [`_extract_reference_context`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/pipeline/integrity_pipeline.py#L1401-L1479) không tìm thấy `body_citation` nào liên kết tới `ref-0009` hay `ref-0014`, nó fallback quét `full_text` (gồm cả trang Bibliography!) để tìm chuỗi `[9]` và `[14]`, rồi **cắt luôn dòng chữ trong mục `REFERENCES` làm `context` câu trích dẫn trong bài**!
  3. **Bắt nhầm khoảng toán học `[0, 1]` và `[0, 100]`:**
     * Regex IEEE trong [`patterns/ieee.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/patterns/ieee.py) cho phép chữ số đầu tiên là `0` (`\d{1,3}`), nên:
       * `"Each verdict carries a confidence in [0, 1]"` (trang 52) → bị bắt thành trích dẫn đa nguồn `[0, 1]` và nối vào `ref-0001`!
       * `"The Citation Integrity Score (CIS) is a single number in [0, 100]"` (trang 53) → bị bắt thành trích dẫn `[0, 100]` và tính thành 1 lỗi `missing_reference`!
  4. **Bắt nhầm các chuỗi cú pháp mẫu trong `Table 4.2` (trang 40):**
     * Trong `Table 4.2: Registered citation styles and their marker patterns`, tác giả viết các ví dụ giả định: `(Author et al., 2020)`, `(Author, 2020)`, `Author (2020)`, `(Author 2020, p. 5)`.
     * Vì hệ thống không lọc bỏ tên tác giả placeholder `"Author"`, nó trích xuất 5 trích dẫn APA/Harvard giả từ bảng này, tạo ra 5 lỗi `missing_reference` giả!

---

### 5. Tầng 4 — Bidirectional Linking ↔ Verdict Mapping: Mất 100% kết quả liên kết trên `verdicts` và `linking_summary`

* **File liên quan:** [`src/integrity_checker/pipeline/integrity_pipeline.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/pipeline/integrity_pipeline.py#L676-L705), [`src/integrity_checker/linking/citation_linker.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/linking/citation_linker.py#L553-L601)
* **Giải phẫu đoạn code gây đứt gãy hoàn toàn tầng Linking và tầng Verification:**
  * Tại [`IntegrityPipeline.run_async` (dòng 680–691)](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/pipeline/integrity_pipeline.py#L680-L691):
    ```python
    if citation.citation_type.value == "reference_list":
        best = source.best_candidate()
        if (
            best
            and best.doi
            and citation.doi
            and best.doi.lower() == citation.doi.lower()
        ):
            mapping_status = CitationMappingStatus.MATCHED
            mapping_confidence = 0.95
        else:
            mapping_status = CitationMappingStatus.UNRESOLVED
            mapping_confidence = 0.5
    ```
  * **Tại sao đoạn code này sai nghiêm trọng?**
    1. `Verdict` chỉ được tạo cho các mục `reference_list` (`_is_verifiable(c)` chỉ nhận `reference_list` khi có danh mục tài liệu tham khảo).
    2. `mapping_status` có ý nghĩa là **trạng thái liên kết hai chiều giữa trích dẫn trong thân bài (in-text) và mục tài liệu tham khảo (bibliography entry)** — kết quả này đã được `CitationLinker.link_citations()` tính toán xong và lưu trong `linking_result` (`ref_id_to_occurrences` và `uncited_reference_ids`).
    3. Thế nhưng đoạn code ở dòng 680–691 lại **không hề đọc `linking_result`**, mà lại đi so sánh `best.doi == citation.doi`! Vì 27 tài liệu trong `thesis.pdf` không ghi DOI trong văn bản (`citation.doi is None`), **tất cả 34/34 `verdicts` đều bị gán `mapping_status = CitationMappingStatus.UNRESOLVED` (`mapping_confidence = 0.5`, `citation_link = None`)!**
  * **3 hậu quả trực tiếp:**
    1. **Vô hiệu hóa `R-WELL-LINKED` và `R-WELL-LINKED-MODERATE` trong `SymbolicRules`:** Trong [`rules.py:696-700`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py#L696-L700), `mapping_is_matched = (mapping_status == CitationMappingStatus.MATCHED and mapping_confidence >= 0.85)` luôn bằng `False`!
    2. **Gợi ý sai trên toàn bộ báo cáo:** Mọi verdict đều bị chèn câu `"Hệ thống chưa đủ thông tin để liên kết. Có thể thử lại sau khi có thêm thông tin từ sinh viên."`
    3. **`linking_summary` sai 100%:** Hàm [`_compute_linking_summary`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/pipeline/integrity_pipeline.py#L1185-L1203) cộng dồn `v.mapping_status` từ `verdicts`, nên xuất ra `matched: 0, uncited_reference: 0, unresolved: 34`!

---

### 6. Tầng 5 — Multi-Source Retrieval: Nghẽn cổ chai Semantic Scholar (HTTP 429 Storm) & Chọn sai `best_candidate`

* **File liên quan:** [`src/integrity_checker/pipeline/integrity_pipeline.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/pipeline/integrity_pipeline.py#L618-L620), [`src/integrity_checker/retrieval/retrieval_orchestrator.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/retrieval/retrieval_orchestrator.py#L1014-L1119)
* **Chi tiết từ [`thesis_debug.log`](file:///Users/iannwendy/.gemini/antigravity-cli/brain/9d665de0-ea61-4403-9eb8-df852e4c34ae/scratch/thesis_debug.log):**
  1. **Bão HTTP 429 trên Semantic Scholar:**
     * Dòng 618 của `integrity_pipeline.py` chạy `await asyncio.gather(*(self.orchestrator.retrieve(c) for c in unique_list))` đồng thời cho cả 34 citations mà không có `Semaphore` giới hạn độ song song ở cấp pipeline.
     * 23 citations không thoát sớm ở `local_db` cùng lúc gọi sang Semantic Scholar API, dẫn tới **13 lần `S2 retry exhausted`** và làm thời gian chạy tăng vọt lên 82 giây.
  2. **Hàm `_select_best_candidate` không xét `author_match_score`:**
     * Trong [`retrieval_orchestrator.py:1079-1118`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/retrieval/retrieval_orchestrator.py#L1079-L1118), điểm xếp hạng để chọn `best_candidate` chỉ tính `score = title_sim + year_bonus` (hoàn toàn không tính điểm trùng khớp tác giả `author_match_score`).
     * Khi một cuốn sách hoặc bài báo có bài trùng tên (ví dụ Book Review cùng năm hoặc bài khác trùng từ khóa tiêu đề), hệ thống có thể chọn nhầm bài có `author_jaccard = 0.0` chỉ vì năm gần hơn, hoặc với sách tái bản như `[22] Krippendorff (2004)`, Crossref trả bản tái bản năm `2019` (`year_distance = 15`), hệ thống không nhận diện được đây là sách tái bản của cùng tác giả.

---

### 7. Tầng 6 — Feature Calculation (`author_matcher.py`): Bug regex `_INITIAL_RE` biến mọi họ 2 chữ cái (`Ji`, `Yu`, `Su`, `Xu`, `Lo`, `Ge`) thành chữ viết tắt!

* **File liên quan:** [`src/integrity_checker/matching/author_matcher.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/matching/author_matcher.py#L46-L135)
* **Giải phẫu bug:**
  * Tại dòng 47 của [`author_matcher.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/matching/author_matcher.py#L47):
    ```python
    _INITIAL_RE = re.compile(r"^[A-Z]\.?$|^[A-Z]\.?[A-Z]\.?$", re.IGNORECASE)
    ```
  * Và trong [`_canonicalize_last_name(name)`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/matching/author_matcher.py#L83-L135):
    * Khi xử lý tên tác giả từ `local_db` hoặc Crossref/OpenAlex/S2 (định dạng `"First Last"` không có dấu phẩy, ví dụ `"Ziwei Ji"`, `"Tiezheng Yu"`, `"Dan Su"`, `"Yan Xu"`, `"Kyle Lo"`):
    * Chuỗi được đưa về chữ thường và tách từ: `tokens = ["ziwei", "ji"]`.
    * Vòng lặp dòng 131–133:
      ```python
      for t in tokens:
          if not _INITIAL_RE.match(t):
              last_non_initial = t
      ```
    * Vì `_INITIAL_RE` có nhánh `^[A-Z]\.?[A-Z]\.?$` với `re.IGNORECASE` và đã strip dấu chấm ở bước trước (`_strip_punctuation`), **bất kỳ từ nào có độ dài đúng 2 chữ cái (`"ji"`, `"yu"`, `"su"`, `"xu"`, `"lo"`, `"ge"`, `"li"`, `"wu"`, `"he"`, `"ma"`, `"lu"`, `"hu"`, `"ye"`, `"do"`, `"vo"`, `"le"`, `"ha"`, `"to"`, `"an"`) đều khớp với `_INITIAL_RE`** và bị coi là chữ viết tắt (như `J.K.`)!
    * Do đó, vòng lặp bỏ qua họ `"ji"` ở cuối và lấy tên riêng `"ziwei"` làm họ!
  * **Bằng chứng trực tiếp trên `thesis.pdf`:**
    * Với **`[13] Ji et al. (2023) Survey of hallucination in natural language generation`**:
      * `cited_set` (có dấu phẩy từ GROBID `"Ji, Z"`, `"Yu, T"`, `"Su, D"`, `"Xu, Y"`): `{"ji", "lee", "frieske", "yu", "su", "xu", "tsvetkov", "choi"}`.
      * `cand_set` (từ `local_db`: `"Ziwei Ji"`, `"Tiezheng Yu"`, `"Dan Su"`, `"Yan Xu"`...): bị biến thành `{"ziwei", "lee", "frieske", "tiezheng", "dan", "yan", "ishii", "bang", "madotto", "fung"}`!
      * 4 tác giả chính (`Ji`, `Yu`, `Su`, `Xu`) bị lệch hoàn toàn (`"ji" != "ziwei"`), làm `author_jaccard` rơi từ mức khớp cao xuống chỉ còn **`2 / 16 = 0.125`**! Kết quả là bài báo trụ cột `[13]` có sẵn trong `local_db` bị đánh **`UNRESOLVED`**!
    * Với **`[12] Beltagy, I., Lo, K., & Cohan, A. (2019). SciBERT`**:
      * Tác giả thứ hai `"Kyle Lo"` trong `local_db` bị biến thành `"kyle"`, làm `author_jaccard` bị tụt từ `1.0` xuống `0.5`!

---

### 8. Tầng 7 — Neuro-Symbolic Rules (`rules.py`): Hàng loạt mâu thuẫn logic trong cây quyết định

* **File liên quan:** [`src/integrity_checker/logic/rules.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py)

1. **Lỗi 8.1 — `_rule_local_db_verified` và `_rule_local_db_good_match` hardcode `year_dist == 0` thay vì `year_dist <= self.year_tolerance`:**
   * Tại [`rules.py:233`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py#L233) và [`rules.py:298`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py#L298), điều kiện năm của `local_db` bị khóa cứng là `year_dist == 0`.
   * Khi `[11] Reimers & Gurevych (2020) Sentence-BERT` khớp tuyệt đối trong `local_db` (`title_sim_fuzzy = 1.0, title_sim_semantic = 1.0, author_jaccard = 1.0`), nhưng năm trong `local_db` là `2019` (`year_distance = 1`, nằm trong `year_tolerance = 1`), cả hai rule `local_db` đều từ chối.
   * Vì `RetrievalOrchestrator` đã thấy match tốt trong `local_db` nên **đã dừng sớm (early exit)** không gọi API ngoài, làm `_has_live_source` bằng `False`. Thế là các rule phía sau (`R-SINGLE-SOURCE-VERIFIED`) cũng từ chối nốt vì đòi `_has_live_source == True`, đẩy `[11]` xuống tận `R-WEAK-EVIDENCE` → **`UNRESOLVED (conf=0.40)`**!

2. **Lỗi 8.2 — Rule 4b (`R-KNOWN-AUTHOR-TITLE-MISMATCH`) kết luận `METADATA_ERROR` mà không kiểm tra `author_sim` của candidate:**
   * Tại [`rules.py:1020-1038`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py#L1020-L1038):
     ```python
     if self._is_known_academic_author_pattern(citation) and title_sim >= 0.3:
         mismatched = self._collect_mismatches(features)
         return RuleDecision(
             label=VerdictLabel.METADATA_ERROR,
             confidence=0.65,
             ...
         )
     ```
   * Hàm [`_is_known_academic_author_pattern`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py#L348-L433) chứa danh sách các họ cực kỳ phổ biến như `"wang"`, `"zhang"`, `"li"`, `"yang"`, `"liu"`, `"chen"`, `"smith"`, `"lee"`, `"kim"`, `"nguyen"`, `"tran"`, `"le"`.
   * Khi một trích dẫn bất kỳ có tác giả mang họ `"Wang"`, `"Chen"`, `"Liu"`, hoặc `"Nguyen"` (như `[15] Jin, Z., Chen, X., Liu, Y., Wang, X...`), chỉ cần API trả về một bài báo **hoàn toàn không liên quan của một tác giả khác** (`author_jaccard = 0.0`) có `title_sim_fuzzy >= 0.3` (mức rất thấp, hầu như câu tiếng Anh dài nào cũng đạt >= 0.3 với `token_set_ratio`), Rule 4b lập tức kết luận đây là **`METADATA_ERROR` ("Known academic author detected but title mismatch")**!

3. **Lỗi 8.3 — Rule 3g (`R-CONTENT-ALIGNMENT` nhánh uncertain `0.2 <= score < 0.5`) chặn ngang trước Rule 4 (`R-METADATA-ERR`):**
   * Tại [`rules.py:988-999`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py#L988-L999), nếu `0.2 <= content_alignment_score < 0.5`, hàm `apply()` lập tức `return RuleDecision(label=VerdictLabel.UNRESOLVED, ...)` ở bước 3g trước khi xuống bước 4 (`R-METADATA-ERR`).
   * Hậu quả:
     * Với **`[24] Chawla (2008)`**: Crossref tìm thấy đúng chương sách của Chawla (`title_sim = 0.90, author_jaccard = 1.0`), chỉ lệch năm xuất bản (`2010` vs `2008`, `year_distance = 2`). Lẽ ra Rule 4 (`R-METADATA-ERR`) ở dòng 1003 sẽ bắt đúng lỗi lệch năm xuất bản (`year`), nhưng bị Rule 3g chặn mất và biến thành `UNRESOLVED (conf=0.27)`!
     * Với **`[2], [4], [8], [26]`**: Khi candidate tìm được không phải là bài báo đang trích dẫn (`author_jaccard = 0.0`, `title_sim < 0.75`), việc đem câu văn trong thân bài so sánh ngữ nghĩa với tiêu đề của một bài báo lạ ngẫu nhiên là hoàn toàn vô nghĩa, nhưng lại kích hoạt `R-CONTENT-ALIGNMENT` và sinh ra thông báo sai bản chất!

4. **Lỗi 8.4 — `R-NO-CANDIDATE` trả về `UNRESOLVED` thay vì đánh giá khả năng `SUSPECTED_HALLUCINATION` (Mâu thuẫn với Chương 4 của `thesis.pdf`):**
   * Trong [`rules.py:663-673`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py#L663-L673), khi các nguồn tra cứu đều hoạt động bình thường (`not provenance.api_exhausted`) nhưng trả về 0 candidate, `R-NO-CANDIDATE` luôn trả về `UNRESOLVED (conf=0.5)`. Đồng thời, nếu có candidate rác với `title_sim < 0.4` và `author_sim == 0.0` (và không khớp regex tên giả `"test"`, `"john doe"`), `R-WEAK-EVIDENCE` ở cuối bảng luật cũng trả về `UNRESOLVED (conf=0.40)`.
   * Điều này có nghĩa là: các trích dẫn bịa đặt tinh vi (AI-generated hallucinated citations có tên tác giả thật + tiêu đề giả hợp lý, như `[15]`) **không bao giờ có thể được phân loại là `SUSPECTED_HALLUCINATION`**!

---

### 9. Tầng 8 — CIS Scoring (`cis.py`): Điểm thành phần cao/thấp giả tạo do không nhìn thấy lỗi liên kết

* **File liên quan:** [`src/integrity_checker/logic/cis.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/cis.py#L72-L299)
* **Phân tích công thức tính điểm hiện tại trên `thesis.pdf` (`CIS = 75.91`):**
  1. `verified_ratio = 12 / 33 = 0.3636`: Mẫu số là `33` vì bị cộng thêm 6 đoạn văn của Chapter 5 & 6 (`ref-0029` → `ref-0034`), và tử số mất đi `[4]–[8]` (lẽ ra là `RESOURCE` không tính vào mẫu số), mất đi `[11], [13], [22]` (lẽ ra là `VERIFIED`).
  2. `metadata_accuracy = 32 / 33 = 0.9697`: Hàm [`_calc_metadata_accuracy`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/cis.py#L140-L157) tính điểm trên toàn bộ `33` citations (bao gồm cả 20 `UNRESOLVED`), nên bất kỳ bài nào có nhiều `UNRESOLVED` đều mặc nhiên được `~1.0` điểm `metadata_accuracy`! Đúng về mặt toán học, `metadata_accuracy` chỉ nên tính trên tập các trích dẫn **đã xác định được kết quả (`resolved`)** hoặc phạt nhẹ `UNRESOLVED`.
  3. `in_text_bib_consistency = 0.9684`: Do đọc `v.mapping_status` bị gán sai thành `"unresolved"`, điểm này không phản ánh đúng tỷ lệ khớp hai chiều từ `CitationLinker`.

---

## PHẦN 3: Bảng đối chiếu chi tiết toàn bộ 37 Body Citations & 34 Verdicts

### 3.1. Bảng 37 Body Citations trích xuất trong [`reports/thesis.json`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/reports/thesis.json)

| STT | ID | Trang PDF | `raw_text` | Kiểu (`style`) | `mapping_status` | Liên kết tới | Đánh giá tính đúng đắn |
| :-: | :--- | :-: | :--- | :---: | :---: | :--- | :--- |
| 1 | `occ-0001` | 14 | `[27]` | IEEE | `matched` | `ref-0027` | Đúng |
| 2 | `occ-0002` | 19 | `[1]` | IEEE | `matched` | `ref-0001` | Đúng |
| 3 | `occ-0003` | 20 | `[2]` | IEEE | `matched` | `ref-0002` | Đúng *(nhưng trang 20 bị rơi mất `\n[9],`)* |
| 4 | `occ-0004` | 20 | `[3]` | IEEE | `matched` | `ref-0003` | Đúng |
| 5 | `occ-0005` | 21 | `[16]` | IEEE | `matched` | `ref-0016` | Đúng *(nhưng trang 21 bị rơi mất `\n[17],` và `\n[14]`)* |
| 6 | `occ-0006` | 21 | `[15]` | IEEE | `matched` | `ref-0015` | Đúng |
| 7 | `occ-0007` | 21 | `[24]` | IEEE | `matched` | `ref-0024` | Đúng |
| 8–13 | `occ-0008`..`0013` | 23 | `[4], [5], [4], [5], [6], [8]` | IEEE | `matched` | `ref-0004..0008` | Đúng |
| 14–15 | `occ-0014`..`0015` | 24 | `[7], [13]` | IEEE | `matched` | `ref-0007, 0013` | Đúng |
| 16–20 | `occ-0016`..`0020` | 25 | `[12], [10], [11], [10], [11]` | IEEE | `matched` | `ref-0010..0012` | Đúng |
| 21 | `occ-0021` | 26 | `[18]` | IEEE | `matched` | `ref-0018` | Đúng |
| 22–26 | `occ-0022`..`0026` | 27 | `[25], [19], [20], [21], [22]` | IEEE | `matched` | `ref-0019..0025` | Đúng *(nhưng trang 27 bị rơi mất `\n[23].`)* |
| 27 | `occ-0027` | 35 | `[26]` | IEEE | `matched` | `ref-0026` | Đúng |
| **28** | `occ-0028` | 40 | `(Author et al., 2020)` | APA | `missing_reference` | `None` | **SAI:** Bắt nhầm chuỗi cú pháp mẫu trong `Table 4.2` |
| **29** | `occ-0029` | 40 | `(Author, 2020)` | APA | `missing_reference` | `None` | **SAI:** Bắt nhầm chuỗi cú pháp mẫu trong `Table 4.2` |
| **30** | `occ-0030` | 40 | `Author (2020)` | APA | `missing_reference` | `None` | **SAI:** Bắt nhầm chuỗi cú pháp mẫu trong `Table 4.2` |
| **31** | `occ-0031` | 40 | `Author (2020)` | APA | `missing_reference` | `None` | **SAI:** Bắt nhầm chuỗi cú pháp mẫu trong `Table 4.2` |
| **32–34** | `occ-0032`..`0034` | 40 | `[1,2]`, `[1]`, `[3]` | IEEE | `matched` | `ref-0001..0003` | **SAI:** Bắt nhầm chuỗi mẫu `IEEE [1], [1,2], [1]–[3]` trong `Table 4.2` |
| **35** | `occ-0035` | 40 | `(Author 2020, p. 5)` | Harvard | `missing_reference` | `None` | **SAI:** Bắt nhầm chuỗi cú pháp mẫu trong `Table 4.2` |
| **36** | `occ-0036` | 52 | `[0, 1]` | IEEE | `matched` | `ref-0001` | **SAI:** Khoảng toán học `confidence in [0, 1]` bị nối vào bài báo `[1]`! |
| **37** | `occ-0037` | 53 | `[0, 100]` | IEEE | `missing_reference` | `None` | **SAI:** Khoảng toán học `number in [0, 100]` bị báo lỗi thiếu reference! |

### 3.2. Bảng 34 Verdicts trong [`reports/thesis.json`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/reports/thesis.json)

| # | ID | Tài liệu gốc trong `thesis.pdf` | Nhãn hiện tại | Nhãn đúng kỳ vọng | Nguyên nhân sai lệch hiện tại |
| :-: | :--- | :--- | :---: | :---: | :--- |
| 1 | `ref-0001` | `[1] Lopez, P. (2009). GROBID...` | `verified` (0.80) | `verified` | Đúng (`local_db`). |
| 2 | `ref-0002` | `[2] Jurtz, P., & Xu, A. (2024). MuPDF...` | `unresolved` (0.34) | `unresolved` / `suspected_hallucination` | Tác giả trong thesis sai; bị chặn ở `R-CONTENT-ALIGNMENT` trên bài báo lạ (`dna-parser`). |
| 3 | `ref-0003` | `[3] Stanley, C. (2024). pdfplumber...` | `unresolved` (0.30) | `unresolved` / `suspected_hallucination` | Tác giả trong thesis sai; S2 429 + OpenAlex 0 hit → `R-FAIL-ALL`. |
| 4 | `ref-0004` | `[4] Crossref. (2024)... https://api.crossref.org/` | `unresolved` (0.40) | **`resource`** | **Lỗi mất URL** khi qua GROBID & SectionSegmenter cắt sai trang. |
| 5 | `ref-0005` | `[5] OpenAlex. (2024)... https://docs.openalex.org/` | `unresolved` (0.47) | **`resource`** | **Lỗi mất URL** khi qua GROBID & SectionSegmenter cắt sai trang. |
| 6 | `ref-0006` | `[6] Allen Institute for AI. (2024)... https://api.semanticscholar.org/` | `unresolved` (0.40) | **`resource`** | **Lỗi mất URL** + GROBID tách sai tên tổ chức thành `["Institute, Allen", "A I"]`. |
| 7 | `ref-0007` | `[7] International DOI Foundation. (2023)... https://www.doi.org/...` | `unresolved` (0.54) | **`resource`** | **Lỗi mất URL** khi qua GROBID & SectionSegmenter cắt sai trang. |
| 8 | `ref-0008` | `[8] ACL. (2024). ACL Anthology... https://aclanthology.org/` | `unresolved` (0.36) | **`resource`** | **Lỗi mất URL** khi qua GROBID & SectionSegmenter cắt sai trang. |
| 9 | `ref-0009` | `[9] Fellegi & Sunter (1969). A theory for record linkage` | `verified` (0.80) | `verified` | Đúng (`local_db`), nhưng mất liên kết in-text `[9]` do xuống dòng. |
| 10 | `ref-0010` | `[10] Devlin et al. (2019). BERT...` | `verified` (0.80) | `verified` | Đúng (`local_db`). |
| 11 | `ref-0011` | `[11] Reimers & Gurevych (2020). Sentence-BERT...` | `unresolved` (0.40) | **`verified`** | **Lỗi `rules.py:233`:** `local_db` có bài năm `2019` (`year_dist=1 <= year_tolerance`), nhưng rule đòi `year_dist == 0`. |
| 12 | `ref-0012` | `[12] Beltagy, Lo, & Cohan (2019). SciBERT...` | `verified` (0.70) | `verified` (0.80) | Họ `"Lo"` bị `_INITIAL_RE` biến thành `"kyle"`, làm `author_jaccard` giảm còn `0.5`. |
| 13 | `ref-0013` | `[13] Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y... (2023)` | `unresolved` (0.40) | **`verified`** | **Lỗi `_INITIAL_RE`:** 4 họ 2 chữ cái (`Ji, Yu, Su, Xu`) bị biến thành tên riêng, làm `author_jaccard` tụt xuống `0.125`. |
| 14 | `ref-0014` | `[14] Sadasivan et al. (2023). Can AI-generated text... arXiv:2303.11156` | `unresolved` (0.40) | **`verified` / `metadata_error`** | Mất mã `arXiv:2303.11156` khi qua GROBID; `local_db` khớp tiêu đề (`0.95`) và năm (`2023`) nhưng đồng tác giả cuối trong thesis lệch (`author_jaccard=0.375`). |
| 15 | `ref-0015` | `[15] Jin, Z., Chen, X... (2024). Be honest or leave...` | `metadata_error` (0.65) | **`unresolved` / `suspected_hallucination`** | **Lỗi `Rule 4b`:** Bắt nhầm bài `AI-LieDar` (`author_jaccard=0.0`) chỉ vì citation có họ `"Wang"`, `"Chen"`, `"Liu"`. |
| 16 | `ref-0016` | `[16] Goodfellow, Bengio, Courville (2016). Deep learning` | `verified` (0.78) | `verified` | Đúng (OpenAlex). |
| 17 | `ref-0017` | `[17] Sculley et al. (2015). Hidden technical debt...` | `verified` (0.80) | `verified` | Đúng (`local_db`), nhưng mất liên kết in-text `[17]` do xuống dòng. |
| 18 | `ref-0018` | `[18] Geifman & El-Yaniv (2017). Selective classification...` | `verified` (0.80) | `verified` | Đúng (`local_db`). |
| 19 | `ref-0019` | `[19] Brier, G. W. (1950). Verification of forecasts...` | `verified` (0.80) | `verified` | Đúng (`local_db`). |
| 20 | `ref-0020` | `[20] Guo et al. (2017). On calibration of modern neural...` | `verified` (0.80) | `verified` | Đúng (`local_db`). |
| 21 | `ref-0021` | `[21] Cohen, J. (1960). A coefficient of agreement...` | `verified` (0.80) | `verified` | Đúng (`local_db`). |
| 22 | `ref-0022` | `[22] Krippendorff, K. (2004). Content analysis...` | `unresolved` (0.40) | **`verified`** | Crossref trả bản tái bản năm 2019 (`title=1.0, author=1.0, year_dist=15`); thiếu rule cho sách tái bản. |
| 23 | `ref-0023` | `[23] Artstein & Poesio (2008). Inter-coder agreement...` | `verified` (0.80) | `verified` | Đúng (`local_db`), nhưng mất liên kết in-text `[23]` do xuống dòng. |
| 24 | `ref-0024` | `[24] Chawla, S. V. (2008). Data mining for imbalanced...` | `unresolved` (0.27) | **`metadata_error` / `verified`** | Khớp `title=0.90, author=1.0`, lệch năm `2010 vs 2008` (`year_dist=2`); bị `R-CONTENT-ALIGNMENT` chặn trước `R-METADATA-ERR`. |
| 25 | `ref-0025` | `[25] Hand, D. J. (2009). Measuring classifier performance...` | `verified` (0.80) | `verified` | Đúng (`local_db`). |
| 26 | `ref-0026` | `[26] Richardson & O'Flanagan (2024). FastAPI...` | `unresolved` (0.21) | `unresolved` / `suspected_hallucination` | Tác giả trong thesis sai; bị chặn ở `R-CONTENT-ALIGNMENT` trên bài báo không liên quan. |
| 27 | `ref-0027` | `[27] Markstein, E. (2008). Citation analysis. In Encyclopedia of GIS` | `unresolved` (0.40) | `unresolved` / `metadata_error` | Crossref trả về mục từ `"Citation Analysis"` (2008) nhưng khuyết tác giả (`authors=[]`). |
| **28–34** | `ref-0028`..`0034` | **7 bảng & đoạn văn của Chapter 5 & 6 (`Table 5.1` .. `CHAPTER 6`)** | `resource` (1) + `unresolved` (6) | **KHÔNG TỒN TẠI (Phải loại bỏ)** | Do `SectionSegmenter` cắt nhầm trang 57–63 làm `BIBLIOGRAPHY`! |

---

## PHẦN 4: Đề xuất phương án xử lý triệt để (Root-Cause Fix Plan kèm Code)

Dưới đây là thiết kế giải pháp sửa tận gốc từng vấn đề theo đúng kiến trúc của dự án.

---

### Fix 1: Sửa triệt để `SectionSegmenter` (Không bắt nhầm từ đơn trong bảng hoặc câu văn xuôi làm Header)

* **File:** [`src/integrity_checker/extraction/section_segmenter.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/section_segmenter.py)
* **Nguyên nhân cần triệt tiêu:**
  1. `_BIBLIOGRAPHY_HEADER_PATTERNS` cho phép từ số ít `reference` và không kiểm tra hình thái dòng tiêu đề (ví dụ chữ `'reference'` viết thường bị rớt dòng trong ô bảng `Table 5.1`).
  2. `_APPENDIX_HEADER_PATTERNS` có `r"^\s*appendix(?:\s+[A-Z0-9]+)?\b.*$"` khớp với bất kỳ dòng văn xuôi nào bắt đầu bằng `"Appendix C, chance-corrected..."`.
  3. `_find_boundaries` lấy trang đầu tiên khớp (`break`) mà không kiểm tra xem trang đó có thực sự chứa danh mục tài liệu tham khảo (hay chỉ là 1 dòng trùng tên), và khi có nhiều trang khớp thì không ưu tiên trang có tiêu đề chuẩn (`REFERENCES` viết hoa/Title Case kèm các mục tài liệu tham khảo bên dưới).
* **Cách sửa triệt để:**
  1. **Siết chặt `_BIBLIOGRAPHY_HEADER_PATTERNS` và `_page_has_bibliography_header`:**
     * Không chấp nhận từ đơn `"reference"` viết thường toàn bộ (`line.strip().islower()`). Tiêu đề mục Tài liệu tham khảo tiếng Anh phải là số nhiều `References` / `REFERENCES` (hoặc `Reference List`), và ít nhất phải viết hoa chữ cái đầu (`References`, `REFERENCES`, `Bibliography`, `Tài liệu tham khảo`).
     * Kiểm tra xác nhận nội dung trang (`_page_looks_like_bibliography_start`): một trang có tiêu đề `References` thật sự phải có các mục tài liệu tham khảo ngay bên dưới nó (hoặc ở đầu trang kế tiếp nếu tiêu đề nằm cuối trang), chứ không phải là một bảng `Table 5.1`!
  2. **Siết chặt `_APPENDIX_HEADER_PATTERNS` và `_page_has_appendix_header`:**
     * Tiêu đề phụ lục chỉ được phép có dạng:
       `Appendix`, `APPENDIX`, `Appendices`, `Appendix A`, `Appendix A: Title`, `Appendix A. Title`, `Appendix A — Title`, `Phụ lục 1: ...`
     * **Tuyệt đối cấm dấu phẩy `,` ngay sau mã phụ lục** (vì `"Appendix C, ..."` là câu văn xuôi tham chiếu tới phụ lục) và giới hạn độ dài dòng tiêu đề (`<= 80` ký tự, không kết thúc bằng từ nối câu văn xuôi như `will be`, `is`, `was`, `and`).

```python
# Trong src/integrity_checker/extraction/section_segmenter.py

_BIBLIOGRAPHY_HEADER_PATTERNS = [
    r"^\s*(?:(?:\d+|I{1,3}|IV|V|VI{0,3}|IX|X)\.?\s+)?(?:references|reference\s+list)\s*:?\s*$",
    r"^\s*(?:(?:\d+|I{1,3}|IV|V|VI{0,3}|IX|X)\.?\s+)?bibliography\s*:?\s*$",
    r"^\s*(?:\d+\.?\s+)?works\s+cited\s*:?\s*$",
    r"^\s*(?:\d+\.?\s+)?literature\s+cited\s*:?\s*$",
    r"^\s*(?:(?:\d+|I{1,3}|IV|V|VI{0,3}|IX|X)\.?\s+)?tài\s+liệu\s+tham\s+khảo\s*:?\s*$",
    r"^\s*(?:\d+\.?\s+)?danh\s+mục\s+tài\s+liệu(?:\s+tham\s+khảo)?\s*:?\s*$",
]

_APPENDIX_HEADER_PATTERNS = [
    # Chỉ khớp tiêu đề độc lập: "APPENDIX", "Appendix A", "Appendix A. Title", "Appendix A: Title"
    # KHÔNG khớp câu văn xuôi như "Appendix C, chance-corrected..."
    r"^\s*(?:appendix|appendices)(?:\s+[A-Z0-9]{1,3}(?:\s*[:.\-—]\s*[^,;]{1,70})?)?\s*$",
    r"^\s*phụ\s+lục(?:\s+[A-Z0-9]{1,3}(?:\s*[:.\-—]\s*[^,;]{1,70})?)?\s*$",
]
```

Và trong `_page_has_bibliography_header(page)` / `_page_has_appendix_header(page)`:
* Bỏ qua các dòng viết thường hoàn toàn (`if stripped.islower(): continue`) — vì không có tiêu đề chương/mục nào viết thường toàn bộ (`"reference"`).
* Trong `_find_boundaries(pages)`: Nếu tìm thấy nhiều ứng viên trang có header Bibliography, ưu tiên trang mà nội dung bên dưới (hoặc trang kế tiếp) thực sự có các dấu hiệu của danh mục tài liệu tham khảo (`_count_reference_like_lines(page) >= 2` hoặc có các mốc `[1]`, `[2]`, `(19xx|20xx)`).

---

### Fix 2: Bảo toàn URL, arXiv ID, Raw Text và Sửa lỗi tách tên tổ chức khi Merge GROBID + Regex

* **Files:**
  * [`src/integrity_checker/extraction/document_parser.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L384-L510)
  * [`src/integrity_checker/extraction/grobid_adapter.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_adapter.py#L467-L586)
  * [`src/integrity_checker/extraction/grobid_parser.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_parser.py)
* **Cách sửa triệt để:**
  1. **Khi Fix 1 hoàn tất**, `SectionSegmenter` sẽ cắt đúng trang 68–70 làm `BIBLIOGRAPHY`. Nhờ đó `ReferenceListParser` (nhánh Regex) sẽ trích xuất đúng 27 mục `[1]`–`[27]` từ trang 68–70 (bao gồm đầy đủ `url`, `raw_text` gốc có `Retrieved from https://...` và `arXiv:2303.11156`, cùng `numeric_index = 1..27`) và **không còn 7 mục rác `ref-0028`..`ref-0034` từ Chapter 5 & 6 nữa**.
  2. **Sửa [`_merge_references`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L384-L453) và [`_enrich_grobid_ref`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L495-L510) trong `document_parser.py`:**
     * Bổ sung so khớp giữa `grobid_ref` và `regex_ref` theo cả **`numeric_index`** (nếu `grobid_ref.numeric_index == regex_ref.numeric_index` và tiêu đề tương đồng `>= 0.65`) bên cạnh DOI và title similarity.
     * Trong `_enrich_grobid_ref(target, donor)`:
       * Copy thêm **`url`** (`for attr in ("doi", "url", "volume", "issue", "pages", "venue"):`).
       * Nếu `donor.raw_text` chứa URL (`http://`, `https://`), `arXiv:`, hoặc `doi:` mà `target.raw_text` (do GROBID tổng hợp) bị thiếu, hoặc `donor.raw_text` dài và đầy đủ hơn, bảo toàn `raw_text` gốc từ PDF (`donor.raw_text`) hoặc nối phần URL/arXiv vào `target.raw_text`.
       * Nếu `donor` phát hiện tác giả là tên tổ chức (như `"Allen Institute for AI"`, `"International DOI Foundation"`, `"Association for Computational Linguistics"`) trong khi GROBID tách nhầm thành `["Institute, Allen", "A I"]`, ưu tiên giữ `donor.authors`.
  3. **Sửa `grobid_parser.py` & `grobid_adapter.py`:**
     * Trích xuất thẻ `<ptr target="..."/>` và `<idno type="arXiv">...</idno>` trong `<biblStruct>` của GROBID TEI XML vào `GrobidReference.url` / `raw_text` để ngay cả khi không có regex donor, GROBID vẫn giữ được URL và arXiv ID.

---

### Fix 3: Sửa `CitationExtractor` (Không làm rơi trích dẫn đầu dòng `\n[9],` & Không bắt nhầm khoảng toán học `[0, 1]`, `[0, 100]` hay ví dụ `"Author (2020)"`)

* **Files:**
  * [`src/integrity_checker/extraction/citation_extractor.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/citation_extractor.py#L67-L85)
  * [`src/integrity_checker/extraction/patterns/ieee.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/patterns/ieee.py)
  * [`src/integrity_checker/extraction/patterns/apa.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/patterns/apa.py)
* **Cách sửa triệt để:**
  1. **Sửa [`_is_reference_list_marker(raw_text, raw_start, raw_end)`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/citation_extractor.py#L67-L85):**
     * Một ký hiệu `[N]` ở đầu dòng chỉ là **Reference List Marker** (đầu mục tài liệu tham khảo) khi ký tự ngay sau `[N]` là khoảng trắng đi kèm chữ cái viết hoa của tên tác giả (`^\s+[A-ZÀ-Ỹ]`).
     * Nếu ngay sau `[N]` là dấu câu (`,`, `.`, `;`, `:`, `)`, `]`) hoặc từ nối viết thường (`^\s+[a-z]`, ví dụ `\n[9], and...`, `\n[14] show that...`, `\n[23].`), thì đó **100% là trích dẫn in-text bị xuống dòng do căn lề PDF**, tuyệt đối không được loại bỏ!
     ```python
     @staticmethod
     def _is_reference_list_marker(raw_text: str, raw_start: int, raw_end: int | None = None) -> bool:
         prefix = raw_text[:raw_start]
         if not (prefix == "" or prefix.isspace() or re.search(r"\n\s*$", prefix)):
             return False
         if raw_end is not None and raw_end < len(raw_text):
             suffix = raw_text[raw_end:]
             # Nếu ngay sau [N] là dấu câu (, . ; : )) hoặc chữ thường -> là in-text citation bị rớt dòng!
             if re.match(r"^\s*[,.;:)\]]", suffix) or re.match(r"^\s+[a-z]", suffix):
                 return False
         return True
     ```
  2. **Loại bỏ khoảng toán học `[0, 1]`, `[0, 100]` trong `patterns/ieee.py`:**
     * Chỉ số tài liệu tham khảo luôn bắt đầu từ `1` (`[1-9]\d{0,2}`), **không bao giờ có tài liệu tham khảo số `0`**.
     * Sửa regex `_IEEE_INLINE_RE` trong [`patterns/ieee.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/patterns/ieee.py#L36-L43) từ `\d{1,3}` thành `[1-9]\d{0,2}`:
       ```python
       _IEEE_INLINE_RE = re.compile(
           r"\["
           r"([1-9]\d{0,2}(?:\s*[,\-–—]\s*[1-9]\d{0,2})*)"
           r"\]"
       )
       ```
       Chỉ với thay đổi 1 dòng này, mọi khoảng toán học bắt đầu bằng `0` như `[0, 1]`, `[0, 100]`, `[0, 255]` sẽ tự động bị loại bỏ hoàn toàn!
  3. **Loại bỏ tên tác giả giả định `"Author"` trong bảng cú pháp (`Table 4.2`):**
     * Trong `CitationExtractor` / `apa.py` / `harvard.py`: Thêm `"author"`, `"authors"` vào tập `_NON_AUTHOR_WORDS` để các chuỗi minh họa cú pháp như `(Author et al., 2020)`, `(Author, 2020)`, `Author (2020)`, `(Author 2020, p. 5)` trong bảng tài liệu kỹ thuật không bị trích xuất thành trích dẫn thật.

---

### Fix 4: Nối đúng kết quả của `CitationLinker` vào `Verdict` và `linking_summary`

* **File:** [`src/integrity_checker/pipeline/integrity_pipeline.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/pipeline/integrity_pipeline.py#L676-L705) và [`citation_linker.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/linking/citation_linker.py#L553-L601)
* **Cách sửa triệt để:**
  1. **Trong [`CitationLinker._apply_links_to_Model`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/linking/citation_linker.py#L553-L601):**
     * Hiện tại hàm này chỉ gán `mapping_status` và `citation_links` cho `body_citations`. Cần gán luôn cho cả `references` (`ref-0001`..`ref-0027`) dựa trên `ref_id_to_occurrences` và `uncited_reference_ids`:
       * Nếu `ref.reference_id` có trong `ref_id_to_occurrences` (được ít nhất 1 in-text citation trỏ tới với `status == MATCHED`): gán `ref.mapping_status = CitationMappingStatus.MATCHED`, `ref.mapping_confidence = max(l.confidence for l in matched_links)`, và `ref.citation_links = matched_links`.
       * Nếu `ref.reference_id` nằm trong `uncited_reference_ids`: gán `ref.mapping_status = CitationMappingStatus.UNCITED_REFERENCE`, `ref.mapping_confidence = 1.0`.
       * Nếu `ref.reference_id` nằm trong `duplicate_reference_ids`: gán `ref.mapping_status = CitationMappingStatus.DUPLICATE_REFERENCE`.
  2. **Trong [`IntegrityPipeline.run_async` (dòng 676–699)](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/pipeline/integrity_pipeline.py#L676-L699):**
     * Xóa bỏ đoạn code lỗi kiểm tra `best.doi == citation.doi` ở dòng 680–691!
     * Thay vào đó, lấy trực tiếp `citation.mapping_status` và `citation.mapping_confidence` đã được `CitationLinker` gán ở bước 3b (và chỉ fallback sang kiểm tra DOI/title nếu văn bản không có body citations nào).
  3. **Trong [`IntegrityPipeline._compute_linking_summary`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/pipeline/integrity_pipeline.py#L1185-L1203):**
     * Tính `linking_summary` từ cả `verdicts` (đã có `mapping_status` chuẩn của từng `reference_list`) VÀ các lỗi `missing_reference` / `in_text_mismatch` / `ambiguous_mapping` từ `body_citations`.
  * **Tác dụng ngay lập tức:**
    * Tất cả các tài liệu `[1]`–`[27]` được trích dẫn trong bài sẽ có `mapping_status = "matched"` (`mapping_confidence = 0.90`).
    * Biến `mapping_is_matched` trong `SymbolicRules` sẽ bằng `True`!
    * Các gợi ý thừa `"Hệ thống chưa đủ thông tin để liên kết"` sẽ biến mất hoàn toàn khỏi các tài liệu đã liên kết!

---

### Fix 5: Sửa lỗi `_INITIAL_RE` trong `author_matcher.py` làm hỏng mọi họ 2 chữ cái (`Ji`, `Yu`, `Su`, `Xu`, `Lo`, `Ge`, `Li`, `Wu`, `Le`, `Vo`)

* **File:** [`src/integrity_checker/matching/author_matcher.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/matching/author_matcher.py#L46-L135)
* **Nguyên nhân gốc rễ:**
  * `_INITIAL_RE = re.compile(r"^[A-Z]\.?$|^[A-Z]\.?[A-Z]\.?$", re.IGNORECASE)` chạy **sau khi** chuỗi đã bị `.lower()` và `_strip_punctuation()` (biến `"J.K."` thành `"j k"`, còn `"Ziwei Ji"` thành `"ziwei ji"`).
  * Do dấu chấm đã bị xóa trước khi kiểm tra `_INITIAL_RE`, nhánh `^[A-Z]\.?[A-Z]\.?$` với `re.IGNORECASE` thực chất khớp với **mọi từ dài 2 chữ cái bất kỳ** (`"ji"`, `"yu"`, `"su"`, `"xu"`, `"lo"`, `"ge"`, `"li"`, `"wu"`, `"le"`, `"vo"`)!
* **Cách sửa triệt để:**
  * Khi chuỗi không có dấu phẩy (ví dụ `"Ziwei Ji"`, `"Kyle Lo"`, `"J. K. Smith"`, `"Smith J K"`):
    * Một token dài **1 ký tự** (`len(t) == 1`) luôn là chữ viết tắt (initial).
    * Một token dài **2 ký tự** ở dạng gốc (trước khi `.lower()` và xóa dấu chấm) chỉ là chữ viết tắt nếu trong chuỗi gốc nó **có dấu chấm** (như `"J.K."`) hoặc **viết hoa cả 2 chữ cái** (như `"JK"` trong `"Smith JK"`), chứ nếu ở chuỗi gốc nó là chữ hoa kèm chữ thường (`"Ji"`, `"Yu"`, `"Su"`, `"Xu"`, `"Lo"`, `"Ge"`, `"Li"`, `"Wu"`, `"Le"`, `"Vo"`) thì đó **chắc chắn 100% là Họ (Surname), không phải chữ viết tắt!**
  ```python
  # Trong src/integrity_checker/matching/author_matcher.py
  # Kiểm tra trực tiếp trên token gốc trước khi lower() hoặc chỉ coi token 1 ký tự là initial:
  _RAW_INITIAL_TOKEN_RE = re.compile(
      r"^(?:[A-Z]\.?|[A-Z]\.[A-Z]\.?|[A-Z]{2})$"  # Chú ý: KHÔNG bật re.IGNORECASE!
  )
  ```
  * Khi áp dụng sửa đổi này:
    * `"Ziwei Ji"` → `"Ji"` có 1 chữ hoa + 1 chữ thường → không phải initial → trả về họ `"ji"`!
    * `"Tiezheng Yu"` → `"yu"`, `"Dan Su"` → `"su"`, `"Yan Xu"` → `"xu"`, `"Kyle Lo"` → `"lo"`!
    * `"Smith JK"` hoặc `"Smith J.K."` → `"JK"` / `"J.K."` viết hoa cả 2 chữ cái → là initial → trả về họ `"smith"`!
    * Nhờ đó:
      * `[12] Beltagy, Lo, & Cohan (2019)` tăng `author_jaccard` từ `0.50` lên **`1.00`** (`R-LOCAL_DB_VERIFIED`, `conf=0.80`)!
      * `[13] Ji et al. (2023)` tăng số tác giả khớp từ 2 lên 6/8 tác giả (`author_jaccard = 0.50`), cộng với `content_alignment_score = 0.80 (high)` và `title_sim = 1.0`, được xác minh chính xác!

---

### Fix 6: Sửa 4 lỗi logic trong `SymbolicRules` (`src/integrity_checker/logic/rules.py`)

* **File:** [`src/integrity_checker/logic/rules.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py)
* **Chi tiết 4 điểm sửa trong `rules.py`:**

1. **Cho phép `year_dist <= self.year_tolerance` trong `_rule_local_db_verified` và `_rule_local_db_good_match`:**
   * Tại [`rules.py:233`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py#L233) và [`rules.py:298`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py#L298):
     * Đổi `if title_sim >= 0.90 and author_sim >= 0.80 and year_dist == 0:` thành `if title_sim >= 0.90 and author_sim >= 0.80 and year_dist <= self.year_tolerance:`.
     * Đổi `if title_sim >= 0.85 and author_sim >= 0.50 and year_dist == 0:` thành `if title_sim >= 0.85 and author_sim >= 0.50 and year_dist <= self.year_tolerance:`.
   * **Tác dụng:** Các bài báo preprint arXiv năm 2019 xuất bản chính thức năm 2020 (như `[11] Sentence-BERT`) khớp trong `local_db` sẽ được `VERIFIED` ngay lập tức thay vì rơi xuống `UNRESOLVED`.

2. **Bổ sung hỗ trợ sách tái bản (Edition Year Tolerance) và đồng tác giả bị lược bớt (`et al.` / partial author list):**
   * Với `[22] Krippendorff, K. (2004). Content analysis: An introduction to its methodology`: Khi `title_sim >= 0.95` và `author_sim == 1.0` (khớp tuyệt đối cả tiêu đề dài và toàn bộ tác giả) trên nguồn học thuật uy tín (`_has_live_source` hoặc `local_db`), nhưng `year_dist > self.year_tolerance`, đây là trường hợp **khác năm tái bản (edition difference)** hoặc **lỗi năm xuất bản (`METADATA_ERROR` về `year`)**, không phải `UNRESOLVED` do thiếu bằng chứng (`R-WEAK-EVIDENCE`).
   * Với `[13] Ji et al. (2023)` và `[14] Sadasivan et al. (2023)`: Khi bài báo có nhiều tác giả (`>= 5` tác giả), tác giả đầu tiên (`first_author`) khớp chính xác, `title_sim >= 0.95`, `year_dist <= self.year_tolerance`, nhưng một vài đồng tác giả ở cuối danh sách bị ghi sai (`0.35 <= author_sim < 0.50`), hệ thống cần phân loại vào `METADATA_ERROR` (chỉ rõ trường lệch là `authors`) hoặc `VERIFIED` (nếu `author_sim >= 0.50`), thay vì rơi vào `R-WEAK-EVIDENCE` (`UNRESOLVED`).

3. **Sửa Rule 4b (`R-KNOWN-AUTHOR-TITLE-MISMATCH`, dòng 1020–1038):**
   * Yêu cầu bắt buộc: Tác giả của `candidate` tìm được trên DB phải thực sự trùng khớp với tác giả trong `citation` (`author_sim >= 0.5`), chứ không được phép chỉ nhìn thấy họ `"Wang"`, `"Chen"`, `"Liu"` trong `citation` rồi ghép đại vào một bài báo của tác giả khác (`author_sim == 0.0`)!
   ```python
   # Rule 4b FIXED: Phải có author_sim >= 0.5 (cùng tác giả thật sự trên candidate)
   if (
       author_sim >= 0.5
       and self._is_known_academic_author_pattern(citation)
       and 0.3 <= title_sim < self.title_threshold
   ):
       ...
   ```

4. **Sửa thứ tự và điều kiện của Rule 3g (`R-CONTENT-ALIGNMENT` nhánh uncertain `0.2 <= score < 0.5`, dòng 988–999):**
   * Không cho nhánh uncertain (`0.2 <= content_alignment_score < 0.5`) trả về `UNRESOLVED` sớm ở bước 3g làm chặn mất Rule 4 (`R-METADATA-ERR`), HOẶC chỉ chạy kiểm tra `content_alignment_score` khi `candidate` tìm được thực sự là bài báo đang xét (`title_sim >= 0.80 and author_sim >= 0.5`).
   * Nếu `candidate` chỉ là một bài báo ngẫu nhiên không khớp tác giả (`author_sim == 0.0`), điểm `content_alignment_score` giữa câu văn trong bài khóa luận và tiêu đề bài báo ngẫu nhiên đó không có ý nghĩa xác thực và không được phép ghi đè lý do của verdict!

---

### Fix 7: Thống nhất Logging (`logging.py`) & Giảm tải Semantic Scholar Rate Limit (`integrity_pipeline.py`)

* **Files:**
  * [`src/integrity_checker/logging.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logging.py)
  * [`src/integrity_checker/pipeline/integrity_pipeline.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/pipeline/integrity_pipeline.py#L618-L620)
* **Cách sửa triệt để:**
  1. **Thêm `InterceptHandler` chuẩn của `loguru` vào [`configure_logging()`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logging.py#L14-L45):**
     * Bắt toàn bộ log từ `logging.getLogger("integrity_checker.*")` đẩy qua `loguru.logger` để mọi quyết định của `SectionSegmenter`, `DocumentParser`, `ReferenceListParser`, `CitationLinker`, `CISCalculator` đều xuất hiện đầy đủ, đồng nhất trong console và file `data/logs/integrity_checker.log`.
  2. **Giới hạn độ song song khi gọi `orchestrator.retrieve` trong `IntegrityPipeline.run_async`:**
     * Bọc `asyncio.Semaphore(4)` quanh `self.orchestrator.retrieve(c)` trong `IntegrityPipeline.run_async` để tránh bắn đồng thời 25–35 request vào Semantic Scholar gây bão `HTTP 429`.

---

## PHẦN 5: Lộ trình thực thi & Kiểm thử chống hồi quy (Regression Testing)

Nếu bạn đồng ý với kế hoạch xử lý triệt để ở **Phần 4**, tôi sẽ thực hiện tuần tự 6 bước sau:

1. **Bước 1:** Cập nhật [`section_segmenter.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/section_segmenter.py), [`citation_extractor.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/citation_extractor.py), [`patterns/ieee.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/patterns/ieee.py), [`patterns/apa.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/patterns/apa.py) (Fix 1 & Fix 3).
2. **Bước 2:** Cập nhật [`document_parser.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py), [`grobid_parser.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_parser.py), [`grobid_adapter.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_adapter.py) để bảo toàn `url`, `arXiv ID`, `raw_text` và tên tổ chức (Fix 2).
3. **Bước 3:** Cập nhật [`citation_linker.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/linking/citation_linker.py) và [`integrity_pipeline.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/pipeline/integrity_pipeline.py) để truyền đúng `mapping_status`, `citation_links` và `linking_summary` (Fix 4 & Fix 7).
4. **Bước 4:** Cập nhật [`author_matcher.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/matching/author_matcher.py) và [`rules.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py), [`logging.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logging.py) (Fix 5, Fix 6 & Fix 7).
5. **Bước 5:** Viết thêm unit tests cho toàn bộ các edge cases vừa phát hiện và chạy lại toàn bộ bộ test `pytest` của dự án để đảm bảo không vỡ bất kỳ tính năng hiện có nào.
6. **Bước 6:** Chạy lại full pipeline trên [`thesis.pdf`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/thesis.pdf), xuất báo cáo mới và đối chiếu Trước vs. Sau trên từng chỉ số (`Section boundaries`, `extracted_citations`, `linking_summary`, 27 `verdicts`, và `CIS`).
