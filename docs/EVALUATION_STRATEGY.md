# Chiến lược Đánh giá — Ghi chú cho Chương 5

> **Ngày lập:** 2026-10-01
> **Người lập:** Claude (Opus 5), tổng hợp từ khảo sát thực tế repository
> **Mục đích:** Ghi lại hai quyết định chiến lược cho phần Đánh giá (Chương 5) của luận văn:
> (1) có nên sinh dataset bằng AI không, và (2) baselines B0–B5 là gì và vì sao bắt buộc.
> **Trạng thái:** Chưa triển khai — đây là ghi chú thiết kế, không phải báo cáo kết quả.

---

## Mục lục

- [Phần A — Về việc sinh dataset bằng AI](#phần-a--về-việc-sinh-dataset-bằng-ai)
- [Phần B — Baselines B0–B5](#phần-b--baselines-b0b5)
- [Phần C — Phụ thuộc và thứ tự thực hiện](#phần-c--phụ-thuộc-và-thứ-tự-thực-hiện)
- [Phần D — Trạng thái hạ tầng hiện có trong repo](#phần-d--trạng-thái-hạ-tầng-hiện-có-trong-repo)

---

# Phần A — Về việc sinh dataset bằng AI

## A.1. Vấn đề không nằm ở "AI hay người", mà ở **tính hợp lệ của phép đo**

Nhìn vào generator hiện tại (`evaluation/synthetic_dataset.py`) để thấy nó đo cái gì:

```python
FAKE_AUTHORS = ["NonExistent Researcher", "FakeAuthor et al.",
                "MysteryPaper", "Invented Scientist", ...]
FAKE_DOIS    = ["10.9999", "10.fake", "10.1234", "10.abric", "10.invalid"]
```

Đây là **positive control** — mẫu mà bất kỳ hệ thống nào cũng bắt được. Precision = 1.0 trên bộ này **không có giá trị khoa học**: nó chỉ chứng minh hệ thống phân biệt được `10.fake` với `10.1038`. Không ai phản biện điều đó ở buổi bảo vệ.

Và nó còn **rò rỉ đáp án**: với `wrong_year`, generator lấy `paper["year"] + randint(5, 15)`. Hệ thống chỉ cần so year lệch > 1 → trúng. Không có "suy luận" nào được kiểm tra.

### Lỗi cứng trong `generate_metadata_error_citations`

```python
similar_authors = ["Wang", "Li", "Zhang", "Liu", "Chen", "Yang", "Huang",
                   "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                   "Kim", "Park", "Lee", "Nguyen", "Tran"]
different_author = self.rng.choice([a for a in similar_authors if a != original_author])
```

`original_author` là **họ đầy đủ** (ví dụ `"Vaswani"`) nhưng tập ứng viên là **họ khác hoàn toàn**. Nghĩa là nó **luôn** chọn được người khác → nhưng đây là "sai tác giả" kiểu *hoàn toàn khác biệt*, dễ phát hiện.

Nó **không** tạo được các lỗi tinh vi — chính là loại khó nhất mà hệ thống cần được kiểm tra:

| Loại lỗi tinh vi | Ví dụ | Generator hiện tại có tạo được? |
|---|---|---|
| Thêm tác giả | `Vaswani` → `Vaswani & Shazeer` | ❌ |
| Typo tên | `Devlin` → `Devlein` | ❌ |
| Hoán đổi venue | bài của tác giả A gán venue của bài B cùng tác giả | ❌ |
| Năm lệch nhỏ | 2017 → 2019 (không phải +5…+15) | ❌ |
| Paraphrase title | đổi cấu trúc câu, giữ nghĩa | ❌ |

---

## A.2. Ba tầng dataset — chỉ tầng giữa trả lời được câu hỏi nghiên cứu

| Tầng | Nguồn | Vai trò hợp lệ | Được dùng làm gold? |
|---|---|---|---|
| **A. Negative control** | Generator (hiện có) | Smoke test, regression, chống crash | ❌ Không |
| **B. Adversarial tổng hợp** | **LLM sinh** | Đo **recall** trên hard negatives | ⚠️ Chỉ dưới tên "adversarial set", không phải gold |
| **C. Natural gold** | Citation **thật** từ 20-theses + PDF thật | Đo **precision** + kết luận Chương 5 | ✅ **Bắt buộc** |

### Tại sao tầng B (LLM) lại đúng chỗ

Thứ hệ thống cần chứng minh không phải "bắt được `MysteryPaper`" — mà là:

> **"Phân biệt được bài báo thật với bài báo AI bịa ra trông y như thật."**

Đây đúng là hallucination trong thực tế hiện nay: trích dẫn do ChatGPT viết, tác giả thật, venue thật, năm hợp lý, DOI đúng định dạng — nhưng **bài không tồn tại**.

Đó là kịch bản generator hiện tại **không thể** tạo ra, nhưng LLM **làm rất giỏi**.

> **Kết luận:** LLM sinh = tấn công hệ thống bằng chính loại đối thủ nguy hiểm nhất.

Đây còn là **đóng góp học thuật thật**, không phải thủ thuật: *"adversarial hallucination benchmark for citation verification"* là phương pháp có tên tuổi, bảo vệ được trước hội đồng.

---

## A.3. Ranh giới tuyệt đối không được vượt

### ❌ Điều KHÔNG được làm

Giao LLM sinh nhãn cho citation **thật**.

Nếu ném 500 reference từ PDF vào GPT-4 bảo "gán nhãn verified/suspected" rồi dùng output đó làm gold — đã tự tạo **circular reasoning**:

> Hệ thống của mình (cũng dùng neural + embedding) được đo bằng một bộ nhãn do một model neural khác tạo.

Kết quả đẹp sẽ bị hỏi ngay: *"Ground truth của em do AI tạo thì làm sao biết AI đó đúng?"* — và **không có câu trả lời**.

### ✅ Ba vai trò hợp lệ của LLM

| Vai trò | Cách làm | Vì sao hợp lệ |
|---|---|---|
| **1. Sinh hard negatives** | Prompt LLM: *"Viết 100 citation giả theo style APA/IEEE, dùng tác giả thật trong NLP, venue thật, năm 2015–2024, title nghe hợp lý"* | **Biết chắc** nhãn = hallucinated vì đã ra lệnh sinh ra nó. Không cần LLM gán nhãn |
| **2. Trợ lý annotation** (không phải annotator) | LLM gợi ý nhãn + lý do → **người đọc guideline và xác nhận/sửa** | Nhãn cuối do người quyết. LLM chỉ tăng tốc |
| **3. Kiểm tra chéo** | Chạy LLM độc lập trên tập natural gold, so với nhãn người → báo cáo agreement | Ăn khớp cao = bằng chứng bổ trợ |

### Verification pass — bước không được bỏ

Với vai trò 1, phải **tự kiểm chứng lại**: 100 citation giả đó có thật sự không tồn tại không?

```
Với mỗi citation do LLM sinh:
    → query Crossref + OpenAlex
    → nếu tìm thấy match  → LOẠI khỏi tập
                          → hoặc chuyển thành METADATA_ERROR (nếu trùng một phần)
    → nếu không tìm thấy   → giữ lại làm hard negative đã kiểm chứng
```

Bước này biến *"LLM bịa"* thành *"negative đã kiểm chứng"*.

---

## A.4. Kế hoạch cụ thể

```
BƯỚC 1 — Natural gold (bắt buộc, ~2 người × 8 giờ)
  Lấy 250–300 reference từ 20-theses, stratified, ưu tiên các bài CIS thấp:
      output_10, output_11, output_20, output_14, output_15
  → 2 SV annotate ĐỘC LẬP theo data/ground_truth/annotation_guideline.md
  → Tính Cohen's κ (đã có metrics/iaa_calculator.py
                    + scripts/collect_dataset/05_compute_iaa.py)
  → Bất đồng → thảo luận → chốt nhãn
  Kết quả: 250–300 nhãn THẬT, có κ để báo cáo

BƯỚC 2 — LLM adversarial set (song song, ~2 giờ)
  150 citation giả sinh bởi LLM, 4 mức độ khó:
    L1: bịa hoàn toàn nhưng tên/venue hợp lý
    L2: tác giả thật + title bịa
    L3: bài thật + năm sai lệch 2–3 năm (khó: hệ thống có thể bỏ qua)
    L4: bài thật + venue bị hoán đổi với bài khác của cùng tác giả
  → Chạy verification pass qua Crossref/OpenAlex
  → 150 nhãn CHẮC CHẮN đúng (vì đã sinh ra chúng)

BƯỚC 3 — Báo cáo tách hai cột, KHÔNG gộp
```

### Bảng báo cáo

```
┌────────────────────────┬───────────┬────────────┐
│ Tập                    │ Precision │ Recall     │
├────────────────────────┼───────────┼────────────┤
│ Natural gold (n≈275)   │ ← số này có ý nghĩa LUẬN VĂN
│ LLM adversarial (n=150)│           │ ← số này chứng minh ĐỘ BỀN
│ Synthetic hiện có      │           │ (regression only)
└────────────────────────┴───────────┴────────────┘
```

**Gộp chung sẽ làm loãng cả hai:** natural gold bị pha loãng bởi mẫu dễ, adversarial bị pha loãng bởi mẫu thật. Báo cáo riêng từng tập là chuẩn mực.

---

## A.5. Rủi ro cần chủ động nêu

| Rủi ro | Cách xử lý |
|---|---|
| Hội đồng hỏi *"LLM sinh thì không khách quan"* | Trả lời: LLM **không gán nhãn** cho dữ liệu thật; nó chỉ **tạo đối thủ** mà nhãn do thiết kế sinh quyết định, đã qua verification pass |
| LLM sinh citation **vô tình có thật** | Bắt buộc verification pass — bước không được bỏ |
| LLM sinh citation **quá dễ** (giống `FAKE_TITLES` hiện tại) | Prompt phải ràng buộc: tác giả thật, venue thật, năm hợp lý. Và **đo** bằng cách cho baseline B1 (Crossref top-1) chạy — nếu B1 bắt được 100% thì tập quá dễ, phải làm khó hơn |
| Chỉ có 1 người annotate | Bắt buộc **2 người annotate độc lập** — yêu cầu của `annotation_guideline.md`, và là bằng chứng chất lượng dữ liệu |

> **Điểm quan trọng:** nếu chỉ có 1 annotator và không có κ, Chương 5 sẽ bị hỏi *"làm sao biết nhãn của em đúng?"* — mà nhóm có **2 SV**, nên hoàn toàn làm được IAA.

---

## A.6. Kết luận Phần A

| Câu hỏi | Trả lời |
|---|---|
| Có nên sinh dataset bằng AI? | **Có**, nhưng đặt ở đúng tầng |
| Vai trò của nó | **Adversarial test set**, KHÔNG phải gold set |
| Gold set bắt buộc là gì? | Citation thật + 2 người gán nhãn độc lập + có κ |
| Chiến lược | Làm cả hai, báo cáo tách cột |

---

# Phần B — Baselines B0–B5

## B.1. Ý tưởng cốt lõi: một con số không chứng minh được gì

Báo cáo: **"hệ thống đạt F1 = 0.857"**.

Hội đồng sẽ hỏi ngay: *"0.857 là cao hay thấp?"* — và **không có câu trả lời**, vì không có mốc so sánh.

| Nếu baseline đơn giản đạt | Thì kết luận về hệ thống |
|---|---|
| F1 = 0.30 | ✅ Hệ thống có giá trị thật, phức tạp là đáng |
| F1 = 0.80 | ⚠️ Chỉ hơn baseline 0.06 — phần "neuro-symbolic" đóng góp rất ít, cần biện luận |
| F1 = 0.90 | ❌ **Toàn bộ luận văn sụp đổ** — baseline đơn giản đã tốt hơn, không cần kiến trúc phức tạp |

> **Baseline chính là thứ biến "con số" thành "bằng chứng khoa học".**
> Không có nó, Chương 5 chỉ là báo cáo kỹ thuật, không phải kết quả nghiên cứu.
>
> *Nguyên tắc: Không bao giờ trình bày kết quả của một phương pháp mà không có phương pháp đối chứng.*

---

## B.2. B0–B5 cụ thể là gì

Đọc trực tiếp từ `src/integrity_checker/evaluation/baselines.py`:

```
B0: Link/DOI only       — chỉ check DOI có resolve được không
B1: Crossref top-1      — lấy kết quả đầu tiên từ Crossref, tin luôn
B2: Fuzzy matching      — so title+author bằng string similarity (Levenshtein)
B3: Embedding only      — cosine similarity giữa title (BERT/SBERT)
B4: ML classifier       — Logistic Regression / XGBoost trên features
B5: BERT/DistilBERT NER — trên reference entries (theo SESSION_SUMMARY_WEEK6_7.md)
Proposed                — multi-source + neural + symbolic + abstention
```

Đây là thang **tăng dần độ phức tạp**. Mỗi bậc thêm một kỹ thuật.

### Câu chuyện nghiên cứu (dùng khi viết Chương 5)

> *"B0 và B1 quá ngây thơ → B2 cải thiện nhưng vẫn thất bại với typo/paraphrase → B3 (embedding) xử lý được paraphrase nhưng hallucinate khi title chung chung → B4 (ML) học được pattern nhưng không giải thích được và không có abstention → B5 (BERT) mạnh nhất nhưng vẫn luôn phải chọn một nhãn → **Phương pháp đề xuất kết hợp đa nguồn + neural + symbolic + abstention, đạt F1 cao nhất VÀ có khả năng nói 'tôi không chắc' (unresolved)**".*

---

## B.3. Vì sao B5 quan trọng hơn tưởng tượng

Nếu hội đồng nói: *"Sao không dùng BERT fine-tune cho xong?"* — **phải có B5 để trả lời**.

Nếu B5 thắng → đó vẫn là kết quả khoa học hợp lệ (và phải trung thực báo cáo), nhưng ít nhất **biết trước**.

### Ba điểm mạnh hệ thống có mà B3/B4/B5 KHÔNG có

| Điểm mạnh | Ý nghĩa |
|---|---|
| **Abstention** | Nhãn `UNRESOLVED` khi không đủ bằng chứng. ML thuần **luôn phải chọn một nhãn** → luôn tự tin sai |
| **Giải thích được** | `triggered_rules` cho biết *vì sao* kết luận. Yêu cầu bắt buộc của decision-support tool |
| **Đa nguồn + consensus** | Không phụ thuộc một API, có cơ chế đồng thuận giữa các nguồn |

> **Chỉ số để thắng không phải F1 thuần, mà là F1 + coverage + calibration (ECE/Brier).**

Module `logic/calibration.py` đã có sẵn (`compute_brier`, `compute_ece`, `compute_coverage_accuracy`) và comment của nó ghi rõ: *"So sánh với baselines B0-B5"*. Nghĩa là **hạ tầng đã sẵn, chỉ thiếu người implement baseline**.

---

## B.4. Điều kiện tiên quyết

**Baselines không tự có ý nghĩa — chúng cần cùng một tập test có nhãn vàng.**

```
gold dataset (có nhãn người)
        │
    ┌───┴───┬───────┬───────┬───────┬───────┬──────────┐
    B0      B1      B2      B3      B4      B5      Proposed
    │       │       │       │       │       │          │
    └───┬───┴───────┴───────┴───────┴───────┴──────────┘
        ↓
  MetricsCalculator (P/R/F1)
+ CalibrationMetrics (ECE/Brier/coverage)
        ↓
  Bảng so sánh → Bảng 5.x trong luận văn
```

> **Nghĩa là:** câu hỏi baselines phụ thuộc trực tiếp vào câu hỏi gold dataset.
> **Không thể** chạy baseline trước khi có nhãn vàng — nếu chạy trên
> `gold_dataset_full_annotation.csv` hiện tại (2.900 dòng, cột nhãn **trống hoàn toàn**),
> mọi con số đều vô nghĩa.
>
> **Thứ tự bắt buộc: Phần A (gold dataset) trước, Phần B (baselines) sau.**

---

## B.5. Bảng kết quả cuối cùng (Bảng 5.x trong luận văn)

| Phương pháp | Precision | Recall | F1 | Coverage | ECE ↓ | Giải thích được? | Abstention? |
|---|---|---|---|---|---|---|---|
| B0 — DOI only | | | | | | ❌ | ❌ |
| B1 — Crossref top-1 | | | | | | ❌ | ❌ |
| B2 — Fuzzy | | | | | | ❌ | ❌ |
| B3 — Embedding | | | | | | ❌ | ❌ |
| B4 — ML classifier | | | | | | ❌ | ❌ |
| B5 — BERT NER | | | | | | ❌ | ❌ |
| **Proposed** | | | | | | ✅ | ✅ |

### Cách đọc bảng này khi bảo vệ

Không cần thắng mọi cột. Cần chỉ ra **đánh đổi có chủ đích**:

> Proposed có thể thua B5 vài điểm F1 nhưng **thắng ở coverage + ECE + khả năng giải thích**
> — và đó chính là điều đề cương yêu cầu ("decision-support, không tự kết luận gian lận").

---

## B.6. Ước lượng thời gian

| Baseline | Nguồn nguyên liệu | Thời gian |
|---|---|---|
| B0 | `retrieval/crossref_client.py` (đã có) | ~2 giờ |
| B1 | `retrieval/crossref_client.py` (đã có) | ~2 giờ |
| B2 | `matching/fuzzy.py` (đã có) | ~3 giờ |
| B3 | `matching/semantic.py` (đã có) | ~3 giờ |
| B4 | Cần làm mới (sklearn) | ~1–2 ngày |
| B5 | Cần làm mới (transformers) | ~2–3 ngày |
| **Tổng** | | **~1 tuần** (sau khi có nhãn) |

---

## B.7. Kết luận Phần B

| Câu hỏi | Trả lời |
|---|---|
| Baselines là gì? | Các phương pháp đơn giản hơn dùng làm mốc so sánh (B0 đơn giản nhất → B5 phức tạp nhất) |
| Tại sao bắt buộc? | Không có mốc so sánh thì F1 = 0.857 vô nghĩa về mặt khoa học |
| Có phải viết từ đầu? | **Không** — B0–B3 ghép từ module đã có; chỉ B4/B5 mới cần làm mới |
| Làm ngay được chưa? | **Chưa** — phải có gold dataset trước |

---

# Phần C — Phụ thuộc và thứ tự thực hiện

```
                    ┌─────────────────────────────┐
                    │  C.0  Xử lý API key public  │  ← LÀM TRƯỚC TIÊN
                    │  (GitHub + GitLab)          │
                    └──────────────┬──────────────┘
                                   ↓
                    ┌─────────────────────────────┐
                    │  A.1  Natural gold          │
                    │  250–300 citation thật      │  ← NÚT THẮT
                    │  + 2 annotator + κ          │
                    └──────────────┬──────────────┘
                                   ↓
                    ┌─────────────────────────────┐
                    │  B.1  Baselines B0–B3       │
                    │  (ghép module có sẵn)       │
                    └──────────────┬──────────────┘
                                   ↓
                    ┌─────────────────────────────┐
                    │  B.2  Baselines B4–B5       │
                    └──────────────┬──────────────┘
                                   ↓
                    ┌─────────────────────────────┐
                    │  A.2  LLM adversarial set   │  ← SONG SONG với B
                    │  + verification pass        │
                    └──────────────┬──────────────┘
                                   ↓
                    ┌─────────────────────────────┐
                    │  C.1  Bảng so sánh cuối     │
                    │  → Chương 5 luận văn        │
                    └─────────────────────────────┘
```

## C.1. Bảng phụ thuộc

| Việc | Phụ thuộc vào | Có thể làm ngay? |
|---|---|---|
| Xử lý API key public | — | ✅ **Ngay** |
| Sinh LLM adversarial set | — | ✅ Ngay (độc lập) |
| Viết code B0–B3 | — | ✅ Ngay (code xong, chờ dữ liệu để chạy) |
| **Chạy** baselines | Gold dataset có nhãn | ❌ Chờ A.1 |
| Viết Chương 5 | Tất cả ở trên | ❌ |

> **Điểm quan trọng:** code baseline B0–B3 và sinh adversarial set **có thể làm song song ngay bây giờ**.
> Nhưng **chạy** baseline thì bắt buộc phải chờ gold dataset.

---

# Phần D — Trạng thái hạ tầng hiện có trong repo

> Đo tại chỗ ngày 2026-10-01, không đọc từ tài liệu.

## D.1. Thành phần phục vụ đánh giá

| Thành phần | Đường dẫn | Trạng thái |
|---|---|---|
| `baselines.py` | `src/integrity_checker/evaluation/baselines.py` | ❌ **Stub** — `raise NotImplementedError("TODO tuần 16")` |
| `MetricsCalculator` | `src/integrity_checker/evaluation/metrics.py` | ✅ Có — P/R/F1/macro-F1/confusion matrix |
| `EvaluationReport` | `src/integrity_checker/evaluation/report.py` | ⚠️ Dataclass + `to_markdown` có, chưa test với dữ liệu thật |
| Calibration (Brier/ECE/coverage) | `src/integrity_checker/logic/calibration.py` | ✅ Có — comment ghi rõ *"So sánh với baselines B0-B5"* |
| `FuzzyMatcher` | `src/integrity_checker/matching/fuzzy.py` | ✅ Có → **nguyên liệu cho B2** |
| `SemanticMatcher` | `src/integrity_checker/matching/semantic.py` | ✅ Có → **nguyên liệu cho B3** |
| `crossref_client` | `src/integrity_checker/retrieval/crossref_client.py` | ✅ Có → **nguyên liệu cho B0, B1** |
| IAA calculator | `src/integrity_checker/metrics/iaa_calculator.py` | ✅ Có |
| Compute IAA script | `scripts/collect_dataset/05_compute_iaa.py` | ✅ Có |
| Annotation guideline | `data/ground_truth/annotation_guideline.md` | ✅ Có — định nghĩa 4 nhãn rõ ràng |
| Annotation tool | `data/annotation/annotate_full.html` | ✅ Có — tái dùng được |
| IAA template | `data/ground_truth/iaa_template.csv` | ✅ Có |

## D.2. Phát hiện then chốt

> **Không phải viết từ đầu.**
> B0, B1, B2, B3 chỉ là **lớp mỏng ghép các module đã có sẵn** — mỗi cái khoảng 30–60 dòng.
> Chỉ **B4 (ML classifier)** và **B5 (BERT NER)** mới thật sự cần làm mới.

## D.3. Tình trạng dữ liệu (đo tại chỗ)

| File | Nội dung | Vấn đề |
|---|---|---|
| `evaluation/real_evaluation_metrics.json` | n=20 samples | ⚠️ Sinh từ `SyntheticDatasetGenerator`, không phải citation từ PDF thật |
| `data/gold_dataset_full_annotation.csv` | 2.900 dòng | 🔴 Cột `ground_truth_label` **TRỐNG HOÀN TOÀN** |
| `data/data_split_manifest.json` | 174 citations | 🔴 `label_distribution: {"unknown": 174}` |
| `evaluation/pipeline_evaluation_results.json` | n=20 | ⚠️ `ci_recall [0.409, 0.928]` — quá rộng để kết luận |
| `data/app.db` | 67 essays, 3.371 citations | ✅ Dùng được |
| `data/local_papers.db` | 128.609 papers | ✅ Dùng được |
| `20-theses/` | 20 PDF + 54 file output JSON | ✅ **Mỏ vàng chưa khai thác** |

## D.4. Vấn đề chất lượng phát hiện trên 20-theses

Các bản `output_N_v2.json` cho thấy phân bố rất không đồng đều:

```
output_10_v2   180 cites   CIS 61.8   verified 32   ⚠ unresolved 118   resource 27
output_11_v2   203 cites   CIS 68.5   verified 49   ⚠ unresolved 149
output_20_v2    78 cites   CIS 60.5   verified  2   ⚠ unresolved 75
output_16_v2   263 cites   CIS 88.1   verified 195
output_19_v2   254 cites   CIS 89.6   verified 197
```

→ 3/11 bài có CIS ~60 và **unresolved chiếm 70–96%**.
Con số "CIS 97–100" trong tài liệu cũ là **cherry-picked** trên BERT/Attention/VietDepression.

→ **Đề xuất:** ưu tiên lấy mẫu annotation từ `output_10, 11, 14, 15, 20` — đây là nơi hệ thống yếu nhất, và cũng là nơi việc đánh giá có giá trị nhất.

---

# Phần E — Việc cần làm ngay (checklist)

- [ ] **C.0** Revoke/rotate OpenAlex API key + GitLab PAT (đang public trên cả 2 remote)
- [ ] **C.0** Purge secret khỏi git history (`git filter-repo`)
- [ ] **A.1** Viết script trích 250–300 reference stratified từ `20-theses/` → CSV
- [ ] **A.1** 2 SV annotate độc lập → tính Cohen's κ
- [ ] **A.2** Viết prompt sinh LLM adversarial 4 mức độ (L1–L4)
- [ ] **A.2** Viết verification pass qua Crossref/OpenAlex
- [ ] **B** Implement `BaselineRunner` cho B0–B3 (ghép module có sẵn)
- [ ] **B** Implement B4 (sklearn) + B5 (transformers)
- [ ] **C.1** Chạy toàn bộ baseline + proposed → xuất bảng so sánh
- [ ] **C.1** Viết Chương 5 từ bảng kết quả

---

**Ghi chú cuối:** File này là ghi chú thiết kế, không phải báo cáo kết quả.
Mọi số liệu ở Phần D là **đo tại chỗ ngày 2026-10-01** và sẽ thay đổi khi code được triển khai.
