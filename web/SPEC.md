# Web UI v1.2 — Spec

**Ngày:** 2026-08-11
**Mục tiêu:** Hoàn thiện Web UI theo KNOWN_ISSUES_AND_TODO.md §2.9 (Tuần 14–15).

## Current State

- UploadPage.tsx — drag-drop + label legend ✅
- EssayPage.tsx — CIS card + verdict table + export JSON/CSV ✅
- HistoryPage.tsx — TODO stub (backend missing) ⚠️
- VerdictTable — basic table + row click → drawer ✅
- CitationDetailDrawer — raw text + verdict + reasoning ✅

## Missing (v1.2 §2.9)

### M1: Style Profile Card
Badge (APA-LIKE / IEEE-LIKE / MIXED / UNKNOWN) + confidence bar + key features list.

### M2: Citation Graph View (2 chiều)
- Integrity layer: MISSING_REFERENCE / UNCITED_REFERENCE / IN_TEXT_MISMATCH / DUPLICATE / AMBIGUOUS / STYLE_INCONSISTENT
- Source layer: VERIFIED / METADATA_ERROR / SUSPECTED_HALLUCINATION / UNRESOLVED
- Filter chips cho mỗi status
- Separate tabs hoặc 2-column layout

### M3: Override Mapping/Labels UI
- Giảng viên click override → dropdown chọn label/status mới
- Log vào `is_overridden` + `override_reason` + timestamp
- Visual indicator (icon) cho overridden rows

### M4: Evidence Drawer mở rộng
- Open Crossref/OpenAlex/Semantic Scholar/arXiv record link
- Show `matched_sources` data đẹp hơn (table thay vì JSON dump)
- Source provenance (which source → which field matched)
- Checked-at timestamp

### M5: Export PDF
- Generate PDF report (react-pdf hoặc html2canvas)
- Must contain 2-layer output: integrity + source side-by-side

### M6: API Types — Update for v1.2 schema
- `Verdict` cần: `mapping_status`, `mapping_confidence`, `citation_link`, `style_penalty`, `domain_exception`
- `AnalysisReport` cần: `style_profile`, `linking_summary`

---

## Implementation Plan

### Phase 1: API Types + Style Profile Card
1. Update `api/client.ts` types
2. Create `StyleProfileCard.tsx`
3. Wire into EssayPage

### Phase 2: Citation Graph + Mapping Status
1. Create `MappingStatusBadge.tsx`
2. Extend VerdictTable with filter chips
3. Add mapping_status column to table

### Phase 3: Evidence Drawer + Override
1. Extend `CitationDetailDrawer` với evidence links + matched_sources table
2. Create `OverrideDropdown.tsx`
3. Wire override API call

### Phase 4: Export PDF
1. Add PDF generation (html2canvas + jsPDF hoặc @react-pdf/renderer)
2. Update download buttons

### Phase 5: History Page + Testing
1. Test against backend (hoặc mock)
2. Write Playwright E2E tests

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
