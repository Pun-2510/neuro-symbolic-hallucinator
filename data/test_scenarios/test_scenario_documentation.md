# Tài Liệu Kịch Bản Kiểm Tra
# Bộ Kiểm Tra Kịch Bản - Citation Integrity Checker v2

## Tổng Quan

Tài liệu này mô tả các kịch bản kiểm tra được sử dụng để xác thực Citation Integrity Checker.
Mỗi kịch bản bao gồm:
- **Trích dẫn trong văn bản (in-text citation)** trong phần nội dung tài liệu
- **Mục từ tài liệu tham khảo (reference entry)** trong danh mục tài liệu tham khảo
- **Trạng thái mapping kỳ vọng** (MATCHED, MISSING_REFERENCE, v.v.)
- **Nhãn xác thực kỳ vọng** (verified, suspected_hallucination, v.v.)

---

## PDF 1: Kịch Bản Phong Cách APA (`test_cite_scenario_a.pdf`)

### Kịch Bản APA-01: MATCHED (Khớp)
**Danh mục:** MATCHED  
**Mô tả:** Bài báo kinh điển - trích dẫn trong văn bản (Vaswani et al., 2017) khớp với tài liệu tham khảo [1]

| Phần tử | Giá trị |
|---------|---------|
| In-text | Deep learning has achieved remarkable success (Vaswani et al., 2017). |
| Reference | [1] A. Vaswani, N. Shazeer, N. Parmar, et al. "Attention Is All You Need." Advances in Neural Information Processing Systems, 2017. |
| Mapping kỳ vọng | `MATCHED` |
| Nhãn kỳ vọng | `verified` |
| Logic khớp | Author-year (Vaswani, 2017) khớp với mục từ tham khảo |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(Vaswani et al., 2017)" được trích xuất đúng
- [ ] Mục từ tham khảo [1] được phân tích đúng với author="Vaswani", year="2017"
- [ ] Trạng thái mapping = MATCHED
- [ ] Nhãn xác thực = verified

---

### Kịch Bản APA-02: MATCHED (Khớp)
**Danh mục:** MATCHED  
**Mô tả:** Bài báo BERT - định dạng author-year khớp với tài liệu tham khảo [2]

| Phần tử | Giá trị |
|---------|---------|
| In-text | BERT revolutionized NLP tasks (Devlin et al., 2019). |
| Reference | [2] J. Devlin, M.-W. Chang, K. Lee, and K. Toutanova. "BERT: Pre-training of Deep Bidirectional Transformers." Association for Computational Linguistics, 2019. |
| Mapping kỳ vọng | `MATCHED` |
| Nhãn kỳ vọng | `verified` |
| Logic khớp | Author-year (Devlin, 2019) khớp với mục từ tham khảo |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(Devlin et al., 2019)" được trích xuất đúng
- [ ] Mục từ tham khảo [2] được phân tích đúng
- [ ] Trạng thái mapping = MATCHED
- [ ] Nhãn xác thực = verified

---

### Kịch Bản APA-03: MATCHED (Khớp)
**Danh mục:** MATCHED  
**Mô tả:** Bài báo Subword NMT - MATCHED qua author-year

| Phần tử | Giá trị |
|---------|---------|
| In-text | Neural machine translation improved significantly (Sennrich et al., 2016). |
| Reference | [3] R. Sennrich, B. Haddow, and A. Birch. "Neural Machine Translation of Rare Words with Subword Units." Association for Computational Linguistics, 2016. |
| Mapping kỳ vọng | `MATCHED` |
| Nhãn kỳ vọng | `verified` |
| Logic khớp | Author-year (Sennrich, 2016) khớp với mục từ tham khảo |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(Sennrich et al., 2016)" được trích xuất đúng
- [ ] Mục từ tham khảo [3] được phân tích đúng
- [ ] Trạng thái mapping = MATCHED
- [ ] Nhãn xác thực = verified

---

### Kịch Bản APA-04: MISSING_REFERENCE (Thiếu Tài Liệu Tham Khảo)
**Danh mục:** MISSING_REFERENCE  
**Mô tả:** MISSING_REFERENCE: Có trích dẫn trong văn bản nhưng không có mục từ tham khảo tương ứng

