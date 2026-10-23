import { useQuery } from '@tanstack/react-query';
import { api, type AnalysisReport } from '@/api/client';

export function useOrphanReport(essayId: number | null) {
  return useQuery({
    queryKey: ['orphan-report', essayId],
    queryFn: () => {
      if (essayId === null) throw new Error('essayId required');
      return api.getEssay(essayId);
    },
    enabled: essayId !== null,
    staleTime: 60_000,
    refetchInterval: (query) => (query.state.data === null ? 3000 : false),
  });
}

export type { AnalysisReport };
