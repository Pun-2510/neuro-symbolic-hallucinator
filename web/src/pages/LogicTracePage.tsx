import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, type AnalysisReport, type Verdict } from '@/api/client';
import { RuleInspector, RuleInspectorCompact } from '@/components/RuleInspector';
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  GitBranch,
  Shield,
  Search,
  Database,
  CheckCircle,
  XCircle,
  HelpCircle,
  ChevronRight,
  FileText,
  Quote,
  Scale,
} from 'lucide-react';

/* ============================================================
   SourceLogic — Logic Trace Page
   Based on UX/UI Concept Section 14: Logic Trace
   Shows step-by-step verification trace for each citation
   ============================================================ */

// Trace step types
type TraceStepStatus = 'pending' | 'active' | 'completed' | 'error';

interface TraceStep {
  id: string;
  label: string;
  description?: string;
  status: TraceStepStatus;
  detail?: string;
  data?: Record<string, unknown>;
}

// Get status color
function getStepStatusColor(status: TraceStepStatus): {
  bg: string;
  border: string;
  icon: React.ReactNode;
  text: string;
} {
  switch (status) {
    case 'completed':
      return {
        bg: 'bg-emerald-50 dark:bg-emerald-950',
        border: 'border-emerald-300 dark:border-emerald-700',
        icon: <CheckCircle className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />,
        text: 'text-emerald-700 dark:text-emerald-300',
      };
    case 'active':
      return {
        bg: 'bg-indigo-50 dark:bg-indigo-950',
        border: 'border-indigo-300 dark:border-indigo-700',
        icon: <Loader2 className="h-5 w-5 text-indigo-600 dark:text-indigo-400 animate-spin" />,
        text: 'text-indigo-700 dark:text-indigo-300',
      };
    case 'error':
      return {
        bg: 'bg-red-50 dark:bg-red-950',
        border: 'border-red-300 dark:border-red-700',
        icon: <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />,
        text: 'text-red-700 dark:text-red-300',
      };
    default:
      return {
        bg: 'bg-slate-50 dark:bg-slate-800',
        border: 'border-slate-200 dark:border-slate-700',
        icon: <HelpCircle className="h-5 w-5 text-slate-400" />,
        text: 'text-slate-500 dark:text-slate-400',
      };
  }
}

// Build trace steps for a verdict
function buildTraceSteps(verdict: Verdict): TraceStep[] {
  const steps: TraceStep[] = [
    {
      id: 'parse',
      label: 'Reference Parsed',
      description: 'Extracted from bibliography',
      status: 'completed',
      detail: verdict.citation_raw,
    },
    {
      id: 'search',
      label: 'Academic Search',
      description: 'Querying 4 academic databases',
      status: verdict.matched_sources.length > 0 ? 'completed' : 'pending',
      data: {
        sources: verdict.matched_sources.map((s) => s.source),
        candidates: verdict.matched_sources.length,
      },
    },
    {
      id: 'compare',
      label: 'Semantic Comparison',
      description: 'Title, author, year matching',
      status: verdict.confidence > 0 ? 'completed' : 'pending',
      data: {
        confidence: `${(verdict.confidence * 100).toFixed(0)}%`,
        matchedFields: verdict.matched_sources.flatMap((s) => s.matched_fields),
      },
    },
    {
      id: 'rules',
      label: 'Symbolic Validation',
      description: 'Applying neuro-symbolic rules',
      status: verdict.triggered_rules.length > 0 ? 'completed' : 'pending',
      data: {
        rules: verdict.triggered_rules,
      },
    },
    {
      id: 'verdict',
      label: 'Final Verdict',
      status:
        verdict.label === 'verified'
          ? 'completed'
          : verdict.label === 'suspected_hallucination'
          ? 'error'
          : verdict.label === 'metadata_error'
          ? 'active'
          : 'pending',
    },
  ];

  return steps;
}

