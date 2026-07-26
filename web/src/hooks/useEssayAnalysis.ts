import { useEffect, useState } from 'react';
import { api, type AnalysisReport } from '@/api/client';

/**
 * Hook poll để fetch analysis report — dùng cho async upload.
 *
 * TODO: implement polling khi backend hỗ trợ async analysis.
 */
export function useEssayAnalysis(essayId: number | null) {
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!essayId) return;
    setLoading(true);
    api
      .getEssay(essayId)
      .then(setReport)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed'))
      .finally(() => setLoading(false));
  }, [essayId]);

  return { report, loading, error };
}