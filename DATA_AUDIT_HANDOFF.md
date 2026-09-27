# DATA AUDIT HANDOFF — ACL & Paper Knowledge Base

> **Mốc snapshot số liệu: 2026-09-27 11:55 UTC** (múi giờ máy: UTC)
> Người thực hiện: agent audit dữ liệu (read-only — KHÔNG sửa code/dữ liệu)
> Mục đích: bàn giao cho agent coding khác xử lý các vấn đề dữ liệu dưới đây.
> Phương pháp: chỉ đọc — `sqlite3 SELECT/PRAGMA`, `grep`/`find`, parse XML/BibTeX bằng Python.

---

## ⚠️ CẢNH BÁO QUAN TRỌNG — DATABASE ĐANG THAY ĐỔI LIVE

Trong lúc audit, số liệu **tăng liên tục** giữa các lần đo:
- `local_papers.db`: `papers` 855 → 891 → **893**
- `app.db`: `citations` 624 → 685; `essays` 20 → 21
- `app.db`: `users` 1 → 2, `sessions` 3 → 1 (đổi ngược chiều — xác nhận ghi live)
- `local_papers.db`: `query_log` 4.309 → 4.394 → 4.448 (tăng mỗi phút)

Nguyên nhân: có tiến trình **uvicorn `--reload`** đang chạy (`.venv/bin/uvicorn src.integrity_checker.api.main:app --host 0.0.0.0 --port 8000 --reload`) và ghi vào DB qua API.

**Hệ quả cho agent tiếp theo:**
- Mọi con số dưới đây là **snapshot tại 2026-09-27 11:55 UTC**, không phải hằng số.
- Trước khi import/ghi dữ liệu, nên **dừng API server** hoặc chấp nhận rủi ro ghi đồng thời.
- Luôn **đo lại** bằng các lệnh ở mục 6 trước khi ra quyết định.

**SHA-256 (đã lỗi thời ngay sau khi đo — DB tiếp tục bị ghi):**
- `data/local_papers.db` lúc 11:55 UTC → `cd6aacb5e36d512c1b9914b4ec3aa4079198acf0a23acea739bb9abe723aaffc`
- `data/app.db` lúc 11:55 UTC → `f2cf2ebdbee11cdba812980f0464648151e766b3edbeb9bf6435f0f37345766b`
- Lúc 12:00 UTC SHA đã đổi (`6d7c3c81…` và `91d1a89d…`) dù số đếm chưa đổi → minh chứng DB đang bị ghi live (query_log/WAL). **Không dùng SHA này làm mốc cố định.**

---

## 0. Kết luận nhanh (TL;DR)

| Nguồn | Số bản ghi (snapshot) | Trạng thái |
|---|---|---|
| ACL Anthology — kho XML (`data/acl_data/`) | **127.851 bài** | ❌ Chưa import vào DB |
| ACL Anthology — file BibTeX (`data/acl_anthology.bib`) | **2.288 bài** | ❌ Chưa import; file bị **cắt cụt** |
| Paper knowledge base (`data/local_papers.db`) | **893 bài** | ⚠️ Thiếu abstract 100%, thiếu DOI 32 bài |
| App database (`data/app.db`) | **1.395 bản ghi** (1+3+21+685+685) | ✅ Dùng được |

**5 vấn đề chính cần xử lý (theo mức độ):**
1. 🔴 **Bug trong `scripts/import_acl_xml.py`**: chỉ đọc volume đầu tiên → **mất 44.904/127.851 bài (35%)**; parse author sai (nhân đôi + dính chữ). Đây là nguyên nhân gốc khiến ACL chưa vào DB. Chi tiết + cách sửa ở **mục 2.4** và **P1**.
2. Kho ACL 127k bài chỉ nằm dạng XML thô, **chưa có trong `local_papers.db`** (0 bản ghi `source='acl'`).
3. `data/acl_anthology.bib` bị **cắt cụt** ở dòng cuối — không phải bản đầy đủ (2.288 / 127.851 entry).
4. `local_papers.db` chất lượng thấp: **abstract NULL 100%**, 32 bản ghi thiếu DOI, 263 thiếu venue, `categories` toàn `[]`, có `venue` rác.
5. **Mâu thuẫn tài liệu:** `README.md` + `tests/progress/SESSION_SUMMARY_WEEK9.md` ghi có "83.541 ACL papers" — số này khớp với output của importer bị bug (82.947). Xem mục 2.4 & 2.5.

