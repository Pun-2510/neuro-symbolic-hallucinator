import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, type AnalysisReport, type Verdict } from '@/api/client';
import { CISScoreCard } from '@/components/CISScoreCard';
import { StyleProfileCard } from '@/components/StyleProfileCard';
import { CitationGraphView } from '@/components/CitationGraphView';
import { VerdictTable } from '@/components/VerdictTable';
import { CitationDetailDrawer } from '@/components/CitationDetailDrawer';
import { OverrideControls } from '@/components/OverrideControls';

type DisplayMode = 'table' | 'graph';

export function EssayPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Verdict | null>(null);
  const [displayMode, setDisplayMode] = useState<DisplayMode>('graph');

  useEffect(() => {
    if (!id) return;
    api
      .getEssay(Number(id))
      .then(setReport)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed'));
  }, [id]);

  async function handleOverride(verdict: Verdict, req: Parameters<typeof api.overrideVerdict>[1]) {
    const updated = await api.overrideVerdict(Number(id), req);
    setReport((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        verdicts: prev.verdicts.map((v) =>
          v.citation_id === updated.citation_id ? updated : v
        ),
      };
    });
    setSelected(updated);
  }

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
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">{report.filename}</h1>
          <p className="text-sm text-muted-foreground">
            {report.num_pages} trang · {report.num_citations} citation
            {report.style_profile && ` · ${report.style_profile.style}`}
            · Essay ID: {report.essay_id}
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <a
            href={api.downloadReport(report.essay_id, 'json')}
            className="px-3 py-1.5 text-sm border rounded hover:bg-muted flex items-center gap-1"
            download
          >
            Export JSON
          </a>
          <a
            href={api.downloadReport(report.essay_id, 'csv')}
            className="px-3 py-1.5 text-sm border rounded hover:bg-muted flex items-center gap-1"
            download
          >
            Export CSV
          </a>
          <a
            href={api.downloadReport(report.essay_id, 'pdf')}
            className="px-3 py-1.5 text-sm border border-primary rounded hover:bg-primary/5 flex items-center gap-1"
            download
          >
            Export PDF
          </a>
        </div>
      </div>

      {/* CIS Score */}
      <CISScoreCard cis={report.cis} />

      {/* Style Profile (v1.2 new) */}
      {report.style_profile && (
        <StyleProfileCard profile={report.style_profile} />
      )}

      {/* Linking Summary (v1.2 new) */}
      {report.linking_summary && (
        <div className="rounded-lg border p-4 bg-card">
          <h3 className="text-sm font-bold mb-3">Citation Mapping Summary</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            {Object.entries(report.linking_summary).map(([k, v]) => (
              <div key={k} className="flex items-center justify-between p-2 bg-muted rounded">
                <span className="capitalize text-muted-foreground">{k.replace('_', ' ')}</span>
                <span className="font-bold">{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* View mode toggle */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">Citations</h2>
        <div className="flex gap-1 bg-muted rounded-lg p-1">
          {(['graph', 'table'] as DisplayMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => setDisplayMode(mode)}
              className={`px-3 py-1 text-xs rounded-md transition-colors capitalize ${
                displayMode === mode
                  ? 'bg-background shadow-sm font-medium'
                  : 'hover:bg-background/50'
              }`}
            >
              {mode === 'graph' ? 'Graph' : 'Table'}
            </button>
          ))}
        </div>
      </div>

      {/* Citation view */}
      {displayMode === 'graph' ? (
        <CitationGraphView
          verdicts={report.verdicts}
          linkingSummary={report.linking_summary}
          onSelect={setSelected}
          onOverride={handleOverride}
        />
      ) : (
        <VerdictTable
          verdicts={report.verdicts}
          onSelect={setSelected}
          onOverride={handleOverride}
        />
      )}

      {/* Detail drawer */}
      {selected && (
        <CitationDetailDrawer
          verdict={selected}
          onClose={() => setSelected(null)}
          onOverride={(req) => handleOverride(selected, req)}
        />
      )}
    </div>
  );
}
