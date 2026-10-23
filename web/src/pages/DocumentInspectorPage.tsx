import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { type Verdict } from '@/api/client';
import { VerdictBadge } from '@/components/VerdictBadge';
import { MappingStatusBadge } from '@/components/MappingStatusBadge';
import { getVerdictExplanation, isUrlResource } from '@/lib/verdictExplanation';
import { useEssayPolling } from '@/hooks/useEssayPolling';
import { EssayHeader } from './essay/EssayHeader';
import { EssayActionBar } from './essay/EssayActionBar';
import {
  Loader2,
  AlertCircle,
  FileText,
  Quote,
  AlertTriangle,
  ExternalLink,
  BookOpen,
  CheckCircle,
  XCircle,
  Link2,
  Terminal,
  Filter,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

/* ============================================================
   SourceLogic — Document Inspector Page (Scholarly Precision v2.0)
   Interactive Citation Debugger IDE — Inline Context Stream
   ============================================================ */

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
  context?: string;
}

function ContextWithHighlight({
  context,
  marker,
}: {
  context: string;
  marker: string;
}) {
  if (!context) return null;
  const lowerContext = context.toLowerCase();
  const lowerMarker = marker.toLowerCase();
  const idx = lowerContext.indexOf(lowerMarker);
  if (idx === -1) {
    return <>{context}</>;
  }
  const before = context.slice(0, idx);
  const match = context.slice(idx, idx + marker.length);
  const after = context.slice(idx + marker.length);
  return (
    <>
      {before}
      <mark className="bg-amber-200/80 dark:bg-amber-900/60 text-inherit rounded px-1 py-0.5 font-medium">
        {match}
      </mark>
      {after}
    </>
  );
}

function buildInlineCitations(verdicts: Verdict[]): InlineCitation[] {
  return verdicts.map((v) => ({
    id: v.citation_id,
    raw: v.citation_raw,
    label: isUrlResource(v) ? 'resource' : v.label,
    mapping_status: v.mapping_status,
    page: 1,
    line: v.citation_raw,
    context: v.context,
  }));
}

function getInlineStatusBadge(label: string): {
  bg: string;
  text: string;
  label: string;
  icon: React.ReactNode;
} {
  switch (label) {
    case 'verified':
      return {
        bg: 'bg-emerald-100/90 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-200/80 dark:border-emerald-800/80',
        text: 'text-emerald-700 dark:text-emerald-300',
        label: 'Verified',
        icon: <CheckCircle className="h-3 w-3" />,
      };
    case 'metadata_error':
      return {
        bg: 'bg-amber-100/90 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 border border-amber-200/80 dark:border-amber-800/80',
        text: 'text-amber-700 dark:text-amber-300',
        label: 'Meta Error',
        icon: <AlertTriangle className="h-3 w-3" />,
      };
    case 'suspected_hallucination':
      return {
        bg: 'bg-red-100/90 dark:bg-red-950/80 text-red-700 dark:text-red-300 border border-red-200/80 dark:border-red-800/80',
        text: 'text-red-700 dark:text-red-300',
        label: 'Suspected',
        icon: <XCircle className="h-3 w-3" />,
      };
    case 'resource':
      return {
        bg: 'bg-violet-100/90 dark:bg-violet-950/80 text-violet-700 dark:text-violet-300 border border-violet-200/80 dark:border-violet-800/80',
        text: 'text-violet-700 dark:text-violet-300',
        label: 'URL Resource',
        icon: <Link2 className="h-3 w-3" />,
      };
    default:
      return {
        bg: 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700',
        text: 'text-slate-700 dark:text-slate-300',
        label: 'Unverifiable',
        icon: <AlertTriangle className="h-3 w-3" />,
      };
  }
}