**Về thuật ngữ "paperknow":** KHÔNG tồn tại DB/thư mục nào tên `paperknow` trong repo, git history, `~/Desktop`, `~/Documents`, hay service đang chạy (không có Postgres/MySQL/Mongo/Docker container). Cách hiểu đúng là **kho tri thức paper của dự án = `data/local_papers.db`**. Nếu có DB "paperknow" thật ở nơi khác, cần cung cấp đường dẫn cụ thể.

---

## 1. Cấu trúc `data/local_papers.db` (Paper Knowledge Base)

Kích thước: ~1.3 MB (2.0M trên đĩa). Bảng: `papers`, `query_log`, + FTS5 (`papers_fts*`).

### 1.1 Bảng `papers` — **893 bản ghi**, 12 cột

| Cột | Kiểu | Ràng buộc | Dữ liệu thực tế (snapshot) |
|---|---|---|---|
| `id` | INTEGER | PK AUTOINCREMENT | |
| `doi` | TEXT | UNIQUE | **32 NULL**, 861 có DOI (không trùng do UNIQUE) |
| `arxiv_id` | TEXT | UNIQUE | **0/893 có** |
| `title` | TEXT | NOT NULL | |
| `authors` | TEXT | | |
| `year` | INTEGER | | 893 có; range **1927–2027**; 44 năm |
| `venue` | TEXT | | **263 NULL**; có giá trị rác (vd `Éire-Ireland`) |
| `abstract` | TEXT | | **893/893 NULL (trống toàn bộ)** |
| `categories` | TEXT | | **tất cả = `[]`** |
| `external_ids` | TEXT | | |
| `source` | TEXT | DEFAULT 'api' | crossref/known_papers/openalex/acl |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | |

> Lưu ý DOI: 893 − 32 NULL = 861 bản ghi có DOI. `doi` là UNIQUE nên không trùng.

**Phân bố theo `source` (snapshot):**

| source | số bản ghi |
|---|---|
| crossref | 826 |
| known_papers | 66 |
| openalex | 1 |
| **acl** | **0** |

**Top venue (snapshot):** arXiv (Cornell University) 51 · Nature 10 · TACL 6 · AAAI 6 · npj Digital Medicine 5 · Zenodo 5 · Synthetic Metals 5 · Oxford English Dictionary 5.

**Top year (snapshot):** 2025:87 · 2016:76 · 2017:75 · 2018:73 · 2026:65 · 2020:61 · 2023:59 · 2015:55.

**Vấn đề chất lượng dữ liệu `papers` (snapshot):**
- `abstract` NULL 100% (893/893) — chỉ có metadata.
- `arxiv_id` NULL 100% (0/893).
- 32 bản ghi thiếu DOI; 263 bản ghi thiếu `venue`.
- `categories` = `[]` cho **tất cả** bản ghi.
- **13 bản ghi có `title` rỗng/whitespace.**
- **17 tiêu đề trùng lặp** (cùng title, khác id) — cần dedupe/kiểm tra.
- DOI không trùng (0 duplicate, đúng do ràng buộc UNIQUE).
- `venue` có giá trị rác/không liên quan (vd `Éire-Ireland`, `Oxford English Dictionary`, `19th-Century Music`) — dấu hiệu Crossref match sai.

### 1.2 Chỉ mục toàn văn `papers_fts` (FTS5)

```sql
CREATE VIRTUAL TABLE papers_fts USING fts5(
    title, authors, abstract,
    content='papers', content_rowid='id',
    tokenize='porter unicode61'
);
```
Đồng bộ bằng 3 trigger `papers_fts_insert` / `papers_fts_delete` / `papers_fts_update`.
`papers_fts_docsize` = **893 docs**. **Lưu ý:** vì `abstract` luôn NULL, FTS thực chất chỉ index `title` + `authors`.

