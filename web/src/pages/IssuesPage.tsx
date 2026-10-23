import { useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { type Verdict, type ValidationLabel } from '@/api/client';
import { VerdictBadge } from '@/components/VerdictBadge';
import { getSourceDisplayName, getVerdictExplanation, isUrlResource } from '@/lib/verdictExplanation';
import { useEssayPolling } from '@/hooks/useEssayPolling';
import {
  AlertTriangle,
  AlertCircle,
  Info,
  ArrowLeft,
  Loader2,
  ChevronDown,
  ChevronUp,
  Database,
  XCircle,
  CheckCircle,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

/* ============================================================
   SourceLogic — Issues Page Component
   Based on UX/UI Concept Section 12: Issues Page
   Shows all verification issues grouped by severity
   ============================================================ */

type Severity = 'critical' | 'warning' | 'info';

function getSeverity(label: ValidationLabel): Severity {
  switch (label) {
    case 'suspected_hallucination':
      return 'critical';
    case 'metadata_error':
      return 'warning';
    case 'unresolved':
      return 'info';
    case 'resource':
      return 'info';
    default:
      return 'info';
  }
}

const severityConfig = {
  critical: {
    label: 'Critical',
    color: 'red',
    bgClass: 'bg-red-50 dark:bg-red-950',
    borderClass: 'border-red-200 dark:border-red-800',
    icon: <XCircle className="h-5 w-5" />,
    iconColor: 'text-red-600 dark:text-red-400',
    textColor: 'text-red-700 dark:text-red-300',
    bgCard: 'bg-red-50/50 dark:bg-red-950/50',
    borderCard: 'border-red-100 dark:border-red-900',
  },
  warning: {
    label: 'Warning',
    color: 'amber',
    bgClass: 'bg-amber-50 dark:bg-amber-950',
    borderClass: 'border-amber-200 dark:border-amber-800',
    icon: <AlertTriangle className="h-5 w-5" />,
    iconColor: 'text-amber-600 dark:text-amber-400',
    textColor: 'text-amber-700 dark:text-amber-300',
    bgCard: 'bg-amber-50/50 dark:bg-amber-950/50',
    borderCard: 'border-amber-100 dark:border-amber-900',
  },
  info: {
    label: 'Info',
    color: 'slate',
    bgClass: 'bg-slate-50 dark:bg-slate-800',
    borderClass: 'border-slate-200 dark:border-slate-700',
    icon: <Info className="h-5 w-5" />,
    iconColor: 'text-slate-600 dark:text-slate-300',
    textColor: 'text-slate-700 dark:text-slate-300',
    bgCard: 'bg-slate-50/50 dark:bg-slate-800/50',
    borderCard: 'border-slate-100 dark:border-slate-800',
  },
};

function SourceIcon({ source }: { source: string }) {
  const lower = source.toLowerCase();
  if (lower.includes('crossref')) return <span className="text-xs font-mono">CR</span>;
  if (lower.includes('openalex')) return <span className="text-xs font-mono">OA</span>;
  if (lower.includes('semantic') || lower.includes('s2')) return <span className="text-xs font-mono">S2</span>;
  if (lower.includes('core')) return <span className="text-xs font-mono">CO</span>;
  return <Database className="h-3 w-3" />;
}

function IssueCard({ verdict }: { verdict: Verdict }) {
  const [expanded, setExpanded] = useState(false);
  const severity = getSeverity(verdict.label);
  const config = severityConfig[severity];

  const citationNum = verdict.citation_id.replace(/[^0-9]/g, '') || verdict.citation_id;

  function getIssueDescription(v: Verdict): string {
    if (isUrlResource(v)) {
      return `URL resource: ${v.citation_raw}. Excluded from CIS scoring.`;
    }
    if (v.label === 'suspected_hallucination') {
      return 'No matching publication was found.';
    }
    if (v.label === 'metadata_error') {
      if (v.mismatched_fields.length > 0) {
        return `${v.mismatched_fields.join(', ')} mismatch`;
      }
      return 'Metadata inconsistency detected.';
    }
    if (v.label === 'unresolved') {
      return 'Unable to verify due to insufficient data.';
    }
    return getVerdictExplanation(v);
  }

  const sourceResults = verdict.matched_sources || [];

  return (
    <Card
      className={`p-4 transition-all ${config.bgCard} ${config.borderCard}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <VerdictBadge verdict={isUrlResource(verdict) ? 'resource' : verdict.label} size="sm" />
            <span className={`text-sm font-semibold ${config.textColor}`}>
              Citation #{citationNum}
            </span>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-300 mb-1">
            <span className="font-medium font-serif">{verdict.citation_raw}</span>
          </p>
          <p className={`text-sm ${config.textColor}`}>
            {getIssueDescription(verdict)}
          </p>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className={`p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors ${config.iconColor}`}
          aria-label={expanded ? 'Collapse details' : 'Expand details'}
        >
          {expanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </button>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700 space-y-4">
          <div className="min-w-0 flex-1">
            <h4 className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide mb-1">
              What this means
            </h4>
            <p className="text-sm text-slate-700 dark:text-slate-300">
              {getVerdictExplanation(verdict)}
            </p>
          </div>

          {verdict.mismatched_fields.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide mb-1">
                Mismatched Fields
              </h4>
              <div className="flex flex-wrap gap-2">
                {verdict.mismatched_fields.map((field) => (
                  <Badge
                    key={field}
                    variant="metadata_error"
                    className="px-2 py-0.5 rounded-md text-xs font-medium"
                  >
                    {field}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {verdict.triggered_rules.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide mb-1">
                Triggered Rules
              </h4>
              <div className="flex flex-wrap gap-2">
                {verdict.triggered_rules.map((rule) => (
                  <Badge
                    key={rule}
                    variant="outline"
                    className="px-2 py-0.5 rounded text-xs font-mono bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                  >
                    {rule}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {sourceResults.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide mb-1">
                Source Lookup
              </h4>
              <div className="space-y-1">
                {sourceResults.map((source, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between py-1 text-sm"
                  >
                    <span className="flex items-center gap-2">
                      <SourceIcon source={source.source} />
                      <span className="text-slate-700 dark:text-slate-300 capitalize">
                        {getSourceDisplayName(source.source)}
                      </span>
                    </span>
                    <span className="text-slate-600 dark:text-slate-300">
                      Match
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {verdict.confidence > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide mb-1">
                Confidence
              </h4>
              <div className="flex items-center gap-2">
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
                <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                  {Math.round(verdict.confidence * 100)}%
                </span>
              </div>
            </div>
          )}

          {verdict.mapping_status && verdict.mapping_status !== 'matched' && (
            <div>
              <h4 className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide mb-1">
                Mapping Status
              </h4>
              <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium ${
                verdict.mapping_status === 'missing_reference'
                  ? 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
                  : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200'
              }`}>
                {verdict.mapping_status === 'missing_reference' && <AlertCircle className="h-3 w-3" />}
                {verdict.mapping_status.replace(/_/g, ' ')}
              </span>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function SeveritySection({
  severity,
  verdicts
}: {
  severity: Severity;
  verdicts: Verdict[];
}) {
  const config = severityConfig[severity];
  const [isOpen, setIsOpen] = useState(true);

  if (verdicts.length === 0) return null;

  return (
    <div className="space-y-3">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between p-3 rounded-xl border ${config.bgCard} ${config.borderCard} transition-all hover:opacity-90`}
      >
        <div className="flex items-center gap-3">
          <div className={`flex items-center justify-center w-8 h-8 rounded-lg ${config.bgClass} ${config.borderClass} border`}>
            <span className={config.iconColor}>{config.icon}</span>
          </div>
          <div className="text-left">
            <span className={`font-semibold ${config.textColor}`}>{config.label}</span>
            <span className="ml-2 text-sm text-slate-600 dark:text-slate-300">
              {verdicts.length} {verdicts.length === 1 ? 'issue' : 'issues'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-lg font-bold ${config.textColor}`}>{verdicts.length}</span>
          {isOpen ? (
            <ChevronUp className={`h-5 w-5 ${config.iconColor}`} />
          ) : (
            <ChevronDown className={`h-5 w-5 ${config.iconColor}`} />
          )}
        </div>
      </button>

      {isOpen && (
        <div className="space-y-3 pl-2">
          {verdicts.map((verdict) => (
            <IssueCard key={verdict.citation_id} verdict={verdict} />
          ))}
        </div>
      )}
    </div>
  );
}

export function IssuesPage() {
  const { id } = useParams<{ id: string }>();
  const [filter, setFilter] = useState<'all' | 'critical' | 'warning' | 'info'>('all');

  const numericId = id ? parseInt(id, 10) : null;
  const { report, error } = useEssayPolling(
    numericId !== null && !Number.isNaN(numericId) && numericId > 0 ? numericId : null,
  );

  const issuesBySeverity = useMemo(() => {
    if (!report) return { critical: [], warning: [], info: [] };
    const issues = report.verdicts.filter((v) => v.label !== 'verified');
    return {
      critical: issues.filter((v) => getSeverity(v.label) === 'critical'),
      warning: issues.filter((v) => getSeverity(v.label) === 'warning'),
      info: issues.filter((v) => getSeverity(v.label) === 'info'),
    };
  }, [report]);

  const totalIssues = Object.values(issuesBySeverity).reduce(
    (sum, arr) => sum + arr.length,
    0
  );

  const displaySections = useMemo(() => {
    if (filter === 'all') {
      return [
        { severity: 'critical' as Severity, data: issuesBySeverity.critical },
        { severity: 'warning' as Severity, data: issuesBySeverity.warning },
        { severity: 'info' as Severity, data: issuesBySeverity.info },
      ];
    }
    return [{ severity: filter as Severity, data: issuesBySeverity[filter as keyof typeof issuesBySeverity] }];
  }, [filter, issuesBySeverity]);

  if (error) {
    return (
      <Alert variant="destructive" className="card p-6">
        <AlertCircle className="h-5 w-5" />
        <AlertTitle className="font-medium">Error loading issues</AlertTitle>
        <AlertDescription>
          <p className="text-sm mt-1">{error}</p>
          <Link to="/history" className="text-indigo-600 dark:text-indigo-400 hover:underline mt-2 inline-block">
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
        <span className="ml-3 text-slate-600 dark:text-slate-300">Loading issues...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          to={`/verification/report/${id}`}
          className="inline-flex items-center gap-1 text-sm text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 mb-3 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Report
        </Link>
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-slate-100">
              Issues
            </h1>
            <p className="text-slate-600 dark:text-slate-300 mt-1 truncate" title={report.filename}>
              {report.filename}
            </p>
          </div>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="stat-card text-center p-4">
          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{totalIssues}</p>
          <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">Total Issues</p>
        </Card>
        <Card className="stat-card text-center p-4 border-red-200 dark:border-red-800">
          <p className="text-2xl font-bold text-red-600 dark:text-red-400">{issuesBySeverity.critical.length}</p>
          <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">Critical</p>
        </Card>
        <Card className="stat-card text-center p-4 border-amber-200 dark:border-amber-800">
          <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">{issuesBySeverity.warning.length}</p>
          <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">Warning</p>
        </Card>
        <Card className="stat-card text-center p-4 border-slate-200 dark:border-slate-700">
          <p className="text-2xl font-bold text-slate-600 dark:text-slate-300">{issuesBySeverity.info.length}</p>
          <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">Info</p>
        </Card>
      </div>

      {/* Filter tabs */}
      <div
        role="group"
        aria-label="Filter issues by severity"
        className="flex gap-2 flex-wrap"
      >
        {(['all', 'critical', 'warning', 'info'] as const).map((f) => {
          const isActive = filter === f;
          return (
            <button
              key={f}
              onClick={() => setFilter(f)}
              aria-pressed={isActive}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
              {f !== 'all' && (
                <span className="ml-2 opacity-75">
                  ({issuesBySeverity[f as keyof typeof issuesBySeverity].length})
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Issues sections */}
      {totalIssues === 0 ? (
        <Card className="p-12 text-center">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center">
              <CheckCircle className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
            </div>
          </div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            No Issues Found
          </h3>
          <p className="text-slate-600 dark:text-slate-300 max-w-sm mx-auto">
            All citations and references have been verified successfully. No critical, warning, or info issues detected.
          </p>
        </Card>
      ) : (
        <div className="space-y-4">
          {displaySections.map(({ severity, data }) => (
            <SeveritySection
              key={severity}
              severity={severity}
              verdicts={data}
            />
          ))}
        </div>
      )}

      {/* Legend */}
      <Card className="p-4 bg-slate-50 dark:bg-slate-800/50">
        <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide mb-2">
          Severity Legend
        </h3>
        <div className="flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
            <span className="text-slate-600 dark:text-slate-300">
              Critical: Suspected hallucination
            </span>
          </div>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            <span className="text-slate-600 dark:text-slate-300">
              Warning: Metadata error
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Info className="h-4 w-4 text-slate-600 dark:text-slate-300" />
            <span className="text-slate-600 dark:text-slate-300">
              Info: Unresolved
            </span>
          </div>
        </div>
      </Card>
    </div>
  );
}
