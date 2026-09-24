# Citation & Reference Styles for Integrity Checker

Tài liệu này tổng hợp các citation/reference styles phổ biến ngoài APA và IEEE, kèm dấu hiệu nhận diện, regex heuristic, ví dụ hợp lệ/sai và gợi ý thiết kế parser cho hệ thống citation/reference integrity checker.

> Lưu ý: Các regex dưới đây chỉ nên dùng để **nhận diện sơ bộ style/family**, không nên dùng làm validator tuyệt đối vì mỗi style có nhiều biến thể.

---

## 1. Tổng quan các style phổ biến

| Style | Dấu hiệu nhận diện citation | Regex heuristic gợi ý |
|---|---|---|
| APA | `(Nguyen, 2024)` | `\([A-Z][A-Za-zÀ-ỹ'-]+(?: et al\.)?,\s?\d{4}[a-z]?\)` |
| Harvard | `(Nguyen 2024)` hoặc `(Nguyen, 2024)` | `\([A-Z][A-Za-zÀ-ỹ'-]+,?\s+\d{4}\)` |
| IEEE | `[1]`, `[2]–[5]` | `\[\d+(?:\s*[-–,]\s*\d+)*\]` |
| ACM | `[1]` hoặc `(Nguyen et al., 2024)` tùy template | IEEE/APA-like |
| Vancouver | `(1)`, `[1]`, superscript | `(?:\(|\[)\d+(?:[-–,]\d+)*(?:\)|\])` |
| MLA | `(Nguyen 25)` | `\([A-Z][A-Za-zÀ-ỹ'-]+\s+\d+\)` |
| Chicago Author-Date | `(Nguyen 2024, 25)` | `\([A-Z][A-Za-zÀ-ỹ'-]+\s+\d{4},\s*\d+\)` |
| Chicago Notes | superscript / footnote | khó parse bằng plain-text regex |
| AMA | superscript hoặc numeric | `\b\d+(?:[-–,]\d+)*\b` |
| ACS | superscript / `(1)` / author-date | numeric hoặc author-date |
| Nature | superscript numeric | thường là số superscript |
| CSE | `(Nguyen 2024)` hoặc numeric | Harvard/Vancouver-like |

---

## 2. APA 7th

### In-text citation hợp lệ

```text
(Nguyen, 2024)
(Nguyen & Tran, 2024)
(Nguyen et al., 2024)
Nguyen et al. (2024)
```

### Regex đơn giản

```regex
\((?:[A-Z][A-Za-zÀ-ỹ'-]+(?:\s*&\s*[A-Z][A-Za-zÀ-ỹ'-]+|\s+et al\.)?),\s*\d{4}[a-z]?\)
```

### Reference hợp lệ

```text
Nguyen, A. T., & Tran, B. H. (2024). Depression detection using deep learning. Journal of Artificial Intelligence, 10(2), 100–115. https://doi.org/10.1234/example
```

### Sai thường gặp

```text
Nguyen A.T and Tran B.H, Depression detection using deep learning, 2024.
```

### Các lỗi parser nên phát hiện

```text
Missing year
Missing author
Citation year ≠ reference year
Cited author not found in references
Reference never cited
```

---

## 3. IEEE

### Citation hợp lệ

```text
[1]
[2]
[1], [3]
[2]–[5]
[1], [4], [7]
```

### Regex

```regex
\[\d+(?:\s*[-–,]\s*\d+)*\]
```

### Reference

```text
[1] A. T. Nguyen and B. H. Tran, "Depression detection using deep learning," Journal of Artificial Intelligence, vol. 10, no. 2, pp. 100–115, 2024.
```

### Sai

```text
Nguyen et al. (2024)
```

nếu document được khai báo là IEEE.

### Test case quan trọng

```text
Text: According to [8]...
References: chỉ có [1]–[7]
```

→ `MISSING_REFERENCE`

---

## 4. Harvard

### Citation

```text
(Nguyen, 2024)
(Nguyen and Tran, 2024)
(Nguyen et al., 2024)
```

Một số Harvard variant bỏ comma:

```text
(Nguyen 2024)
```

### Regex tolerant

```regex
\([A-Z][A-Za-zÀ-ỹ'-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-zÀ-ỹ'-]+|\s+et al\.)?,?\s+\d{4}[a-z]?\)
```

### Reference

```text
Nguyen, A.T. and Tran, B.H., 2024. Depression detection using deep learning. Journal of Artificial Intelligence, 10(2), pp.100–115.
```

---

## 5. MLA

