# 📋 Hướng Dẫn Gán Nhãn Citations (Citation Annotation)

## Mục đích

Gán nhãn 2887 citations từ 55 bài báo arXiv NLP để tạo **gold dataset** cho việc đánh giá hallucination detection.

> **Thuật ngữ:** Một "citation" là một tham chiếu trong danh mục tài liệu tham khảo (reference list) của một bài báo.

## Bước 1: Mở Tool Gán Nhãn

Mở file `annotate_full.html` trong trình duyệt (Chrome, Safari, Firefox đều được):

```
data/annotation/annotate_full.html
```

**Cách mở:**
- **Mac:** Kéo file vào icon trình duyệt, hoặc nhấp đúp vào file
- **Windows:** Nhấp đúp vào file (sẽ mở bằng trình duyệt mặc định)

> **Lưu ý:** Đường dẫn tuyệt đối: `file:///Users/iannwendy/Desktop/DATN/essay-integrity-checker/data/annotation/annotate_full.html`

---

## Bước 2: Hiểu Giao Diện

Mỗi trang hiển thị **25 citations**. Mỗi citation card gồm:

```
┌─────────────────────────────────────────────────┐
│ [Số thứ tự]  📄 1706.03762                      │
│ [1] Jimmy Lei Ba, Jamie Ryan Kiros, and        │
│ Geoffrey E Hinton. Layer normalization.         │
│ [arXiv preprint arXiv:1607.06450, 2016.]       │
│                                                 │
│ 🔍 Tra Google với full citation →              │
├─────────────────────────────────────────────────┤
│ [Chọn nhãn ▼]          [Ghi chú]    [Saved]    │
└─────────────────────────────────────────────────┘
```

### Các nhãn cần gán:

| Nhãn | Ý nghĩa | Khi nào dùng |
|------|----------|--------------|
| **✓ Verified** | Citation tồn tại và chính xác | Tìm thấy paper trên Google Scholar |
| **⚠️ Suspected Hallucination** | Citation có thể bị bịa đặt | **Không tìm thấy** paper trên Google Scholar |
| **⚡ Metadata Error** | Paper có tồn tại, nhưng thông tin (tên, năm, tác giả) bị sai | Tìm thấy paper nhưng thông tin không khớp |
| **○ Unresolved** | Không chắc chắn, cần xem xét thêm | Không đủ thông tin để quyết định |

---

## Bước 3: Quy Trình Gán Nhãn

### Với mỗi citation, làm theo 3 bước:

**Bước 3a.** Đọc **full citation text** trong card (dòng bắt đầu bằng `[1]`, `[2]`, v.v.)

**Bước 3b.** Click nút **"🔍 Tra Google với full citation"**
   → Trình duyệt mở Google Search với citation được đặt trong quotes

**Bước 3c.** Trên Google Search, kiểm tra:

| Kết quả Google | Hành động |
|----------------|-----------|
| **Google Scholar hiển thị đúng paper** (đúng tên, tác giả, năm) | → Chọn **"✓ Verified"** |
| **Google Scholar hiển thị paper cùng chủ đề nhưng thông tin (tên/năm/tác giả) không khớp** | → Chọn **"⚡ Metadata Error"** |
| **Không tìm thấy paper nào** (0 kết quả hoặc toàn kết quả khác) | → Chọn **"⚠️ Suspected Hallucination"** |
| **Có tìm thấy nhưng không chắc chắn** | → Chọn **"○ Unresolved"** + ghi chú lý do |

**Bước 3d.** *(Tùy chọn)* Điền ghi chú nếu cần giải thích thêm

**Bước 3e.** Nhãn tự động được **lưu** (thấy dấu ✓ Saved)

---

## Bước 4: Các Tính Năng Hữu Ích

### Filter (Lọc)
Dùng dropdown **"Filter"** để ưu tiên:

