import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type AnalysisReport, type OverrideRequest } from '@/api/client';

interface UseEssayReportOptions {
  /** Enable polling while essay is still processing (default: true) */
  pollUntilDone?: boolean;
  /** Poll interval in ms (default: 2000) */
  intervalMs?: number;
}

export function useEssayReport(
  essayId: number | null,
  options: UseEssayReportOptions = {},
) {
  const { pollUntilDone = true, intervalMs = 2000 } = options;

  return useQuery({
    queryKey: ['essay-report', essayId],
    queryFn: async (): Promise<AnalysisReport | null> => {
      if (essayId === null) return null;
      // Try direct report first
      const report = await api.getEssay(essayId);
      if (report) return report;
      // If null, check status — if processing, return null (refetch will retry)
      const status = await api.getEssayStatus(essayId);
      if (status.status === 'failed') {
        throw new Error(status.error ?? 'Essay processing failed');
      }
      return null;
    },
    enabled: essayId !== null,
    refetchInterval: (query) => {
      if (!pollUntilDone) return false;
      const data = query.state.data;
      // Poll while no report yet
      return data ? false : intervalMs;
    },
    refetchIntervalInBackground: false,
  });
}

export function useOverrideVerdict() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ verdictId, req }: { verdictId: number | string; req: OverrideRequest }) =>
      // api.overrideVerdict signature: (verdictId, body) — verdictId may be a citation_id string
      api.overrideVerdict(verdictId as number, req),
    onSuccess: () => {
      // Invalidate all essay-report queries (we don't know which one)
      qc.invalidateQueries({ queryKey: ['essay-report'] });
    },
  });
}
