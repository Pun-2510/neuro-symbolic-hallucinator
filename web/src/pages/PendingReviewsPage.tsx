import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ClipboardCheck, ExternalLink, AlertCircle } from 'lucide-react';
import { api, type PendingVerdict, type Class } from '@/api/client';

/**
 * PendingReviewsPage — teacher queue of verdicts awaiting review (Phase 4).
 *
 * Class filter chips at top; rows are click-throughs to the essay report.
 * Each verdict row has a colored label badge (rose for suspected, amber for
 * metadata_error).
 */
export function PendingReviewsPage() {
  const navigate = useNavigate();
  const [classes, setClasses] = useState<Class[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<number | null>(null);
  const [reviews, setReviews] = useState<PendingVerdict[]>([]);
  const [loadingClasses, setLoadingClasses] = useState(true);
  const [loadingReviews, setLoadingReviews] = useState(false);
  const [error, setError] = useState('');

  const loadClasses = useCallback(async () => {
    try {
      const data = await api.listMyClasses();
      setClasses(data);
      // Auto-select first class if any
      if (data.length > 0 && selectedClassId === null) {
        setSelectedClassId(data[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load classes');
    } finally {
      setLoadingClasses(false);
    }
    // selectedClassId intentionally excluded — we only want this on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadReviews = useCallback(async (cid: number) => {
    setLoadingReviews(true);
    setError('');
    try {
      const data = await api.listPendingReviews(cid);
      setReviews(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load reviews');
    } finally {
      setLoadingReviews(false);
    }
  }, []);

  useEffect(() => {
    loadClasses();
  }, [loadClasses]);

  useEffect(() => {
    if (selectedClassId !== null) loadReviews(selectedClassId);
  }, [selectedClassId, loadReviews]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-950 flex items-center justify-center">
          <ClipboardCheck className="h-5 w-5 text-amber-600 dark:text-amber-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Pending Reviews</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Verdict cần xem xét & override.
          </p>
        </div>
      </div>

      {error && (
        <div
          className="flex items-start gap-2 p-3 rounded-lg bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 text-sm"
          role="alert"
        >
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loadingClasses ? (
        <p className="text-slate-500 text-sm">Loading…</p>
      ) : classes.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 p-12 text-center">
          <p className="text-slate-700 dark:text-slate-300 font-medium">
            Bạn chưa phụ trách lớp nào.
          </p>
          <p className="text-sm text-slate-500 mt-1">
            Tạo lớp ở trang My Classes trước khi xem reviews.
          </p>
        </div>
      ) : (
        <>
          <div role="group" aria-label="Lọc theo lớp" className="flex flex-wrap gap-2">
            {classes.map((c) => {
              const isActive = selectedClassId === c.id;
              return (
                <button
                  key={c.id}
                  onClick={() => setSelectedClassId(c.id)}
                  aria-pressed={isActive}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                    isActive
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                  }`}
                >
                  {c.name}
                </button>
              );
            })}
          </div>

          <div className="rounded-xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 divide-y divide-slate-100 dark:divide-slate-800">
            {loadingReviews ? (
              <p className="p-6 text-center text-sm text-slate-500">Loading…</p>
            ) : reviews.length === 0 ? (
              <p className="p-6 text-center text-sm text-slate-500">
                Không có verdict chờ xem xét trong lớp này.
              </p>
            ) : (
              reviews.map((r) => (
                <button
                  key={r.verdict_id}
                  onClick={() => navigate(`/verification/report/${r.essay_id}`)}
                  className="w-full text-left p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 flex items-start gap-3 focus:outline-none focus:bg-slate-50 dark:focus:bg-slate-800/50"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-mono ${
                          r.label === 'suspected_hallucination'
                            ? 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300'
                            : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                        }`}
                      >
                        {r.label}
                      </span>
                      <span className="text-xs text-slate-500">{r.student_username ?? '—'}</span>
                    </div>
                    <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                      {r.filename}
                    </p>
                    {r.reasoning && (
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">
                        {r.reasoning}
                      </p>
                    )}
                  </div>
                  <ExternalLink className="h-4 w-4 text-slate-400 mt-1 shrink-0" />
                </button>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
