import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

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
      className="space-y-6"
      role="status"
      aria-live="polite"
      aria-label="Loading page"
    >
      {/* Header */}
      <div className="flex items-center gap-4">
        <Skeleton className="w-12 h-12 rounded-xl" />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </div>
      </div>

      {/* Stat row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <Card key={i} className="p-5 h-24">
            <Skeleton className="h-4 w-24 mb-3" />
            <Skeleton className="h-7 w-16" />
          </Card>
        ))}
      </div>

      {/* Main card */}
      <Card className="p-6 h-64 space-y-4">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-3/4" />
      </Card>

      <span className="sr-only">Loading…</span>
    </div>
  );
}
