import { ClipboardCheck } from 'lucide-react';

/**
 * PendingReviewsPage — placeholder for Phase 3.
 *
 * Full implementation lands in Phase 4. Will show verdicts flagged for
 * teacher review (metadata_error / suspected_hallucination across all
 * classes the teacher owns).
 */
export function PendingReviewsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-950 flex items-center justify-center">
          <ClipboardCheck className="h-5 w-5 text-amber-600 dark:text-amber-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Pending Reviews
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Danh sách verdict cần giảng viên xem xét và override.
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-12 text-center">
        <p className="text-base font-medium text-slate-700 dark:text-slate-300">
          Phase 4 — Implementation in progress
        </p>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
          Trang này sẽ hiển thị các verdict có label
          <code className="px-1.5 py-0.5 mx-1 rounded bg-slate-100 dark:bg-slate-800 text-xs">
            metadata_error
          </code>
          hoặc
          <code className="px-1.5 py-0.5 mx-1 rounded bg-slate-100 dark:bg-slate-800 text-xs">
            suspected_hallucination
          </code>
          chưa được override, kèm khả năng xem chi tiết và override trực tiếp.
        </p>
      </div>
    </div>
  );
}