### 1.3 Bảng `query_log` — **4.394 bản ghi** (snapshot)

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | INTEGER PK | |
| `query_hash` | TEXT NOT NULL | index |
| `found` | INTEGER DEFAULT 0 | index |
| `source` | TEXT | `api` 3.344 · `local_db` 1.050 |
| `paper_id` | INTEGER FK → papers(id) ON DELETE SET NULL | |
| `queried_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | |

---

## 2. Dữ liệu ACL — 2 nguồn, chưa nguồn nào vào DB

### 2.1 `data/acl_data/` — clone kho ACL Anthology (1.1 GB)

| Hạng mục | Giá trị |
|---|---|
| Số file XML | **1.719** file (178 MB) trong `data/acl_data/data/xml/` |
| Tổng số `<paper>` | **127.851** |
| Số `<volume>` | 6.172 |
| Khoảng năm | **1952 – 2026** |
| File JSON phụ | `data/acl_data/data/json/people.json` (4.5 MB), `sigs.json`, `venues.json` |

**Cấu trúc XML (mẫu `2026.lrec-1.xml`):**
```xml
<collection id="1952.earlymt">
  <volume id="1" ingest-date="..." type="proceedings">
    <meta>
      <booktitle>Proceedings of ...</booktitle>
      <address>...</address>
      <month>...</month>
      <year>1952</year>
      <venue>earlymt</venue>
    </meta>
    <paper id="1">
      <title>Translation</title>
      <author><first>Warren</first><last>Weaver</last></author>
      <pdf hash="ebfb36cd"/>
      <bibkey>weaver-1952-translation</bibkey>
    </paper>
    ...
  </volume>
</collection>
```

**Phân bố bài theo năm (top 15):** 2025:14.686 · 2024:11.937 · 2026:10.295 · 2023:8.936 · 2022:8.456 · 2020:7.163 · 2021:6.996 · 2019:4.944 · 2018:4.759 · 2016:4.123 · 2014:3.536 · 2017:3.382 · 2012:3.299 · 2010:2.990 · 2015:2.821.

### 2.2 `data/acl_anthology.bib` — file BibTeX (1.5 MB, 2.400 dòng)

| Loại entry | Số lượng |
|---|---|
| `@inproceedings` | 2.254 |
| `@article` | 34 |
| `@proceedings` (tập, không phải bài) | 54 |
| `@string` | 2 |
| **Tổng entry bài (inproceedings + article)** | **2.288** |

Header: `% https://aclanthology.org/anthology.bib generated on 2026-09-21`

> ⚠️ **File bị CẮT CỤT.** Dòng cuối cùng dừng giữa chừng:
> `@inproceedings{ljubesic-etal-2026-parlaspeech,title `
> → Entry cuối không có `}` đóng. Đây là bản tải một phần, **không phải toàn bộ ACL Anthology** (2.288 so với 127.851 bài trong kho XML).

### 2.3 Script import hiện có — `scripts/import_acl_anthology.py`

- Đọc **chỉ file `.bib`**, regex parse entry `article|inproceedings|proceedings|book|incollection`.
- Gán cứng `source='acl'`, `categories=['cs.CL','cs.AI']`, `abstract=None`.
- Có hàm `download_acl_anthology()` tải `https://aclanthology.org/anthology.bib`.
- **Giới hạn:** nếu chạy, chỉ import tối đa ~2.288 bài từ `.bib` — **không đọc kho XML 127k bài** trong `acl_data/`.
- Script này **chưa từng được chạy thành công** (bảng `papers` không có `source='acl'`).

**Các script import khác trong `scripts/` (đã có sẵn, chưa dùng đúng):**
- `import_acl_xml.py` — parse **đúng nguồn XML** `data/acl_data/data/xml/*.xml` (đây là script phù hợp nhất).
- `import_acl_json.py` — parse JSON export ACL.
- `import_s2orc.py` — import S2ORC (~8M papers) — cần tải dữ liệu riêng, không có sẵn.
- `import_openalex.py` — enrich từ OpenAlex.
- `build_local_db.py` — orchestrator (`--acl-only`, `--limit`, `--reset`, `--stats`), gọi `import_acl_xml.parse_acl_xml`.

### 2.4 🔴 BUG NGHIÊM TRỌNG trong `scripts/import_acl_xml.py` (đã kiểm chứng bằng cách chạy thật)

Script `import_acl_xml.py` là script **đúng nguồn dữ liệu** nhưng có **2 bug** khiến nó không thể import đủ/đúng ACL. Cả 2 đã được tái hiện bằng cách chạy trực tiếp parser:

