# Web UI v1.2 — Spec

**Ngày cập nhật:** 2026-09-12
**Mục tiêu:** Mô tả trạng thái Web UI v1.2 và các phần còn lại trước khi demo/đóng gói.

## Current State

- `UploadPage.tsx` — drag-drop, upload progress và label legend ✅
- `EssayPage.tsx` — CIS card, style profile, verdict table và export JSON/CSV/PDF ✅
- `HistoryPage.tsx` — gọi backend list/delete essay, refresh định kỳ ✅
- `CitationGraphView.tsx` — 3 chế độ Integrity/Source/Combined, filter status/label ✅
- `CitationDetailDrawer.tsx` — evidence theo nguồn, matched fields, links và override history ✅
- `OverrideControls.tsx` — UI override label/status và reason ✅
- `AppLayout.tsx` — layout dùng chung cho dashboard/upload/history/report ✅
- Production build (`npm run build`) ✅

## Remaining

- Hoàn thiện E2E Playwright cho login → upload → report → history.
- Đồng bộ TypeScript types với toàn bộ trường mapping (`mapping_status`, `mapping_confidence`, `citation_link`, `style_penalty`, `domain_exception`).
- Backend override cần persist thật vào DB và ghi `audit_logs`.
- Thêm màu/hiển thị đầy đủ cho mọi `CitationMappingStatus` ở các màn hình.
- Kiểm tra deployment Docker production và cấu hình `VITE_API_BASE_URL`.

---

## Implementation Plan

### Đã hoàn thành
1. Update `api/client.ts` types
2. Create `StyleProfileCard.tsx`
3. Wire into EssayPage

### Đã hoàn thành
1. Create `MappingStatusBadge.tsx`
2. Extend VerdictTable with filter chips
3. Add mapping_status column to table

### Đã hoàn thành phần UI; còn persistence backend
1. Extend `CitationDetailDrawer` với evidence links + matched_sources table
2. Create `OverrideDropdown.tsx`
3. Wire override API call

### Đã hoàn thành
1. Add PDF generation (html2canvas + jsPDF hoặc @react-pdf/renderer)
2. Update download buttons

### Tiếp theo
1. Hoàn thiện Playwright E2E.
2. Kiểm thử với backend thật và dữ liệu nhiều citation.
3. Sửa persistence/audit cho override.

---

## Tech Stack
- React 18 + TypeScript
- Tailwind CSS + Radix UI
- Lucide React (icons)
- react-dropzone (file upload)
- @react-pdf/renderer hoặc html2canvas + jsPDF (PDF export)
- Playwright (E2E tests)

## Color Tokens (Tailwind + CSS variables)
```css
/* Verdict colors */
--verdict-verified: #16a34a
--verdict-metadata-error: #ca8a04
--verdict-suspected: #dc2626
--verdict-unresolved: #6b7280

/* Mapping status colors */
--status-matched: #16a34a
--status-missing: #dc2626
--status-uncited: #f59e0b
--status-mismatch: #f97316
--status-duplicate: #9333ea
--status-ambiguous: #8b5cf6
--status-style-inconsistent: #0ea5e9
```