Điểm khác biệt lớn so với APA: **không có năm trong citation**.

### Citation

```text
(Nguyen 25)
(Nguyen 25–27)
(Nguyen and Tran 42)
```

### Regex

```regex
\([A-Z][A-Za-zÀ-ỹ'-]+(?:\s+and\s+[A-Z][A-Za-zÀ-ỹ'-]+)?\s+\d+(?:[-–]\d+)?\)
```

### Reference

```text
Nguyen, Anh T., and Binh H. Tran. "Depression Detection Using Deep Learning." Journal of Artificial Intelligence, vol. 10, no. 2, 2024, pp. 100–115.
```

### Test case

```text
(Nguyen, 2024)
```

Có thể là APA nhưng gần như chắc chắn không phải MLA chuẩn.

---

## 6. Chicago Author-Date

### Citation

```text
(Nguyen 2024)
(Nguyen 2024, 25)
(Nguyen and Tran 2024, 25–28)
```

### Regex

```regex
\([A-Z][A-Za-zÀ-ỹ'-]+(?:\s+and\s+[A-Z][A-Za-zÀ-ỹ'-]+)?\s+\d{4}(?:,\s*\d+(?:[-–]\d+)?)?\)
```

### Reference

```text
Nguyen, Anh T., and Binh H. Tran. 2024. "Depression Detection Using Deep Learning." Journal of Artificial Intelligence 10 (2): 100–115.
```

### Heuristic APA vs Chicago Author-Date

```text
APA:
(Nguyen, 2024)

Chicago:
(Nguyen 2024)
```

Chỉ nên coi đây là heuristic, không phải quy tắc tuyệt đối.

---

## 7. Chicago Notes & Bibliography

Citation thường là footnote.

```text
Depression detection remains challenging.^1
```

Footnote:

```text
1. Anh T. Nguyen and Binh H. Tran, "Depression Detection Using Deep Learning," Journal of Artificial Intelligence 10, no. 2 (2024): 100–115.
```

Nếu pipeline chỉ extract plain text, nên lưu dưới dạng entity thay vì ép vào regex APA/IEEE.

```json
{
  "citation_type": "FOOTNOTE",
  "marker": "1",
  "location": "page_3"
}
```

---

## 8. Vancouver

### Citation

```text
(1)
(2,3)
(4-7)
[1]
[1-3]
```

### Regex

```regex
[\[(]\d+(?:\s*[-–,]\s*\d+)*[\])]
```

### Reference

```text
1. Nguyen AT, Tran BH. Depression detection using deep learning. J Artif Intell. 2024;10(2):100-115.
```

Vancouver phù hợp để test biomedical metadata vì reference có cấu trúc khá rõ.

---

## 9. AMA

Citation thường là superscript:

```text
Previous research has demonstrated this association.¹
```

hoặc:

```text
...as demonstrated previously.1,2
```

### Reference

```text
1. Nguyen AT, Tran BH. Depression detection using deep learning. Journal of Artificial Intelligence. 2024;10(2):100-115.
```

AMA và Vancouver có thể rất giống nhau nếu chỉ nhìn phần reference.

---

## 10. ACM

ACM thường dùng numeric citation.

```text
[1]
[3, 7]
```

### Reference ví dụ

```text
[1] Anh T. Nguyen and Binh H. Tran. 2024. Depression detection using deep learning. Journal of Artificial Intelligence 10, 2 (2024), 100–115.
```

### Regex citation

```regex
\[\d+(?:\s*,\s*\d+)*\]
```

IEEE và ACM rất khó phân biệt chỉ bằng `[1]`.

Nên detect trước:

```text
citation_family = NUMERIC_BRACKET
```

sau đó mới classify:

```text
IEEE / ACM / other numeric
```

dựa vào reference formatting.

---

## 11. Nature

Citation thường numeric superscript:

```text
Depression affects millions worldwide.¹
```

### Reference ví dụ

```text
1. Nguyen, A. T. & Tran, B. H. Depression detection using deep learning. J. Artif. Intell. 10, 100–115 (2024).
```

Một pattern khá đặc trưng:

```text
Journal volume pages (year)
```

Ví dụ:

```text
Nature 615, 123–130 (2023)
```

---

## 12. ACS

Có thể gặp:

```text
Smith et al.^1
```

hoặc:

```text
Smith et al. (1)
```

### Reference

```text
(1) Nguyen, A. T.; Tran, B. H. Depression Detection Using Deep Learning. J. Artif. Intell. 2024, 10, 100–115.
```

Dấu hiệu khá thường gặp:

