# Hướng dẫn sử dụng — Essay Integrity Checker

## 1. Mục đích

Essay Integrity Checker hỗ trợ giảng viên rà soát tính nhất quán của citation và độ tin cậy của tài liệu tham khảo trong file PDF.

Hệ thống không chấm điểm toàn bài, không kiểm tra đạo văn và không tự kết luận gian lận học thuật.

## 2. Khởi động hệ thống

### Backend

```bash
source .venv/bin/activate
uvicorn integrity_checker.api.main:app --reload --port 8000
```

### Frontend

```bash
cd web
npm install
npm run dev
```

Mở địa chỉ Vite hiển thị trong terminal, thường là `http://localhost:5173`.

## 3. Đăng nhập

Đăng nhập bằng tài khoản đã được tạo trong hệ thống. Sau khi đăng nhập, người dùng có thể:

- Upload essay.
- Xem lịch sử essay của mình.
- Mở report.
- Tải report xuống.

## 4. Upload và phân tích essay

1. Vào **Upload**.
2. Chọn hoặc kéo-thả file PDF.
3. Chờ pipeline hoàn tất.
4. Mở report được tạo.

MVP hỗ trợ PDF có text layer. PDF scan/encrypted có thể không được xử lý đầy đủ.

## 5. Đọc report

Report gồm các phần:

- **Style profile:** APA-like, IEEE-like, MIXED hoặc UNKNOWN và confidence.
- **CIS:** điểm hỗ trợ về citation integrity, không phải điểm tổng bài.
- **Integrity status:** quan hệ giữa citation trong bài và reference list.
- **Source label:** kết quả xác minh source.
- **Evidence:** candidate từ Crossref, OpenAlex, Semantic Scholar hoặc arXiv, các field khớp và rule đã kích hoạt.

### Ý nghĩa source label

| Label | Ý nghĩa |
|---|---|
| VERIFIED | Có record phù hợp và metadata chính khớp |
| METADATA_ERROR | Nguồn có thật nhưng citation khai báo sai một hoặc nhiều trường |
| SUSPECTED_HALLUCINATION | Chưa tìm thấy record phù hợp sau quy trình truy hồi |
| UNRESOLVED | Chưa đủ evidence hoặc hệ thống gặp lỗi/ambiguity |

### Ý nghĩa integrity status

`MATCHED` là liên kết hợp lệ. `MISSING_REFERENCE`, `UNCITED_REFERENCE`, `IN_TEXT_MISMATCH`, `DUPLICATE_REFERENCE`, `AMBIGUOUS_MAPPING` và `STYLE_INCONSISTENT` là các cảnh báo cần xem xét.

## 6. Evidence drawer và override

Chọn một citation trong bảng để mở evidence drawer. Có thể xem:

- Raw citation/reference.
- Source candidates.
- Field matching.
- Triggered rules.
- Link mở record nguồn.

Nếu giảng viên có bằng chứng khác, dùng **Override** để chọn label/status mới và ghi lý do. Override chỉ nên dùng khi đã kiểm tra thủ công.

## 7. Export

Trong trang report có thể tải:

- **JSON:** dữ liệu đầy đủ cho tích hợp hoặc phân tích.
- **CSV:** bảng citation/verdict.
- **PDF:** báo cáo trình bày cho lưu trữ/chia sẻ.

Mọi report export đều kèm disclaimer decision-support.

## 8. Giới hạn cần biết

- `UNRESOLVED` không đồng nghĩa nguồn giả.
- `SUSPECTED_HALLUCINATION` chỉ là cảnh báo, không phải kết luận.
- Citation cùng một nguồn nhiều lần không tự động bị xem là dư thừa.
- Kết quả phụ thuộc chất lượng text extraction, metadata và tình trạng các scholarly APIs.

