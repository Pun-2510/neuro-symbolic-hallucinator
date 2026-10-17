import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type EssaySummary } from '@/api/client';

const ESSAYS_KEY = ['essays'] as const;

export function useEssays() {
  return useQuery({
    queryKey: ESSAYS_KEY,
    queryFn: () => api.listEssays(),
    staleTime: 30_000,
  });
}

export function useDeleteEssay() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteEssay(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ESSAYS_KEY });
    },
  });
}

export type { EssaySummary };