| Phần tử | Giá trị |
|---------|---------|
| In-text | This breakthrough changed the field (MysteryPaper, 2020). |
| Reference | **<<KHÔNG CÓ MỤC TỪ THAM KHẢO>>** |
| Mapping kỳ vọng | `MISSING_REFERENCE` |
| Nhãn kỳ vọng | `suspected_hallucination` |
| Logic khớp | Trích dẫn trong văn bản không có tài liệu tham khảo tương ứng trong danh mục |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(MysteryPaper, 2020)" được trích xuất đúng
- [ ] Không tìm thấy mục từ tham khảo cho trích dẫn này
- [ ] Trạng thái mapping = MISSING_REFERENCE
- [ ] Nhãn xác thực = suspected_hallucination

**Tại sao điều này quan trọng:** Điều này có thể cho thấy trích dẫn bị bịa đặt hoặc tài liệu tham khảo bị quên.

---

### Kịch Bản APA-05: UNCITED_REFERENCE (Tài Liệu Tham Khảo Không Được Trích Dẫn)
**Danh mục:** UNCITED_REFERENCE  
**Mô tả:** UNCITED_REFERENCE: Có mục từ tham khảo nhưng không có trích dẫn trong văn bản nào tham chiếu đến nó

| Phần tử | Giá trị |
|---------|---------|
| In-text | Traditional methods remain useful in some contexts (Smith, 2015). |
| Reference | [4] J. Smith. "Introduction to Classical Methods." Journal of Classical Studies, 2015. |
| Mapping kỳ vọng | `UNCITED_REFERENCE` (cho reference [4]) |
| Nhãn kỳ vọng | `unresolved` |
| Logic khớp | Mục từ tham khảo [4] tồn tại nhưng không có trích dẫn trong văn bản nào tham chiếu đến nó |

**Xác minh:**
- [ ] Mục từ tham khảo [4] được phân tích đúng
- [ ] Mục từ tham khảo [4] không được tham chiếu bởi bất kỳ trích dẫn trong văn bản nào
- [ ] Trạng thái mapping = UNCITED_REFERENCE
- [ ] Nhãn xác thực = unresolved

**Lưu ý:** Trích dẫn trong văn bản "(Smith, 2015)" là riêng biệt - nó nên là UNCITED nếu không có mục từ tham khảo tương ứng.

**Tại sao điều này quan trọng:** Tài liệu tham khảo không được trích dẫn gợi ý rằng đây có thể là bản nháp sót lại hoặc trích dẫn không đúng.

---

### Kịch Bản APA-06: IN_TEXT_MISMATCH (Trích Dẫn Trong Văn Bản Không Khớp)
**Danh mục:** IN_TEXT_MISMATCH  
**Mô tả:** IN_TEXT_MISMATCH: Author/year khớp nhưng title khác nhau

| Phần tử | Giá trị |
|---------|---------|
| In-text | Transformers use self-attention (Vaswani et al., 2017). |
| Reference | [5] A. Vaswani, N. Shazeer, N. Parmar, et al. "Graph Neural Networks: A Survey." Different venue, 2017. |
| Mapping kỳ vọng | `IN_TEXT_MISMATCH` |
| Nhãn kỳ vọng | `metadata_error` |
| Logic khớp | Author (Vaswani) và year (2017) khớp với reference [5], nhưng title khác nhau |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(Vaswani et al., 2017)" trích xuất author="Vaswani", year="2017"
- [ ] Mục từ tham khảo [5] có author="Vaswani", year="2017" nhưng title="Graph Neural Networks..."
- [ ] Trạng thái mapping = IN_TEXT_MISMATCH (hoặc AMBIGUOUS)
- [ ] Nhãn xác thực = metadata_error hoặc unresolved

**Tại sao điều này quan trọng:** Điều này cho thấy lỗi trích dẫn tiềm ẩn - tác giả có thể đã trích dẫn sai bài báo.

---

### Kịch Bản APA-07: DUPLICATE_REFERENCE (Tài Liệu Tham Khảo Trùng Lặp)
**Danh mục:** DUPLICATE_REFERENCE  
**Mô tả:** DUPLICATE_REFERENCE: Cùng một bài báo xuất hiện hai lần trong tài liệu tham khảo

| Phần tử | Giá trị |
|---------|---------|
| In-text | Attention mechanisms are powerful (Vaswani et al., 2017). See also (Vaswani et al., 2017b). |
| Reference | [6-7] A. Vaswani, et al. "Attention Is All You Need." NeurIPS, 2017. (TRÙNG LẶP) |
| Mapping kỳ vọng | `DUPLICATE_REFERENCE` |
| Nhãn kỳ vọng | `metadata_error` |
| Logic khớp | Các mục từ tham khảo [6] và [7] giống nhau hoặc rất tương tự |

