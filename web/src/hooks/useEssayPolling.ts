import { useEffect, useState, useRef } from 'react';
import { api, type AnalysisReport } from '@/api/client';
import { queryClient } from '@/lib/queryClient';

function getValidCachedReport(essayId: number | null): AnalysisReport | null {
  if (essayId == null || Number.isNaN(essayId) || essayId <= 0) {
    return null;
  }
  const queryKey = ['essay-report', essayId] as const;
  const queryState = queryClient.getQueryState<AnalysisReport | null>(queryKey);
  const cached = queryState?.data;
  if (cached && Array.isArray(cached.verdicts) && !queryState?.isInvalidated) {
    return cached;
  }
  return null;
}

function cacheValidReport(essayId: number, data: AnalysisReport): void {
  if (Array.isArray(data.verdicts)) {
    queryClient.setQueryData(['essay-report', essayId], data);
  }
}

/**
 * Hook poll analysis report cho async upload pages.
 *
 * Behavior:
 * 1. Gọi `getEssay(id)` ngay lập tức
 * 2. Nếu trả về report (HTTP 200) → done
 * 3. Nếu trả về null (HTTP 425 "still processing") → poll `getEssayStatus` mỗi 2s
 * 4. Khi status = 'completed' → fetch lại `getEssay` để lấy report đầy đủ
 * 5. Khi status = 'failed' → set error
 *
 * Lifecycle:
 * - Tạo AbortController mỗi khi `essayId` thay đổi
 * - Cleanup: abort() controller + clear interval khi unmount hoặc essayId đổi
 * - State updates được bảo vệ bởi `cancelled` flag (AbortController chỉ cancel
 *   network, không cancel React state updates)
 *
 * @param essayId - Essay ID cần poll, hoặc null để skip
 * @param options.intervalMs - Poll interval (default 2000ms)
 */
export interface UseEssayPollingOptions {
  intervalMs?: number;
  /** Error message khi fetch fail (không phải abort). Default: "Failed to load report. Please try again." */
  errorMessage?: string;
}

export interface UseEssayPollingResult {
  report: AnalysisReport | null;
  error: string | null;
  /** True khi đang trong quá trình poll (chưa có report, chưa lỗi) */
  isPolling: boolean;
}

export function useEssayPolling(
  essayId: number | null,
  options: UseEssayPollingOptions = {},
): UseEssayPollingResult {
  const { intervalMs = 2000, errorMessage = 'Failed to load report. Please try again.' } = options;
  const [report, setReport] = useState<AnalysisReport | null>(() => getValidCachedReport(essayId));
  const [error, setError] = useState<string | null>(null);
  // Ref giữ cancelled flag — tránh re-create closure mỗi lần effect re-run
  const cancelledRef = useRef(false);

  useEffect(() => {
    // Reset state khi essayId đổi (hoặc dùng ngay dữ liệu đã có trong queryClient cache)
    cancelledRef.current = false;
    const cached = getValidCachedReport(essayId);
    if (cached) {
      setReport(cached);
      setError(null);
      return;
    }

    setReport(null);
    setError(null);

    if (essayId == null || Number.isNaN(essayId) || essayId <= 0) {
      if (essayId != null) setError('Invalid essay ID');
      return;
    }

    // AbortController để cancel in-flight fetch khi unmount / essayId đổi
    const controller = new AbortController();
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    const tryFetch = async () => {
      try {
        const data = await api.getEssay(essayId, { signal: controller.signal });
        if (cancelledRef.current) return;

        if (data) {
          // Report sẵn sàng — đồng bộ vào TanStack Query cache để chuyển tab tức thì
          cacheValidReport(essayId, data);
          setReport(data);
          setError(null);
          if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
          }
          return;
        }

        // Pipeline vẫn đang chạy (HTTP 425) — check status
        const status = await api.getEssayStatus(essayId, { signal: controller.signal });
        if (cancelledRef.current) return;

        if (status.status === 'failed') {
          setError(status.error ?? 'Pipeline failed.');
          if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
          }
          return;
        }

        if (status.status === 'completed') {
          // Race condition: report có thể chưa được persist. Retry 1 lần.
          const retry = await api.getEssay(essayId, { signal: controller.signal });
          if (cancelledRef.current) return;
          if (retry) {
            cacheValidReport(essayId, retry);
            setReport(retry);
            setError(null);
            if (pollTimer) {
              clearInterval(pollTimer);
              pollTimer = null;
            }
            return;
          }
        }

        // Vẫn processing — bắt đầu poll nếu chưa có timer
        if (!pollTimer) {
          pollTimer = setInterval(() => {
            void tryFetch();
          }, intervalMs);
        }
      } catch (err) {
        // AbortError là kết quả mong đợi khi unmount — không set error
        if (err instanceof DOMException && err.name === 'AbortError') return;
        if (cancelledRef.current) return;
        setError(errorMessage);
        if (pollTimer) {
          clearInterval(pollTimer);
          pollTimer = null;
        }
      }
    };

    void tryFetch();

    return () => {
      cancelledRef.current = true;
      controller.abort();
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [essayId, intervalMs]);

  return { report, error, isPolling: report == null && error == null && essayId != null };
}
