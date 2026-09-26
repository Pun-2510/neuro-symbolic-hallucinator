import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, type AnalysisReport, type Verdict } from '@/api/client';
import { VerdictBadge } from '@/components/VerdictBadge';
import { MappingStatusBadge } from '@/components/MappingStatusBadge';
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  FileText,
  Quote,
  AlertTriangle,
  ExternalLink,
  BookOpen,
  CheckCircle,
  XCircle,
} from 'lucide-react';

/* ============================================================
   SourceLogic — Document Inspector Page
   Based on UX/UI Concept Section 13: Document Inspector
   Shows document with inline verification status for citations
   ============================================================ */

// Color mapping for inline verification status
const UNDERLINE_COLORS = {
  verified: 'border-emerald-500 dark:border-emerald-400',
  metadata_error: 'border-amber-500 dark:border-amber-400',
  suspected_hallucination: 'border-red-500 dark:border-red-400',
  unresolved: 'border-slate-400 dark:border-slate-500',
};

interface InlineCitation {
  id: string;
  raw: string;
  label: string;
  mapping_status: string;
  page: number;
  line: string;
}

// Build inline citations from verdict data
function buildInlineCitations(verdicts: Verdict[]): InlineCitation[] {
  return verdicts.map((v) => ({
    id: v.citation_id,
    raw: v.citation_raw,
    label: v.label,
    mapping_status: v.mapping_status,
    page: 1, // Default page, would need from actual extraction
    line: v.citation_raw,
  }));
}

// Get inline status badge
function getInlineStatusBadge(label: string): {
  bg: string;
  text: string;
  label: string;
  icon: React.ReactNode;
} {
  switch (label) {
    case 'verified':
      return {
        bg: 'bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300',
        text: 'text-emerald-700 dark:text-emerald-300',
        label: 'Verified',
        icon: <CheckCircle className="h-3 w-3" />,
      };
    case 'metadata_error':
      return {
        bg: 'bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300',
        text: 'text-amber-700 dark:text-amber-300',
        label: 'Meta Error',
        icon: <AlertTriangle className="h-3 w-3" />,
      };
    case 'suspected_hallucination':
      return {
        bg: 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300',
        text: 'text-red-700 dark:text-red-300',
        label: 'Suspected',
        icon: <XCircle className="h-3 w-3" />,
      };
    default:
      return {
        bg: 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300',
        text: 'text-slate-700 dark:text-slate-300',
        label: 'Unverifiable',
        icon: <AlertTriangle className="h-3 w-3" />,
      };
  }
}

