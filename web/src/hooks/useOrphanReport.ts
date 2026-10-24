import { useQuery } from '@tanstack/react-query';
import { api, type AnalysisReport } from '@/api/client';

export function useOrphanReport(essayId: number | null) {
  return useQuery({
    queryKey: ['essay-report', essayId],
    queryFn: async () => {
      if (essayId === null) throw new Error('essayId required');
      const report = await api.getEssay(essayId);
      if (report !== null) {
        return report;
      }
      const status = await api.getEssayStatus(essayId);
      if (status.status === 'failed') {
        throw new Error(status.error || 'Essay processing failed');
      }
      return null;
    },
    enabled: essayId !== null,
    staleTime: 60_000,
    refetchInterval: (query) => {
      if (query.state.status === 'error') return false;
      return query.state.data === null ? 3000 : false;
    },
  });
}

export type { AnalysisReport };