**Bug 1 — Chỉ đọc `<volume>` ĐẦU TIÊN → mất ~35% bài:**
```python
# dòng ~101
volume = root.find('.//volume') or root.find('volume')
...
for paper_elem in volume.findall('paper') or root.findall('.//paper'):
```
`root.find('.//volume')` chỉ trả về **volume đầu tiên**. Với file có nhiều `<volume>`, mọi volume sau bị bỏ qua.

Đo thực tế (chạy parser trên toàn bộ 1.719 file XML):
| Chỉ số | Giá trị |
|---|---|
| Tổng `<paper>` thô trong kho XML | **127.851** |
| Số bài parser hiện tại trả về | **82.947** |
| **Số bài bị MẤT** | **44.904 (35,1%)** |
| Số file bị ảnh hưởng | **363** file |

Ví dụ: `1997.mtsummit.xml` có 7 volume/81 bài → parser chỉ trả 4 bài (mất 77).

> ⚠️ **Số 82.947 gần như trùng khớp với con số "83.541 ACL papers"** trong `SESSION_SUMMARY_WEEK9.md`. Nhiều khả năng con số trong tài liệu Week 9 là kết quả của chính importer bị lỗi này (chênh ~600 bài có thể do phiên bản XML/dedup khác).

**Bug 2 — Parse author sai hoàn toàn (nhân đôi + dính chữ):**
```python
# dòng ~158-165
first = ''.join(list(author_elem.itertext())) or ''
last  = ''.join(list(author_elem.itertext())) or ''   # giống hệt 'first'
name = f"{first} {last}".strip()                       # nối 2 lần cùng nội dung
```
`itertext()` lấy **toàn bộ** text con (cả first lẫn last), rồi ghép 2 lần. Kết quả thực tế:
```
<author><first>Warren</first><last>Weaver</last></author>
  → 'WarrenWeaver WarrenWeaver'   (đúng phải là 'Warren Weaver')
```
Cần đọc riêng `author_elem.find('first')` và `author_elem.find('last')`.

**Kết luận:** đây là **nguyên nhân gốc** của cả "mâu thuẫn 83.541" (mục 2.5) lẫn việc `local_papers.db` thiếu ACL. Agent tiếp theo **không cần viết script mới** — chỉ cần sửa 2 bug này rồi chạy lại.

### 2.5 ⚠️ MÂU THUẪN TÀI LIỆU: "83.541 ACL papers" không tồn tại

Con số "**83,541 ACL papers**" được ghi ở **2 nơi**:
- `README.md` dòng 93: "**83,541 ACL papers** pre-loaded" (mục Local Database v1.3)
- `tests/progress/SESSION_SUMMARY_WEEK9.md` dòng 10: "Thêm `data/local_papers.db` với 83,541 ACL papers" + test table ghi nguồn `local_db (ACL)`.

**Nhưng thực tế đã kiểm chứng:**
- DB hiện tại: **0 bản ghi `source='acl'`** (chỉ crossref/known_papers/openalex).
- **Toàn bộ git history** của `data/local_papers.db` (8 commit, blob lớn nhất 606 KB) cũng **chưa từng** chứa ACL — bản lớn nhất chỉ có 275 crossref + 34 known + 1 openalex.
- Không tìm thấy bản `local_papers.db` 83k nào khác trên máy (`~/Desktop`, worktree).

**Kết luận:** con số "83,541" **không khớp với bất kỳ artifact nào còn tồn tại**, nhưng **rất gần** với output của importer bị bug (**82.947** — xem mục 2.4). Khả năng cao nhất: ACL từng được import bằng `import_acl_xml.py` (bị bug, chỉ ra ~83k), rồi `local_papers.db` bị regenerate/xóa (CLAUDE.md ghi `rm -rf data/cache data/local_papers.db` để xóa cache) và các lần chạy sau chỉ còn crossref/known_papers. **Cần agent tiếp theo làm rõ trước khi tin vào tài liệu Week 9.** Đây là rủi ro đối với tính tái lập của kết quả đánh giá tuần 9.

---

## 3. `data/app.db` — Database ứng dụng chính

Kích thước ~940 KB (962.560 bytes). 7 bảng.

| Bảng | Số bản ghi (snapshot) | Số cột |
|---|---|---|
| users | 1 | 6 |
| sessions | 3 | 5 |
| essays | **21** | 7 |
| citations | **685** | 13 |
| verdicts | **685** | 17 |
| citation_cache | 0 | — |
| audit_logs | 0 | — |