| Filter | Dùng khi |
|--------|----------|
| **Tất cả** | Xem tất cả |
| **Chưa annotate** | Xem những cái chưa có nhãn |
| **Không có Crossref match** | ⚠️ **Ưu tiên đầu tiên** — những cái này có xác suất cao là hallucination |
| **Verified / Suspected / Meta Error** | Xem theo nhãn |

### Sort (Sắp xếp)
| Sort | Ý nghĩa |
|------|---------|
| **Theo thứ tự** | Mặc định |
| **Không Crossref trước** | Ưu tiên những cái khó nhất |
| **Theo paper** | Nhóm theo bài báo nguồn |

### Nút "→ Chưa annotate"
Nhảy nhanh đến citation chưa annotate gần nhất.

### Auto-save
Dữ liệu **tự động lưu** vào trình duyệt (localStorage). Đóng mở lại trình duyệt không mất dữ liệu.

---

## Bước 5: Export Kết Quả

Khi gán nhãn xong (hoặc xong một phần), click:

- **📥 Export CSV** → Tải file `annotations.csv` — dùng cho IAA và training
- **📄 Export JSON** → Tải file `annotations.json` — dùng cho analysis

**Gửi file đã export cho người quản lý** (hoặc commit lên Git).

---

## Bước 6: Bao Nhiêu Là Đủ?

| Mục tiêu | Số citations | Thời gian ước tính |
|-----------|-------------|-------------------|
| **Pilot / Test** | 50–100 | 1–2 tiếng |
| **Đủ cho thesis** | 200–500 | 4–8 tiếng |
| **Toàn bộ** | 2887 | 15–20 tiếng |

**Khuyến nghị:** Bắt đầu với **100 citations** (filter → "Không có Crossref match" trước) để có baseline nhanh.

---

## Ví Dụ Thực Tế

### Ví dụ 1: Verified ✅
```
Citation: [1] Jimmy Lei Ba, Jamie Ryan Kiros, and Geoffrey E Hinton.
          Layer normalization. arXiv preprint arXiv:1607.06450, 2016.

Tra Google → Tìm thấy paper "Layer Normalization" trên arXiv, đúng
tên tác giả, đúng năm 2016.
→ Chọn: ✓ Verified
```

### Ví dụ 2: Suspected Hallucination ⚠️
```
Citation: [5] Smith, J. (2024). A Revolutionary New Method for AI.
          Journal of Artificial Intelligence, 12(3), 45-67.

Tra Google → Không tìm thấy paper nào tên "A Revolutionary New Method
for AI" của Smith trên Journal of AI 2024.
→ Chọn: ⚠️ Suspected Hallucination
→ Ghi chú: "Paper không tồn tại, DOI không hợp lệ"
```

### Ví dụ 3: Metadata Error ⚡
```
Citation: [3] LeCun, Y. (2015). Deep Learning. Nature, 521, 436-444.

Tra Google → Tìm thấy paper "Deep Learning" nhưng năm đúng là 2015
NHƯNG tác giả đúng phải là "Yoshua Bengio, Ian Goodfellow, Aaron
Courville" — không phải LeCun.
→ Chọn: ⚡ Metadata Error
→ Ghi chú: "Tác giả sai — đây là review book, LeCun không phải tác giả chính"
```

---

## Câu Hỏi Thường Gặp

**Q: Google Scholar bắt xác minh robot (CAPTCHA)?**
A: Thử đợi 30 giây rồi refresh, hoặc dùng search query khác.

**Q: Đóng trình duyệt có mất dữ liệu không?**
A: Không — tự động lưu vào localStorage của trình duyệt.

**Q: Gán sai nhãn thì sửa được không?**
A: Được — click vào dropdown, chọn nhãn khác, tự động save lại.

**Q: Có cần gán nhãn hết 2887 citations không?**
A: Không bắt buộc — 200-500 citations đã đủ cho thesis.

---

## Liên hệ

Nếu có thắc mắc về quy tắc gán nhãn, liên hệ người quản lý để thống nhất tiêu chí.
