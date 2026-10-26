# BÁO CÁO ĐÁNH GIÁ TOÀN DIỆN HỆ THỐNG TRÊN 20 KHÓA LUẬN (`20-theses/1.pdf` – `20.pdf`)

- **Ngày lập báo cáo**: `26/10/2026`
- **Phạm vi kiểm thử**: Toàn bộ 20 tập tin khóa luận tốt nghiệp PDF trong thư mục [`20-theses/`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/20-theses) (`1.pdf` đến `20.pdf`).
- **Mục tiêu ưu tiên hàng đầu**: Đánh giá độ chính xác toàn diện của hệ thống (đặc biệt là **tầng Parsing phải đạt chuẩn 100%**: phân đoạn cấu trúc tài liệu, bóc tách danh mục tài liệu tham khảo bằng GROBID + Regex, hợp nhất/khử trùng lặp, trích xuất trích dẫn trong bài, và liên kết hai chiều In-text ↔ Reference), đối chiếu trực tiếp với **Ground Truth** trong từng file PDF, truy vết nguyên nhân gốc rễ (root cause) của mọi bug và đề xuất giải pháp khắc phục triệt để.
- **Trạng thái mã nguồn**: **Chưa chỉnh sửa bất kỳ dòng code nào** theo đúng yêu cầu (chỉ chạy kiểm thử, debug và lập báo cáo).

---

## PHẦN 1: TỔNG QUAN & BẢNG ĐỐI CHIẾU TOÀN DIỆN 20 KHÓA LUẬN

### 1.1. Bảng tổng hợp đối chiếu Ground Truth vs. Kết quả Hệ thống (`1.pdf` – `20.pdf`)

| File | Chuẩn trích dẫn (GT) | Số trang | Phân đoạn Section (`SectionSegmenter`) | GT Refs | GROBID Bib | Regex Refs | Merged Refs | Đánh giá Parsing Reference | Body Cit | Matched Refs | Missing Ref (In-Text) | Uncited Refs | Verdicts (`V` / `R` / `M` / `H` / `U`)* | Điểm CIS |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`1.pdf`** | APA 7 | 38 | `body`(1-34), `bib`(35-38) | **31** | 30 | 31 | **30** (-1) | Mất 2 mục thật (`ALA`, `Brennen`), tách đôi 1 mục (`Ballot`), 9 URL bị dính họ tác giả kế tiếp | 99 | 23 | 40 | 7 | `11V / 17R / 0M / 1H / 1U` | 89.66 |
| **`2.pdf`** | APA 7 | 42 | `body`(1-38), `bib`(39-40), `app`(41-42) | **15** | 14 | 15 | **14** (-1) | GROBID gộp `Jaus` + `Labele`; `_is_fake_entry` xóa `OpenRocket`; `Wikipedia 2025a/b` mất suffix | 12 | 9 | 2 | 5 | `6V / 7R / 0M / 0H / 1U` | 93.93 |
| **`3.pdf`** | Bluebook / Chicago Footnotes | 34 | `body`(1-34) *(không có mục Bib cuối bài)* | **0** *(177 footnotes)* | 17 *(bị bỏ)* | 0 | **0** | Không có mục Bib cuối bài; hệ thống bỏ qua 177 footnotes trong thân bài | 0 | 0 | 0 | 0 | `0` | 0.00 |
| **`4.pdf`** | Scanned PDF (Ảnh quét) | 37 | `body`(1-37) | **N/A** *(0 ký tự text)* | 0 *(HTTP 500)* | 0 | **0** | File PDF scan dạng ảnh (`0 chars`), không có OCR fallback, GROBID lỗi HTTP 500 | 0 | 0 | 0 | 0 | `0` | 0.00 |
| **`5.pdf`** | APA 7 | 33 | `body`(1-27), `bib`(28-33) | **40** | 40 | 40 | **40** (Chuẩn) | **Đạt 100% số lượng (40/40)**; chỉ có 2 FP in-text `(see Figure 1)` & `(see Appendix B)` | 106 | 39 | 2 | 1 | `39V / 0R / 0M / 0H / 1U` | 98.90 |
| **`6.pdf`** | Chicago NB | 33 | `body`(1-30), `bib`(31-33) | **35** | 37 | 27 | **52** (+17) | Regex gom nhiều mục Chicago NB thành 17 bản ghi rác `YouTube video...` rồi cộng dồn vào GROBID | 16 *(16 FP)* | 0 | 16 | 52 | `12V / 34R / 3M / 3H / 0U` | 76.32 |
| **`7.pdf`** | MLA 9 | 29 | `body`(1-27), `bib`(28-29) | **22** | 21 | 17 | **22** *(lệch 2)* | Mất 2 mục thật (`Sophocles`, `Homer The Iliad`), thêm 2 mục rác (`ESV Bible`, `Homer yr=1996`) | 38 | 20 | 4 | 2 | `12V / 2R / 4M / 1H / 3U` | 79.00 |
| **`8.pdf`** | Mixed MLA 9 + APA 7 | 35 | `body`(1-28), `bib`(29-35) | **57** | 56 | 40 | **56** (-1) | `_is_fake_entry` xóa mất 1 mục thật (`Chesterton - The Defendant`) vì không có năm/DOI/URL | 72 | 54 | 0 | 2 | `29V / 27R / 0M / 0H / 0U` | 99.87 |
| **`9.pdf`** | APA 7 | 39 | `body`(1-34), `bib`(35-39) | **35** | 32 | 33 | **33** (-2) | GROBID gộp 3 cặp mục liên tiếp (`Allen+Amen Clinics`, `Amen+ACR`, `NIBIB+NIMH`); rơi 8 tác giả đầu ở `[G14, G20]` | 46 | 28 | 5 | 5 | `25V / 6R / 0M / 0H / 2U` | 95.95 |
| **`10.pdf`** | Chicago NB (Primary + Secondary) | 57 | `body`(1-51), `bib`(52-57) | **68** *(+4 báo)* | 102 *(33 footnotes!)* | 47 | **94** (+26) | GROBID hút 33 footnotes từ trang 1-51 vào Bib; `_is_fake_entry` xóa 17 mục; Regex nối thêm 10 mục rác | 27 *(26 FP)* | 0 | 27 | 94 | `28V / 26R / 8M / 18H / 14U` | 57.14 |
| **`11.pdf`** | APA 7 | 35 | `body`(1-31), `bib`(32-35) | **23** | 24 | 23 | **24** (+1) | GROBID tách đôi `Shao et al. (2025)` tại tiêu đề dịch `[...]`; lỗi họ ghép `Santa Rosa Lana` (10 lần) & 25 câu `as cited in` | 114 | 21 | 27 | 3 | `21V / 1R / 0M / 0H / 2U` | 95.27 |
| **`12.pdf`** | APA 7 | 40 | `body`(1-31), `bib`(32-40) | **60** | 56 | 61 | **58** (-2) | GROBID gộp 4 cụm (`Ablon+Ajmal`, `Haider+Hunt.io`, `Hurel+IBM+Iqbal`, `MITRE+Nagar`); parse mã bài `1981` làm năm của `Dawood (2023)` | 57 | 39 | 13 | 19 | `19V / 33R / 0M / 1H / 5U` | 88.28 |
| **`13.pdf`** | Chicago NB | 30 | `body`(1-28), `bib`(29-30) | **26** | 26 | 18 | **28** (+2) | `_is_fake_entry` xóa `The ESV Study Bible (2008)` khỏi GROBID; Regex nối thêm 3 bản ghi rác/trùng | 19 *(17 FP)* | 1 | 18 | 27 | `14V / 4R / 6M / 1H / 3U` | 73.77 |
| **`14.pdf`** | APA 7 | 32 | `body`(1-28), `bib`(29-32) | **24** | 24 | 22 | **24** (Chuẩn) | **Đạt 100% số lượng (24/24)**; lỗi dấu gạch nối ngắt dòng `(Popławska- Domaszewicz, 2025)` | 69 | 23 | 5 | 1 | `22V / 0R / 1M / 0H / 1U` | 95.66 |
| **`15.pdf`** | Chicago NB (`References`) | 30 | `body`(1-26), `bib`(27-30) | **45** | 50 *(5 footnotes!)* | 37 | **51** (+6) | GROBID hút 5 footnotes trang 26 vào Bib; URL bị ngắt dòng tách đôi mục tham khảo | 10 *(6 FP)* | 5 | 5 | 46 | `10V / 31R / 1M / 1H / 8U` | 69.00 |
| **`16.pdf`** | APA 7 | 51 | `body`(1-39), `bib`(40-51) | **66** | 66 | 65 | **66** (Chuẩn) | **Đạt 100% số lượng (66/66)**; nhưng 9 câu in-text `However, Author et al. (YYYY)` bị lấy `"However"` làm họ tác giả! | 150 | 52 | 24 | 14 | `62V / 2R / 1M / 0H / 1U` | 97.51 |
| **`17.pdf`** | APA 7 | 48 | `body`(1-42), `bib`(43-47), `app`(48) | **35** | 30 | 35 | **36** (+1) | GROBID gộp 5 cặp mục web/title-first, lấy `2020` trong tiêu đề `2020–2026` làm năm của `Likhil (2025)`; Regex đẻ 6 mục trùng/hỏng URL | 140 | 26 | 48 | 10 | `15V / 17R / 0M / 4H / 0U` | 84.63 |
| **`18.pdf`** | APA 7 | 37 | `body`(1-34), `bib`(35-37) | **25** | 24 | 25 | **24** (-1) | GROBID gộp `RocketPy Team` + `RocketSerializer Developers`; cắt cụt DOI ngắt dòng của `Zhou (2021)` | 24 | 20 | 1 | 4 | `18V / 4R / 0M / 0H / 2U` | 95.59 |
| **`19.pdf`** | APA 7 | 42 | `body`(1-29), `bib`(30-42) | **75** | 75 | 75 | **75** *(lệch 2 năm)* | Đủ 75/75 mục, nhưng GROBID lấy mã bài `2008` và `2015` làm năm của `Rinninella (2021)` & `Stolfi (2023)`; lỗi chữ ghép `Præstholm` | 102 | 71 | 3 | 4 | `69V / 2R / 1M / 0H / 3U` | 97.29 |
| **`20.pdf`** | Chicago NB / Turabian | 49 | `body`(1-46), `bib`(47-49) | **29** | 29 | 10 | **36** (+7) | GROBID bóc đúng 29/29 mục, nhưng Regex nối thêm 7 mục rác `title="ProQuest Ebook Central"`; 26 FP in-text `(City: Publisher, Year)` | 33 *(27 FP)* | 7 | 27 | 29 | `21V / 1R / 3M / 4H / 7U` | 77.69 |

*\*Chú thích cột Verdicts: `V` = `VERIFIED`, `R` = `RESOURCE`, `M` = `METADATA_ERROR`, `H` = `SUSPECTED_HALLUCINATION`, `U` = `UNRESOLVED`.*

---

### 1.2. Đánh giá tổng quát mức độ chính xác hiện tại

1. **Về phân đoạn cấu trúc tài liệu (`SectionSegmenter`)**:
   - Đạt độ chính xác rất cao (**19/19 file có văn bản**, tức **100%** trên các file có text): nhận diện chính xác ranh giới trang `BODY`, `BIBLIOGRAPHY` (`References`, `Works Cited`, `Bibliography`, kể cả tiêu đề phụ `Primary Sources` / `Secondary Sources` trong `10.pdf`) và `APPENDIX` (`2.pdf`, `17.pdf`).
   - Ngoại lệ duy nhất là `4.pdf` (file PDF scan ảnh hoàn toàn, `0` ký tự text trên cả 37 trang) và `3.pdf` (luận văn luật dùng 177 footnotes dưới chân trang, không có mục Bibliography cuối bài).