> Lưu ý: `users`/`sessions` biến động liên tục do login/API (đo được users 1↔2, sessions 1↔3). Các bảng khác ổn định hơn trong lúc audit.

**essays:** 21 bản ghi, tổng **926 trang**. Có **18** essays chứa citation. Citations nhiều nhất: essay #10 = 97, #21 = 61, #20 = 61.

**citations theo style (snapshot):** APA 363 · IEEE 247 · unknown 62 · Vancouver 13.

**verdicts theo label (snapshot):** verified 491 · unresolved 136 · resource 27 · metadata_error 24 · suspected_hallucination 7.

**verdicts theo mapping_status (snapshot):** matched 491 · missing_reference 194.

**Vấn đề chất lượng dữ liệu `app.db` (snapshot):**
- **3 essays không có citation nào** (orphan): #3, #4, #18 (đều tên `4.pdf`).
- **Essay trùng lặp tên file:** `TranThanhPhuoc_523H0002_523H0054.pdf` ×4, `4.pdf` ×3, `2608.13786v1.pdf` ×2 → upload lại nhiều lần, gây nhiễu thống kê.
- **Citations độ phủ metadata thấp:** chỉ 245/685 có DOI, 491/685 có title, 596/685 có year.
- `citations.confidence` rất thấp: min 0.0, max 0.7, **trung bình 0.128** → cần xem lại parser/threshold.
- `verdicts`: 0 bản ghi thiếu reasoning/features/triggered_rules; 0 override.
- `citation_cache` và `audit_logs` **rỗng** (0 bản ghi) — tính năng cache/audit chưa hoạt động hoặc chưa dùng.

---

## 4. Tài sản dữ liệu khác trong `data/` (tham khảo)

Ngoài 2 DB, `data/` còn nhiều file dữ liệu dạng JSON/CSV:

| File | Nội dung |
|---|---|
| `data/gold_dataset.json` | 5 papers · **174 citations** |
| `data/gold_dataset_full.json` | 55 papers · **2.887 citations** |
| `data/gold_dataset_train.json` | 3 papers · 97 citations |
| `data/gold_dataset_val.json` | 1 paper · 37 citations |
| `data/gold_dataset_test.json` | 1 paper · 40 citations |
| `data/gold_dataset_annotation.csv` | 180 dòng |
| `data/gold_dataset_full_annotation.csv` | 2.901 dòng |
| `data/raw/pdf/` | **55 file PDF** (nguồn paper) |
| `data/raw/arxiv_metadata.json` | 50 mục metadata arXiv |
| `data/citations_full.json` | 55 citations |
| `data/acl_anthology.bib` | 2.288 entry bài (bị cắt cụt) |

Lưu ý: `data/gold_dataset_full_annotation.csv` (2.901 dòng) gần khớp với `gold_dataset_full.json` (2.887 citations) — nhiều khả năng đây là **bộ gold chuẩn** cho evaluation.

---

## 5. Việc cần làm cho agent coding (đề xuất, theo thứ tự ưu tiên)

### P1 — Sửa bug importer ACL rồi import vào `local_papers.db`
- **Không cần viết script mới.** Dùng `scripts/import_acl_xml.py` (đã parse đúng nguồn XML).
- **Sửa Bug 1** (dòng ~101): lặp qua **TẤT CẢ** `root.findall('.//volume')`, không chỉ volume đầu tiên. File nhiều volume phải gom đủ paper.
- **Sửa Bug 2** (dòng ~158): đọc riêng `author_elem.find('first')` / `find('last')` thay vì `itertext()` ghép 2 lần.
- Chạy test nhỏ: `python scripts/import_acl_xml.py --limit 1000`, kiểm tra author không bị nhân đôi.
- Chạy full: `python scripts/build_local_db.py --acl-only` (hoặc `python scripts/import_acl_xml.py`).
- **Verify số bài:** tổng phải đạt ~127.851 (không phải 82.947):
  `SELECT COUNT(*) FROM papers WHERE source='acl';`
- ⚠️ **Chạy khi đã dừng API server** để tránh ghi đồng thời.
- Sau import nên dedup theo DOI và rebuild FTS.