**Xác minh:**
- [ ] Cả mục từ tham khảo [6] và [7] được phân tích
- [ ] Cùng author, title, year, venue
- [ ] Trạng thái mapping = DUPLICATE_REFERENCE
- [ ] Nhãn xác thực = metadata_error

**Tại sao điều này quan trọng:** Tài liệu tham khảo trùng lặp lãng phí không gian và có thể gây nhầm lẫn cho người đọc.

---

### Kịch Bản APA-08: MATCHED (Khớp)
**Danh mục:** MATCHED  
**Mô tả:** Bài báo Word2Vec - MATCHED qua DOI/author-year

| Phần tử | Giá trị |
|---------|---------|
| In-text | Word embeddings capture semantic relationships (Mikolov et al., 2013). |
| Reference | [8] T. Mikolov, K. Chen, G. Corrado, and J. Dean. "Efficient Estimation of Word Representations." arXiv, 2013. |
| Mapping kỳ vọng | `MATCHED` |
| Nhãn kỳ vọng | `verified` |
| Logic khớp | Author-year (Mikolov, 2013) khớp với mục từ tham khảo |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(Mikolov et al., 2013)" được trích xuất đúng
- [ ] Mục từ tham khảo [8] được phân tích đúng
- [ ] Trạng thái mapping = MATCHED
- [ ] Nhãn xác thực = verified

---

### Kịch Bản APA-09: AMBIGUOUS_MAPPING (Mapping Mơ Hồ)
**Danh mục:** AMBIGUOUS_MAPPING  
**Mô tả:** AMBIGUOUS_MAPPING: Nhiều ứng viên khớp với author+year

| Phần tử | Giá trị |
|---------|---------|
| In-text | Transfer learning proved effective (Pan et al., 2020). |
| Reference | [9] S. J. Pan and Q. Yang. "A Survey on Transfer Learning." IEEE Transactions, 2010.\n[10] F. Pan et al. "Transfer Learning in 2020." New Journal, 2020. |
| Mapping kỳ vọng | `AMBIGUOUS_MAPPING` |
| Nhãn kỳ vọng | `unresolved` |
| Logic khớp | (Pan et al., 2020) có thể khớp với reference [9] hoặc [10] - mơ hồ |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(Pan et al., 2020)" khớp với nhiều tài liệu tham khảo
- [ ] Cả [9] và [10] đều là ứng viên hợp lệ
- [ ] Trạng thái mapping = AMBIGUOUS_MAPPING
- [ ] Nhãn xác thực = unresolved

**Tại sao điều này quan trọng:** Các mapping mơ hồ cần được người đọc xem xét để xác định khớp đúng.

---

### Kịch Bản APA-10: MATCHED (Khớp)
**Danh mục:** MATCHED  
**Mô tả:** Bài báo GPT-3 - MATCHED qua DOI/author-year

| Phần tử | Giá trị |
|---------|---------|
| In-text | Large language models show emergent abilities (Brown et al., 2020). |
| Reference | [11] T. B. Brown et al. "Language Models are Few-Shot Learners." NeurIPS, 2020. |
| Mapping kỳ vọng | `MATCHED` |
| Nhãn kỳ vọng | `verified` |
| Logic khớp | Author-year (Brown, 2020) khớp với mục từ tham khảo |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(Brown et al., 2020)" được trích xuất đúng
- [ ] Mục từ tham khảo [11] được phân tích đúng
- [ ] Trạng thái mapping = MATCHED
- [ ] Nhãn xác thực = verified

---

## PDF 2: Kịch Bản Phong Cách IEEE (`test_cite_scenario_b.pdf`)

### Kịch Bản IEEE-01: MATCHED (Khớp)
**Danh mục:** MATCHED  
**Mô tả:** Trích dẫn số IEEE khớp với mục từ tham khảo [1]

| Phần tử | Giá trị |
|---------|---------|
| In-text | Self-attention mechanisms have transformed deep learning (Vaswani et al., 2017). |
| Reference | [1] A. Vaswani et al., "Attention Is All You Need," NeurIPS, 2017. |
| Mapping kỳ vọng | `MATCHED` |
| Nhãn kỳ vọng | `verified` |
| Logic khớp | Author-year (Vaswani, 2017) khớp với mục từ tham khảo [1] |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(Vaswani et al., 2017)" được trích xuất đúng
- [ ] Mục từ tham khảo [1] được phân tích đúng
- [ ] Trạng thái mapping = MATCHED
- [ ] Nhãn xác thực = verified