function InlineCitationMarker({
  citation,
  onClick,
}: {
  citation: InlineCitation;
  onClick?: () => void;
}) {
  const status = getInlineStatusBadge(citation.label);
  const underlineColor =
    UNDERLINE_COLORS[citation.label as keyof typeof UNDERLINE_COLORS] ||
    UNDERLINE_COLORS.unresolved;

  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border-b-2 ${underlineColor} ${status.bg} hover:opacity-85 transition-all text-xs font-mono font-medium shadow-2xs`}
      title={`[${citation.label}] ${citation.raw}`}
    >
      <span className="max-w-[160px] truncate">{citation.raw}</span>
      <span className="shrink-0">{status.icon}</span>
    </button>
  );
}

function CitationPopup({
  essayId,
  citation,
  verdict,
  onClose,
}: {
  essayId: string;
  citation: InlineCitation;
  verdict: Verdict | null;
  onClose: () => void;
}) {
  const status = getInlineStatusBadge(citation.label);

  return (
    <div
      className="fixed inset-0 bg-slate-950/50 backdrop-blur-xs z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3.5 bg-slate-50/90 dark:bg-slate-900/90 border-b border-slate-200/80 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-400/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80" />
            </div>
            <Separator orientation="vertical" className="h-4" />
            <Quote className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
            <span className="text-xs font-mono font-semibold text-slate-700 dark:text-slate-200">
              citation_inspector.modal
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            aria-label="Close modal"
          >
            <XCircle className="h-4 w-4" />
          </button>
        </div>

        <div className={`px-6 py-3.5 border-b border-slate-200/60 dark:border-slate-800 ${status.bg}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              {status.icon}
              <div>
                <h3 className={`text-sm font-semibold ${status.text}`}>Citation Detail</h3>
                <p className={`text-xs font-mono ${status.text} opacity-85`}>{status.label}</p>
              </div>
            </div>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-white/60 dark:bg-slate-900/60 text-slate-700 dark:text-slate-300">
              ID: {citation.id}
            </span>
          </div>
        </div>

        <div className="p-6 space-y-4">
          <div className="min-w-0 flex-1">
            <label className="text-[11px] font-mono font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              In-text Citation
            </label>
            <p className="mt-1.5 text-sm text-slate-900 dark:text-slate-100 font-medium font-serif p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/70">
              {citation.raw}
            </p>
          </div>

          <div className="flex flex-wrap gap-4">
            <div>
              <label className="text-[11px] font-mono font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Verification
              </label>
              <div className="mt-1.5">
                <VerdictBadge verdict={citation.label} size="sm" />
              </div>
            </div>
            <div>
              <label className="text-[11px] font-mono font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Mapping
              </label>
              <div className="mt-1.5">
                <MappingStatusBadge status={citation.mapping_status as any} size="sm" />
              </div>
            </div>
          </div>

          {verdict && (
            <>
              <div>
                <label className="text-[11px] font-mono font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  What we found
                </label>
                <p className="mt-1 text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {getVerdictExplanation(verdict)}
                </p>
              </div>

              <div>
                <label className="text-[11px] font-mono font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Confidence
                </label>
                <div className="mt-2 flex items-center gap-3">
                  <Progress
                    value={verdict.confidence * 100}
                    className="flex-1 h-2"
                    indicatorClassName={
                      verdict.confidence >= 0.8
                        ? 'bg-emerald-500'
                        : verdict.confidence >= 0.5
                        ? 'bg-amber-500'
                        : 'bg-red-500'
                    }
                  />
                  <span className="text-xs font-mono font-semibold text-slate-700 dark:text-slate-300">
                    {(verdict.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {verdict.mismatched_fields.length > 0 && (
                <div>
                  <label className="text-[11px] font-mono font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Mismatched Fields
                  </label>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {verdict.mismatched_fields.map((field) => (
                      <Badge
                        key={field}
                        variant="metadata_error"
                        className="px-2 py-0.5 rounded text-xs font-mono"
                      >
                        {field}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {verdict.triggered_rules.length > 0 && (
                <div>
                  <label className="text-[11px] font-mono font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Triggered Rules
                  </label>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {verdict.triggered_rules.map((rule) => (
                      <Badge
                        key={rule}
                        variant="outline"
                        className="px-2 py-0.5 bg-indigo-50 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800 rounded text-xs font-mono"
                      >
                        {rule}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <Link
              to={`/verification/report/${essayId}`}
              className="inline-flex items-center gap-1.5 text-xs font-mono font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              View full report
            </Link>
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function DocumentInspectorPage() {
  const { id } = useParams<{ id: string }>();
  const [selectedCitation, setSelectedCitation] = useState<InlineCitation | null>(null);
  const [selectedVerdict, setSelectedVerdict] = useState<Verdict | null>(null);
  const [filterLabel, setFilterLabel] = useState<string>('all');

  const numericId = id ? parseInt(id, 10) : null;
  const { report, error } = useEssayPolling(
    numericId !== null && !Number.isNaN(numericId) && numericId > 0 ? numericId : null,
    { errorMessage: 'Failed to load document. Please try again.' },
  );

  const inlineCitations = report ? buildInlineCitations(report.verdicts) : [];

  const filteredCitations =
    filterLabel === 'all'
      ? inlineCitations
      : inlineCitations.filter((c) => c.label === filterLabel);

  useEffect(() => {
    if (selectedCitation && report) {
      const verdict = report.verdicts.find(
        (v) => v.citation_id === selectedCitation.id
      );
      setSelectedVerdict(verdict || null);
    }
  }, [selectedCitation, report]);

  const statusCounts = {
    verified: inlineCitations.filter((c) => c.label === 'verified').length,
    metadata_error: inlineCitations.filter((c) => c.label === 'metadata_error').length,
    suspected_hallucination: inlineCitations.filter((c) => c.label === 'suspected_hallucination').length,
    unresolved: inlineCitations.filter((c) => c.label === 'unresolved').length,
  };

  if (error) {
    return (
      <Alert variant="destructive" className="card p-6 rounded-2xl">
        <AlertCircle className="h-5 w-5" />
        <AlertTitle className="font-medium">Error: {error}</AlertTitle>
        <AlertDescription>
          <Link
            to="/history"
            className="text-indigo-600 dark:text-indigo-400 hover:underline mt-2 inline-block"
          >
            ← Back to Reports
          </Link>
        </AlertDescription>
      </Alert>
    );
  }

  if (!report) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 text-indigo-600 dark:text-indigo-400 animate-spin" />
        <span className="ml-3 text-slate-600 dark:text-slate-300 font-mono text-sm">
          Loading document...
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-10">
      {/* Shared Report Header */}
      <EssayHeader
        essayId={report.essay_id}
        filename={report.filename}
        numPages={report.num_pages}
        numCitations={report.num_citations}
        styleName={report.style_profile?.style}
      />

      {/* Shared Multi-Tab Diagnostic Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <EssayActionBar essayId={id ?? ''} />
        <div className="flex items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400">
          <BookOpen className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          <span>
            Document Inspector · {report.num_pages} pages · {inlineCitations.length} citations
          </span>
        </div>
      </div>

      {/* Architectural Inline Status Legend & Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <div className="w-3 h-1 rounded-full bg-emerald-500" />
              <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                Verified ({statusCounts.verified})
              </span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/80 text-emerald-600 dark:text-emerald-400">
              01
            </span>
          </div>
          <p className="text-2xl font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400">
            {statusCounts.verified}
          </p>
        </Card>

        <Card className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <div className="w-3 h-1 rounded-full bg-amber-500" />
              <span className="text-xs font-medium text-amber-600 dark:text-amber-400">
                Meta Error ({statusCounts.metadata_error})
              </span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950/80 text-amber-600 dark:text-amber-400">
              02
            </span>
          </div>
          <p className="text-2xl font-bold font-mono tabular-nums text-amber-600 dark:text-amber-400">
            {statusCounts.metadata_error}
          </p>
        </Card>

        <Card className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <div className="w-3 h-1 rounded-full bg-red-500" />
              <span className="text-xs font-medium text-red-600 dark:text-red-400">
                Suspected ({statusCounts.suspected_hallucination})
              </span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-50 dark:bg-red-950/80 text-red-600 dark:text-red-400">
              03
            </span>
          </div>
          <p className="text-2xl font-bold font-mono tabular-nums text-red-600 dark:text-red-400">
            {statusCounts.suspected_hallucination}
          </p>
        </Card>

        <Card className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <div className="w-3 h-1 rounded-full bg-slate-400" />
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                Unverifiable ({statusCounts.unresolved})
              </span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              04
            </span>
          </div>
          <p className="text-2xl font-bold font-mono tabular-nums text-slate-700 dark:text-slate-200">
            {statusCounts.unresolved}
          </p>
        </Card>
      </div>

      {/* Main IDE Container */}
      <div className="rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
        {/* IDE Top Chrome & Filter Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 bg-slate-50/90 dark:bg-slate-900/90 border-b border-slate-200/80 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-400/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80" />
            </div>
            <Separator orientation="vertical" className="h-4" />
            <Terminal className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
            <span className="text-xs font-mono font-semibold text-slate-700 dark:text-slate-200">
              document_inspector.tei
            </span>
          </div>

          {/* Filter controls */}
          <div className="flex flex-wrap items-center gap-1.5">
            <Filter className="h-3.5 w-3.5 text-slate-400 mr-1" />
            <button
              onClick={() => setFilterLabel('all')}
              className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-all ${
                filterLabel === 'all'
                  ? 'bg-indigo-600 text-white shadow-2xs'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              All ({inlineCitations.length})
            </button>
            {Object.entries(statusCounts).map(([label, count]) => (
              <button
                key={label}
                onClick={() => setFilterLabel(label)}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-all ${
                  filterLabel === label
                    ? 'bg-indigo-600 text-white shadow-2xs'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                }`}
              >
                {label.replace(/_/g, ' ')} ({count})
              </button>
            ))}
          </div>
        </div>

        {/* Dual-Pane Document & Citation List View */}
        <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-slate-200/80 dark:divide-slate-800">
          {/* Document panel */}
          <div className="lg:col-span-7 p-6">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100 dark:border-slate-800/80">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                <h3 className="font-display text-base font-semibold text-slate-900 dark:text-slate-100">
                  Document View
                </h3>
              </div>
              <span className="text-[11px] font-mono text-slate-400">
                Inline Context Stream
              </span>
            </div>

            <div className="prose prose-slate dark:prose-invert max-w-none">
              <div className="space-y-4 text-sm leading-relaxed max-h-[540px] overflow-y-auto pr-2">
                {filteredCitations.length === 0 ? (
                  <p className="text-slate-500 dark:text-slate-400 italic py-8 text-center font-mono text-xs">
                    No citations match the current filter.
                  </p>
                ) : (
                  filteredCitations.map((citation, idx) => (
                    <div
                      key={citation.id}
                      className={`group relative rounded-xl p-3.5 border transition-colors ${
                        selectedCitation?.id === citation.id
                          ? 'bg-indigo-50/60 dark:bg-indigo-950/30 border-indigo-300 dark:border-indigo-700'
                          : 'bg-slate-50/60 dark:bg-slate-800/30 border-slate-200/70 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <span className="text-[11px] font-mono text-slate-400 dark:text-slate-500 shrink-0 pt-0.5 select-none">
                          p{citation.page}:{String(idx + 1).padStart(2, '0')}
                        </span>
                        <p className="flex-1 text-slate-700 dark:text-slate-300 font-serif leading-relaxed">
                          {citation.context ? (
                            <>
                              <ContextWithHighlight
                                context={citation.context}
                                marker={citation.raw}
                              />{' '}
                              <InlineCitationMarker
                                citation={citation}
                                onClick={() => setSelectedCitation(citation)}
                              />
                            </>
                          ) : (
                            <>
                              <span className="text-slate-500 dark:text-slate-400 italic font-sans text-xs">
                                [No surrounding text extracted]
                              </span>{' '}
                              <InlineCitationMarker
                                citation={citation}
                                onClick={() => setSelectedCitation(citation)}
                              />
                            </>
                          )}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Citation list panel */}
          <div className="lg:col-span-5 p-6 bg-slate-50/30 dark:bg-slate-900/40">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100 dark:border-slate-800/80">
              <div className="flex items-center gap-2">
                <Quote className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                <h3 className="font-display text-base font-semibold text-slate-900 dark:text-slate-100">
                  Citation List
                </h3>
              </div>
              <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                {filteredCitations.length} citations
              </span>
            </div>

            <div className="space-y-2.5 max-h-[540px] overflow-y-auto pr-1">
              {filteredCitations.map((citation, index) => {
                const status = getInlineStatusBadge(citation.label);
                return (
                  <button
                    key={citation.id}
                    onClick={() => setSelectedCitation(citation)}
                    className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                      selectedCitation?.id === citation.id
                        ? 'bg-indigo-50/90 dark:bg-indigo-950/60 border-indigo-300 dark:border-indigo-700 shadow-2xs'
                        : 'bg-white dark:bg-slate-900 border-slate-200/80 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-700'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-xs font-mono font-semibold text-slate-400 dark:text-slate-500 shrink-0 pt-0.5">
                        [{String(index + 1).padStart(2, '0')}]
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-serif text-slate-800 dark:text-slate-200 line-clamp-2">
                          {citation.raw}
                        </p>
                        <div className="flex items-center gap-2 mt-2 flex-wrap">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-medium ${status.bg}`}
                          >
                            {status.icon}
                            {status.label}
                          </span>
                          <MappingStatusBadge
                            status={citation.mapping_status as any}
                            size="sm"
                          />
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {selectedCitation && (
        <CitationPopup
          essayId={id ?? ''}
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