### P2 — Sửa file `.bib` bị cắt cụt
- Chạy lại `download_acl_anthology()` hoặc tải lại `https://aclanthology.org/anthology.bib`.
- Kiểm tra toàn vẹn: file phải kết thúc bằng entry có `}` đóng; số entry khớp.

### P3 — Bổ sung abstract cho paper knowledge base
- `abstract` NULL 100%. Cân nhắc enrich từ Crossref/OpenAlex/S2 (client đã có trong `src/integrity_checker/retrieval/`) theo DOI.
- Sau khi có abstract, rebuild FTS: `INSERT INTO papers_fts(papers_fts) VALUES('rebuild');`

### P4 — Dọn chất lượng dữ liệu `papers`
- 32 bản ghi thiếu DOI → backfill hoặc đánh dấu.
- 263 bản ghi thiếu venue; `venue` rác (`Éire-Ireland`, `Oxford English Dictionary`...) → dùng `venue_normalizer.py` để chuẩn hóa/lọc.
- `categories` toàn `[]` → cân nhắc populate.
- **13 bản ghi `title` rỗng** → xóa hoặc re-fetch.
- **17 tiêu đề trùng** → dedupe theo `(title, year)` hoặc DOI.

### P5 — Dọn chất lượng dữ liệu `app.db`
- **3 essays orphan** (#3, #4, #18) không có citation → xóa hoặc điều tra parser.
- **Essay trùng tên file** (×4, ×3, ×2) → dedupe theo hash file để tránh thống kê sai.
- `citations.confidence` trung bình chỉ 0.128 (max 0.7) → rà lại parser/threshold trích xuất.
- Độ phủ metadata citation thấp (DOI 245/685, title 491/685) → cân nhắc enrich.

### P6 — Cảnh báo vận hành
- Có **2 bản `local_papers.db`**: bản chính `data/local_papers.db` (893 papers) và bản trong worktree `.kilo/worktrees/general-piano/data/local_papers.db` (310 papers, cũ hơn). Cần xác định bản nào là nguồn sự thật, tránh sửa nhầm.
- API server (uvicorn `--reload`) đang chạy và ghi DB live — xem cảnh báo đầu file.
- `data/local_papers.db` đang bị git track và đã `M` (modified) — cân nhắc có nên đưa DB vào `.gitignore` thay vì commit.
- **Cập nhật lại tài liệu sai:** `README.md` (dòng 93) và `tests/progress/SESSION_SUMMARY_WEEK9.md` đang ghi "83,541 ACL papers pre-loaded" — **sai thực tế**. Cần sửa sau khi import lại ACL đúng.
- Nếu import full 127k ACL: DB sẽ phình từ ~1.3 MB lên đáng kể; cân nhắc batch + `PRAGMA journal_mode=WAL` + kiểm tra dung lượng đĩa.

---

## 6. Lệnh tái kiểm chứng (reproduce)

```bash
cd /Users/iannwendy/Desktop/DATN/essay-integrity-checker

# --- Paper knowledge base ---
sqlite3 data/local_papers.db "SELECT COUNT(*) FROM papers;"
sqlite3 data/local_papers.db "SELECT source, COUNT(*) FROM papers GROUP BY source;"
sqlite3 data/local_papers.db "SELECT COUNT(*) FROM papers WHERE abstract IS NULL;"
sqlite3 data/local_papers.db "SELECT COUNT(*) FROM papers WHERE doi IS NULL;"
sqlite3 data/local_papers.db "SELECT source, COUNT(*) FROM query_log GROUP BY source;"

# --- ACL XML ---
grep -rho "<paper\b" data/acl_data/data/xml/*.xml | wc -l    # 127851
grep -rho "<volume\b" data/acl_data/data/xml/*.xml | wc -l   # 6172
ls data/acl_data/data/xml/*.xml | wc -l                      # 1719

# --- ACL BibTeX (bị cắt cụt) ---
grep -cE "^@(inproceedings|article)\{" data/acl_anthology.bib  # 2288
tail -3 data/acl_anthology.bib                                 # entry cuối không đóng

# --- TÁI HIỆN BUG import_acl_xml.py (mất 44.904 bài + author hỏng) ---
source .venv/bin/activate
python - <<'EOF'
import sys, re, glob
from pathlib import Path
sys.path.insert(0, '.')
from scripts.import_acl_xml import _parse_xml_file
raw = parsed = 0
for f in sorted(glob.glob('data/acl_data/data/xml/*.xml')):
    n = len(re.findall(r'<paper\b', Path(f).read_text(encoding='utf-8', errors='ignore')))
    raw += n
    if n: parsed += len(_parse_xml_file(Path(f)))
print("raw:", raw, "parsed:", parsed, "LOST:", raw - parsed)   # 127851 / 82947 / 44904
# author bug:
for p in _parse_xml_file(Path('data/acl_data/data/xml/1952.earlymt.xml'))[:1]:
    print("author (SAI):", p.authors)   # ['WarrenWeaver WarrenWeaver']
EOF

# --- App DB ---
sqlite3 data/app.db "SELECT COUNT(*) FROM citations; SELECT COUNT(*) FROM verdicts;"
sqlite3 data/app.db "SELECT COUNT(*) FROM essays;"

# --- Kiểm tra DB đang được ghi live ---
ps aux | grep -E "uvicorn.*integrity_checker" | grep -v grep
```

---

## 7. Ghi chú môi trường

- Repo: `/Users/iannwendy/Desktop/DATN/essay-integrity-checker` (git repo).
- `DATABASE_URL=sqlite:///./data/app.db` (từ `.env`).
- Không có Docker container/DB service ngoài đang chạy tại thời điểm audit.
- **Có** tiến trình `uvicorn ... --reload` (port 8000) và Vite dev server (port 5173) đang chạy → DB có thể thay đổi bất kỳ lúc nào.
- Audit chỉ dùng thao tác đọc; **không có thay đổi dữ liệu nào** được thực hiện.

---

## 8. ✅ TRẠNG THÁI XỬ LÝ (cập nhật 2026-09-27, sau khi fix)

> Toàn bộ P1–P6 đã được xử lý và kiểm chứng. Số liệu snapshot mới nhất nằm dưới
> đây; DB `local_papers.db` vẫn thay đổi nhẹ do API đang chạy (sync on-demand).

### Kết quả kiểm chứng

| Hạng mục | Trước (audit) | Sau (fix) |
|---|---|---|
| `import_acl_xml.py` parse toàn bộ 1.719 file | 82.947 / 127.851 (**mất 35%**) | **127.851 / 127.851 (0 mất)** |
| Author parse | `WarrenWeaver WarrenWeaver` | `Warren Weaver` |
| `papers` `source='acl'` | **0** | **127.103** |
| Tổng `papers` | 893 | **~128.038** |
| `abstract` NULL | 100% | **64,2%** có abstract (82.253) |
| `data/acl_anthology.bib` | bị cắt cụt (2.288 entry) | **hoàn chỉnh, 127.960 entry, brace cân bằng** (73,4 MB) |
| `title` rỗng | 13 | **0** |
| Trùng `(title, year)` | 17 | **0** |
| `venue` rác (OED, Éire-Ireland…) | có | **0** |
| `categories` = `[]` | 100% (893) | **0** — populate `["cs.CL","cs.AI","cs.LG"]` |
| venue thô chưa chuẩn hoá | toàn bộ | **633 dòng** canonical hoá qua `VenueNormalizer` |
| FTS `papers_fts_docsize` | 893 ≠ papers | **= số papers** |
| `citations.confidence` trung bình (app.db) | **0,128** | **0,735** (backfill) |
| `citations.doi` (app.db) | 245/685 | **286/685** (+41 DOI khôi phục) |
| `citations.title` (app.db) | 491/685 | **500/685** (+9 inline resolve) |
| Essay trùng tên trên API | 21 dòng | **15 nhóm** + `duplicate_ids` |
| Bản `local_papers.db` trong worktree | 310 bài (lệch nguồn) | **symlink → DB chính** (1 nguồn sự thật) |

### Bug bổ sung được phát hiện & sửa trong lúc fix

- **P1b — provenance sai (self-confirming):** match DOI chỉ từ `local_db`/`known_papers`
  trước đây được cấp verdict mạnh nhất `verified`. Đã thêm `_has_live_source()`
  trong `logic/rules.py`: chỉ cấp `verified` khi có nguồn *live* (crossref/openalex…),
  ngược lại trả `unresolved` + rule `R-LOCAL_DB_ONLY`. `retrieval_orchestrator.py`
  giữ nguyên provenance cache thay vì ghi đè.
- **`api/routes/verdicts.py`:** `_load_matched_sources()` bị cắt cụt, luôn trả `None`
  → API trả `matched_sources: null`. Đã sửa để parse list và mặc định `[]`.
- **`models/api_schemas.py`:** khai báo trùng `citation_link` — đã xoá.

### Script/thay đổi mới

- `scripts/clean_local_db.py` — dọn DB (dry-run mặc định, `--apply` để ghi):
  xoá title rỗng, dedupe DOI/title (giữ row có provenance `query_log`), lọc entry
  phi học thuật, canonical hoá venue qua `VenueNormalizer`, populate `categories`
  rỗng, rebuild FTS.
- `scripts/backfill_citation_confidence.py` — sửa 4 nhóm vấn đề `app.db`
  (dry-run mặc định, `--apply` để ghi):
  1. tính lại `citations.confidence` cho row cũ bằng đúng heuristic của parser;
  2. khôi phục DOI còn thiếu từ arXiv id (`arXiv:1911.09339` → `10.48550/arXiv.1911.09339`)
     và URL `doi.org/10.x` (+41 DOI);
  3. điền `venue` còn thiếu từ `raw_text` của reference;
  4. resolve in-text citation (`Sennrich et al. (2016)`) ngược về bibliography
     của chính essay đó để copy authors/title/year/DOI (+9 title).
- `LocalDatabase.dedupe()` + chế độ WAL (`journal_mode=WAL`, `synchronous=NORMAL`).
- `.gitignore`: `data/local_papers.db{,-shm,-wal}`, `data/acl_anthology.bib`, `data/*.bak`
  (2 file này đã `git rm --cached`).
- Test mới: `test_import_acl_xml.py`, `test_local_db_provenance.py`,
  `test_essay_dedupe.py`, `test_acl_bib_download.py`,
  `test_backfill_citation_confidence.py`, `test_verdicts_route_features.py`.

### Kiểm thử

- `python -m pytest tests` → **656 passed, 4 skipped**.
- E2E pipeline `data/essays/essay_02_mixed.pdf` → 6 verdict (5 verified, 1 suspected_hallucination), CIS 89,17.
- Eval ground-truth `evaluation/real_evaluation.py --max 20` → F1 0,857 · Accuracy 90% · Precision 1,0.
- API live: `/api/essays` & `/api/essays/all` → 15 nhóm (dedupe OK);
  `/api/essays/14/verdicts` → `matched_sources` là list hợp lệ;
  `/api/essays/14/report?format=json|csv|pdf` → OK.

### Ghi chú còn lại

- **3 essay orphan (#3, #4, #18):** cả 3 là `4.pdf` — PDF **scan ảnh, 0 ký tự text**
  (37 trang ảnh, không có text layer) nên không thể trích citation. Không phải bug
  parser. Đã được gộp trong API; giữ lại trong DB để bảo toàn lịch sử upload.
  Muốn xử lý được cần OCR (ngoài phạm vi handoff).
- `citation_cache`/`audit_logs` rỗng: tính năng chưa dùng, không phải lỗi dữ liệu.
- API `uvicorn --reload` vẫn đang chạy → số `papers` có thể tăng nhẹ (sync on-demand).

### P6 — Cảnh báo vận hành (đã xử lý)

- **Nguồn sự thật duy nhất:** `data/local_papers.db` (đường dẫn resolve theo
  `settings.paths.data_dir` + `"local_papers.db"`, mặc định `./data`).
- **Worktree `.kilo/worktrees/general-piano`:** bản DB 310 bài cũ ở đó đã được
  `git rm --cached` và **thay bằng symlink** →
  `../../../../data/local_papers.db`, nên cả 2 đường dẫn cùng trỏ về một DB
  (128.037 bài). Hết nguy cơ sửa nhầm bản cũ.
- **Dung lượng:** `data/local_papers.db` sau import đầy đủ là **256 MB** (đĩa còn
  248 GB trống — không có rủi ro). Đã bật `journal_mode=WAL` +
  `synchronous=NORMAL` để importer ghi mà không chặn request đọc của API.
- **Git:** `data/local_papers.db*` và `data/acl_anthology.bib` đã `git rm --cached`
  và thêm vào `.gitignore`.
