import { useEffect, useState, useRef } from 'react';
import { api, type AnalysisReport } from '@/api/client';

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
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Ref giữ cancelled flag — tránh re-create closure mỗi lần effect re-run
  const cancelledRef = useRef(false);

  useEffect(() => {
    // Reset state khi essayId đổi
    cancelledRef.current = false;
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
          // Report sẵn sàng
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