---

### Kịch Bản IEEE-02: MATCHED (Khớp)
**Danh mục:** MATCHED  
**Mô tả:** BERT - khớp với reference [2]

| Phần tử | Giá trị |
|---------|---------|
| In-text | BERT introduced bidirectional pre-training (Devlin et al., 2019). |
| Reference | [2] J. Devlin et al., "BERT: Pre-training," ACL, 2019. |
| Mapping kỳ vọng | `MATCHED` |
| Nhãn kỳ vọng | `verified` |
| Logic khớp | Author-year (Devlin, 2019) khớp với mục từ tham khảo [2] |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(Devlin et al., 2019)" được trích xuất đúng
- [ ] Mục từ tham khảo [2] được phân tích đúng
- [ ] Trạng thái mapping = MATCHED
- [ ] Nhãn xác thực = verified

---

### Kịch Bản IEEE-03: MATCHED (Khớp)
**Danh mục:** MATCHED  
**Mô tả:** GPT-3 - khớp với reference [3]

| Phần tử | Giá trị |
|---------|---------|
| In-text | Recent advances demonstrate the power of scale (Brown et al., 2020). |
| Reference | [3] T. B. Brown et al., "GPT-3," NeurIPS, 2020. |
| Mapping kỳ vọng | `MATCHED` |
| Nhãn kỳ vọng | `verified` |
| Logic khớp | Author-year (Brown, 2020) khớp với mục từ tham khảo [3] |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(Brown et al., 2020)" được trích xuất đúng
- [ ] Mục từ tham khảo [3] được phân tích đúng
- [ ] Trạng thái mapping = MATCHED
- [ ] Nhãn xác thực = verified

---

### Kịch Bản IEEE-04: MISSING_REFERENCE (Thiếu Tài Liệu Tham Khảo)
**Danh mục:** MISSING_REFERENCE  
**Mô tả:** MISSING_REFERENCE: Được trích dẫn nhưng không có mục từ tham khảo

| Phần tử | Giá trị |
|---------|---------|
| In-text | This novel approach shows promise (NovelPaper, 2021). |
| Reference | **<<KHÔNG CÓ MỤC TỪ THAM KHẢO>>** |
| Mapping kỳ vọng | `MISSING_REFERENCE` |
| Nhãn kỳ vọng | `suspected_hallucination` |
| Logic khớp | Trích dẫn (NovelPaper, 2021) không có tài liệu tham khảo tương ứng |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(NovelPaper, 2021)" được trích xuất đúng
- [ ] Không tìm thấy mục từ tham khảo
- [ ] Trạng thái mapping = MISSING_REFERENCE
- [ ] Nhãn xác thực = suspected_hallucination

---

### Kịch Bản IEEE-05: UNCITED_REFERENCE (Tài Liệu Tham Khảo Không Được Trích Dẫn)
**Danh mục:** UNCITED_REFERENCE  
**Mô tả:** UNCITED_REFERENCE: Tài liệu tham khảo tồn tại nhưng không được trích dẫn

| Phần tử | Giá trị |
|---------|---------|
| In-text | Baseline methods remain relevant (TraditionalMethod, 2018). |
| Reference | [4] J. Smith, "Classical Methods," 2018. (Không được trích dẫn trong phần nội dung) |
| Mapping kỳ vọng | `UNCITED_REFERENCE` (cho reference [4]) |
| Nhãn kỳ vọng | `unresolved` |
| Logic khớp | Mục từ tham khảo [4] không được tham chiếu bởi bất kỳ trích dẫn trong văn bản nào |

**Xác minh:**
- [ ] Mục từ tham khảo [4] được phân tích đúng
- [ ] Mục từ tham khảo [4] không được tham chiếu bởi bất kỳ trích dẫn trong văn bản nào
- [ ] Trạng thái mapping = UNCITED_REFERENCE
- [ ] Nhãn xác thực = unresolved

---

### Kịch Bản IEEE-06: MATCHED (Khớp)
**Danh mục:** MATCHED  
**Mô tả:** Nhiều trích dẫn APA-style khớp với references [5] và [6]