// Trace step component
function TraceStepCard({ step, isLast }: { step: TraceStep; isLast: boolean }) {
  const colors = getStepStatusColor(step.status);

  return (
    <div className="flex gap-4">
      {/* Timeline connector */}
      <div className="flex flex-col items-center">
        <div
          className={`w-10 h-10 rounded-xl flex items-center justify-center border-2 ${colors.bg} ${colors.border}`}
        >
          {colors.icon}
        </div>
        {!isLast && (
          <div
            className={`w-0.5 flex-1 min-h-[60px] ${
              step.status === 'completed' || step.status === 'active'
                ? 'bg-indigo-300 dark:bg-indigo-700'
                : 'bg-slate-200 dark:bg-slate-700'
            }`}
          />
        )}
      </div>

      {/* Step content */}
      <div className={`flex-1 pb-8`}>
        <div className={`rounded-xl border p-4 ${colors.bg} ${colors.border}`}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <h4 className={`font-semibold ${colors.text}`}>{step.label}</h4>
              {step.description && (
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                  {step.description}
                </p>
              )}
            </div>
            {step.data && Object.keys(step.data).length > 0 && (
              <ChevronRight className="h-5 w-5 text-slate-400 shrink-0" />
            )}
          </div>

          {/* Step detail */}
          {step.detail && (
            <p className="text-sm text-slate-700 dark:text-slate-300 mt-2 font-mono bg-white/50 dark:bg-slate-900/50 p-2 rounded-lg border border-slate-200/50 dark:border-slate-700/50">
              {step.detail}
            </p>
          )}

          {/* Step data */}
          {step.data && (
            <div className="mt-3 space-y-2">
              {Object.entries(step.data).map(([key, value]) => (
                <div key={key} className="flex items-center gap-2 text-sm">
                  <span className="text-slate-500 dark:text-slate-400 capitalize">
                    {key.replace(/_/g, ' ')}:
                  </span>
                  {Array.isArray(value) ? (
                    <div className="flex flex-wrap gap-1">
                      {value.map((v, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 bg-white dark:bg-slate-800 rounded text-xs font-mono border border-slate-200 dark:border-slate-700"
                        >
                          {v}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="font-medium text-slate-700 dark:text-slate-300">
                      {String(value)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Single verdict trace view
function VerdictTrace({
  verdict,
  index,
}: {
  verdict: Verdict;
  index: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const steps = buildTraceSteps(verdict);

  const verdictColor =
    verdict.label === 'verified'
      ? 'text-emerald-600 dark:text-emerald-400'
      : verdict.label === 'suspected_hallucination'
      ? 'text-red-600 dark:text-red-400'
      : verdict.label === 'metadata_error'
      ? 'text-amber-600 dark:text-amber-400'
      : 'text-slate-500 dark:text-slate-400';

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-4 p-4 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors text-left"
      >
        <span className="text-sm font-mono text-slate-500 dark:text-slate-400 w-8">
          #{index + 1}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
            {verdict.citation_raw}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-sm font-semibold capitalize ${verdictColor}`}>
            {verdict.label.replace(/_/g, ' ')}
          </span>
          <ChevronRight
            className={`h-5 w-5 text-slate-400 transition-transform ${
              expanded ? 'rotate-90' : ''
            }`}
          />
        </div>
      </button>

      {/* Expanded trace */}
      {expanded && (
        <div className="border-t border-slate-200 dark:border-slate-700 p-4 bg-slate-50 dark:bg-slate-900">
          {/* Trace steps */}
          <div className="mb-6">
            <h5 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-4">
              Verification Trace
            </h5>
            <div>
              {steps.map((step, idx) => (
                <TraceStepCard
                  key={step.id}
                  step={step}
                  isLast={idx === steps.length - 1}
                />
              ))}
            </div>
          </div>

          {/* Reasoning */}
          {verdict.reasoning && (
            <div className="mb-4">
              <h5 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                Reasoning
              </h5>
              <p className="text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
                {verdict.reasoning}
              </p>
            </div>
          )}

          {/* Triggered rules */}
          {verdict.triggered_rules.length > 0 && (
            <div>
              <h5 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                Triggered Rules
              </h5>
              <RuleInspector
                triggeredRules={verdict.triggered_rules}
                verdictLabel={verdict.label}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ============================================================
   Main LogicTracePage Component
   ============================================================ */

export function LogicTracePage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedVerdict, setSelectedVerdict] = useState<Verdict | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .getEssay(Number(id))
      .then(setReport)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed'));
  }, [id]);

  // Filter verdicts with issues (show non-verified first)
  const sortedVerdicts = report?.verdicts
    ? [...report.verdicts].sort((a, b) => {
        // Non-verified first
        if (a.label !== 'verified' && b.label === 'verified') return -1;
        if (a.label === 'verified' && b.label !== 'verified') return 1;
        // Then by confidence (low first)
        return a.confidence - b.confidence;
      })
    : [];

  if (error) {
    return (
      <div className="card p-6 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-red-700 dark:text-red-300">Error: {error}</p>
            <Link to="/history" className="text-indigo-600 dark:text-indigo-400 hover:underline mt-2 inline-block">
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
        <span className="ml-3 text-slate-600 dark:text-slate-400">Loading trace data...</span>
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
              Logic Trace
            </h1>
            <p className="text-slate-500 dark:text-slate-400 mt-1">
              {report.filename}
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Scale className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            <span className="text-slate-600 dark:text-slate-400">
              {sortedVerdicts.length} citations traced
            </span>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="card p-4 bg-slate-50 dark:bg-slate-800/50">
        <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">
          Trace Legend
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-emerald-100 dark:bg-emerald-950 border border-emerald-300 dark:border-emerald-700 flex items-center justify-center">
              <CheckCircle className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <span className="text-slate-600 dark:text-slate-400">Completed</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-indigo-100 dark:bg-indigo-950 border border-indigo-300 dark:border-indigo-700 flex items-center justify-center">
              <Loader2 className="h-4 w-4 text-indigo-600 dark:text-indigo-400 animate-spin" />
            </div>
            <span className="text-slate-600 dark:text-slate-400">In Progress</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-red-100 dark:bg-red-950 border border-red-300 dark:border-red-700 flex items-center justify-center">
              <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
            </div>
            <span className="text-slate-600 dark:text-slate-400">Error</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 flex items-center justify-center">
              <HelpCircle className="h-4 w-4 text-slate-400" />
            </div>
            <span className="text-slate-600 dark:text-slate-400">Pending</span>
          </div>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="stat-card text-center">
          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {report.verdicts.length}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Total</p>
        </div>
        <div className="stat-card text-center border-emerald-200 dark:border-emerald-800">
          <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {report.verdicts.filter((v) => v.label === 'verified').length}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Verified</p>
        </div>
        <div className="stat-card text-center border-amber-200 dark:border-amber-800">
          <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">
            {report.verdicts.filter((v) => v.label === 'metadata_error').length}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Meta Errors</p>
        </div>
        <div className="stat-card text-center border-red-200 dark:border-red-800">
          <p className="text-2xl font-bold text-red-600 dark:text-red-400">
            {report.verdicts.filter((v) => v.label === 'suspected_hallucination').length}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Suspected</p>
        </div>
      </div>

      {/* Verdict traces */}
      <div>
        <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Citation Traces
        </h2>
        <div className="space-y-3">
          {sortedVerdicts.map((verdict, index) => (
            <VerdictTrace key={verdict.citation_id} verdict={verdict} index={index} />
          ))}
        </div>
      </div>

      {/* Full trace for selected verdict */}
      {selectedVerdict && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50" onClick={() => setSelectedVerdict(null)}>
          <div
            className="absolute right-0 top-0 h-full w-full md:max-w-3xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700 overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <button
                onClick={() => setSelectedVerdict(null)}
                className="mb-4 text-sm text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
              >
                ← Close
              </button>
              <h3 className="font-display text-xl font-bold text-slate-900 dark:text-slate-100 mb-4">
                Full Trace: {selectedVerdict.citation_raw}
              </h3>
              <RuleInspector
                triggeredRules={selectedVerdict.triggered_rules}
                verdictLabel={selectedVerdict.label}
                className="mt-4"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
