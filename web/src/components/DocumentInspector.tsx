import { useEffect, useState, useRef } from 'react';
import { FileText, ZoomIn, ZoomOut, ChevronLeft, ChevronRight, Loader2, ExternalLink } from 'lucide-react';
import { api, type AnalysisReport, type Verdict, type ValidationLabel } from '@/api/client';
import { VerdictBadge } from './VerdictBadge';
import { cn } from '@/lib/utils';

/* ============================================================
   SourceLogic — Document Inspector Component
   Based on UX/UI Concept Section 13: Document Inspector
   Shows PDF preview with inline citation status underlines
   ============================================================ */

interface DocumentInspectorProps {
  report: AnalysisReport;
  onCitationClick?: (verdict: Verdict) => void;
  selectedCitation?: Verdict | null;
  className?: string;
}

// Status colors for inline underlines (from UX Section 13)
const STATUS_COLORS: Record<ValidationLabel, { light: string; dark: string }> = {
  verified: { light: 'bg-emerald-500', dark: 'bg-emerald-500' },
  metadata_error: { light: 'bg-amber-500', dark: 'bg-amber-500' },
  suspected_hallucination: { light: 'bg-red-500', dark: 'bg-red-500' },
  unresolved: { light: 'bg-slate-400', dark: 'bg-slate-400' },
};

export function DocumentInspector({
  report,
  onCitationClick,
  selectedCitation,
  className = '',
}: DocumentInspectorProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const containerRef = useRef<HTMLDivElement>(null);

  // Fetch PDF URL
  useEffect(() => {
    const fetchPdf = async () => {
      try {
        setLoading(true);
        // Get PDF from download endpoint
        const url = api.downloadReport(report.essay_id, 'pdf');
        setPdfUrl(url);
        setError(null);
      } catch (e) {
        setError('Failed to load PDF');
      } finally {
        setLoading(false);
      }
    };

    fetchPdf();
  }, [report.essay_id]);

  // Zoom controls
  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.25, 2));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.5));

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        handleZoomIn();
      } else if (e.key === '-') {
        e.preventDefault();
        handleZoomOut();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Get status color for a citation
  const getStatusColor = (verdict: Verdict) => {
    return STATUS_COLORS[verdict.label] || STATUS_COLORS.unresolved;
  };

  // Check if citation is selected
  const isSelected = (verdict: Verdict) => {
    return selectedCitation?.citation_id === verdict.citation_id;
  };

  // Summary stats
  const statusCounts = report.verdicts.reduce(
    (acc, v) => {
      acc[v.label] = (acc[v.label] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900">
            <FileText className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h3 className="font-display text-sm font-semibold text-slate-900 dark:text-slate-100">
              Document Viewer
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {report.filename}
            </p>
          </div>
        </div>

        {/* Zoom controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomOut}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
            title="Zoom out (-)"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="text-xs font-mono text-slate-500 dark:text-slate-400 w-12 text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
            title="Zoom in (+)"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Status legend */}
      <div className="flex items-center gap-4 px-4 py-2 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
        <span className="text-xs text-slate-500 dark:text-slate-400">Legend:</span>
        <div className="flex items-center gap-1">
          <span className="w-8 h-1.5 rounded-full bg-emerald-500" />
          <span className="text-xs text-slate-600 dark:text-slate-400">Verified ({statusCounts.verified || 0})</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-8 h-1.5 rounded-full bg-amber-500" />
          <span className="text-xs text-slate-600 dark:text-slate-400">Metadata Issue ({statusCounts.metadata_error || 0})</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-8 h-1.5 rounded-full bg-red-500" />
          <span className="text-xs text-slate-600 dark:text-slate-400">Hallucination ({statusCounts.suspected_hallucination || 0})</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-8 h-1.5 rounded-full bg-slate-400" />
          <span className="text-xs text-slate-600 dark:text-slate-400">Unverifiable ({statusCounts.unresolved || 0})</span>
        </div>
      </div>

      {/* PDF viewer */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto bg-slate-200 dark:bg-slate-950 p-4"
      >
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 text-indigo-600 dark:text-indigo-400 animate-spin" />
            <span className="ml-3 text-slate-500 dark:text-slate-400">Loading document...</span>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-64 text-slate-500 dark:text-slate-400">
            {error}
          </div>
        ) : pdfUrl ? (
          <div
            className="mx-auto bg-white shadow-2xl transition-transform origin-top"
            style={{ transform: `scale(${zoom})`, width: 'fit-content' }}
          >
            <iframe
              src={pdfUrl}
              className="w-[816px] h-[1056px] border-0"
              title="Document preview"
            />
          </div>
        ) : null}
      </div>

      {/* Citation reference list (collapsible) */}
      <div className="border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <details className="group">
          <summary className="flex items-center justify-between p-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Citations in Document ({report.verdicts.length})
            </span>
            <ChevronLeft className="h-4 w-4 text-slate-400 transition-transform group-open:rotate-[-90deg]" />
          </summary>
          <div className="max-h-48 overflow-y-auto p-3 pt-0 space-y-1">
            {report.verdicts.slice(0, 10).map((verdict, idx) => {
              const colors = getStatusColor(verdict);
              return (
                <button
                  key={verdict.citation_id}
                  onClick={() => onCitationClick?.(verdict)}
                  className={cn(
                    'w-full flex items-start gap-2 p-2 rounded-lg text-left transition-colors hover:bg-slate-50 dark:hover:bg-slate-800',
                    isSelected(verdict) && 'bg-indigo-50 dark:bg-indigo-950'
                  )}
                >
                  <span className={cn('w-1 self-stretch rounded-full shrink-0', colors.light)} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-700 dark:text-slate-300 truncate">
                      {verdict.citation_raw}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <VerdictBadge verdict={verdict.label} size="sm" />
                      <span className="text-xs text-slate-400">
                        #{idx + 1}
                      </span>
                    </div>
                  </div>
                </button>
              );
            })}
            {report.verdicts.length > 10 && (
              <p className="text-xs text-slate-500 dark:text-slate-400 text-center py-2">
                + {report.verdicts.length - 10} more citations
              </p>
            )}
          </div>
        </details>
      </div>
    </div>
  );
}

/* ============================================================
   Inline Citation Marker Component
   For overlaying on document text (future enhancement)
   ============================================================ */

interface CitationMarkerProps {
  verdict: Verdict;
  position: { top: number; left: number; width: number };
  onClick?: () => void;
  isSelected?: boolean;
}

export function CitationMarker({
  verdict,
  position,
  onClick,
  isSelected = false,
}: CitationMarkerProps) {
  const colors = STATUS_COLORS[verdict.label] || STATUS_COLORS.unresolved;

  return (
    <button
      onClick={onClick}
      className={cn(
        'absolute h-5 px-1 rounded cursor-pointer transition-all hover:scale-105',
        colors.light,
        isSelected && 'ring-2 ring-indigo-500 ring-offset-1'
      )}
      style={{
        top: `${position.top}px`,
        left: `${position.left}px`,
        width: `${position.width}px`,
      }}
      title={verdict.citation_raw}
    >
      <span className="text-xs font-mono text-white opacity-75">[{verdict.citation_id}]</span>
    </button>
  );
}