| Phần tử | Giá trị |
|---------|---------|
| In-text | Multiple papers demonstrate versatility (AuthorA, 2018) and (AuthorB, 2019). |
| Reference | [5] A. Author, "Paper A," 2018.\n[6] B. Author, "Paper B," 2019. |
| Mapping kỳ vọng | `MATCHED` (cho cả [5] và [6]) |
| Nhãn kỳ vọng | `verified` |
| Logic khớp | Mỗi author-year khớp với mục từ tham khảo tương ứng |

**Xác minh:**
- [ ] Trích dẫn "(AuthorA, 2018)" → Reference [5]: MATCHED
- [ ] Trích dẫn "(AuthorB, 2019)" → Reference [6]: MATCHED
- [ ] Cả hai nhãn xác thực = verified

---

### Kịch Bản IEEE-07: STYLE_INCONSISTENT (Phong Cách Không Nhất Quán)
**Danh mục:** STYLE_INCONSISTENT  
**Mô tả:** STYLE_INCONSISTENT: Trộn lẫn các phong cách trong cùng tài liệu

| Phần tử | Giá trị |
|---------|---------|
| In-text | Traditional (Johnson, 2018) and modern (ModernPaper, 2019) approaches coexist. |
| Reference | [7] R. Johnson, "Modern Methods," IEEE, 2018. |
| Mapping kỳ vọng | `STYLE_INCONSISTENT` |
| Nhãn kỳ vọng | `unresolved` |
| Logic khớp | Tài liệu sử dụng các phong cách trích dẫn hỗn hợp |

**Xác minh:**
- [ ] Phát hiện trích dẫn phong cách APA hỗn hợp
- [ ] Mục từ tham khảo [7] được phân tích với phong cách IEEE
- [ ] Trạng thái mapping = STYLE_INCONSISTENT
- [ ] Nhãn xác thực = unresolved

---

### Kịch Bản IEEE-08: MATCHED (Khớp)
**Danh mục:** MATCHED  
**Mô tả:** Bài báo GAN - MATCHED

| Phần tử | Giá trị |
|---------|---------|
| In-text | GANs revolutionized generative modeling (Goodfellow et al., 2014). |
| Reference | [8] I. Goodfellow et al., "Generative Adversarial Networks," NeurIPS, 2014. |
| Mapping kỳ vọng | `MATCHED` |
| Nhãn kỳ vọng | `verified` |
| Logic khớp | Author-year (Goodfellow, 2014) khớp với mục từ tham khảo [8] |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(Goodfellow et al., 2014)" được trích xuất đúng
- [ ] Mục từ tham khảo [8] được phân tích đúng
- [ ] Trạng thái mapping = MATCHED
- [ ] Nhãn xác thực = verified

---

### Kịch Bản IEEE-09: MATCHED (Khớp)
**Danh mục:** MATCHED  
**Mô tả:** Bài báo ResNet - MATCHED

| Phần tử | Giá trị |
|---------|---------|
| In-text | ResNet enabled deeper networks (He et al., 2016). |
| Reference | [9] K. He et al., "Deep Residual Learning," CVPR, 2016. |
| Mapping kỳ vọng | `MATCHED` |
| Nhãn kỳ vọng | `verified` |
| Logic khớp | Author-year (He, 2016) khớp với mục từ tham khảo [9] |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(He et al., 2016)" được trích xuất đúng
- [ ] Mục từ tham khảo [9] được phân tích đúng
- [ ] Trạng thái mapping = MATCHED
- [ ] Nhãn xác thực = verified

---

### Kịch Bản IEEE-10: MATCHED (Khớp)
**Danh mục:** MATCHED  
**Mô tả:** Bài báo Survey - MATCHED

| Phần tử | Giá trị |
|---------|---------|
| In-text | Transformer variants continue to evolve (SurveyAuthors, 2023). |
| Reference | [10] Various Authors, "Survey of Transformers," ACM Computing Surveys, 2023. |
| Mapping kỳ vọng | `MATCHED` |
| Nhãn kỳ vọng | `verified` |
| Logic khớp | Author-year (SurveyAuthors, 2023) khớp với mục từ tham khảo [10] |

**Xác minh:**
- [ ] Trích dẫn trong văn bản "(SurveyAuthors, 2023)" được trích xuất đúng
- [ ] Mục từ tham khảo [10] được phân tích đúng
- [ ] Trạng thái mapping = MATCHED
- [ ] Nhãn xác thực = verified

