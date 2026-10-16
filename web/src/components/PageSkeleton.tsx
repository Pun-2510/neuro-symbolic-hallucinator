/**
 * PageSkeleton — Generic loading skeleton for lazy-loaded routes.
 *
 * Used as the Suspense fallback for React.lazy() route imports. Renders a
 * low-fidelity placeholder so the layout doesn't shift when the page
 * module loads. Matches the chrome (max-w-6xl mx-auto) so the transition
 * is seamless.
 */
export function PageSkeleton() {
  return (
    <div
      className="space-y-6 animate-pulse"
      role="status"
      aria-live="polite"
      aria-label="Loading page"
    >
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-xl bg-slate-200 dark:bg-slate-800" />
        <div className="space-y-2 flex-1">
          <div className="h-6 w-48 rounded bg-slate-200 dark:bg-slate-800" />
          <div className="h-4 w-72 rounded bg-slate-200 dark:bg-slate-800" />
        </div>
      </div>

      {/* Stat row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="card p-5 h-24 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800"
          />
        ))}
      </div>

      {/* Main card */}
      <div className="card p-6 h-64 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800" />

      <span className="sr-only">Loading…</span>
    </div>
  );
}