// Inline citation marker component
function InlineCitationMarker({
  citation,
  onClick,
}: {
  citation: InlineCitation;
  onClick?: () => void;
}) {
  const status = getInlineStatusBadge(citation.label);
  const underlineColor = UNDERLINE_COLORS[citation.label as keyof typeof UNDERLINE_COLORS] || UNDERLINE_COLORS.unresolved;

  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border-b-2 ${underlineColor} ${status.bg} hover:opacity-80 transition-opacity text-xs font-medium`}
      title={`[${citation.label}] ${citation.raw}`}
    >
      <span className="max-w-[150px] truncate">{citation.raw}</span>
      <span className="shrink-0">{status.icon}</span>
    </button>
  );
}

// Citation detail popup
function CitationPopup({
  citation,
  verdict,
  onClose,
}: {
  citation: InlineCitation;
  verdict: Verdict | null;
  onClose: () => void;
}) {
  const status = getInlineStatusBadge(citation.label);

  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50"
      onClick={onClose}
    >
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-white dark:bg-slate-900 rounded-2xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`px-6 py-4 ${status.bg}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white/20 rounded-lg">
                <Quote className="h-5 w-5" />
              </div>
              <div>
                <h3 className={`font-semibold ${status.text}`}>Citation Detail</h3>
                <p className={`text-sm ${status.text} opacity-80`}>{status.label}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors"
            >
              <XCircle className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Citation raw text */}
          <div>
            <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
              In-text Citation
            </label>
            <p className="mt-1 text-sm text-slate-900 dark:text-slate-100 font-medium">
              {citation.raw}
            </p>
          </div>

          {/* Status badges */}
          <div className="flex flex-wrap gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Verification
              </label>
              <div className="mt-1">
                <VerdictBadge verdict={citation.label} size="sm" />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Mapping
              </label>
              <div className="mt-1">
                <MappingStatusBadge status={citation.mapping_status as any} size="sm" />
              </div>
            </div>
          </div>

          {/* Verdict details */}
          {verdict && (
            <>
              {/* Reasoning */}
              {verdict.reasoning && (
                <div>
                  <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                    Reasoning
                  </label>
                  <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">
                    {verdict.reasoning}
                  </p>
                </div>
              )}

              {/* Confidence */}
              <div>
                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  Confidence
                </label>
                <div className="mt-2 flex items-center gap-3">
                  <div className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        verdict.confidence >= 0.8
                          ? 'bg-emerald-500'
                          : verdict.confidence >= 0.5
                          ? 'bg-amber-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${verdict.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
                    {(verdict.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Mismatched fields */}
              {verdict.mismatched_fields.length > 0 && (
                <div>
                  <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                    Mismatched Fields
                  </label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {verdict.mismatched_fields.map((field) => (
                      <span
                        key={field}
                        className="px-2 py-1 bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded text-xs font-medium"
                      >
                        {field}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Triggered rules */}
              {verdict.triggered_rules.length > 0 && (
                <div>
                  <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                    Triggered Rules
                  </label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {verdict.triggered_rules.map((rule) => (
                      <span
                        key={rule}
                        className="px-2 py-1 bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 rounded text-xs font-mono"
                      >
                        {rule}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Navigation link */}
          <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
            <Link
              to={`/verification/report/${citation.id}`}
              className="inline-flex items-center gap-2 text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
            >
              <ExternalLink className="h-4 w-4" />
              View full report
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   Main DocumentInspectorPage Component
   ============================================================ */

export function DocumentInspectorPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<InlineCitation | null>(null);
  const [selectedVerdict, setSelectedVerdict] = useState<Verdict | null>(null);
  const [filterLabel, setFilterLabel] = useState<string>('all');

  useEffect(() => {
    if (!id) return;
    api
      .getEssay(Number(id))
      .then(setReport)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed'));
  }, [id]);

  // Build inline citations
  const inlineCitations = report ? buildInlineCitations(report.verdicts) : [];

  // Filter citations
  const filteredCitations =
    filterLabel === 'all'
      ? inlineCitations
      : inlineCitations.filter((c) => c.label === filterLabel);

  // Get selected verdict
  useEffect(() => {
    if (selectedCitation && report) {
      const verdict = report.verdicts.find(
        (v) => v.citation_id === selectedCitation.id
      );
      setSelectedVerdict(verdict || null);
    }
  }, [selectedCitation, report]);

  // Count by status
  const statusCounts = {
    verified: inlineCitations.filter((c) => c.label === 'verified').length,
    metadata_error: inlineCitations.filter((c) => c.label === 'metadata_error')
      .length,
    suspected_hallucination: inlineCitations.filter(
      (c) => c.label === 'suspected_hallucination'
    ).length,
    unresolved: inlineCitations.filter((c) => c.label === 'unresolved').length,
  };

  if (error) {
    return (
      <div className="card p-6 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-red-700 dark:text-red-300">Error: {error}</p>
            <Link
              to="/history"
              className="text-indigo-600 dark:text-indigo-400 hover:underline mt-2 inline-block"
            >
              ← Back to Reports
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 text-indigo-600 dark:text-indigo-400 animate-spin" />
        <span className="ml-3 text-slate-600 dark:text-slate-400">
          Loading document...
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          to={`/verification/report/${id}`}
          className="inline-flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 mb-3 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Report
        </Link>
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-slate-100">
              Document Inspector
            </h1>
            <p className="text-slate-500 dark:text-slate-400 mt-1">
              {report.filename}
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
            <BookOpen className="h-5 w-5" />
            <span>
              {report.num_pages} pages · {inlineCitations.length} citations
            </span>
          </div>
        </div>
      </div>

      {/* Status legend */}
      <div className="card p-4">
        <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">
          Inline Status Legend
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-emerald-500" />
            <span className="text-sm text-slate-600 dark:text-slate-400">
              Verified ({statusCounts.verified})
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-amber-500" />
            <span className="text-sm text-slate-600 dark:text-slate-400">
              Meta Error ({statusCounts.metadata_error})
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-red-500" />
            <span className="text-sm text-slate-600 dark:text-slate-400">
              Suspected ({statusCounts.suspected_hallucination})
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-slate-400" />
            <span className="text-sm text-slate-600 dark:text-slate-400">
              Unverifiable ({statusCounts.unresolved})
            </span>
          </div>
        </div>
      </div>

      {/* Filter controls */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setFilterLabel('all')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            filterLabel === 'all'
              ? 'bg-indigo-600 text-white'
              : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
          }`}
        >
          All ({inlineCitations.length})
        </button>
        {Object.entries(statusCounts).map(([label, count]) => (
          <button
            key={label}
            onClick={() => setFilterLabel(label)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              filterLabel === label
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            {label.replace(/_/g, ' ')} ({count})
          </button>
        ))}
      </div>

      {/* Document view with inline citations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Document panel */}
        <div className="card p-6 bg-white dark:bg-slate-800">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            <h3 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100">
              Document View
            </h3>
          </div>

          {/* Simulated document content with inline markers */}
          <div className="prose prose-slate dark:prose-invert max-w-none">
            <div className="space-y-4 text-sm leading-relaxed">
              {filteredCitations.length === 0 ? (
                <p className="text-slate-500 dark:text-slate-400 italic">
                  No citations match the current filter.
                </p>
              ) : (
                filteredCitations.map((citation, index) => (
                  <div key={citation.id} className="relative">
                    {/* Page indicator */}
                    <span className="absolute -left-8 text-xs text-slate-400 dark:text-slate-500">
                      p{citation.page}
                    </span>
                    {/* Citation with inline marker */}
                    <p className="pl-6">
                      Recent studies in machine learning have explored various
                      approaches to natural language processing{' '}
                      <InlineCitationMarker
                        citation={citation}
                        onClick={() => setSelectedCitation(citation)}
                      />{' '}
                      demonstrating significant improvements in performance
                      benchmarks.
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Citation list panel */}
        <div className="card p-6 bg-white dark:bg-slate-800">
          <div className="flex items-center gap-2 mb-4">
            <Quote className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            <h3 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100">
              Citation List
            </h3>
            <span className="ml-auto text-sm text-slate-500 dark:text-slate-400">
              {filteredCitations.length} citations
            </span>
          </div>

          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {filteredCitations.map((citation, index) => {
              const status = getInlineStatusBadge(citation.label);
              return (
                <button
                  key={citation.id}
                  onClick={() => setSelectedCitation(citation)}
                  className={`w-full text-left p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600 transition-colors ${
                    selectedCitation?.id === citation.id
                      ? 'bg-indigo-50 dark:bg-indigo-950 border-indigo-300 dark:border-indigo-700'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-xs font-mono text-slate-500 dark:text-slate-400 shrink-0">
                      [{index + 1}]
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-700 dark:text-slate-300 line-clamp-2">
                        {citation.raw}
                      </p>
                      <div className="flex items-center gap-2 mt-2">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${status.bg}`}
                        >
                          {status.icon}
                          {status.label}
                        </span>
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Citation detail popup */}
      {selectedCitation && (
        <CitationPopup
          citation={selectedCitation}
          verdict={selectedVerdict}
          onClose={() => {
            setSelectedCitation(null);
            setSelectedVerdict(null);
          }}
        />
      )}
    </div>
  );
}