---

## Bảng Tổng Kết

### PDF 1 (Phong Cách APA) - 10 Kịch Bản
| ID | Danh mục | Mapping kỳ vọng | Nhãn kỳ vọng | Chi tiết chính |
|----|----------|-----------------|---------------|----------------|
| APA-01 | MATCHED | MATCHED | verified | Vaswani 2017 → [1] |
| APA-02 | MATCHED | MATCHED | verified | Devlin 2019 → [2] |
| APA-03 | MATCHED | MATCHED | verified | Sennrich 2016 → [3] |
| APA-04 | MISSING_REFERENCE | MISSING_REFERENCE | suspected_hallucination | MysteryPaper 2020 - KHÔNG CÓ REF |
| APA-05 | UNCITED_REFERENCE | UNCITED_REFERENCE | unresolved | Smith 2015 - [4] tồn tại nhưng không được trích dẫn |
| APA-06 | IN_TEXT_MISMATCH | IN_TEXT_MISMATCH | metadata_error | Vaswani 2017 → [5] nhưng title khác |
| APA-07 | DUPLICATE_REFERENCE | DUPLICATE_REFERENCE | metadata_error | [6-7] trùng lặp |
| APA-08 | MATCHED | MATCHED | verified | Mikolov 2013 → [8] |
| APA-09 | AMBIGUOUS_MAPPING | AMBIGUOUS_MAPPING | unresolved | Pan 2020 → [9] hoặc [10] |
| APA-10 | MATCHED | MATCHED | verified | Brown 2020 → [11] |

### PDF 2 (Phong Cách IEEE) - 10 Kịch Bản
| ID | Danh mục | Mapping kỳ vọng | Nhãn kỳ vọng | Chi tiết chính |
|----|----------|-----------------|---------------|----------------|
| IEEE-01 | MATCHED | MATCHED | verified | Vaswani 2017 → [1] |
| IEEE-02 | MATCHED | MATCHED | verified | Devlin 2019 → [2] |
| IEEE-03 | MATCHED | MATCHED | verified | Brown 2020 → [3] |
| IEEE-04 | MISSING_REFERENCE | MISSING_REFERENCE | suspected_hallucination | NovelPaper 2021 - KHÔNG CÓ REF |
| IEEE-05 | UNCITED_REFERENCE | UNCITED_REFERENCE | unresolved | [4] tồn tại nhưng không được trích dẫn |
| IEEE-06 | MATCHED | MATCHED | verified | AuthorA/B → [5]/[6] |
| IEEE-07 | STYLE_INCONSISTENT | STYLE_INCONSISTENT | unresolved | Trộn lẫn phong cách |
| IEEE-08 | MATCHED | MATCHED | verified | Goodfellow 2014 → [8] |
| IEEE-09 | MATCHED | MATCHED | verified | He 2016 → [9] |
| IEEE-10 | MATCHED | MATCHED | verified | SurveyAuthors 2023 → [10] |

---

## Định Nghĩa Trạng Thái Mapping Trích Dẫn

| Trạng thái | Mô tả | Điểm trừ |
|-------------|-------|-----------|
| MATCHED | Trích dẫn trong văn bản ↔ Tài liệu tham khảo khớp | 0.0 |
| MISSING_REFERENCE | Trích dẫn trong văn bản không có tài liệu tham khảo | 1.0 |
| UNCITED_REFERENCE | Tài liệu tham khảo không được trích dẫn | 0.5 |
| IN_TEXT_MISMATCH | Author/year khớp nhưng title khác | 0.8 |
| DUPLICATE_REFERENCE | ≥2 tài liệu tham khảo trỏ cùng một nguồn | 0.6 |
| AMBIGUOUS_MAPPING | ≥2 ứng viên phù hợp | 0.4 |
| STYLE_INCONSISTENT | Phong cách trích dẫn không nhất quán | 0.2 |
| UNRESOLVED | Chưa đủ thông tin | 0.0 |

## Định Nghĩa Nhãn Xác Thực

| Nhãn | Mô tả |
|-------|-------|
| verified | Nguồn được xác minh thành công |
| metadata_error | Metadata không khớp |
| suspected_hallucination | Nghi ngờ bịa đặt |
| unresolved | Không đủ bằng chứng |

---

*Tạo cho Citation Integrity Checker v1.2*
