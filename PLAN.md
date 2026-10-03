# Plan: Batch PDF Processing for Essay Integrity Checker

## Context

**Problem:** Hiện tại hệ thống chỉ xử lý 1 PDF/lần. User muốn upload và phân tích nhiều PDF cùng lúc.

**Current State:**
- Backend: Single endpoint `POST /essays` nhận 1 file
- Frontend: UploadPage chỉ accept 1 file (`multiple: false`)
- Pipeline: `IntegrityPipeline.run_async()` xử lý 1 PDF

**Why:** Khi cần verify nhiều tiểu luận cùng lúc (ví dụ: kiểm tra cả lớp học), việc upload từng file rất tốn thời gian.

---

## Design Decision (APPROVED)

### Selected Approach: Sequential Upload + Separate Page

**Confirmed by user:**
- ✅ Sequential Upload (Frontend-driven, N requests)
- ✅ Separate page (`/batch-upload`)

**Lý do:**
1. **Ít thay đổi backend** - tận dụng endpoint hiện có
2. **Dễ debug** - mỗi file độc lập
3. **Frontend-driven** - không cần thêm batch state management phức tạp ở backend
4. **Error isolation** - file này fail không ảnh hưởng file khác
5. **Progressive enhancement** - có thể cải thiện thành True Batch sau nếu cần

---

## Implementation Plan

### Phase 1: Frontend - New Batch Upload Page (Main Work)

**File:** `web/src/pages/BatchUploadPage.tsx` (NEW)

New page with:
- Multi-file dropzone (`multiple: true`)
- File list with per-file status tracking
- Summary stats (pending/processing/completed/failed)
- Sequential upload using existing `api.uploadEssay()`
- Per-file progress polling using existing `api.getEssayStatus()`
- "View Report" links for completed files

Key components:
- `BatchFileItem` interface: `{ id, file, status, progress, essayId, error }`
- `FileStatusCard` component for each file
- Summary statistics grid
- Clear/Remove individual file buttons

### Phase 2: Frontend - API Client Extension

**File:** `web/src/api/client.ts`

No new API methods needed! We use existing:
- `uploadEssay(file)` - already returns `essay_id`
- `getEssayStatus(id)` - already returns status

We only need to extend TypeScript types:
```typescript
interface BatchFileItem {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';
  progress: number;
  essayId?: number;
  error?: string;
}
```

### Phase 3: Frontend - Add Route

**File:** `web/src/router.tsx`

Add:
```typescript
{ path: '/batch-upload', element: <BatchUploadPage /> }
```

### Phase 4: Frontend - Navigation Update

**File:** `web/src/components/AppLayout.tsx` or sidebar

Add "Batch Upload" menu item linking to `/batch-upload`

### Phase 5 (Optional): Backend - Batch Progress Tracker

**File:** `src/integrity_checker/api/progress.py`

Only needed if we want to track batch-level progress in backend:
```python
class BatchProgressTracker:
    """Track progress for batch jobs (optional enhancement)."""
    def init_batch(self, batch_id: str, essay_ids: list[int]) -> None
    def get_batch_status(self, batch_id: str) -> BatchStatusResponse
```

**Skip for MVP** - frontend manages batch state internally.

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `web/src/pages/BatchUploadPage.tsx` | Create | New batch upload page (main deliverable) |
| `web/src/api/client.ts` | Modify | Add BatchFileItem type (no new API methods needed) |
| `web/src/router.tsx` | Modify | Add `/batch-upload` route |
| `web/src/components/AppLayout.tsx` | Modify | Add "Batch Upload" navigation link |

**No backend changes required for MVP!** - Reuses existing endpoints.

---

## UI/UX Design

### Batch Upload Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Batch Verification                                          │
│  Upload multiple PDFs for concurrent analysis                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │           📁 Drop multiple PDFs here                     │ │
│  │              or browse files                              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 📄 essay1.pdf          │ 2.5 MB │ ✓ Complete │ Report │ │
│  │ 📄 essay2.pdf          │ 1.8 MB │ ⟳ Processing 45%  │ │
│  │ 📄 essay3.pdf          │ 3.2 MB │ ⏳ Pending        │ │
│  │ 📄 essay4.pdf          │ 2.1 MB │ ✗ Failed         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────┬──────────┬──────────┬──────────┐               │
│  │ Pending  │Processing│ Completed│  Failed  │               │
│  │    1     │    1     │    1     │    1     │               │
│  └──────────┴──────────┴──────────┴──────────┘               │
│                                                              │
│  [ Clear All ]  [ Download All Reports (CSV) ]               │
└─────────────────────────────────────────────────────────────┘
```

### Per-File Status Card

| Status | Color | Icon | Actions |
|--------|-------|------|---------|
| Pending | Gray | Clock | Remove |
| Uploading | Blue | Upload | - |
| Processing | Amber | Loader | - |
| Completed | Green | Check | View Report |
| Failed | Red | X | Remove, Retry |

---

## Verification

### Manual Testing
1. Navigate to `/batch-upload`
2. Drop 3-5 PDF files
3. Verify files appear in list with "Pending" status
4. Click "Start Verification"
5. Verify first file changes to "Uploading" then "Processing"
6. Verify progress bar updates during processing
7. Verify "Completed" status when done, with "View Report" link
8. Verify remaining files process sequentially
9. Verify batch summary stats update correctly
10. Test error case: one file fails → others continue

### Existing Tests (No Backend Changes)
```bash
# Verify no regressions - no new backend code
python -m pytest tests/ -v
```

---

## Rollout Strategy

1. **Create BatchUploadPage.tsx** - New page component
2. **Add Route** - `/batch-upload` in router.tsx
3. **Add Navigation** - Link in sidebar/AppLayout
4. **Test** - Verify with 3-5 PDFs

---

## Future Enhancements (Out of Scope for v1)

- `POST /essays/batch` - True batch endpoint (Option A)
- Batch result export (combined CSV)
- Email notification when batch completes
- Batch history page

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| No backend changes | N/A | Low | Uses existing, tested endpoints |
| Frontend state complexity | Low | Low | Sequential processing, simple state |
| Pipeline overload (many concurrent users) | Low | Medium | Each user processes their own batch sequentially |

**Overall Risk: LOW** - Minimal changes, maximum reuse.

---

## Estimated Effort

- **Backend:** 0 hours (reuses existing endpoints)
- **Frontend:** 3-4 hours (new page + route + nav)
- **Testing:** 1 hour (manual verification)
- **Total:** ~4-5 hours
