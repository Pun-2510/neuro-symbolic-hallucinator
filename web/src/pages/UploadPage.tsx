import { useState } from 'react';
import { UploadDropzone } from '@/components/UploadDropzone';
import { api, type UploadResponse, type AnalysisReport } from '@/api/client';
import { CISScoreCard } from '@/components/CISScoreCard';
import { StyleProfileCard } from '@/components/StyleProfileCard';
import { CitationGraphView } from '@/components/CitationGraphView';
import { VerdictTable } from '@/components/VerdictTable';
import { CitationDetailDrawer } from '@/components/CitationDetailDrawer';
import { OverrideControls } from '@/components/OverrideControls';
import { Loader2, FileBarChart, Download, X } from 'lucide-react';

type DisplayMode = 'table' | 'graph';

export function UploadPage() {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [selected, setSelected] = useState<AnalysisReport['verdicts'][number] | null>(null);
  const [displayMode, setDisplayMode] = useState<DisplayMode>('graph');

  async function handleFile(file: File) {
    setUploading(true);
    setError(null);
    setUploadProgress('Đang upload và phân tích PDF...');
    try {
      const result = await api.uploadEssay(file);
      setUploadResult(result);
      setUploadProgress('Đang tải báo cáo chi tiết...');
      setLoadingReport(true);
      // Auto-load full report (không navigate, hiển thị ngay tại trang)
      const fullReport = await api.getEssay(result.essay_id);
      setReport(fullReport);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setUploading(false);
      setLoadingReport(false);
      setUploadProgress('');
    }
  }

  function handleReset() {
    setUploadResult(null);
    setReport(null);
    setSelected(null);
    setError(null);
  }

  async function handleOverride(verdict: AnalysisReport['verdicts'][number], req: Parameters<typeof api.overrideVerdict>[1]) {
    if (!report) return;
    const updated = await api.overrideVerdict(report.essay_id, req);
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

  // If we have a report, show results inline
  if (report) {
    return (
      <div className="space-y-6">
        {/* Success header with reset button */}
        <div className="card-elevated p-5">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-green-100 text-green-600">
                <FileBarChart className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-foreground">
                  ✓ Phân tích hoàn tất: {report.filename}
                </p>
                <p className="text-sm text-muted-foreground">
                  {report.num_pages} trang · {report.num_citations} citation · Essay ID: {report.essay_id}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <a
                href={api.downloadReport(report.essay_id, 'json')}
                className="px-3 py-1.5 text-sm border border-border rounded-xl hover:bg-muted transition-colors flex items-center gap-1"
                download
              >
                <Download className="h-3.5 w-3.5" />
                JSON
              </a>
              <a
                href={api.downloadReport(report.essay_id, 'csv')}
                className="px-3 py-1.5 text-sm border border-border rounded-xl hover:bg-muted transition-colors flex items-center gap-1"
                download
              >
                <Download className="h-3.5 w-3.5" />
                CSV
              </a>
              <a
                href={api.downloadReport(report.essay_id, 'pdf')}
                className="px-3 py-1.5 text-sm border border-primary rounded-xl hover:bg-primary/5 transition-colors flex items-center gap-1"
                download
              >
                <Download className="h-3.5 w-3.5" />
                PDF
              </a>
              <button
                onClick={handleReset}
                className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
                title="Upload essay khác"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
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
          <div className="rounded-lg border border-border/50 p-4 bg-card">
            <h3 className="text-sm font-bold mb-3">Citation Mapping Summary</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              {Object.entries(report.linking_summary).map(([k, v]) => (
                <div
                  key={k}
                  className="flex items-center justify-between p-2 bg-muted rounded-lg"
                >
                  <span className="capitalize text-muted-foreground">
                    {k.replace(/_/g, ' ')}
                  </span>
                  <span className="font-bold">{v}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* View mode toggle */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-foreground">Citations</h2>
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

  // Default: Upload form
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Upload Essay PDF</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Hệ thống sẽ trích xuất citations, tra cứu qua 4 nguồn (Crossref,
          OpenAlex, Semantic Scholar, arXiv), gán nhãn 4 loại, và tính Citation
          Integrity Score.
        </p>
      </div>

      <UploadDropzone onFile={handleFile} disabled={uploading} />

      {uploading && (
        <div className="card-elevated p-4 flex items-center gap-3">
          <Loader2 className="h-5 w-5 text-primary animate-spin" />
          <p className="text-sm text-foreground">{uploadProgress}</p>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          <strong>Lỗi:</strong> {error}
        </div>
      )}

      <div className="card-elevated p-5 text-sm">
        <h3 className="font-semibold mb-3 text-foreground">4 nhãn citation:</h3>
        <ul className="space-y-2 text-muted-foreground">
          <li className="flex items-start gap-2">
            <span className="verdict-badge bg-verdict_verified shrink-0 mt-0.5">✓</span>
            <span>
              <strong className="text-foreground">Verified</strong> — nguồn có thật, metadata khớp
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="verdict-badge bg-verdict_metadata_error shrink-0 mt-0.5">△</span>
            <span>
              <strong className="text-foreground">Metadata error</strong> — nguồn có thật nhưng 1+ trường sai
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="verdict-badge bg-verdict_suspected shrink-0 mt-0.5">✗</span>
            <span>
              <strong className="text-foreground">Suspected hallucination</strong> — không tìm thấy ở 4 nguồn
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="verdict-badge bg-verdict_unresolved shrink-0 mt-0.5">?</span>
            <span>
              <strong className="text-foreground">Unresolved</strong> — chưa đủ bằng chứng
            </span>
          </li>
        </ul>
      </div>
    </div>
  );
}