2. **Về bóc tách và hợp nhất Danh mục Tài liệu tham khảo (`GROBID` + `Regex` -> `Merged References`)**:
   - **Chưa đạt chuẩn 100%**: Trong 18 khóa luận có mục Tài liệu tham khảo cuối bài:
     - Chỉ có **3/18 khóa luận** (`5.pdf`, `14.pdf`, `16.pdf`) đạt khớp tuyệt đối số lượng reference và không bị hỏng trường nghiêm trọng ở danh sách hợp nhất.
     - Có **1/18 khóa luận** (`19.pdf`) khớp số lượng `75/75` nhưng bị GROBID ghi sai năm xuất bản của 2 bài báo (`2021 -> 2008`, `2023 -> 2015`) do nhầm mã bài báo 4 chữ số.
     - Có **14/18 khóa luận** (`1.pdf`, `2.pdf`, `6.pdf`, `7.pdf`, `8.pdf`, `9.pdf`, `10.pdf`, `11.pdf`, `12.pdf`, `13.pdf`, `15.pdf`, `17.pdf`, `18.pdf`, `20.pdf`) bị sai lệch số lượng hoặc hư hỏng dữ liệu do **5 nhóm lỗi cốt lõi**:
       1. `_is_fake_entry()` trong [`document_parser.py`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L580-L595) xóa nhầm tài liệu tham khảo hợp lệ của GROBID khi không có năm/DOI/URL hoặc khi `raw_text` tái tạo ngắn hơn 30 ký tự (`1.pdf`, `2.pdf`, `7.pdf`, `8.pdf`, `10.pdf`, `13.pdf`).
       2. [`GrobidParser.parse_bibliography()`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_parser.py) hút luôn cả các thẻ `<biblStruct>` nằm trong **Footnotes của phần thân bài** (`3.pdf`, `10.pdf`, `15.pdf`).
       3. GROBID gộp 2–3 mục tham khảo liên tiếp thành 1 mục hoặc tách đôi 1 mục thành 2 mục (`2.pdf`, `9.pdf`, `11.pdf`, `12.pdf`, `15.pdf`, `17.pdf`, `18.pdf`).
       4. Regex [`_URL_BOUNDARY_RE`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/reference_parser.py#L317-L320) làm **dính họ tác giả của mục tiếp theo vào đuôi URL/DOI của mục trước** trên **14/20 khóa luận**, làm hỏng URL (gây lỗi HTTP 404 -> phán nhầm `SUSPECTED_HALLUCINATION`) và làm cụt họ tác giả của mục sau.
       5. Regex [`_split_by_year_boundary()`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/reference_parser.py#L371-L454) không tách được các mục Chicago NB / MLA 9, sinh ra các bản ghi rác rồi được [`_merge_reference_lists()`](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L636-L702) cộng dồn vào kết quả của GROBID (`6.pdf`, `7.pdf`, `10.pdf`, `13.pdf`, `15.pdf`, `20.pdf`).

3. **Về trích xuất In-text Citations (`CitationExtractor`) và Liên kết (`CitationLinker`)**:
   - Bắt nhầm **88 cụm `(City: Publisher, Year)`** bên trong footnotes của 5 khóa luận Chicago NB (`6.pdf`, `10.pdf`, `13.pdf`, `15.pdf`, `20.pdf`) thành trích dẫn APA `(Author, Year)`.
   - Bắt nhầm trạng từ đầu câu (`However,`, `Similarly,`, `Conversely,`, `Yet,`) làm tên tác giả thứ nhất trong trích dẫn tự sự APA (`16.pdf`).
   - Không liên kết được trích dẫn có dấu gạch nối ngắt dòng (`Hosseini- Motlagh`, `Lenaerts- Bergmans`, `Popławska- Domaszewicz`, `Abu- Omar`, `Eichenberger- Archer`), chữ ghép Bắc Âu (`Præstholm` vs `Praestholm`), dấu phụ (`Hrncir` vs `Hrncír`, `O’Mathúna`), họ ghép (`Santa Rosa Lana & Afonso Brardo Duarte`), và trích dẫn thứ cấp (`as cited in`).

---

## PHẦN 2: KIỂM TRA & ĐỐI CHIẾU CHI TIẾT TỪNG FILE (`1.pdf` ĐẾN `20.pdf`)

### File `1.pdf` — *Journalism, AI, and Misinformation* (APA 7, 38 trang)
- **Phân đoạn**: `body` (trang 1–34), `bibliography` (trang 35–38) — **Chính xác 100%**.
- **Ground Truth References**: **31** mục.
- **Kết quả Hệ thống**: GROBID = `30`, Regex = `31`, Merged = **`30`** (thiếu 1 mục về số lượng, nhưng thực chất **mất 2 mục thật và thừa 1 mục bị tách đôi**):
  1. **Mục bị mất #1**: `American Library Association. (n.d.). First Amendment and censorship. https://www.ala.org/advocacy/intfreedom/censorship`
     - GROBID bóc thành `[G1]` với `auth=[]`, `yr=None`, `url='https://www.ala.org/...'`.
     - Regex `[R1]` làm dính họ tác giả mục #2 (`Ballot`) vào đuôi URL: `url='https://www.ala.org/advocacy/intfreedom/censorshipBallot'`.
     - Khi hợp nhất, `[M1]` mất hoàn toàn tên tác giả `American Library Association`, khiến trích dẫn `(American Library Association, n.d.)` trong bài bị báo `missing_reference`, còn `[M1]` bị báo `uncited_reference`.
  2. **Mục bị tách đôi (#2 -> `[M2]` & `[M3]`)**: `Ballot, P., &Allcott, H. (2024). In truth we trust? Information disorder as a function of...`
     - Vì sinh viên gõ thiếu dấu cách sau dấu `&` (`&Allcott`), GROBID tách thành 2 mục: `[G2]` (`Ballot, P.`, `yr=None`) và `[G3]` (`Allcott, H.`, `yr=2024`). Cả hai đều được giữ lại trong `merged_refs` (`[M2]` và `[M3]`).
  3. **Mục bị xóa nhầm #4**: `Brennen, J. S., Simon, F. M., Howard, P. N., & Nielsen, R. K. (2020). Types, sources, and claims of COVID-19 misinformation. Reuters Institute for the Study of Journalism.` (không có DOI/URL).
     - GROBID bóc thành `[G5]` nhưng để `yr=None`. Tại `document_parser.py:582`, vì `ref.year is None and not ref.doi and not ref.url` và `ref.venue` rỗng (`len < 30`), hàm `_is_fake_entry(ref.venue or "")` trả về `True` và **xóa sổ hoàn toàn `[G5]`**!
     - Trong khi đó, ở phía Regex, mục #3 (` Beauvais, C. (2022)... https://doi.org/10.1111/bioe.13060`) bị dính chữ `Brennen,` của mục #4 vào đuôi DOI (`doi='10.1111/bioe.13060Brennen'`), khiến mục #4 trong Regex (`[R4]`) mất họ tác giả đầu tiên `Brennen` (chỉ còn `Simon, F. M., Howard, P. N., & Nielsen, R. K.`), rồi bị `_merge_reference_lists` gộp nhầm hoặc bỏ sót! Hệ quả: mọi trích dẫn `(Brennen et al., 2020)` trong bài đều bị báo `missing_reference`!
  4. **9 URL bị dính họ tác giả mục kế tiếp -> Phán nhầm `SUSPECTED_HALLUCINATION`**:
     - Mục `[M14]` (`Fake news statistics & facts (2024) - Redline Digital`) bị Regex dán chữ `Journalism` của mục #15 vào URL (`https://www.redlinedigital.org/fake-news-statistics-and-facts/Journalism`). Khi `LinkValidator` kiểm tra URL này thì nhận về **HTTP 404**, dẫn đến phán quyết sai `[V14] suspected_hallucination (conf=0.99)`!
  5. **Lỗi In-text & Linking (40 `missing_reference`)**:
     - Các mục có tác giả là tiêu đề bài viết hoặc tổ chức (`"First Amendment and censorship"`, `"The Ethics of Using AI"`, `"The state of local news 2025"`, `"Misinformation: What it is..."`, `"Social media and news fact sheet"`) không khớp với cách trích dẫn trong bài (`(ALA, n.d.)`, `(Pew Research Center, 2024)`).
     - Trích dẫn thứ cấp `(Pew Research Center, as cited in Naseer, 2024)` bị tách sai và báo thiếu `Pew Research Center`.

---

### File `2.pdf` — *Active Control System for a Canard-Controlled Rocket* (APA 7, 42 trang)
- **Phân đoạn**: `body` (trang 1–38), `bibliography` (trang 39–40), `appendix` (trang 41–42) — **Chính xác 100%**.
- **Ground Truth References**: **15** mục.
- **Kết quả Hệ thống**: GROBID = `14`, Regex = `15`, Merged = **`14`** (thiếu 1 mục):
  1. **GROBID gộp 2 mục liên tiếp (`[G5]`)**:
     - Mục #5: `Jaus, A., ... (2025). An Introduction to Metamodelling...`
     - Mục #6: `Labele, J. (2025). Metamodelling - Advanced Methods [Class slides]. ENGR 380...`
     - GROBID gộp cả hai thành `[G5]` (`auth=['Jaus, A', ..., 'Labele, J']`, `yr=2025`, `title='Metamodelling - Advanced Methods [Class slides]'`).
  2. **`_is_fake_entry` xóa mất mục #11 (`OpenRocket`) khỏi GROBID**:
     - Mục #11: `Niskanen, S. (2025). OpenRocket © (Version 24.12) [Computer software]. OpenRocket. https://openrocket.info/`
     - GROBID `[G10]` bóc thiếu năm (`yr=None`) và URL (`url=None`), nên bị `document_parser.py:582` xóa mất! Rất may Regex `[R11]` giữ lại được nhưng ở `[R10]` (`Missile Defense Agency, 2025`) bị dính chữ `Niskanen` vào URL (`.../mda.mil/Niskanen`), nên `[R11]` bị mất họ tác giả `Niskanen` (chỉ còn `auth=[]`, `title='OpenRocket © (Version 24'`).
  3. **Mất hậu tố năm `2025a` / `2025b` và tiền tố `Adapted from`**:
     - Hai mục `Wikipedia contributors. (2025a)` và `Wikipedia contributors. (2025b)` bị GROBID gộp hoặc parse thành `yr=2025` (mất `year_suffix='a'/'b'`), và trích dẫn trong bài `(Adapted from White, 2022)` / `(Adapted from Wikipedia Contributors, 2025a)` bị parse họ tác giả thành `"Adapted from White"` và `"Adapted from Wikipedia Contributors"`, gây ra 2 lỗi `missing_reference`!

---

### File `3.pdf` — *Constitutional Law / Legal Thesis* (Bluebook / Chicago Footnotes, 34 trang)
- **Phân đoạn**: `body` (trang 1–34).
- **Ground Truth**: Khóa luận ngành Luật sử dụng **177 footnotes dưới chân trang** (theo chuẩn Bluebook / Chicago Full Note), **không có mục Bibliography riêng ở cuối bài**.
- **Kết quả Hệ thống**:
  - Vì không có section `BIBLIOGRAPHY`, `DocumentParser.parse()` (dòng 150: `has_bib_section = False`) **vứt bỏ toàn bộ 17 mục `<biblStruct>`** mà GROBID trích xuất được từ footnotes, đồng thời `CitationExtractor` không có regex cho superscript/footnote citations, nên hệ thống trả về **`0 references, 0 body_citations, CIS=0.0`**.

---

### File `4.pdf` — *Scanned Thesis Document* (Ảnh quét PDF, 37 trang)
- **Ground Truth**: Toàn bộ 37 trang PDF là ảnh scan (`0` ký tự text khi đọc bằng PyMuPDF `page.get_text()`).
- **Kết quả Hệ thống**:
  - `PDFLoader` trả về 37 trang rỗng (`char_len = 0`).
  - `GrobidClient` gửi file PDF scan sang GROBID server và nhận lỗi **`HTTP 500 Internal Server Error`**.
  - Hệ thống không có bước kiểm tra PDF scan (`total_chars == 0`) để kích hoạt OCR (Tesseract / PaddleOCR / macOS Vision) hoặc trả về cảnh báo chuyên biệt `SCANNED_PDF_UNSUPPORTED`, mà âm thầm trả về **`0 references, 0 body_citations, CIS=0.0`**.

---

### File `5.pdf` — *Emotional Intelligence and Heart Rate Variability* (APA 7, 33 trang)
- **Phân đoạn**: `body` (trang 1–27), `bibliography` (trang 28–33) — **Chính xác 100%**.
- **Ground Truth References**: **40** mục.
- **Kết quả Hệ thống**: GROBID = `40`, Regex = `40`, Merged = **`40` (Đạt 100% số lượng)**.
- **Các lỗi nhỏ phát hiện được**:
  1. **Regex `[R19]` bị cắt cụt tại dấu chấm sau tiêu đề tiếng Pháp**: `Laborde, S., ... (2017). Heart rate variability and cardiac vagal tone in psychophysiological research – Recommendations for experiment planning, data analysis, and data reporting. Frontiers in Psychology, 8, 213.` (GROBID cứu được nhờ merge).
  2. **2 False Positives ở `CitationExtractor`**: Bắt nhầm `(see Figure 1)` và `(see Appendix B)` trong thân bài thành trích dẫn in-text (báo 2 `missing_reference`).
  3. **1 lỗi `UNRESOLVED` oan ở `[V40]` (`Wei, G., Xiran, Z., Gaik, L. P., & Liang, K., 2024`, `doi=10.21834/e-bpj.v9i29.6009`)**:
     - Đây là bài báo có thật (`title_sim=1.00`, `DOI match=True`), nhưng tên tác giả trên Crossref là tên người Hoa/Malaysia viết theo thứ tự `Gao Wei, Zhang Xiran, Lee Phaik Gaik, Kuang Liang`. Sinh viên đảo ngược Họ và Tên khi viết APA (`Wei, G., Xiran, Z.`), khiến `author_jaccard = 0.00`. Do kết quả được lấy từ `local_db` ở Tier 0 (`_has_live_source=False`), `SymbolicRules` đẩy bài báo có DOI khớp 100% này xuống `UNRESOLVED (conf=0.28)`!

---

### File `6.pdf` — *Independent Christian Music Industry* (Chicago NB, 33 trang)
- **Phân đoạn**: `body` (trang 1–30), `bibliography` (trang 31–33) — **Chính xác 100%**.
- **Ground Truth References**: **35** mục (gồm sách, bài báo, podcast và video YouTube trình bày theo chuẩn Chicago Notes & Bibliography).
- **Kết quả Hệ thống**: GROBID = `37`, Regex = `27`, Merged = **`52` (+17 mục thừa/rác!)**:
  1. **GROBID tách 2 mục thành 4 (`35 -> 37`)** và `_is_fake_entry` xóa 1 mục (`[G16]`):
     - Mục podcast có tên host và tên chương trình bị GROBID tách đôi.
  2. **Regex `ReferenceListParser` phá vỡ cấu trúc Chicago NB (`27` mục rác)**:
     - Vì các mục YouTube/Podcast trong Chicago NB có dạng:
       `Ruslan KD. “Viral Rapper Connor Price Doesn’t Need A Label.” October 14, 2023. YouTube video, 19:33. https://www.youtube.com/watch?v=...`
     - `_split_by_year_boundary()` cắt sai vị trí năm `2023.`, để lại phần đuôi `YouTube video, 19:33. https://...` ghép với mục tiếp theo, rồi `_HARVARD_ARTICLE_RE` parse ra 17 bản ghi có `title="YouTube video, 19:33"`, `title="YouTube video, 8:14"`, `title="________"` (3-em dash)!
     - Khi chạy `_merge_reference_lists()`, 17 bản ghi rác này của Regex không khớp với bất kỳ bản ghi GROBID nào nên được **cộng dồn toàn bộ vào cuối danh sách** (`[M36]` đến `[M52]`)!
  3. **URL bị dính họ tác giả kế tiếp -> 3 phán quyết `SUSPECTED_HALLUCINATION` oan (`[V13, V22, V48]`)**:
     - Ví dụ: URL của bộ phim `The Jesus Music (2021)` bị dính họ tác giả mục tiếp theo (`.../Erwin,`), trả về HTTP 404 và bị phán `suspected_hallucination (conf=0.99)`.
  4. **In-text Citations & Linking (`0/52 matched`, `16/16 False Positives`)**:
     - Bài viết dùng footnotes Chicago NB, nhưng `CitationExtractor` bắt nhầm **16 cụm `(City: Publisher, Year)`** trong footnotes (ví dụ: `(Thousand Oaks, CA: SAGE Publications, Inc., 2017)`, `(New York: Simon & Schuster, 2023)`) làm trích dẫn APA! Kết quả: 16 `missing_reference` giả và 52/52 tài liệu tham khảo bị báo `uncited_reference`!

---

### File `7.pdf` — *Fate and Free Will in Classical Literature* (MLA 9, 29 trang)
- **Phân đoạn**: `body` (trang 1–27), `bibliography` (trang 28–29) — **Chính xác 100%**.
- **Ground Truth References**: **22** mục (`Works Cited` chuẩn MLA 9).
- **Kết quả Hệ thống**: GROBID = `21`, Regex = `17`, Merged = **`22`** (con số 22 nhìn tưởng đúng nhưng thực tế **mất 2 mục thật và chèn 2 mục rác**!):
  1. **Mục thật bị GROBID bỏ sót #21**: `Sophocles. The Three Theban Plays: Antigone; Oedipus the King; Oedipus at Colonus. Translated by Robert Fagles, Penguin Books, 1984.`
     - GROBID gộp mục này vào mục #20 (`Sartre, Jean-Paul`), còn Regex gộp 4 mục cuối trang 29 thành 1 khối nên **tác phẩm `Sophocles (1984)` biến mất hoàn toàn khỏi danh sách `merged_refs`**! Hệ quả: 2 trích dẫn `(Sophocles 71)` và `(Sophocles 112)` trong bài bị báo `missing_reference`!
  2. **Mục thật bị `_is_fake_entry` xóa sổ #12**: `Homer. The Iliad. Arcturus Publishing Limited, 2016.`
     - GROBID bóc đúng `[G12]` (`auth=['Homer']`, `yr=2016`, `title='The Iliad'`, `venue=None`).
     - Nhưng `grobid_adapter.py` tạo lại `raw_text = "Homer (2016) The Iliad"` (dài **22 ký tự** `< 30` ký tự và không có dấu phẩy sau họ).
     - Tại `document_parser.py:591`, `_is_fake_entry("Homer (2016) The Iliad")` trả về `True` và **xóa thẳng `[G12]`**! Hệ quả: 2 trích dẫn `(Homer 55)` và `(Homer 327)` trong bài bị báo `missing_reference`!
  3. **2 mục rác từ Regex được chèn vào (`[M21]` & `[M22]`)**:
     - `[M21]` làm trùng lặp `English Standard Version Bible (2002)`.
     - `[M22]` là một bản ghi Frankenstein do Regex ghép mảnh dư của `Homer. The Iliad` với `Kafka, Franz. The Trial (1998)` (`title='Homer'`, `yr=1996`, `url='https://.../The-Trial-by-Franz-Kafka.pdfKierkegaard'`). URL hỏng này trả về 404 và bị phán `[V22] suspected_hallucination (conf=0.99)`!

---

### File `8.pdf` — *BookTok and Erotic Literature* (Mixed MLA 9 + APA 7, 35 trang)
- **Phân đoạn**: `body` (trang 1–28), `bibliography` (trang 29–35) — **Chính xác 100%**.
- **Ground Truth References**: **57** mục (`Works Cited`).
- **Kết quả Hệ thống**: GROBID = `56`, Regex = `40`, Merged = **`56`** (thiếu **1** mục):
  1. **Mục thật bị `_is_fake_entry` xóa sổ (`[G7]`)**:
     - Ground Truth #7 (trang 29): `Chesterton, G. K. The Defendant. Project Gutenberg.` (không có năm, không có DOI/URL).
     - GROBID bóc chính xác `[G7]` (`auth=['Chesterton, G K']`, `yr=None`, `title='The Defendant'`, `venue='Project Gutenberg'`).
     - Nhưng tại `document_parser.py:582-586`: vì `ref.year is None and not ref.doi and not ref.url`, hệ thống kiểm tra `_is_fake_entry(ref.title or "") or _is_fake_entry(ref.venue or "")`. Do `"The Defendant"` (13 ký tự) và `"Project Gutenberg"` (17 ký tự) đều ngắn hơn 30 ký tự, `_is_fake_entry` trả về `True` và **xóa mất `[G7]`**!
  2. **Các lỗi Regex & Enrich trong `8.pdf`**:
     - Mục #33 dùng 3-em dash `---. Kingdom of Ash. Bloomsbury Publishing, 2018.` (kế thừa tác giả `Maas, Sarah J.` từ mục #32), nhưng GROBID để `auth=[]` còn Regex bỏ sót.
     - Mục #57 `The Bible (ESV ed.). (2022). Bible Gateway.` bị GROBID và Regex parse tên tác giả thành `auth=['The Bible', 'Esv']`.

---

### File `9.pdf` — *SPECT vs. fMRI Neuroimaging in Psychiatry* (APA 7, 39 trang)
- **Phân đoạn**: `body` (trang 1–34), `bibliography` (trang 35–39) — **Chính xác 100%**.
- **Ground Truth References**: **35** mục.
- **Kết quả Hệ thống**: GROBID = `32`, Regex = `33`, Merged = **`33`** (thiếu **2** mục và hỏng nặng 5 mục):
  1. **GROBID gộp 3 cặp mục liên tiếp (`35 -> 32`)**:
     - **Cặp 1 (`[G2]`)**: Gộp `Allen, M. (2023). fMRI vs. SPECT.` + `Amen Clinics. Brain SPECT. https://www.amenclinics.com/services/brain-spect/` thành 1 mục! Sau đó ở Regex `[R3]`, URL của `Amen Clinics` bị dính họ tác giả mục #4 (`.../brain-spect/Amen,`), rồi được `_enrich_grobid_ref` chép đè sang mục `[M4] Amen et al. (2012)`!
     - **Cặp 2 (`[G8]` & `[R9]`)**: Gộp `Amen, D. (2020). The End of Mental Illness.` + `American College of Radiology. (2021). ACR–ACNM–SNMMI–SPR practice parameter...` thành 1 mục duy nhất (`auth=['Amen, D']`, `yr=2020`, `title='American College of Radiology'`), làm mất hoàn toàn mục `American College of Radiology (2021)`!
     - **Cặp 3 (`[G22]`)**: Gộp `National Institute of Biomedical Imaging and Bioengineering. (2025). Nuclear Medicine.` + `National Institute of Mental Health. (2024). Mental Illness.` thành 1 mục (`auth=['National Institute of Biomedical Imaging and Bioengineering']`, `yr=2024`, `title='Nuclear Medicine'`, `url='https://www.nimh.nih.gov/...'`), làm **mất hoàn toàn mục `National Institute of Mental Health (2024)`**, khiến 3 trích dẫn `(National Institute of Mental Health [NIMH], 2024)` và `(NIMH, 2024)` trong bài bị báo `missing_reference`!
  2. **GROBID đánh rơi 7–8 tác giả đầu tiên trong danh sách tác giả dài (`[G14]` & `[G20]`)**:
     - **`[G14]`**: `Ayano, G., Demelash, S., Gizachew, Y., Tsegay, L., ... Solomon, M., Chaka, A., & Tsegay, L. (2021)` (11 tác giả). GROBID đánh rơi 8 tác giả đầu (trước ngắt dòng), chỉ giữ `['Solomon, M', 'Chaka, A', 'Tsegay, L']`! Dù Regex `[R14]` bóc đủ cả 11 tác giả bắt đầu bằng `Ayano, G.`, `_enrich_grobid_ref` không cập nhật `target.authors` vì `target.authors` của GROBID không rỗng! Hệ quả: `Ayano et al. (2021)` trong bài bị báo `missing_reference`, còn `[M14]` bị báo `uncited_reference`!
     - **`[G20]`**: `Kapucu, Ö. L., Nobili, F., Varrone, A., Booij, J., Vander Borght, T., Nagren, K., Darcourt, J., Tatsch, K., & Van Laere, K. J. (2009)` (9 tác giả). GROBID đánh rơi 7 tác giả đầu, chỉ giữ `['Tatsch, K', 'Van Laere, K J']`! Dù Regex `[R20]` bóc đủ 9 tác giả bắt đầu bằng `Kapucu`, `[M20]` vẫn mang họ `Tatsch`, khiến `(Kapucu et al., 2009)` trong bài bị báo `missing_reference` và `[M20]` bị báo `uncited_reference`!
  3. **Regex cắt cụt tiêu đề tại dấu chấm viết tắt**:
     - `fMRI vs. SPECT` -> `title="fMRI vs"` (`[M2]`)
     - `Confronting Dr. Amen` -> `title="Confronting Dr"` (`[M31]`)
     - `Radiopharmaceuticals 3.0.` -> `title="...Radiopharmaceuticals 3"` (`[R25]`).

---

### File `10.pdf` — *Karl Barth, Dietrich Bonhoeffer, and the Confessing Church* (Chicago NB, 57 trang)
- **Phân đoạn**: `body` (trang 1–51), `bibliography` (trang 52–57) — **Chính xác 100%** (không bị cắt tại tiêu đề phụ `Primary Sources` ở trang 52 hay `Secondary Sources` ở trang 54).
- **Ground Truth References**: **68** mục đầy đủ + **4** tên tờ báo liệt kê riêng ở trang 53 (`The Manchester Guardian.`, `The New York Times.`, `The Washington Post.`, `Wireless to the New York Times.`).
- **Kết quả Hệ thống**: GROBID = `102`, Regex = `47`, Merged = **`94` (+26 mục thừa/rác, kéo CIS tụt xuống `57.14` với 18 `SUSPECTED_HALLUCINATION`!)**:
  1. **GROBID hút 33 Footnotes & Đoạn văn thân bài (trang 1–51) vào Bibliography (`[G1]` – `[G33]`)**:
     - Các mục `[G1]` đến `[G33]` hoàn toàn không nằm ở trang 52–57 mà là footnotes dưới chân các trang 1–51 (ví dụ: `[G3]` `title="154 Barth made no public comments on the political events of 1932..."`, `[G4]` `title="370. The 1920 Nazi Party Platform..."`, `[G11]` `title="While in Switzerland, Barth published articles..."`, `[G16]` `"Ibid., 88. Rom. 13: 3-5"`, `[G17]` `"Dietrich Bonhoeffer also joined Niemoller..."`).
     - Đặc biệt, `[G33]` gộp footnote cuối cùng ở trang 51 (`Barnett, For the Soul of the People, 67.`) với mục đầu tiên của Bibliography ở trang 52 (`Bibliography Primary Sources "Article 48." Holocaust Encyclopedia...`), làm hỏng luôn mục `"Article 48"`!
     - Chính các đoạn văn/footnotes bị biến thành reference này đã gây ra **10 phán quyết `SUSPECTED_HALLUCINATION` giả** (`[V03, V04, V08, V09, V10, V11, V12, V13, V14, V15]`)!
  2. **`_is_fake_entry` xóa mất các mục không có năm/URL trong GROBID**:
     - Bao gồm cả sách thật trong Bibliography trang 56: `[G78] Kaplan, Leonard V. and Rudy Koshar. The Weimar Moment: Liberalism, Political Theology, and Law. Lexington Books.` (vì sinh viên quên ghi năm xuất bản và `"The Weimar Moment..."` không có `venue >= 30 chars`).
  3. **Regex nối thêm 10 mục rác (`[M85]` – `[M94]`)**:
     - Do Chicago NB có `—————.` (3-em dash) và ngày tháng báo chí, Regex tạo ra `[M85] title="—————"`, `[M89] title=": 229-251"`, `[M94] title=": 297-305"` -> gây thêm **8 phán quyết `SUSPECTED_HALLUCINATION` giả**!
  4. **In-text Citations**: Bắt nhầm **23 cụm `(City: Publisher, Year)`** trong footnotes (ví dụ `(Cambridge: Cambridge University Press, 2003)`) và 2 ngày tháng `(September 23, 1934)`, `(July 23, 1933)` làm trích dẫn APA (`0/94 matched`).

---

### File `11.pdf` — *ESG Performance and Circular Economy in Fast Fashion* (APA 7, 35 trang)
- **Phân đoạn**: `body` (trang 1–31), `bibliography` (trang 32–35) — **Chính xác 100%**.
- **Ground Truth References**: **23** mục.
- **Kết quả Hệ thống**: GROBID = `24`, Regex = `23`, Merged = **`24` (+1 mục bị tách đôi)**:
  1. **GROBID tách đôi mục #18 (`Shao et al., 2025`) tại tiêu đề dịch tiếng Romania trong ngoặc vuông `[...]`**:
     - Ground Truth #18: `Shao, Y., Zheng, M., Xu, X., & Ji, X. (2025). Does ESG performance have an impact on firm value? Evidence from sustainable development practices in the fashion industry [Performanța ESG are impact asupra valorii firmei? Dovezi din practicile de dezvoltare durabilă în industria modei]. Industria Textila, 76(2), 249–256. https://doi.org/10.35530/IT.076.02.2023126`
     - GROBID tách thành `[G18]` (`Shao et al., 2025`, mất venue và mất DOI) và `[G19]` (`auth=['Textila, Industria']`, `yr=None`, `title=None`, `doi='10.35530/IT.076.02.2023126'`).
     - Khi hợp nhất với Regex `[R18]` (vốn bóc đúng hoàn toàn!), vì `[G19]` giữ DOI `10.35530/...`, `_merge_reference_lists` lấy `[R18]` làm giàu cho `[G19]` thay vì `[G18]`, tạo ra mục thứ 24 giả mạo `[M19] Textila, Industria (2025) Does ESG performance...` (bị báo `uncited` và `UNRESOLVED`)!
  2. **Lỗi phân tích Họ ghép Bồ Đào Nha (`Santa Rosa Lana, G., & Afonso Brardo Duarte, P., 2025`)**:
     - GROBID tách thành 4 tác giả `['Rosa, Santa', 'Lana', 'Afonso Brardo, G', 'Duarte, P']`, còn Regex lấy từ cuối làm họ `['Lana, G', 'Duarte, P']`.
     - Trong thân bài, sinh viên trích dẫn `(Santa Rosa Lana & Afonso Brardo Duarte, 2025)` **10 lần**, và cả 10 lần đều thất bại khi link (`missing_reference`), đồng thời `[M17]` bị báo `uncited_reference`!
  3. **Lỗi trích dẫn thứ cấp `as cited in` (25 lần trong `11.pdf`!)**:
     - Ví dụ: `(Hiller Connell & Kozar, 2017, as cited in Dzhengiz et al., 2023)`, `(Paula, 2015, as cited in Santa Rosa Lana & Afonso Brardo Duarte, 2025)`.
     - Hệ thống tách theo dấu `;` hoặc lấy tác giả đầu tiên (`Hiller Connell`, `Paula`, `Egri`, `Vinken`, `Morris`, `Diabat`, `World Bank` — vốn là nguồn sơ cấp không có trong References) để tìm trong References và báo `missing_reference` hàng loạt!
  4. **Lỗi gạch nối ngắt dòng**: `(Hosseini- Motlagh et al., 2024)` có dấu cách sau dấu `-` do ngắt dòng PDF, không khớp với `Hosseini-Motlagh` trong `[M12]`.

---

### File `12.pdf` — *Red, Blue, and Purple Teaming in Cybersecurity* (APA 7, 40 trang)
- **Phân đoạn**: `body` (trang 1–31), `bibliography` (trang 32–40) — **Chính xác 100%**.
- **Ground Truth References**: **60** mục.
- **Kết quả Hệ thống**: GROBID = `56`, Regex = `61`, Merged = **`58` (-2 mục, nhưng thực tế mất 5 mục thật và thêm 3 mục rác/cụt)**:
  1. **GROBID gộp 4 cụm mục liên tiếp (`60 -> 56`) làm mất 4 mục thật trong `merged_refs`**:
     - **Cụm 1 (`[G1]`)**: Gộp `Ablon, L. (2018). Data thieves... RAND Corporation` + `Ajmal, A. B., ... (2023). Offensive security: Towards proactive threat hunting... IEEE Access. https://doi.org/10.1109/ACCESS.2023.3272629`. Vì `[G1]` mang tên `Ablon (2018)` nhưng lại gắn DOI của `Ajmal (2023)`, nên khi hợp nhất, Regex `[R2] Ajmal (2023)` bị khử trùng lặp vào `[G1]` theo DOI! Hậu quả kép: **`Ajmal et al. (2023)` bị xóa sổ hoàn toàn khỏi danh sách tham khảo** (khiến `(Ajmal et al., 2023)` trong bài bị báo `missing_reference`), còn `[M1] Ablon (2018)` bị lệch tiêu đề với DOI của Ajmal nên bị phán `[V01] UNRESOLVED`!
     - **Cụm 2 (`[G24]`)**: Gộp `Haider, U., ... (2024)... International Journal of Information Security. https://doi.org/10.1007/s10207-024-00850-y` + `Hunt.io. (2024, December 19). Understanding adversary emulation... https://hunt.io/glossary/adversary-emulation`. Hậu quả: DOI của `Haider` bị hỏng thành `10.1007/s10207-024-00850-yHunt.io`, còn mục **`Hunt.io (2024)` bị xóa sổ hoàn toàn**, khiến cả `(Haider et al., 2024)` lẫn `(Hunt.io, 2024)` trong bài đều bị báo `missing_reference`!
     - **Cụm 3 (`[G25]`)**: Gộp 3 mục liên tiếp: `Hurel, L. M. (2026)... RUSI` + `IBM. (n.d.). What is data exfiltration?` + `Iqbal, S., Mat Kiah, M. L., ... (2016). On cloud security attacks: A taxonomy...` thành 1 mục có `auth=['Hurel, L M', 'Mat Kiah, S', ...]`, `yr=2016`, `title='On cloud security attacks...'`, `url='https://www.rusi.org/...'`! Hậu quả: **cả `Hurel (2026)` lẫn `Iqbal et al. (2016)` đều mất tích** (vì tác giả đầu của bài 2016 bị đổi thành `Hurel`), khiến `(Hurel, 2026)` và `(Iqbal et al., 2016)` trong bài bị báo `missing_reference`!
     - **Cụm 4 (`[G34]`)**: Gộp `MITRE. (n.d.-a). APT29.` + `Nagar, G. (2018). The evolution of security operations centers...` thành `[G34]` (`auth=['Mitre']`, `yr=2018`, `title='The evolution of security operations centers...'`), **xóa sổ tác giả `Nagar (2018)`**, khiến `(Nagar, 2018)` trong bài bị báo `missing_reference` và `[V34]` bị phán `UNRESOLVED`!
  2. **GROBID lấy mã bài báo `1981` làm năm xuất bản của `Dawood et al. (2023)` (`[G14]`)**:
     - Ground Truth #15: `Dawood, M., Tu, S., Xiao, C., Alasmary, H., Waqas, M., & Rehman, S. U. (2023). Cyberattacks and Security of Cloud Computing: A Complete Guideline. Symmetry (20738994), 15(11), 1981. https://doi.org/10.3390/sym15111981`
     - GROBID parse `yr = "1981"` (từ số trang/mã bài `1981`) thay vì `2023`! Dù Regex `[R15]` parse đúng `yr = 2023`, `_enrich_grobid_ref` không sửa `target.year`. Hậu quả: `(Dawood et al., 2023)` trong bài bị báo `missing_reference`, `[M14]` bị báo `uncited_reference`, và `[V14]` bị phán `UNRESOLVED` do lệch năm `1981 vs 2023`!
  3. **URL bị ngắt dòng giữa từ (`.p\ndf`, `hundreds_o\nf_websites.html`) và tác giả tổ chức bị đảo (`OffSec Team` -> `['Team']`)**:
     - `[R1]` cắt URL `.../RAND_CT490.p\ndf` tại `.p`, đẩy `df Ajmal...` sang `[R2]`.
     - `[R40]` cắt URL `.../hundreds_o\nf_websites.html` tại `_o`, đẩy `f_websites.html` sang tác giả mục `[R41]`.
     - `OffSec Team. (2025)` bị GROBID parse thành `['Team, Offsec']` và Regex parse thành `['Team']`, khiến `(OffSec Team, 2025)` trong bài không link được!

---

### File `13.pdf` — *Gen Z Loneliness and Christian Community* (Chicago NB, 30 trang)
- **Phân đoạn**: `body` (trang 1–28), `bibliography` (trang 29–30) — **Chính xác 100%**.
- **Ground Truth References**: **26** mục.
- **Kết quả Hệ thống**: GROBID = `26`, Regex = `18`, Merged = **`28` (+2 mục thừa, mất 1 mục thật)**:
  1. **`_is_fake_entry` xóa mất `[G24] The ESV Study Bible (2008)` khỏi GROBID**:
     - Ground Truth #24: `The ESV Study Bible, Wheaton, IL: Crossway, 2008.`
     - GROBID bóc `[G24]` (`auth=[]`, `yr=2008`, `title='The ESV Study Bible'`, `venue='The ESV Study Bible'`). Tại `grobid_adapter.py:155`, vì `venue == title`, `venue` bị xóa thành `None`, khiến `raw_text = "(2008) The ESV Study Bible"` (26 ký tự `< 30`) -> bị `_is_fake_entry` xóa bỏ!
     - Trong khi đó ở Regex, URL của mục #23 (`Swindoll, 2016`) bị dính chữ `The` của mục #24 (`.../9781414300605?srsltid=...The` -> gây lỗi 404 và phán nhầm `[V23] suspected_hallucination`!), còn phần còn lại `ESV Study Bible, Wheaton, IL: Crossway, 2008.` bị ghép vào mục #25 (`Turkle, Sherry, 2016`) tạo thành `[M28]` (`yr=2016, title='The ESV Study Bible, Wheaton, IL: Crossway, 2008'`)!
  2. **2 mục thừa từ Regex (`[M26]` & `[M27]`)**: Nhân bản `Barna Group (2022)` và `Heaton (1956)`.
  3. **In-text Citations**: Bắt nhầm **16 cụm `(City: Publisher, Year)`** trong footnotes làm trích dẫn APA (`1/28 matched`).

---

### File `14.pdf` — *Early-Onset vs. Late-Onset Alzheimer's Disease* (APA 7, 32 trang)
- **Phân đoạn**: `body` (trang 1–28), `bibliography` (trang 29–32) — **Chính xác 100%**.
- **Ground Truth References**: **24** mục.
- **Kết quả Hệ thống**: GROBID = `24`, Regex = `22`, Merged = **`24` (Đạt 100% số lượng)**.
- **Các lỗi phát hiện được**:
  1. **Dấu gạch nối ngắt dòng trong trích dẫn in-text**: `(Popławska- Domaszewicz et al., 2025)` (trang 11) có khoảng trắng sau dấu `-` nên không link được tới `[M15] Popławska-Domaszewicz, K. et al. (2025)`, làm `[M15]` bị báo oan là `uncited_reference`!
  2. **Lỗi sinh viên ghi nhầm năm trong thân bài (4 chỗ)**: Sinh viên viết `(Tellechea et al., 2015)` (3 lần, trong khi Reference là `2018`) và `(Polsinelli et al., 2022)` (1 lần, trong khi Reference là `2023`). Đáng lẽ `CitationLinker` phải phân loại đây là **`IN_TEXT_MISMATCH`** (cùng họ tác giả duy nhất trong bài nhưng lệch năm > 1), thay vì báo `MISSING_REFERENCE`!

---

### File `15.pdf` — *Podcasts, Social Media, and the 2024 Presidential Election* (Chicago NB với tiêu đề `References`, 30 trang)
- **Phân đoạn**: `body` (trang 1–26), `bibliography` (trang 27–30) — **Chính xác 100%**.
- **Ground Truth References**: **45** mục (trình bày theo chuẩn Chicago NB dưới tiêu đề `References`).
- **Kết quả Hệ thống**: GROBID = `50`, Regex = `37`, Merged = **`51` (+6 mục thừa)**:
  1. **GROBID hút 5 Footnotes ở trang 26 vào Bibliography (`[G1]` – `[G5]`)**:
     - 5 mục đầu tiên của GROBID là footnotes của trang 26, trong đó `[G5]` dán luôn tiêu đề `References` của trang 27 vào đuôi URL (`https://.../4-top-voting-issues-in-2016-election/.References`), gây ra 1 phán quyết `SUSPECTED_HALLUCINATION` (`[V01]`) và 1 `UNRESOLVED` (`[V02]`).
  2. **GROBID tách đôi mục có URL bị ngắt dòng (`[G9]+[G10]` và `[G20]+[G21]`)**:
     - Mục `Bump, Philip (2024)` có URL dài ngắt qua dòng bị GROBID tách thành `[G9]` và `[G10]` (`title=None`).
     - Mục `Flegenheimer, Matt (2024)` có URL Wayback Machine dài bị GROBID tách thành `[G20]` và `[G21]` (`title=None`).
  3. **Regex cắt đứt URL bị ngắt dòng giữa từ (`markin\ng%20all`, `A_theoretical_ac\ncount`, `aid=9\n6753`)**:
     - Làm đứt đôi URL và đẩy phần đuôi URL (`g%20all...`, `count_of_media...`, `6753.`) sang làm tên tác giả của mục tiếp theo!

---

### File `16.pdf` — *Gut Microbiota, Nutrition, Probiotics, and Stress* (APA 7, 51 trang)
- **Phân đoạn**: `body` (trang 1–39), `bibliography` (trang 40–51) — **Chính xác 100%**.
- **Ground Truth References**: **66** mục.
- **Kết quả Hệ thống**: GROBID = `66`, Regex = `65`, Merged = **`66` (Đạt 100% số lượng)**.
- **Các lỗi nghiêm trọng ở tầng In-text Extraction, Linking & Rules**:
  1. **`_APA_NARRATIVE_RE` bắt nhầm trạng từ đầu câu làm tên tác giả thứ nhất (9 lần!)**:
     - Trong thân bài, sinh viên viết:
       - `Similarly, Mysonhimer et al. (2023)` (trang 19)
       - `However, Vandeputte et al. (2017)` (trang 19)
       - `Conversely, Bongiovani et al. (2025)` (trang 24)
       - `However, Gargari et al. (2016)` (trang 25)
       - `However, Li et al. (2024b)` (trang 25)
       - `Yet, Kato-Katoaka et al. (2016)` (trang 28)
       - `However, Crichton et al. (2023)` (trang 31)
       - `However, Sasaki et al. (2025)` (trang 31)
       - `However, Holscher et al. (2018b)` (trang 31)
     - Regex `_APA_NARRATIVE_RE` coi `However, Vandeputte et al. (2017)` là trích dẫn 2 tác giả (`Author 1 = "However"`, `Author 2 = "Vandeputte"`). Khi `CitationLinker` tìm tác giả đầu `"however"`, cả 9 trích dẫn đều bị báo `missing_reference`, kéo theo 5 tài liệu tham khảo thật (`Crichton 2023`, `Gargari 2016`, `Holscher 2018`, `Kato-Kataoka 2016`, `Sasaki 2025`) bị báo oan là `uncited_reference`!
  2. **Lỗi không khớp dấu phụ / dấu nháy / gạch nối trong `CitationLinker` (9 lần)**:
     - `(Hrncir, 2022)` (3 lần) không khớp với `[M27] Hrncír, T (2022)` -> làm `[M27]` bị báo `uncited`!
     - `(Larimore & O’Mathúna, 2003)` (2 lần) không khớp với `[M33] auth=['Larimore, W L', "O'mathúna, D P"]` -> làm `[M33]` bị báo `uncited`!
     - `Marquez-Morales et al. (2021)` (2 lần) không khớp với `[M40] Márquez-Morales, L (2021)` -> làm `[M40]` bị báo `uncited`!
     - `(Vásquez Castellanos et al., 2025)` và `(Vázquez Castellanos et al., 2025)` (thiếu dấu `-`) không khớp với `[M58] Vázquez-Castellanos, J F (2025)`.
  3. **Bẫy `local_db` Tier 0 làm `[V01] Aslam et al. (2018)` bị phán `UNRESOLVED`**:
     - Có `DOI match=True` (`10.1080/1028415X.2018.1544332`), `title_sim=1.00`, `author_sim=1.00`, nhưng vì `local_db` lưu năm in `2020` (`year_dist=2`) và không gọi live API nên rơi vào `R-WEAK-EVIDENCE` (`UNRESOLVED`)!

---

### File `17.pdf` — *AI Wellness & Fitness App Business Plan* (APA 7, 48 trang)
- **Phân đoạn**: `body` (trang 1–42), `bibliography` (trang 43–47), `appendix` (trang 48) — **Chính xác 100%**.
- **Ground Truth References**: **35** mục.
- **Kết quả Hệ thống**: GROBID = `30`, Regex = `35`, Merged = **`36` (hỏng nặng do GROBID gộp 5 cặp mục và Regex đẻ 6 mục trùng/hỏng URL)**:
  1. **GROBID gộp 5 cặp mục liên tiếp (`35 -> 30`)**:
     - `[G9]` gộp #9 (`CAC payback period | KPI example | Geckoboard, 2024`) + #10 (`CAC payback period vs LTV: CAC ratio, 2022, MetricHQ`).
     - `[G12]` gộp #13 (`Eichenberger-Archer, S., 2023`) + #14 (`Fitness app market growth, 2023, Thryve Health`), làm mất hoàn toàn mục #14!
     - `[G23]` gộp #25 (`Rawat, A., 2025`) + #26 (`Retention metrics for fitness apps: Industry insights, 2025, Lucid Now`).
     - `[G24]` gộp #27 (`Shah, K., 2026`) + #28 (`State of subscription apps 2025, RevenueCat`), đổi năm của `Shah` từ `2026` thành `2025` và gán nhầm URL của `RevenueCat` cho `Shah`! Làm **4 trích dẫn `(Shah, 2026)` trong bài bị báo `missing_reference`**!
     - `[G26]` gộp #30 (`Top 7 user behavior metrics for fitness apps, 2025, Sport Fitness Apps`) + #31 (`Top fitness marketing statistics 2025, Amra and Elma LLC`).
  2. **GROBID lấy năm `2020` trong tiêu đề `2020–2026` làm năm xuất bản của `Likhil, G. (2025)` (`[G19]`)**:
     - Ground Truth #21: `Likhil, G. (2025, August). Fitness app market size, growth & value: Industry report, 2020–2026. Polaris Market Research.`
     - GROBID parse `yr = 2020` thay vì `2025`! Dù Regex `[R21]` parse đúng `yr = 2025`, `_enrich_grobid_ref` không sửa `target.year`. Hậu quả: **cả 7 trích dẫn `(Likhil, 2025)` trong bài đều bị báo `missing_reference`**, còn `[M19] Likhil (2020)` bị báo `uncited_reference`!
  3. **Regex làm dính họ tác giả tiếp theo vào 9 URL và tạo ra 6 bản ghi trùng `[M31]`–`[M36]`, gây ra 4 phán quyết `SUSPECTED_HALLUCINATION` giả (`[V31, V32, V33, V35]`)**:
     - `[M31]` (`title='Geckoboard'`, `url='.../cac-payback-period/CAC'`) -> HTTP 404 -> `suspected_hallucination`!
     - `[M32]` (`title='MetricHQ'`, `url='.../cac-payback-period-vs-ltv-cac-ratio/Calibraint'`) -> HTTP 404 -> `suspected_hallucination`!
     - `[M33]` (`title='Lucid Now'`, `url='.../retention-metrics-for-fitness-apps-industry-insights/Shah'`) -> HTTP 404 -> `suspected_hallucination`!
     - `[M35]` (`title='RevenueCat'`, `url='.../state-of-subscription-apps-2025/Teixeira'`) -> HTTP 404 -> `suspected_hallucination`!
  4. **Lỗi In-text Extraction & Linking**:
     - Bắt nhầm `(Years 1–3)` (2 lần ở trang 39, 41) làm trích dẫn MLA `(Author Page)`.
     - Dấu gạch nối ngắt dòng `(Abu- Omar et al., 2023)` và `(Eichenberger- Archer, 2023)` (2 lần) không link được.
     - Các mục không có tác giả người (Title-first entries) được trích dẫn trong bài theo tên tiêu đề hoặc tên Website (`(Z2A Digital, 2025)`, `(Sportsfitnessapps, 2025)`, `(Lucid. Now, 2025)`, `(RevenueCat, 2025)`, `(Top Fitness Marketing Statistics, 2025)`, `(Retention Metrics for Fitness Apps: Industry Insights, 2025)`) đều không link được!

---

### File `18.pdf` — *Machine Learning Apogee Prediction for Suborbital Rockets* (APA 7, 37 trang)
- **Phân đoạn**: `body` (trang 1–34), `bibliography` (trang 35–37) — **Chính xác 100%**.
- **Ground Truth References**: **25** mục.
- **Kết quả Hệ thống**: GROBID = `24`, Regex = `25`, Merged = **`24` (thiếu 1 mục)**:
  1. **GROBID gộp 2 mục phần mềm `(n.d.)` liên tiếp (`[G19]`)**:
     - Mục #19: `RocketPy Team. (n.d.). RocketPy (Version 1.10.0) [Computer software]. https://rocketpy.org/`
     - Mục #20: `RocketSerializer Developers. (n.d.). RocketSerializer [Computer software]. https://github.com/RocketPy-Team/RocketSerializer`
     - GROBID gộp cả hai thành `[G19]` và lấy URL của `RocketSerializer`, khiến Regex `[R20]` bị khử trùng lặp theo URL, **xóa sổ mục `RocketSerializer Developers (n.d.)`**!
  2. **GROBID cắt cụt DOI bị ngắt dòng của `Zhou (2021)` (`[G24]`)**:
     - Ground Truth #25: `Zhou, Z.-H. (2021). Machine Learning. Springer Singapore. https://doi.org/10.1007/978-981-15-\n1967-3`
     - GROBID cắt cụt DOI tại chỗ xuống dòng: `doi='10.1007/978-981-15-'`. Dù Regex `[R25]` đã nối đúng `doi='10.1007/978-981-15-1967-3'`, `_enrich_grobid_ref` không ghi đè vì `target.doi` đã khác rỗng!
  3. **Lỗi không nhận diện DataCite arXiv DOI `10.48550/arXiv.2206.11721` (`[V10] Jain et al., 2022`)**:
     - Bài báo arXiv có thật 100% nhưng因為 `10.48550/arXiv.2206.11721` là DataCite DOI (không nằm trên Crossref), hệ thống báo `DOI match=False` và đánh nhãn `[V10] UNRESOLVED (conf=0.37)`!
  4. **1 False Positive In-text Citation**: Bắt nhầm `Networks (p.56)` ở trang 9 (từ câu `...in Artificial Neural Networks (p.56)`) làm trích dẫn tự sự MLA!

---

### File `19.pdf` — *Titanium Dioxide Nanoparticles, Gut Dysbiosis, and Metabolic Disease* (APA 7, 42 trang)
- **Phân đoạn**: `body` (trang 1–29), `bibliography` (trang 30–42) — **Chính xác 100%**.
- **Ground Truth References**: **75** mục.
- **Kết quả Hệ thống**: GROBID = `75`, Regex = `75`, Merged = **`75` (Đủ 75/75 mục, nhưng toàn bộ 3 lỗi `missing_reference` và 3 lỗi `UNRESOLVED` đều do Bug của hệ thống!)**:
  1. **GROBID lấy mã bài báo `2008` và `2015` (của MDPI) làm năm xuất bản (`[M50]` & `[M64]`)**:
     - **`[M50]`**: `Rinninella, E., ... (2021). Impact of Food Additive Titanium Dioxide... International Journal of Environmental Research and Public Health, 18(4), 2008. https://doi.org/10.3390/ijerph18042008` -> GROBID parse `yr = "2008"` thay vì `2021`!
     - **`[M64]`**: `Stolfi, C., ... (2023). Impact of Western Diet... Biomedicines, 11(7), 2015. https://doi.org/10.3390/biomedicines11072015` -> GROBID parse `yr = "2015"` thay vì `2023`!
     - Dù Regex `[R50]` (`yr=2021`) và `[R64]` (`yr=2023`) parse đúng 100% từ `(2021)` và `(2023)`, `_enrich_grobid_ref` vẫn giữ `2008` và `2015` của GROBID!
     - Hậu quả dây chuyền:
       - Trong thân bài, `(Rinninella et al., 2021)` và `(Stolfi et al., 2023)` bị báo `missing_reference`!
       - Trong danh mục tham khảo, `[M50]` và `[M64]` bị báo `uncited_reference`!
       - Ở tầng Verification, vì lệch năm (`2008 vs 2021` và `2015 vs 2023`) kết hợp với bẫy `local_db` Tier 0, cả `[V50]` lẫn `[V64]` đều bị phán **`UNRESOLVED (conf=0.28)`** dù có DOI khớp 100%!
  2. **Lỗi chữ ghép Bắc Âu `æ` (`Præstholm` vs `Praestholm`) ở `[M45]`**:
     - Trong thân bài: `(Præstholm et al., 2020)`. Trong GROBID `[M45]`: `auth=['Praestholm, S M', ...]`.
     - Vì `unicodedata.normalize("NFKD", "æ")` không tách `æ` thành `ae`, `CitationLinker` coi `"præstholm"` != `"praestholm"`, khiến `(Præstholm et al., 2020)` bị báo `missing_reference` và `[M45]` bị báo `uncited_reference`!
     - Như vậy, nếu sửa 2 bug trên (năm của GROBID và chữ ghép `æ`), **`19.pdf` sẽ đạt 102/102 in-text citations matched (0 `missing_reference`)**!

---

### File `20.pdf` — *Prophecy According to Paul in 1 Corinthians 12–14* (Chicago NB / Turabian, 49 trang)
- **Phân đoạn**: `body` (trang 1–46), `bibliography` (trang 47–49) — **Chính xác 100%**.
- **Ground Truth References**: **29** mục.
- **Kết quả Hệ thống**: GROBID = `29`, Regex = `10`, Merged = **`36` (+7 mục rác)**:
  1. **GROBID bóc chuẩn 29/29 mục (`[G1]` – `[G29]`), nhưng Regex nối thêm 7 mục rác (`[M30]` – `[M36]`)**:
     - Nhiều sách trong `20.pdf` kết thúc bằng tên cơ sở dữ liệu `ProQuest Ebook Central.` sau năm xuất bản (ví dụ: `...Dorset: Deo Publishing, 2013. ProQuest Ebook Central.`).
     - Regex `_split_by_year_boundary` cắt sau `2013.`, rồi `_HARVARD_ARTICLE_RE` biến toàn bộ mục trước thành `author.last_name`, lấy `2013` làm `year`, và lấy `"ProQuest Ebook Central"` làm `title`!
     - 7 bản ghi rác `title="ProQuest Ebook Central"` (`[M30]`–`[M36]`) được nối vào cuối danh sách và gây ra **3 phán quyết `SUSPECTED_HALLUCINATION` giả (`[V30, V33, V35]`)** cùng 3 `UNRESOLVED` (`[V31, V32, V36]`)!
  2. **In-text Citations**: Bắt nhầm **26 cụm `(City: Publisher, Year)`** trong footnotes (ví dụ `(Grand Rapids, MI: Baker Academic, 2017)`) và 1 trích dẫn Kinh Thánh `(Acts 18)` làm trích dẫn trong bài, gây ra 27 `missing_reference` giả!


---

## Phần 3: Danh Mục Toàn Diện 22 Bugs Gốc Rễ Phân Theo 6 Tầng Kiến Trúc

Dưới đây là toàn bộ **22 lỗi gốc rễ (Root-Cause Bugs)** được xác định qua quá trình đối chiếu từng dòng Ground Truth với đầu ra của hệ thống trên cả 20 khóa luận, được phân bổ theo 6 tầng xử lý của pipeline:

---

### Tầng 1 — Document Loading & Section Segmentation

#### **BUG-01: Không phát hiện PDF dạng ảnh scan (Image-only PDF) và gây lỗi `HTTP 500` trên GROBID**
- **Vị trí code**:
  - [pdf_loader.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/pdf_loader.py#L46-L90)
  - [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L97-L165)
- **File bị ảnh hưởng**: `4.pdf` (37 trang, `0` ký tự văn bản trích xuất được).
- **Nguyên nhân gốc rễ**:
  - `PDFLoader.load()` dùng PyMuPDF `page.get_text("text")` trả về chuỗi rỗng `""` cho cả 37 trang của `4.pdf` mà không kiểm tra mật độ ký tự trên trang.
  - Khi đẩy file PDF không có text layer sang GROBID (`processFulltextDocument`), GROBID trả về `500 Server Error: Internal Server Error`, sau đó pipeline âm thầm rơi về Regex trên chuỗi rỗng và xuất báo cáo `0 citations, CIS = 0.0` mà không có cờ cảnh báo `SCANNED_PDF_NO_TEXT` hay cơ chế OCR fallback.

#### **BUG-02: Không hỗ trợ khóa luận chỉ dùng Footnotes mà không có mục Bibliography cuối bài**
- **Vị trí code**:
  - [section_segmenter.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/section_segmenter.py#L70-L155)
  - [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L148-L160)
- **File bị ảnh hưởng**: `3.pdf` (34 trang, 177 chú thích chân trang kiểu Luật học Bluebook/Chicago, không có mục `Bibliography`/`References` cuối bài).
- **Nguyên nhân gốc rễ**:
  - Tại [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L150), khi `SectionSegmenter` không tìm thấy section `BIBLIOGRAPHY` (`has_bib_section = False`), hệ thống vứt bỏ toàn bộ kết quả `<biblStruct>` của GROBID (`grobid_refs = []`) và không có luồng trích xuất chú thích chân trang (footnotes) độc lập.

---

### Tầng 2 — GROBID Bibliography Extraction & Adapter

#### **BUG-03 [CRITICAL]: GROBID hút các Footnotes và câu văn trong thân bài vào danh sách `bibliography`**
- **Vị trí code**:
  - [grobid_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_parser.py#L198-L231) (`parse_bibliography`)
  - [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L148-L185)
- **File bị ảnh hưởng**: `3.pdf` (+17 footnotes), `10.pdf` (**+32 footnotes/câu thân bài `[G1]`–`[G32]`**), `15.pdf` (**+5 footnotes `[G1]`–`[G5]`**).
- **Nguyên nhân gốc rễ**:
  - Khi gọi GROBID `processFulltextDocument` cho toàn bộ file PDF, GROBID đóng gói cả các chú thích chân trang (footnotes ở cuối các trang thân bài) vào thẻ `<biblStruct>` trong TEI XML, hoặc `GrobidParser.parse_bibliography()` lấy mọi thẻ `<biblStruct>` mà không kiểm tra xem thẻ đó nằm trong vùng trang `BIBLIOGRAPHY` đã được `SectionSegmenter` xác định hay nằm ở các trang thân bài (`BODY`).
  - Ngoài ra, ở ranh giới chuyển trang từ trang thân bài cuối cùng sang trang đầu tiên của `Bibliography`/`References` (`10.pdf` `[G33]` trang 51–52 và `15.pdf` `[G5]` trang 26–27), GROBID dán luôn chú thích cuối trang trước vào tiêu đề `Bibliography`/`References` và mục tham khảo đầu tiên của trang sau!
- **Hậu quả**: Riêng trên `10.pdf` và `15.pdf`, lỗi này tạo ra **37 mục tham khảo giả**, dẫn tới **11 phán quyết `SUSPECTED_HALLUCINATION` sai** trên các câu văn/chú thích của sinh viên!

#### **BUG-04 [CRITICAL]: GROBID nhận nhầm mã bài báo 4 chữ số (Article Number / eLocator) hoặc năm trong tiêu đề làm Năm xuất bản (`year`)**
- **Vị trí code**:
  - [grobid_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_parser.py#L319-L343) (`_extract_year`)
  - [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L220-L265) (`_enrich_grobid_ref`)
- **File bị ảnh hưởng**: `12.pdf` (`[G14]`), `17.pdf` (`[G19]`), `19.pdf` (`[G50]`, `[G64]`).
- **Nguyên nhân gốc rễ**:
  - Các tạp chí điện tử (như MDPI *Symmetry*, *IJERPH*, *Biomedicines*) dùng mã bài báo 4 chữ số bắt đầu bằng `19xx` hoặc `20xx` ở vị trí số trang:
    - `12.pdf` `[G14]`: `Dawood, M. et al. (2023)... Symmetry, 15(11), 1981.` -> GROBID gắn `<date when="1981">`, parse `year = 1981` thay vì `2023`!
    - `19.pdf` `[G50]`: `Rinninella, E. et al. (2021)... IJERPH, 18(4), 2008.` -> GROBID parse `year = 2008` thay vì `2021`!
    - `19.pdf` `[G64]`: `Stolfi, C. et al. (2023)... Biomedicines, 11(7), 2015.` -> GROBID parse `year = 2015` thay vì `2023`!
  - Hoặc khi tiêu đề có dải năm dự báo:
    - `17.pdf` `[G19]`: `Likhil, G. (2025, August). Fitness app market size... report, 2020–2026.` -> GROBID parse `year = 2020` thay vì `2025`!
  - Dù Regex parser (`ReferenceListParser`) luôn bắt chính xác 100% năm nằm trong ngoặc đơn `(2023)`, `(2021)`, `(2025)` ngay sau tên tác giả, hàm `_enrich_grobid_ref()` tại `document_parser.py:225` chỉ gán `if not target.year and source.year: target.year = source.year`, nên không bao giờ sửa năm sai của GROBID!
- **Hậu quả**: Phá vỡ toàn bộ liên kết in-text (`missing_reference` + `uncited_reference`) và làm tầng Verification đánh nhãn nhầm `METADATA_ERROR` hoặc `UNRESOLVED` trên các bài báo có DOI chuẩn 100%!

#### **BUG-05 [CRITICAL]: GROBID gộp 2–3 tài liệu tham khảo liên tiếp thành 1 thẻ `<biblStruct>` duy nhất**
- **Vị trí code**:
  - [grobid_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_parser.py#L198-L231)
  - [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L465-L595) (`_merge_reference_lists`)
- **File bị ảnh hưởng**: `2.pdf` (1 cặp), `7.pdf` (1 cặp), `9.pdf` (3 cặp), `12.pdf` (4 cụm = mất 5 mục), `17.pdf` (5 cặp), `18.pdf` (1 cặp). Tổng cộng **15 cụm bị gộp (làm mất hoặc làm hỏng 31 mục tham khảo)**.
- **Nguyên nhân gốc rễ**:
  - Khi một mục tham khảo kết thúc bằng URL dài hoặc không có dấu chấm kết thúc trước khi xuống dòng sang một mục mới có tác giả là tên Tổ chức (`Amen Clinics`, `American College of Radiology`, `Hunt.io`, `IBM`, `MITRE`, `National Institute of Mental Health`, `RocketSerializer Developers`) hoặc mục mở đầu bằng Tiêu đề (`CAC payback period...`, `Fitness app market growth...`, `State of subscription apps 2025...`), mô hình CRF của GROBID không nhận ra ranh giới ngắt mục và gộp cả 2–3 mục vào chung 1 `<biblStruct>`.
  - Nguy hiểm hơn, thẻ `<biblStruct>` bị gộp này thường lấy `authors` của mục 1 nhưng lại lấy `year`, `venue` hoặc `url` của mục 2 (ví dụ: `17.pdf` `[G24]` lấy tác giả `Shah, K.` của mục #27 nhưng lấy năm `2025` và URL `revenuecat.com` của mục #28; `12.pdf` `[G1]` lấy tác giả `Ablon, L. (2018)` của mục #1 nhưng lấy tiêu đề và DOI `Ajmal et al. (2023)` của mục #2!).

#### **BUG-06: GROBID tách 1 tài liệu tham khảo thành 2 thẻ `<biblStruct>` rời rạc**
- **Vị trí code**:
  - [grobid_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_parser.py#L198-L231)
  - [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L465-L595)
- **File bị ảnh hưởng**: `1.pdf` (`[G2]+[G3]`), `6.pdf` (`[G15]+[G16]`), `11.pdf` (`[G18]+[G19]`), `15.pdf` (`[G9]+[G10]`, `[G20]+[G21]`).
- **Nguyên nhân gốc rễ**:
  - Khi một mục tham khảo có tiêu đề dịch trong ngoặc vuông `[Performanța ESG...]` (`11.pdf`), lỗi thiếu khoảng trắng sau dấu `&` (`Ballot, P., &Allcott, H.` trong `1.pdf`), hoặc URL quá dài bị ngắt qua nhiều dòng (`15.pdf`), GROBID tách phần nửa sau thành một `<biblStruct>` thứ hai không có năm hoặc không có tiêu đề, dẫn đến sinh thêm bản ghi trùng lặp hoặc mảnh vỡ (`UNRESOLVED` / `SUSPECTED_HALLUCINATION`).

#### **BUG-07: GROBID làm rớt các tác giả đầu trong danh sách tác giả dài và cắt cụt DOI bị ngắt dòng**
- **Vị trí code**:
  - [grobid_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_parser.py#L233-L317)
  - [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L220-L265) (`_enrich_grobid_ref`)
- **File bị ảnh hưởng**: `9.pdf` (`[G14]`, `[G20]`), `18.pdf` (`[G24]`).
- **Nguyên nhân gốc rễ**:
  - Trên `9.pdf`, mục `[G14] Ayano, G. et al. (2021)` (11 tác giả) bị GROBID bỏ sót 8 tác giả đầu (kể cả tác giả chính `Ayano, G.`), chỉ giữ 3 tác giả cuối `['Solomon, M', 'Chaka, A', 'Tsegay, L']`; mục `[G20] Kapucu, L. O. et al. (2009)` (9 tác giả) bị bỏ sót 7 tác giả đầu, chỉ giữ 2 tác giả cuối `['Tatsch, K', 'Van Laere, K']`. Hậu quả là mọi trích dẫn `(Ayano et al., 2021)` và `(Kapucu et al., 2009)` trong bài đều không thể link tới Reference!
  - Trên `18.pdf`, mục `[G24] Zhou, Z.-H. (2021)` có DOI ngắt dòng `10.1007/978-981-15-\n1967-3` bị GROBID cắt cụt thành `'10.1007/978-981-15-'`.

#### **BUG-08: `grobid_adapter.py` xóa tác giả tổ chức có dấu phẩy và tái tạo `raw_text` quá ngắn (< 30 ký tự)**
- **Vị trí code**: [grobid_adapter.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_adapter.py#L145-L185) (`_grobid_bib_to_citation`)
- **File bị ảnh hưởng**: `7.pdf` (`[G12]`), `13.pdf` (`[G24]`), `16.pdf` (`[M44]`).
- **Nguyên nhân gốc rễ**:
  1. Dòng 160: `authors = [a for a in authors if "," not in a or len(a.split(",")) == 2]` xóa mất các tác giả tổ chức có từ 2 dấu phẩy trở lên như `"National Academies of Sciences, Engineering, and Medicine"` (`16.pdf` `[M44]`).
  2. Dòng 154–156: Nếu `venue.lower() == title.lower()`, `venue` bị gán `None`.
  3. Dòng 166–180: Hàm tự ghép lại `raw_text` từ `authors + (year) + title + venue` thay vì giữ `bib.raw_reference`. Với các mục ngắn như `Homer (2016) The Iliad` (22 ký tự, `7.pdf` `[G12]`) hoặc `(2008) The ESV Study Bible` (26 ký tự, `13.pdf` `[G24]`), `len(raw_text) < 30` khiến chúng bị bộ lọc `_is_fake_entry(ref.raw_text)` tại `document_parser.py:591` xóa sổ hoàn toàn!

---

### Tầng 3 — Regex `ReferenceListParser` & Reference Splitting

#### **BUG-09 [CRITICAL]: `_split_by_year_boundary` và `_URL_BOUNDARY_RE` làm dính từ đầu tiên của mục tiếp theo vào đuôi URL/DOI và cắt đứt URL ngắt dòng**
- **Vị trí code**:
  - [reference_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/reference_parser.py#L220-L245) (`_URL_BOUNDARY_RE`, `_join_wrapped_urls`)
  - [reference_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/reference_parser.py#L424-L485) (`_split_by_year_boundary`)
- **File bị ảnh hưởng**: **14/20 khóa luận** (`1.pdf`, `2.pdf`, `6.pdf`, `7.pdf`, `9.pdf`, `10.pdf`, `12.pdf`, `13.pdf`, `14.pdf`, `15.pdf`, `17.pdf`, `18.pdf`, `19.pdf`, `20.pdf`).
- **Nguyên nhân gốc rễ**:
  1. **Dính chữ đầu của mục sau vào đuôi URL/DOI của mục trước**: Khi một mục kết thúc bằng URL/DOI ở cuối dòng và dòng tiếp theo bắt đầu bằng tên tác giả của mục mới (`https://.../censorship\nBallot, P.`), bước nối dòng URL hoặc tách mục theo `_URL_BOUNDARY_RE` nối thẳng từ đầu tiên của mục sau vào URL (`.../censorshipBallot`, `.../brain-spect/Amen,`, `.../cac-payback-period/CAC`, `.../state-of-subscription-apps-2025/Teixeira`, `.../9781414300605?...The`, `10.1007/978-3-662-49851-4_1Nisbet`).
     - Điều này vừa **làm hỏng URL/DOI của mục trước** (gây lỗi HTTP 404 và dẫn tới hàng loạt phán quyết `SUSPECTED_HALLUCINATION` giả!), vừa **ăn cắp mất họ của tác giả đầu tiên ở mục tiếp theo**!
  2. **Cắt đứt URL bị ngắt dòng giữa chừng**: Tại dòng 435 của `reference_parser.py`, `_split_by_year_boundary` thực hiện `text = re.sub(r"\s*\n\s*", " ", text)` (biến mọi ký tự xuống dòng `\n` thành dấu cách `" "`). Khi một URL dài bị PDF ngắt dòng ngay giữa một từ (ví dụ `...RAND_CT490.p\ndf`, `...hundreds_o\nf_websites.html`, `...markin\ng%20all...`), việc thay `\n` bằng dấu cách biến URL thành 2 token cách nhau bởi khoảng trắng! Phần đầu trở thành URL bị cụt (`.p`, `_o`, `markin`), còn phần đuôi (`df`, `f_websites.html`, `g%20all...`) bị đẩy sang làm tên tác giả của mục tiếp theo!

#### **BUG-10 [CRITICAL]: `_split_by_year_boundary` và `_HARVARD_ARTICLE_RE` phá hỏng danh mục tài liệu chuẩn Chicago NB và MLA 9**
- **Vị trí code**:
  - [reference_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/reference_parser.py#L96-L115) (`_HARVARD_ARTICLE_RE`)
  - [reference_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/reference_parser.py#L424-L535) (`_split_by_year_boundary`, `_parse_single_entry`)
- **File bị ảnh hưởng**: Toàn bộ 7 khóa luận dùng chuẩn MLA 9 & Chicago NB (`6.pdf`, `7.pdf`, `8.pdf`, `10.pdf`, `13.pdf`, `15.pdf`, `20.pdf`).
- **Nguyên nhân gốc rễ**:
  - Trong chuẩn Chicago NB và MLA 9, năm xuất bản không nằm trong ngoặc đơn sau tên tác giả mà nằm ở **gần cuối mục tham khảo** (`City: Publisher, 2013. ProQuest Ebook Central.` hoặc `October 14, 2023. YouTube video, 19:33. https://...` hoặc `Journal 17, no. 2 (2018): 229-251.`).
  - `_split_by_year_boundary` được thiết kế giả định năm nằm ở đầu mục (chuẩn APA), nên nó cắt ngay sau `2013.` hoặc `(2018): 229-251.`, tách phần đuôi `ProQuest Ebook Central.` / `YouTube video, 19:33.` sang mục tiếp theo.
  - Sau đó, biểu thức fallback `_HARVARD_ARTICLE_RE` (vốn rất lỏng: `^(?P<authors>.+?)\s+(?P<year>(?:19|20)\d{2})\.\s+(?P<title>.+)$`) nuốt toàn bộ chuỗi văn bản trước năm `2013.` làm `authors`, lấy `2013` làm `year`, và lấy `"ProQuest Ebook Central"` hoặc `"YouTube video, 19:33"` làm `title`!
- **Hậu quả**: Sinh ra **33 bản ghi rác** được nối thêm vào `merged_refs` trên các file `6.pdf` (+17), `10.pdf` (+10), `13.pdf` (+2), `15.pdf` (+6), `20.pdf` (+7), gây ra hàng loạt phán quyết `SUSPECTED_HALLUCINATION` giả!

#### **BUG-11: `_APA_ENTRY_RE` cắt cụt tiêu đề (`title`) tại dấu chấm đầu tiên bên trong tiêu đề**
- **Vị trí code**: [reference_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/reference_parser.py#L54-L66) (`_APA_ENTRY_RE`)
- **File bị ảnh hưởng**: `1.pdf`, `7.pdf`, `8.pdf`, `9.pdf`, `12.pdf`, `14.pdf`, `16.pdf`, `18.pdf`, `19.pdf`.
- **Nguyên nhân gốc rễ**:
  - Trong `_APA_ENTRY_RE`, nhóm `(?P<title>[^\.]+?)` dừng lại ngay ở dấu chấm `.` đầu tiên. Khi tiêu đề chứa từ viết tắt hoặc số thập phân như `vs.`, `Dr.`, `U.S.`, `J. R. R. Tolkien`, `Sarah J. Maas`, `Physalis peruviana L.`, `Web 3.0.`, `RocketPy (Version 1.10.0)`, tiêu đề bị cắt cụt ngay tại dấu chấm đó, còn phần sau của tiêu đề bị đẩy sang trường `rest` (`venue`)!

#### **BUG-12: Parse sai Tác giả Tổ chức (Corporate Authors), Họ kép không gạch nối, Học vị (`PhD`, `Esq`), và các mục APA mở đầu bằng Tiêu đề (Title-first entries)**
- **Vị trí code**:
  - [reference_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/reference_parser.py#L600-L795) (`_parse_authors`, `_CORP_AUTHOR_HEAD_R`)
- **File bị ảnh hưởng**: `7.pdf`, `8.pdf`, `9.pdf`, `11.pdf`, `12.pdf`, `13.pdf`, `15.pdf`, `16.pdf`, `17.pdf`, `18.pdf`, `19.pdf`.
- **Nguyên nhân gốc rễ**:
  1. **Tác giả tổ chức**: Các tổ chức không nằm trong danh sách từ khóa hẹp của `_CORP_AUTHOR_HEAD_R` bị đảo ngược hoặc cắt bớt từ như tên người (`European Environment Agency` -> `'Environment Agency, E'`, `OffSec Team` -> `'Team'`, `Security Risk Advisors` -> `'Advisors'`, `Pew Research Center` -> `'Center'`, `Barna Group` -> `'Group'`, `OpenRocket Project` -> `'Project'`, `RocketPy Team` -> `'Team'`).
  2. **Họ kép nhiều từ không có dấu gạch nối**: `Santa Rosa Lana, G., & Afonso Brardo Duarte, P.` (`11.pdf`) hoặc `da Silva, I. N., Hernane Spatti, D., Andrade Flauzino, R.` (`18.pdf`) bị cắt mất từ đầu của họ (`Rosa Lana, G`, `Brardo Duarte, P`).
  3. **Học vị / chức danh đi kèm tên tác giả**: Trong `16.pdf` `[M14]` (`Eichner, Amy K, PhD; Coyles, Jon, Esq; Fedoruk, Matthew, PhD...`), các học vị `Phd`, `Esq`, `Cscs`, `Facsm`, `Bs` bị tách thành các tác giả độc lập!
  4. **Mục tham khảo APA không có tác giả (Title-first entries)**: Trong `17.pdf` (8 mục web/báo cáo như `4 health & fitness apps marketing case studies for 2025. (2025, February 9). Z2A Digital. https://...`) và `19.pdf` (`Cortisol in metabolic syndrome. (2024). In Advances in clinical chemistry...`), cả GROBID lẫn Regex đều nhét tiêu đề bài viết vào trường `authors` và nhét tên Website/Nhà xuất bản (`Z2A Digital`, `Geckoboard`, `MetricHQ`, `Lucid Now`, `RevenueCat`) vào trường `title`!

#### **BUG-13: Không xử lý ký hiệu gạch ngang `———.` / `________.` thay thế tác giả lặp lại trong chuẩn MLA 9 và Chicago NB**
- **Vị trí code**:
  - [reference_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/reference_parser.py#L510-L595)
  - [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L465-L595)
- **File bị ảnh hưởng**: `6.pdf` (`[G15]`), `8.pdf` (`[G16]`), `10.pdf`, `15.pdf` (`[G37]`, `[G43]`).
- **Nguyên nhân gốc rễ**:
  - Theo quy chuẩn MLA và Chicago, khi liệt kê nhiều tác phẩm của cùng một tác giả liên tiếp nhau, tác giả ở mục sau được thay bằng `---.` hoặc `———.` hoặc `________.`. Hiện tại hệ thống để `authors = []` hoặc `authors = ['________']` thay vì kế thừa `authors` từ mục ngay phía trước.

---

### Tầng 4 — Reference Merging, Enrichment & Post-Filtering (`document_parser.py`)

#### **BUG-14 [CRITICAL]: Bộ lọc `_is_fake_entry` trong `document_parser.py` xóa nhầm hàng loạt tài liệu tham khảo hợp lệ của GROBID**
- **Vị trí code**:
  - [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L580-L595)
  - [reference_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/reference_parser.py#L352-L422) (`_is_fake_entry`)
- **File bị ảnh hưởng**: `1.pdf` (mất 1 mục), `2.pdf` (mất 2 mục), `7.pdf` (mất 1 mục), `8.pdf` (mất 1 mục), `10.pdf` (mất 2 mục), `13.pdf` (mất 1 mục).
- **Nguyên nhân gốc rễ**:
  - Hàm `ReferenceListParser._is_fake_entry(text)` được thiết kế để kiểm tra một **đoạn văn bản thô nguyên mục** (yêu cầu `len(text) >= 30` và phải có định dạng `Surname, F.` hoặc năm/URL).
  - Tuy nhiên, tại `document_parser.py:582-591`, hệ thống lại truyền **từng trường đơn lẻ** `ref.title` và `ref.venue` của GROBID vào `_is_fake_entry`:
    ```python
    if ref.year is None and not ref.doi and not ref.url:
        if ReferenceListParser._is_fake_entry(ref.title or "") or ReferenceListParser._is_fake_entry(ref.venue or ""):
            continue
    if ReferenceListParser._is_fake_entry(ref.raw_text):
        continue
    ```
  - Vì `_is_fake_entry("")` luôn trả về `True` (do `len("") < 30`) và bất kỳ `title` hay `venue` nào ngắn hơn 30 ký tự (như `"Journal of Marketing"`, `"The Iliad"`, `"The ESV Study Bible"`, `"The New Yorker"`) cũng trả về `True`, câu lệnh `or` ở dòng 584 **xóa sạch 100% các mục tham khảo không có năm/URL của GROBID nếu `venue` rỗng hoặc `len(venue) < 30` hoặc `len(title) < 30`**!

#### **BUG-15 [CRITICAL]: `_merge_reference_lists` nối thêm các mục rác của Regex vào kết quả GROBID và `_enrich_grobid_ref` không sửa các trường bị GROBID parse sai**
- **Vị trí code**:
  - [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L220-L265) (`_enrich_grobid_ref`)
  - [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L465-L578) (`_merge_reference_lists`)
- **File bị ảnh hưởng**: `6.pdf`, `7.pdf`, `9.pdf`, `10.pdf`, `12.pdf`, `13.pdf`, `15.pdf`, `17.pdf`, `18.pdf`, `19.pdf`, `20.pdf`.
- **Nguyên nhân gốc rễ**:
  1. **Nối thêm rác từ Regex**: Khi GROBID đã parse được danh mục tham khảo, mọi bản ghi Regex không khớp tiêu đề/tác giả với GROBID (thường là các mảnh vỡ do `_split_by_year_boundary` và `_HARVARD_ARTICLE_RE` tạo ra như `title="ProQuest Ebook Central"`, hoặc mảnh vỡ URL) đều được `_merge_reference_lists` coi là "mục mới mà GROBID bỏ sót" và nối thẳng vào cuối `merged_refs`!
  2. **Không ghi đè trường sai của GROBID, nhưng lại chép URL hỏng của Regex sang GROBID**:
     - Khi GROBID lấy nhầm mã bài báo làm năm (`1981` thay vì `2023` ở `12.pdf`, `2008` thay vì `2021` và `2015` thay vì `2023` ở `19.pdf`, `2020` thay vì `2025` ở `17.pdf`), hoặc làm rớt 8 tác giả đầu (`9.pdf`), hoặc cắt cụt DOI (`18.pdf`), `_enrich_grobid_ref` bỏ qua không sửa vì trường của GROBID đã khác `None`.
     - Ngược lại, khi GROBID không bắt được URL ở một mục web, `_enrich_grobid_ref` lại chép URL đã bị dính chữ của Regex (`https://.../brain-spect/Amen,`, `https://.../understanding-machine-learning-data-poisoning-attacksNagar,`) sang bản ghi GROBID!

---

### Tầng 5 — In-Text Citation Extraction & Citation Linking

#### **BUG-16 [CRITICAL]: `_APA_NARRATIVE_RE` bắt nhầm các Trạng từ chuyển ý đầu câu (`However,`, `Similarly,`, `Conversely,`, `Yet,`) làm Tác giả thứ nhất**
- **Vị trí code**:
  - [citation_extractor.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/citation_extractor.py#L50-L95) (`_APA_NARRATIVE_RE`, `_parse_intext_authors`)
- **File bị ảnh hưởng**: `16.pdf` (**9 trích dẫn trong bài bị hỏng, làm 5 tài liệu tham khảo bị báo oan là `uncited_reference`**).
- **Nguyên nhân gốc rễ**:
  - Trong câu `However, Vandeputte et al. (2017) found that...` hoặc `Similarly, Mysonhimer et al. (2023) reported...`, biểu thức `_APA_NARRATIVE_RE` cho phép 1 hoặc 2 họ tác giả ngăn cách bởi dấu phẩy trước `et al. (YYYY)`. Nó khớp `However, Vandeputte` như 2 họ tác giả (`authors = ['However', 'Vandeputte']`).
  - Khi `CitationLinker` tìm khóa tác giả đầu tiên `"however"`, tất cả 9 trích dẫn đều thất bại (`missing_reference`), đồng thời làm 5 bài báo trong danh mục tham khảo không có lượt trích dẫn nào khác bị đánh dấu oan là `uncited_reference`!

#### **BUG-17 [CRITICAL]: `_APA_PAREN_SINGLE_RE` và `_MLA_PAREN_PAGE_RE` bắt nhầm 88 cụm `(City: Publisher, Year)` trong Footnotes và các cụm ngoặc đơn thông thường làm trích dẫn trong bài**
- **Vị trí code**:
  - [citation_extractor.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/citation_extractor.py#L30-L150)
- **File bị ảnh hưởng**: `5.pdf` (2), `6.pdf` (20), `10.pdf` (16), `13.pdf` (16), `15.pdf` (10), `17.pdf` (2), `18.pdf` (1), `20.pdf` (27). Tổng cộng **94 False Positive in-text citations**.
- **Nguyên nhân gốc rễ**:
  - Trong các khóa luận chuẩn Chicago NB (`6.pdf`, `10.pdf`, `13.pdf`, `15.pdf`, `20.pdf`), mỗi chú thích chân trang đầy đủ đều chứa thông tin xuất bản trong ngoặc đơn: `(Grand Rapids, MI: Baker Academic, 2017)` hoặc `(Downers Grove: IVP Academic, 2023)`. Vì kết thúc bằng `, YYYY)`, `_APA_PAREN_SINGLE_RE` bắt toàn bộ 88 cụm này làm trích dẫn APA với `author = "Baker Academic"` / `"IVP Academic"`!
  - Ngoài ra, `_MLA_PAREN_PAGE_RE` và `_APA_NARRATIVE_RE` còn bắt nhầm:
    - `(see Figure 1)` và `(see Appendix B)` (`5.pdf`)
    - `(September 23, 1934)` (`10.pdf`)
    - `(Years 1–3)` (`17.pdf`)
    - `Networks (p.56)` (`18.pdf`)
    - `(Acts 18)` (`20.pdf`)

#### **BUG-18 [CRITICAL]: Thiếu bộ trích xuất và liên kết Chú thích chân trang (Chicago Notes & Bibliography Footnote Extractor & Linker)**
- **Vị trí code**:
  - [citation_extractor.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/citation_extractor.py)
  - [citation_linker.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/linking/citation_linker.py)
- **File bị ảnh hưởng**: Toàn bộ 6 khóa luận dùng Footnotes (`3.pdf`, `6.pdf`, `10.pdf`, `13.pdf`, `15.pdf`, `20.pdf`).
- **Nguyên nhân gốc rễ**:
  - Hệ thống hiện chỉ hỗ trợ trích dẫn trong ngoặc kiểu APA `(Author, Year)`, MLA `(Author Page)`, và IEEE `[1]`.
  - Với chuẩn Chicago Notes & Bibliography, sinh viên đặt số mũ ở thân bài và ghi chú thích ở chân trang dưới 3 dạng:
    1. **Full note**: `1. First Last, Title of Book (City: Publisher, Year), 45–47.`
    2. **Shortened note**: `2. Last, Short Title, 52.`
    3. **Ibid.**: `3. Ibid., 55.`
  - Do không có parser cho cấu trúc dòng footnote ở cuối trang, hệ thống bỏ sót toàn bộ các trích dẫn thật của 6 khóa luận này và báo gần như 100% danh mục `Bibliography` là `uncited_reference`!

#### **BUG-19: Các lỗ hổng chuẩn hóa chuỗi và so khớp trong `CitationLinker` (Chữ ghép Bắc Âu, Dấu phụ, Gạch nối ngắt dòng, Trích dẫn thứ cấp `"as cited in"`, Tiền tố, Tên viết tắt, Mục không có tác giả người, và Lệch năm cùng tác giả)**
- **Vị trí code**: [citation_linker.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/linking/citation_linker.py#L45-L380)
- **File bị ảnh hưởng**: `1.pdf`, `2.pdf`, `7.pdf`, `8.pdf`, `9.pdf`, `11.pdf`, `12.pdf`, `14.pdf`, `16.pdf`, `17.pdf`, `19.pdf`.
- **Nguyên nhân gốc rễ** (8 trường hợp cụ thể):
  1. **Chữ ghép (Ligatures) không được tách bởi `NFKD`**: `Præstholm` vs `Praestholm` (`19.pdf` `[M45]`). Trong Python, `unicodedata.normalize("NFKD", "æ")` giữ nguyên `"æ"` chứ không chuyển thành `"ae"` (tương tự với `ø -> o`, `œ -> oe`, `ß -> ss`, `đ -> d`, `ł -> l`).
  2. **Dấu phụ & Dấu nháy đơn trong họ tác giả**: `(Hrncir, 2022)` vs `Hrncír, T` (`16.pdf` `[M27]`), `Marquez-Morales` vs `Márquez-Morales` (`16.pdf` `[M40]`), `(Larimore & O’Mathúna, 2003)` vs `"O'mathúna, D P"` (`16.pdf` `[M33]`).
  3. **Khoảng trắng sau dấu gạch nối do ngắt dòng PDF**: `(Hosseini- Motlagh et al., 2020)` (`11.pdf`), `(Lenaerts- Bergmans, 2024)` (`12.pdf`), `(Popławska- Domaszewicz et al., 2025)` (`14.pdf`), `(Abu- Omar et al., 2023)` và `(Eichenberger- Archer, 2023)` (`17.pdf`).
  4. **Trích dẫn thứ cấp (`"as cited in"`)**: Trong `11.pdf` (25 lần, ví dụ `(Belz & Binder, 2015, as cited in Shao et al., 2025)`) và `1.pdf` (`(Zubiaga et al., 2018, as cited in Pennycook & Rand, 2021)`), theo chuẩn APA 7, chỉ tài liệu thứ cấp (`Shao et al., 2025`, `Pennycook & Rand, 2021`) mới nằm trong danh mục `References`. Hiện tại hệ thống tách vế đầu (`Belz & Binder, 2015`) thành một trích dẫn độc lập và báo lỗi `missing_reference` 25 lần!
  5. **Tiền tố dẫn nhập trong ngoặc**: `(Adapted from White, 2022)` (`2.pdf`) bị parse họ tác giả là `"Adapted from White"`.
  6. **Định nghĩa tên viết tắt trong ngoặc vuông**: `(National Institute of Mental Health [NIMH], 2024)` ở lần trích dẫn đầu và `(NIMH, 2024)` ở các lần sau (`9.pdf`).
  7. **Trích dẫn tới mục Title-first hoặc theo tên Website/Publisher**: Trong `17.pdf`, các báo cáo không có tác giả người được trích dẫn theo tiêu đề rút gọn (`(Top Fitness Marketing Statistics, 2025)`) hoặc tên đơn vị phát hành (`(Z2A Digital, 2025)`, `(RevenueCat, 2025)`, `(Lucid. Now, 2025)`), nhưng `CitationLinker` chỉ đánh chỉ mục trên trường `authors`.
  8. **Cùng họ tác giả duy nhất trong bài nhưng sinh viên gõ nhầm năm > 1 năm**: Ví dụ `(Tellechea et al., 2015)` vs `2018` (`14.pdf`), `(Kaveripakam, 2024)` vs `2025` (`11.pdf`), `(Budler & Bozic, 2023)` vs `2024` (`17.pdf`). Khi trong danh mục tham khảo chỉ có duy nhất 1 tài liệu của tác giả đó, `CitationLinker` nên ghép cặp và gán trạng thái `IN_TEXT_MISMATCH` (cảnh báo lệch năm) thay vì báo lỗi kép `MISSING_REFERENCE` + `UNCITED_REFERENCE`.

---

### Tầng 6 — Retrieval, Author Matching & Neuro-Symbolic Rules

#### **BUG-20 [CRITICAL]: Bẫy Short-Circuit ở Tier 0 (`local_db`) kết hợp với điều kiện `_has_live_source` trong `SymbolicRules` đẩy các bài báo có DOI khớp 100% vào `UNRESOLVED`**
- **Vị trí code**:
  - [retrieval_orchestrator.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/retrieval/retrieval_orchestrator.py#L1320-L1355)
  - [rules.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py#L105-L215) (`SymbolicRules.apply`, `_rule_local_db_verified`, `_rule_local_db_good_match`)
- **File bị ảnh hưởng**: `5.pdf` (`[V40]`), `11.pdf` (`[V20]`), `16.pdf` (`[V01]`), `19.pdf` (`[V50]`, `[V64]`).
- **Nguyên nhân gốc rễ**:
  1. Tại `retrieval_orchestrator.py:1325`, khi tìm thấy bài báo trong cơ sở dữ liệu cục bộ (`local_db` ở Tier 0), hệ thống **dừng ngay lập tức (short-circuit)** và không gọi bất kỳ API trực tuyến nào (`Crossref`, `OpenAlex`, `SemanticScholar`, `PubMed`), nên `sources_succeeded = ["local_db"]` -> cờ `_has_live_source = False`.
  2. Trong `SymbolicRules.apply()` (`rules.py`), tất cả các luật kiểm chứng theo DOI và xử lý lệch năm/tác giả (`Rule 1: R-DOI-TITLE-AUTHOR`, `Rule 3b: R-STRONG-METADATA-YEAR`, `Rule 3c: R-PARTIAL-AUTHOR`, `Rule 4a2: R-TITLE-VENUE-YEAR-CONFLICT`) đều có điều kiện tiên quyết `if _has_live_source:`.
  3. Trong khi đó, 2 luật duy nhất dành cho `local_db` (`_rule_local_db_verified` và `_rule_local_db_good_match`) lại đòi hỏi cứng `year_dist <= 1` và `author_sim >= 0.35`.
  4. Hệ quả tất yếu: Bất kỳ bài báo nào tìm thấy trong `local_db` (dù có **`doi_exact_match = True` và `title_sim = 1.00`**) nhưng có `year_dist == 2` (như `16.pdf` `[V01] Aslam et al., 2018` xuất bản online năm 2018 trên DOI `10.1080/1028415X.2018.1544332` nhưng bản in năm 2020) hoặc `author_sim == 0.0` (do đảo họ tên Á Đông ở `5.pdf` `[V40]` và `11.pdf` `[V20]`) đều **trượt qua tất cả các luật** và rơi thẳng xuống `R-WEAK-EVIDENCE` -> **`UNRESOLVED (conf=0.28)`**!

#### **BUG-21: Đảo thứ tự Họ – Tên tác giả Á Đông và Chương sách không ghi tác giả làm `author_jaccard = 0.0`**
- **Vị trí code**:
  - [author_matcher.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/verification/author_matcher.py)
  - [rules.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py#L220-L350)
- **File bị ảnh hưởng**: `5.pdf` (`[V40]`), `11.pdf` (`[V20]`), `19.pdf` (`[V13]`).
- **Nguyên nhân gốc rễ**:
  - Trong `5.pdf` `[V40]`, sinh viên viết tên các tác giả Trung Quốc theo thứ tự `Wei, G., Xiran, Z., Gaik, L. P., & Liang, K.` (lấy tên riêng làm họ và viết tắt họ `Gao -> G.`, `Zhang -> Z.`), trong khi metadata chuẩn là `Gao Wei, Zhang Xiran, Lee Phaik Gaik, Kuang Liang`. Tương tự ở `11.pdf` `[V20]`: `Shuyun, R., Hau-Ling, C., Tana, S.` vs `Shuyun Ren, Hau-Ling Chan, Tana Si`. Vì `AuthorMatcher` chỉ so sánh họ với họ, `author_jaccard = 0.0` dù cả 3–4 tác giả đều khớp hoàn toàn nếu kiểm tra đảo vị trí `(surname == candidate_given_name and initial == candidate_surname[0])`!
  - Trong `19.pdf` `[V13]` (`Cortisol in metabolic syndrome (2024). In Advances in clinical chemistry (Vol. 123, pp. 133-176). Elsevier. https://doi.org/10.1016/bs.acc.2024.06.008`), chương sách được trích dẫn mở đầu bằng tiêu đề nhưng khi đối chiếu với Crossref (có tác giả `Stankovic, S.`), `author_jaccard = 0.0` khiến bài báo có DOI khớp 100% và `title_sim = 1.00` bị đánh nhãn `UNRESOLVED (conf=0.27)`!

#### **BUG-22: Không trích xuất `arxiv_id` từ DataCite arXiv DOI `10.48550/arXiv.<id>`**
- **Vị trí code**:
  - [retrieval_orchestrator.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/retrieval/retrieval_orchestrator.py#L420-L490)
  - [feature_extractor.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/verification/feature_extractor.py)
- **File bị ảnh hưởng**: `18.pdf` (`[V10] Jain, A. et al., 2022`).
- **Nguyên nhân gốc rễ**:
  - DOI chính thức của arXiv (`10.48550/arXiv.2206.11721`) được đăng ký qua DataCite chứ không phải Crossref. Khi `Citation` có `doi = "10.48550/arXiv.2206.11721"` nhưng `arxiv_id = None`, `CrossrefClient.get_by_doi()` trả về 404, còn bản ghi tìm được từ `OpenAlex`/`SemanticScholar` không lưu chuỗi DOI `10.48550/...` mà lưu `arxiv_id = "2206.11721"`, dẫn đến `doi_exact_match = False` và bị đánh nhãn `UNRESOLVED (conf=0.37)`!

---

## Phần 4: Giải Pháp Kỹ Thuật & Kế Hoạch Fix Triệt Để (Đưa Parsing Lên Chuẩn 100%)

Để giải quyết triệt để cả 22 bugs trên và đưa độ chính xác Parsing + Linking + Verification lên mức chuẩn mực, dưới đây là thiết kế giải pháp cụ thể cho từng module theo thứ tự ưu tiên triển khai:

---

### Giai đoạn P0 (Ưu tiên Tối thượng): Chuẩn hóa 100% Reference Parsing, Splitting & Merging

#### **1. Khắc phục BUG-03, BUG-05, BUG-06, BUG-14, BUG-15 trong [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py)**
1. **Lọc bỏ Footnotes của GROBID ngoài vùng `BIBLIOGRAPHY` (Fix BUG-03)**:
   - Trong `DocumentParser.parse()`, sau khi `SectionSegmenter` xác định được văn bản vùng `BIBLIOGRAPHY` (`bib_text`), kiểm tra từng mục `g_ref` trong `grobid_refs`:
     - Một mục `g_ref` chỉ được giữ lại nếu `g_ref.title` hoặc họ tác giả đầu tiên + năm của `g_ref` thực sự xuất hiện trong `bib_text` (sử dụng chuẩn hóa chữ thường không dấu).
     - Nếu `g_ref.raw_text` chứa tiêu đề mục `Bibliography` / `References` nằm ở giữa chuỗi (như `[G33]` của `10.pdf` và `[G5]` của `15.pdf`), cắt bỏ toàn bộ phần văn bản footnote đứng trước tiêu đề `Bibliography`/`References`!
2. **Phát hiện và tách các mục GROBID bị gộp (`Merged <biblStruct>`) bằng Regex đối chiếu (Fix BUG-05)**:
   - Trong `_merge_reference_lists(grobid_refs, regex_refs)`:
     - Kiểm tra xem một bản ghi `g_ref` có chứa từ **2 bản ghi `regex_refs` riêng biệt trở lên** cùng nằm trong phạm vi văn bản của nó hay không (hoặc `g_ref.raw_text` chứa `>= 2` cụm `(YYYY)` / `>= 2` URL/DOI khác nhau).
     - Khi phát hiện `g_ref` là một bản ghi bị GROBID gộp từ $k \ge 2$ mục, **thay thế `g_ref` đó bằng $k$ bản ghi `regex_refs` thành phần** (đã được làm sạch), thay vì giữ bản ghi gộp của GROBID!
3. **Hợp nhất các mảnh GROBID bị tách đôi (`Split <biblStruct>`) (Fix BUG-06)**:
   - Nếu `grobid_refs[i+1]` không có `year` hoặc không có `title` (chỉ có URL hoặc nửa sau tiêu đề) và cả `grobid_refs[i]` lẫn `grobid_refs[i+1]` đều khớp vào cùng một bản ghi `regex_ref` duy nhất, gộp thông tin (URL/DOI/title) của `grobid_refs[i+1]` vào `grobid_refs[i]` và loại bỏ mảnh rời `grobid_refs[i+1]`.
4. **Sửa hoàn toàn logic `_enrich_grobid_ref(target, source)` (Fix BUG-04, BUG-07, BUG-15B)**:
   - **Ưu tiên Năm trong ngoặc đơn `(YYYY)` của APA**: Nếu `target.year != source.year` và `source.year` xuất hiện ngay trong cấu trúc ngoặc đơn `\((19|20)\d{2}[a-z]?(?:,\s*[A-Za-z]+\s*\d{0,2})?\)` sau tên tác giả trong `source.raw_text` (trong khi `target.year` nằm ở cuối câu làm số trang/mã bài báo hoặc trong tiêu đề), **ghi đè `target.year = source.year`**!
   - **Khôi phục tác giả bị GROBID làm rớt**: Nếu `len(source.authors) > len(target.authors)` và họ tác giả đầu tiên của `source.authors` nằm ở đầu dòng `source.raw_text` (trước các tác giả trong `target.authors`), **ghi đè `target.authors = source.authors`**!
   - **Khôi phục DOI bị GROBID cắt cụt**: Nếu `target.doi` kết thúc bằng dấu `-` hoặc `source.doi.startswith(target.doi)` với `len(source.doi) > len(target.doi)`, **ghi đè `target.doi = source.doi`**.
   - **Không chép URL bị dính chữ từ Regex**: Trước khi gán `target.url = source.url`, làm sạch đuôi URL nếu bị dính họ tác giả mục sau.
5. **Bỏ việc gọi `_is_fake_entry` trên từng trường `ref.title` / `ref.venue` của GROBID và chặn nối rác Regex (Fix BUG-08, BUG-14, BUG-15A)**:
   - Trong [grobid_adapter.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/grobid_adapter.py#L166-L180), luôn lưu `bib.raw_reference` (nếu có và dài hơn chuỗi tự ghép) vào `raw_text`, và không xóa tác giả tổ chức có dấu phẩy khi `len(authors) == 1`.
   - Tại [document_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/document_parser.py#L580-L595), thay điều kiện `_is_fake_entry(ref.title) or _is_fake_entry(ref.venue)` bằng kiểm tra cấu trúc thực chất: một bản ghi GROBID hợp lệ khi thuộc vùng `BIBLIOGRAPHY` và có `(bool(ref.title) and bool(ref.authors or ref.year or ref.venue or ref.doi or ref.url))`.
   - Trong `_merge_reference_lists`, khi GROBID đã trích xuất thành công danh mục tham khảo, **không nối thêm các bản ghi `regex_ref` được sinh ra từ mẫu fallback yếu `_HARVARD_ARTICLE_RE`** hoặc các bản ghi `regex_ref` mà `title` chỉ là mảnh vỡ cuối câu (`ProQuest Ebook Central`, `YouTube video...`) của một mục GROBID đã có!

---

#### **2. Khắc phục BUG-09, BUG-10, BUG-11, BUG-12, BUG-13 trong [reference_parser.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/reference_parser.py)**
1. **Tách mục tham khảo dựa trên cấu trúc dòng (Line-start Boundary) TRƯỚC khi xóa `\n` (Fix BUG-09 & BUG-10)**:
   - Không chạy `re.sub(r"\s*\n\s*", " ", text)` trên toàn văn bản `BIBLIOGRAPHY` trước khi tách mục!
   - Thay vào đó, duyệt theo từng dòng của `BIBLIOGRAPHY`:
     - Một dòng mới bắt đầu một mục tham khảo mới khi dòng trước đã kết thúc một mục hoàn chỉnh (kết thúc bằng dấu chấm `.`, URL, hoặc DOI) VÀ dòng mới bắt đầu bằng mẫu đầu mục (`Surname, First/Initial`, `Corporate Author. (YYYY)`, `———.`, hoặc tiêu đề viết hoa theo sau bởi `(YYYY)`).
     - Chỉ nối URL ngắt dòng (`_join_wrapped_urls`) **bên trong phạm vi của cùng một mục tham khảo**, nhờ đó:
       - Không bao giờ dán họ tác giả ở đầu dòng mục mới (`Ballot`, `Amen`, `Nagar`, `CAC`, `Shah`, `Teixeira`, `The`) vào đuôi URL/DOI của mục cũ!
       - Các URL bị ngắt giữa từ (`RAND_CT490.p\ndf`, `hundreds_o\nf_websites.html`, `markin\ng%20all`) được nối liền chính xác mà không bị chèn dấu cách vào giữa!
2. **Hỗ trợ đầy đủ chuẩn Chicago NB & MLA 9 trong `ReferenceListParser` (Fix BUG-10 & BUG-13)**:
   - Cho phép phần đuôi sau năm xuất bản của Chicago NB / MLA 9 bao gồm tên cơ sở dữ liệu / định dạng (`ProQuest Ebook Central\.?`, `YouTube video,\s*[\d:]+\.?`, số trang `: \d+[–-]\d+\.?`, và URL/DOI) nằm trọn trong cùng một mục.
   - Siết chặt `_HARVARD_ARTICLE_RE`: trường `authors` không được dài quá 120 ký tự và không được chứa dấu hai chấm `:`, dấu ngoặc kép `“...”` hay từ khóa `https://`.
   - Khi một mục bắt đầu bằng `^[\-\u2013\u2014_]{3,}\.?` (`———.` hoặc `________.`), tự động sao chép danh sách `authors` của mục tham khảo ngay liền trước đó.
3. **Sửa `_APA_ENTRY_RE` không cắt tiêu đề tại dấu chấm viết tắt / số phiên bản (Fix BUG-11)**:
   - Thay `(?P<title>[^\.]+?)` bằng biểu thức cho phép dấu chấm bên trong tiêu đề nếu theo sau các từ viết tắt phổ biến (`vs\.`, `Dr\.`, `Mr\.`, `Mrs\.`, `Ms\.`, `Jr\.`, `Sr\.`, `U\.S\.`, `U\.K\.`, `Vol\.`, `No\.`, `ed\.`, `eds\.`, `et al\.`, chữ cái viết tắt tên `(?<=\b[A-Z])\.`, hoặc số thập phân/phiên bản `(?<=\d)\.(?=\d)`).
4. **Mở rộng nhận diện Tác giả Tổ chức, Họ kép, Học vị và Mục Title-first (Fix BUG-12)**:
   - Bổ sung từ khóa tổ chức vào `_CORP_AUTHOR_HEAD_R`: `Team`, `Project`, `Developers`, `Center`, `Centre`, `Agency`, `Advisors`, `Group`, `Clinics`, `Foundation`, `College`, `Academy`, `Academies`, `Libraries`, `Press`, `Publishing`, `Society`, `Council`, `Ministry`, `Organization`, `Organisation`, `Network`.
   - Loại bỏ các hậu tố học vị/chứng chỉ (`PhD`, `Ph\.D\.`, `MD`, `M\.D\.`, `MPH`, `Esq\.?`, `CSCS`, `FACSM`, `BS`, `MS`, `RN`) trước khi tách tên tác giả trong `_parse_authors()`.
   - Bảo toàn toàn bộ cụm từ viết hoa đứng trước dấu phẩy đầu tiên làm Họ (`last_name`) cho các họ kép không gạch nối (`Santa Rosa Lana, G.`, `Hernane Spatti, D.`).
   - Nhận diện **Title-first APA entry**: Nếu phần đứng trước `(YYYY)` không có cấu trúc `Surname, F.` và không phải là Corporate Author (mà chứa các từ thường/giới từ của một câu tiêu đề như `4 health & fitness apps marketing case studies for 2025` hoặc `Cortisol in metabolic syndrome`), gán phần trước `(YYYY)` vào `title`, `authors = []`, và phần sau `(YYYY).` vào `venue`!

---

### Giai đoạn P1: Chuẩn hóa In-Text Citation Extraction & Bidirectional Linking

#### **3. Khắc phục BUG-16, BUG-17, BUG-18 trong [citation_extractor.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/extraction/citation_extractor.py)**
1. **Chặn Trạng từ chuyển ý đầu câu khỏi `_APA_NARRATIVE_RE` (Fix BUG-16)**:
   - Thêm danh sách từ dừng đầu câu `_DISCOURSE_ADVERBS = {"however", "similarly", "conversely", "yet", "furthermore", "moreover", "additionally", "specifically", "notably", "therefore", "meanwhile", "consequently", "nevertheless", "nonetheless", "instead", "rather", "indeed", "overall", "finally", "first", "second", "third", "subsequently", "accordingly", "traditionally", "historically", "importantly", "interestingly"}`.
   - Trong `_parse_intext_authors()`, nếu token tác giả đầu tiên (sau khi `.lower()`) nằm trong `_DISCOURSE_ADVERBS`, loại bỏ token đó để lấy đúng họ tác giả thực sự đứng sau dấu phẩy (ví dụ: `However, Vandeputte et al. (2017)` -> `authors = ["Vandeputte"]`).
2. **Loại bỏ 94 False Positive `(City: Publisher, Year)` và cụm ngoặc thường (Fix BUG-17)**:
   - Trong `CitationExtractor`, từ chối mọi kết quả khớp `_APA_PAREN_SINGLE_RE` nếu chuỗi bên trong ngoặc:
     - Chứa dấu hai chấm `:` của cấu trúc xuất bản Chicago `(City: Publisher, Year)` (ví dụ `(Grand Rapids, MI: Baker Academic, 2017)`).
     - Là ngày tháng `(January|February|...|December)\s+\d{1,2},\s+\d{4}`.
     - Bắt đầu bằng từ chỉ mục lục/hình bảng/kinh thánh: `see Figure`, `see Table`, `see Appendix`, `see Chapter`, `Years`, `Acts`, `Rom.`, `Cor.`, `Gen.`, `Matt.`, `John`, `Rev.`.
   - Với `_MLA_PAREN_PAGE_RE` / narrative `(p. X)`: từ chối nếu từ đứng trước `(p. X)` là danh từ học thuật thông thường (`Networks`, `Model`, `Table`, `Figure`, `Equation`, `Section`, `Chapter`).
3. **Bổ sung bộ trích xuất Chú thích chân trang Chicago (`_extract_chicago_footnotes`) (Fix BUG-02 & BUG-18)**:
   - Nhận diện các dòng footnote ở cuối trang (`^\s*(?P<num>\d{1,3})[\.\s]+(?P<note>[A-Z“"].+)$`) hoặc từ các thẻ `<note place="foot">` của GROBID TEI XML:
     - Hỗ trợ **Full Note**: `First Last, Title (City: Publisher, Year), page.`
     - Hỗ trợ **Shortened Note**: `Last, Short Title, page.`
     - Hỗ trợ **Ibid.**: kế thừa tác giả + tiêu đề của footnote ngay trước đó.

---

#### **4. Khắc phục BUG-19 trong [citation_linker.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/linking/citation_linker.py)**
1. **Chuẩn hóa triệt để Chữ ghép (Ligatures), Dấu phụ, Dấu nháy và Gạch nối ngắt dòng**:
   - Trong hàm chuẩn hóa tên tác giả `_normalize_name(name)`:
     - Thay thế bảng chữ ghép trước khi chạy `NFKD`: `{"æ": "ae", "Æ": "ae", "ø": "o", "Ø": "o", "œ": "oe", "Œ": "oe", "ß": "ss", "đ": "d", "Đ": "d", "ł": "l", "Ł": "l"}` (giúp `Præstholm` khớp 100% với `Praestholm` trên `19.pdf`!).
     - Xóa khoảng trắng quanh dấu gạch nối: `re.sub(r"\s*-\s*", "-", name)` (giúp `Hosseini- Motlagh`, `Lenaerts- Bergmans`, `Popławska- Domaszewicz`, `Abu- Omar`, `Eichenberger- Archer` khớp 100%!).
     - Chuẩn hóa mọi biến thể dấu nháy đơn (`’`, `‘`, `` ` ``, `'`) và cho phép khớp bất biến với dấu gạch nối vs dấu cách trong họ kép (`Vázquez Castellanos` <-> `Vázquez-Castellanos`).
2. **Xử lý chuẩn trích dẫn thứ cấp `"as cited in"`**:
   - Khi một cụm ngoặc chứa `, as cited in ` hoặc ` as cited in ` (ví dụ `(Belz & Binder, 2015, as cited in Shao et al., 2025)`), chỉ trích xuất và liên kết vế sau `as cited in` (`Shao et al., 2025`) với danh mục `References` (hoặc đánh dấu vế đầu là `secondary_source` không yêu cầu có mặt trong `References`).
3. **Xử lý tiền tố dẫn nhập, tên viết tắt `[ACRONYM]`, và mục Title-first / Website**:
   - Cắt bỏ các tiền tố dẫn nhập `Adapted from `, `Modified from `, `Based on `, `Cited in ` ở đầu trích dẫn.
   - Khi gặp `(Full Organization Name [ACRONYM], YYYY)`, đăng ký `ACRONYM` làm bí danh (alias) cho tổ chức đó để các trích dẫn `(ACRONYM, YYYY)` sau đó tự động khớp.
   - Đánh chỉ mục bổ sung theo **từ khóa tiêu đề (`title_key`)** và **tên đơn vị phát hành (`venue_key`)** cho các mục tham khảo không có tác giả người (Title-first entries), giúp khớp toàn bộ các trích dẫn kiểu `(Z2A Digital, 2025)`, `(RevenueCat, 2025)`, `(Top Fitness Marketing Statistics, 2025)` trên `17.pdf`.
4. **Phân loại đúng `IN_TEXT_MISMATCH` khi lệch năm trên cùng tác giả duy nhất**:
   - Nếu một trích dẫn `(Surname, Year_A)` không khớp năm nhưng trong danh mục `References` chỉ có duy nhất một mục của `Surname` với `Year_B` (`|Year_A - Year_B| >= 2`), liên kết chúng với trạng thái `IN_TEXT_MISMATCH` thay vì báo lỗi kép `MISSING_REFERENCE` + `UNCITED_REFERENCE`.

---

### Giai đoạn P2: Khắc phục Bẫy `local_db` Tier 0, Tên Á Đông & arXiv DOI ở Tầng Verification

#### **5. Khắc phục BUG-20, BUG-21, BUG-22 trong `retrieval_orchestrator.py`, `author_matcher.py`, và `rules.py`**
1. **Gỡ bẫy Short-Circuit ở Tier 0 (`local_db`) ([retrieval_orchestrator.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/retrieval/retrieval_orchestrator.py#L1325-L1350) & [rules.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/logic/rules.py#L105-L215))**:
   - Trong `RetrievalOrchestrator`: nếu ứng viên từ `local_db` có `year_dist > 1` hoặc `author_jaccard < 0.5`, tiếp tục truy vấn thêm Tier 1 (`Crossref`/`OpenAlex`) để kiểm tra ngày xuất bản online (`published-online`) vs ngày in (`published-print`).
   - Trong `SymbolicRules`:
     - Cho phép `_rule_local_db_verified` chấp nhận `year_dist <= 2` khi `doi_exact_match == True` và `title_sim_fuzzy >= 0.95` (đặc biệt khi năm trích dẫn nằm ngay trong chuỗi DOI như `10.1080/1028415X.2018.1544332`).
     - Bổ sung `_rule_local_db_partial` cho các trường hợp `local_db` có `title_sim_fuzzy >= 0.90` nhưng lệch năm (`year_dist > 1`) hoặc lệch tác giả để trả về `METADATA_ERROR` rõ ràng thay vì rơi xuống `R-WEAK-EVIDENCE` (`UNRESOLVED`).
2. **Hỗ trợ đảo vị trí Họ – Tên tác giả Á Đông và Chương sách không ghi tác giả ([author_matcher.py](file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/src/integrity_checker/verification/author_matcher.py))**:
   - Khi so khớp tác giả `cited` (`last_name="Wei", initials="G"`) với `candidate` (`first_name="Wei", last_name="Gao"`), nếu khớp trực tiếp thất bại, kiểm tra khớp đảo chiều: `cited.last_name == candidate.first_name and cited.initials[0] == candidate.last_name[0]`.
   - Trong `SymbolicRules`: khi `doi_exact_match == True` và `title_sim_fuzzy >= 0.95` và `year_dist <= 1` nhưng `cited.authors` rỗng (như chương sách Elsevier `Cortisol in metabolic syndrome (2024)` ở `19.pdf` `[V13]`), phân loại là `VERIFIED` (hoặc `METADATA_ERROR` nhắc thiếu tên tác giả) thay vì `UNRESOLVED`.
3. **Trích xuất tự động `arxiv_id` từ DOI `10.48550/arXiv.<id>` (Fix BUG-22)**:
   - Khi `citation.doi` khớp biểu thức `^10\.48550/arxiv\.(.+)$` (không phân biệt hoa thường), tự động gán `citation.arxiv_id = match.group(1)` để kích hoạt `ArxivClient` và coi ứng viên khớp `arxiv_id` tương đương với `doi_exact_match = True`.
4. **Cảnh báo rõ ràng cho PDF dạng ảnh scan (Fix BUG-01)**:
   - Trong `DocumentParser.parse()`, nếu tổng số ký tự trích xuất được từ toàn bộ PDF `< 100` ký tự (như `4.pdf`), bỏ qua lệnh gọi GROBID (tránh lỗi `HTTP 500`) và gắn cờ trạng thái `parser_status = "SCANNED_PDF_NO_TEXT_LAYER"` (hoặc kích hoạt OCR fallback qua PyMuPDF/Tesseract nếu được bật).

---

### Bảng Tổng Hợp Tác Động Dự Kiến Sau Khi Triển Khai Fix (P0 + P1 + P2)

| Chỉ số Đánh giá trên tập 20 Theses | Trước khi Fix (Hiện tại) | Sau khi Fix (Dự kiến) |
| :--- | :---: | :---: |
| **Số file phân đoạn đúng vùng `BIBLIOGRAPHY`** | 19/19 file có text (`100%`) | **20/20** (thêm cảnh báo OCR cho `4.pdf`) |
| **Số file có Reference Count khớp 100% Ground Truth** | **5 / 19** (`26.3%`) | **19 / 19 (`100%`)** |
| **Tổng số mục rác từ Footnotes/Regex lọt vào References** | **+70 mục rác** | **0 mục rác** |
| **Tổng số mục thật bị GROBID gộp hoặc `_is_fake_entry` xóa** | **39 mục bị mất/hỏng** | **0 mục bị mất** |
| **Tổng số False Positive In-text Citations (`(City: Publisher, Year)`, v.v.)** | **94 False Positives** | **0 False Positives** |
| **Tổng số phán quyết `SUSPECTED_HALLUCINATION` giả do lỗi Parser** | **26 phán quyết sai** | **0 phán quyết sai do Parser** |
| **Tổng số phán quyết `UNRESOLVED` oan trên bài báo có DOI chuẩn** | **6 bài báo** (`5, 11, 16, 18, 19.pdf`) | **0 bài báo** (đều lên `VERIFIED`) |