```text
Nguyen, A. T.; Tran, B. H.
```

ACS thường dùng dấu semicolon giữa các tác giả.

---

## 13. CSE

CSE có ba hệ thống phổ biến:

```text
Citation-sequence
Name-year
Citation-name
```

### Name-year

```text
(Nguyen 2024)
```

### Citation-sequence

```text
(1)
```

### Reference

```text
Nguyen AT, Tran BH. 2024. Depression detection using deep learning. Journal of Artificial Intelligence. 10(2):100–115.
```

CSE là test case tốt để kiểm tra xem classifier có bị quá tự tin hay không.

---

# 14. Gợi ý thiết kế parser: chia thành 2 tầng

Không nên trả thẳng:

```text
APA / IEEE / MLA
```

ngay từ bước đầu.

## Tầng 1: Citation Family Detection

```text
AUTHOR_YEAR_COMMA
AUTHOR_YEAR
AUTHOR_PAGE
NUMERIC_BRACKET
NUMERIC_PAREN
NUMERIC_SUPERSCRIPT
FOOTNOTE
UNKNOWN
```

Ví dụ:

```python
from enum import Enum

class CitationFamily(Enum):
    AUTHOR_YEAR_COMMA = "AUTHOR_YEAR_COMMA"
    AUTHOR_YEAR = "AUTHOR_YEAR"
    AUTHOR_PAGE = "AUTHOR_PAGE"

    NUMERIC_BRACKET = "NUMERIC_BRACKET"
    NUMERIC_PAREN = "NUMERIC_PAREN"
    NUMERIC_SUPERSCRIPT = "NUMERIC_SUPERSCRIPT"

    FOOTNOTE = "FOOTNOTE"
    UNKNOWN = "UNKNOWN"
```

## Tầng 2: Style Inference

```text
AUTHOR_YEAR_COMMA
    → APA / Harvard

AUTHOR_YEAR
    → Chicago / Harvard / CSE

NUMERIC_BRACKET
    → IEEE / ACM / Vancouver

NUMERIC_SUPERSCRIPT
    → AMA / Nature / ACS
```

Cách này an toàn hơn nhiều so với:

```python
if "[1]" in document:
    style = "IEEE"
```

vì `[1]` hoàn toàn có thể là ACM, Vancouver hoặc một journal-specific style.

---

# 15. Bộ test tối thiểu đề xuất

Ví dụ:

```json
[
  {
    "text": "Previous research supports this finding (Nguyen, 2024).",
    "expected_family": "AUTHOR_YEAR_COMMA",
    "possible_styles": ["APA", "Harvard"]
  },
  {
    "text": "Previous research supports this finding [12].",
    "expected_family": "NUMERIC_BRACKET",
    "possible_styles": ["IEEE", "ACM", "Vancouver"]
  },
  {
    "text": "Previous research supports this finding (Nguyen 2024, 25).",
    "expected_family": "AUTHOR_YEAR",
    "possible_styles": ["Chicago"]
  },
  {
    "text": "Previous research supports this finding (Nguyen 25).",
    "expected_family": "AUTHOR_PAGE",
    "possible_styles": ["MLA"]
  }
]
```

---

# 16. Gợi ý output của classifier

Thay vì output duy nhất:

```json
{
  "style": "IEEE"
}
```

nên trả:

```json
{
  "family": "NUMERIC_BRACKET",
  "likely_styles": [
    {
      "style": "IEEE",
      "confidence": 0.65
    },
    {
      "style": "ACM",
      "confidence": 0.25
    },
    {
      "style": "Vancouver",
      "confidence": 0.10
    }
  ]
}
```

Sau đó dùng thêm:

- reference formatting,
- venue/domain,
- document-level consistency,
- numbering behavior,
- author formatting,
- year placement,
- punctuation pattern,

để phân biệt chính xác hơn.

---

# 17. Bộ style nên ưu tiên cho Integrity Checker

Nếu muốn test đủ rộng mà vẫn thực tế, nên ưu tiên:

1. APA
2. IEEE
3. Harvard
4. MLA
5. Chicago Author-Date
6. Chicago Notes & Bibliography
7. Vancouver
8. AMA
9. ACM
10. Nature
11. ACS
12. CSE

Bộ này bao phủ tốt ba nhóm chính:

- **Author–date**
- **Numeric**
- **Footnote / Notes**

Đây là nền tảng phù hợp cho hệ thống kiểm tra citation/reference, đặc biệt khi xử lý PDF sinh viên có format không hoàn toàn chuẩn.
