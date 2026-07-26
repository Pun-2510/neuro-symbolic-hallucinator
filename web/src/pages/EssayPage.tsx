import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, type AnalysisReport, type Verdict } from '@/api/client';
import { VerdictTable } from '@/components/VerdictTable';
import { CISScoreCard } from '@/components/CISScoreCard';

export function EssayPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .getEssay(Number(id))
      .then(setReport)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed'));
  }, [id]);

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded text-sm text-red-700">
        Lỗi: {error}
        <Link to="/" className="ml-3 underline">
          ← Quay lại
        </Link>
      </div>
    );
  }
  if (!report) {
    return <p className="text-muted-foreground">Đang tải...</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{report.filename}</h1>
          <p className="text-sm text-muted-foreground">
            {report.num_pages} trang · {report.num_citations} citation · Essay
            ID: {report.essay_id}
          </p>
        </div>
        <div className="flex gap-2">
          <a
            href={api.downloadReport(report.essay_id, 'json')}
            className="px-3 py-1 text-sm border rounded hover:bg-muted"
            download
          >
            Export JSON
          </a>
          <a
            href={api.downloadReport(report.essay_id, 'csv')}
            className="px-3 py-1 text-sm border rounded hover:bg-muted"
            download
          >
            Export CSV
          </a>
        </div>
      </div>

      <CISScoreCard cis={report.cis} />

      <div>
        <h2 className="text-lg font-bold mb-3">Verdicts</h2>
        <VerdictTable verdicts={report.verdicts} />
      </div>
    </div>
  );
}