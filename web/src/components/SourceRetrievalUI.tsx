import { useMemo } from 'react';
import { Database, ExternalLink, CheckCircle, XCircle, Loader2, Search, TrendingUp } from 'lucide-react';
import type { AnalysisReport, MatchedSource } from '@/api/client';
import { cn } from '@/lib/utils';

/* ============================================================
   SourceLogic — Source Retrieval UI Component
   Based on UX/UI Concept Section 18: Source Retrieval UI
   Shows retrieval results from academic databases
   ============================================================ */

interface SourceRetrievalUIProps {
  report: AnalysisReport;
  className?: string;
}

// Source database configuration
const SOURCE_CONFIG: Record<string, {
  name: string;
  shortName: string;
  color: string;
  bgColor: string;
  borderColor: string;
  icon: string;
}> = {
  crossref: {
    name: 'Crossref',
    shortName: 'CR',
    color: 'text-emerald-600 dark:text-emerald-400',
    bgColor: 'bg-emerald-50 dark:bg-emerald-950',
    borderColor: 'border-emerald-200 dark:border-emerald-800',
    icon: '📚',
  },
  openalex: {
    name: 'OpenAlex',
    shortName: 'OA',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-950',
    borderColor: 'border-blue-200 dark:border-blue-800',
    icon: '🔷',
  },
  s2: {
    name: 'Semantic Scholar',
    shortName: 'S2',
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-50 dark:bg-purple-950',
    borderColor: 'border-purple-200 dark:border-purple-800',
    icon: '📖',
  },
  core: {
    name: 'CORE',
    shortName: 'CO',
    color: 'text-orange-600 dark:text-orange-400',
    bgColor: 'bg-orange-50 dark:bg-orange-950',
    borderColor: 'border-orange-200 dark:border-orange-800',
    icon: '🔶',
  },
};

/* ============================================================
   Source Card Component
   ============================================================ */

function SourceCard({
  sourceKey,
  stats,
}: {
  sourceKey: string;
  stats: { total: number; verified: number; withUrl: number };
}) {
  const config = SOURCE_CONFIG[sourceKey] || {
    name: sourceKey,
    shortName: sourceKey.slice(0, 2).toUpperCase(),
    color: 'text-slate-600 dark:text-slate-400',
    bgColor: 'bg-slate-50 dark:bg-slate-800',
    borderColor: 'border-slate-200 dark:border-slate-700',
    icon: '📦',
  };

  const hasResults = stats.total > 0;
  const successRate = stats.total > 0 ? Math.round((stats.verified / stats.total) * 100) : 0;

  return (
    <div
      className={cn(
        'rounded-xl border p-4 transition-all',
        hasResults ? config.bgColor : 'bg-slate-50 dark:bg-slate-800',
        hasResults ? config.borderColor : 'border-slate-200 dark:border-slate-700'
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{config.icon}</span>
          <span className={cn('text-sm font-semibold', config.color)}>
            {config.name}
          </span>
        </div>
        <span
          className={cn(
            'text-xs font-mono px-2 py-0.5 rounded-full',
            hasResults
              ? 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300'
              : 'bg-slate-100 dark:bg-slate-700 text-slate-400'
          )}
        >
          {config.shortName}
        </span>
      </div>

      {hasResults ? (
        <>
          {/* Stats */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-500 dark:text-slate-400">Candidates</span>
              <span className="font-semibold text-slate-900 dark:text-slate-100">
                {stats.total}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-500 dark:text-slate-400">Verified</span>
              <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                {stats.verified}
              </span>
            </div>
            {stats.withUrl > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-500 dark:text-slate-400">With Links</span>
                <span className="font-semibold text-indigo-600 dark:text-indigo-400">
                  {stats.withUrl}
                </span>
              </div>
            )}
          </div>

          {/* Success rate bar */}
          <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="h-3 w-3 text-slate-400" />
              <span className="text-xs text-slate-500 dark:text-slate-400">Success Rate</span>
            </div>
            <div className="h-2 bg-white dark:bg-slate-900 rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all',
                  successRate >= 70
                    ? 'bg-emerald-500'
                    : successRate >= 40
                    ? 'bg-amber-500'
                    : 'bg-red-500'
                )}
                style={{ width: `${successRate}%` }}
              />
            </div>
            <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 block">
              {successRate}% match rate
            </span>
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center py-4 text-center">
          <XCircle className="h-6 w-6 text-slate-300 dark:text-slate-600 mb-2" />
          <span className="text-xs text-slate-400 dark:text-slate-500">No results</span>
        </div>
      )}
    </div>
  );
}

/* ============================================================
   Candidate List Component
   ============================================================ */

function CandidateList({
  sources,
}: {
  sources: MatchedSource[];
}) {
  // Group by source
  const grouped = useMemo(() => {
    const groups: Record<string, MatchedSource[]> = {};
    for (const src of sources) {
      if (!groups[src.source]) {
        groups[src.source] = [];
      }
      groups[src.source].push(src);
    }
    return groups;
  }, [sources]);

  // Sort by source name
  const sortedSources = Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div className="space-y-4">
      {sortedSources.map(([source, items]) => {
        const config = SOURCE_CONFIG[source] || {
          name: source,
          shortName: source.slice(0, 2).toUpperCase(),
          color: 'text-slate-600 dark:text-slate-400',
          bgColor: 'bg-slate-50 dark:bg-slate-800',
          borderColor: 'border-slate-200 dark:border-slate-700',
          icon: '📦',
        };

        return (
          <div key={source} className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                {config.name}
              </span>
              <span className={cn(
                'text-xs px-2 py-0.5 rounded-full font-medium',
                config.bgColor,
                config.color
              )}>
                {items.length} {items.length === 1 ? 'candidate' : 'candidates'}
              </span>
            </div>

            <div className="space-y-2">
              {items.slice(0, 3).map((item, idx) => (
                <div
                  key={idx}
                  className={cn(
                    'rounded-lg border p-3',
                    config.bgColor,
                    config.borderColor
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <CheckCircle className={cn('h-4 w-4 shrink-0', config.color)} />
                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                          Candidate #{idx + 1}
                        </span>
                      </div>
                      {item.matched_fields.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {item.matched_fields.slice(0, 4).map((field) => (
                            <span
                              key={field}
                              className="text-xs px-1.5 py-0.5 bg-white dark:bg-slate-900 rounded text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700"
                            >
                              {field}
                            </span>
                          ))}
                          {item.matched_fields.length > 4 && (
                            <span className="text-xs text-slate-400">
                              +{item.matched_fields.length - 4} more
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    {item.url && (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={cn(
                          'flex items-center gap-1 text-xs px-2 py-1 rounded-lg transition-colors',
                          config.bgColor,
                          'hover:bg-opacity-80'
                        )}
                        title="Open in browser"
                      >
                        <ExternalLink className="h-3 w-3" />
                        <span className={config.color}>Open</span>
                      </a>
                    )}
                  </div>
                  {item.checked_at && (
                    <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                      Checked: {new Date(item.checked_at).toLocaleString()}
                    </p>
                  )}
                </div>
              ))}
              {items.length > 3 && (
                <p className="text-xs text-slate-500 dark:text-slate-400 text-center py-2">
                  + {items.length - 3} more candidates from {config.name}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ============================================================
   Main SourceRetrievalUI Component
   ============================================================ */

export function SourceRetrievalUI({
  report,
  className = '',
}: SourceRetrievalUIProps) {
  // Calculate stats per source
  const sourceStats = useMemo(() => {
    const stats: Record<string, { total: number; verified: number; withUrl: number }> = {
      crossref: { total: 0, verified: 0, withUrl: 0 },
      openalex: { total: 0, verified: 0, withUrl: 0 },
      s2: { total: 0, verified: 0, withUrl: 0 },
      core: { total: 0, verified: 0, withUrl: 0 },
    };

    // Count from all verdicts
    for (const verdict of report.verdicts) {
      for (const source of verdict.matched_sources || []) {
        const key = source.source.toLowerCase();
        if (stats[key] !== undefined) {
          stats[key].total++;
          if (source.matched_fields.length > 0) {
            stats[key].verified++;
          }
          if (source.url) {
            stats[key].withUrl++;
          }
        }
      }
    }

    return stats;
  }, [report.verdicts]);

  // Total candidates
  const totalCandidates = Object.values(sourceStats).reduce(
    (sum, s) => sum + s.total,
    0
  );

  // Total verified
  const totalVerified = Object.values(sourceStats).reduce(
    (sum, s) => sum + s.verified,
    0
  );

  // All sources for candidate list
  const allSources = report.verdicts.flatMap((v) => v.matched_sources || []);

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900">
          <Database className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <h3 className="font-display text-base font-semibold text-slate-900 dark:text-slate-100">
            Source Retrieval
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Academic database lookup results
          </p>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {totalCandidates}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Total Lookups</p>
        </div>
        <div className="card p-4 text-center border-emerald-200 dark:border-emerald-800">
          <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {totalVerified}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Matches Found</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
            {Object.values(sourceStats).filter(s => s.total > 0).length}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Sources Used</p>
        </div>
      </div>

      {/* Source cards */}
      <div>
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 uppercase tracking-wide">
          Database Coverage
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Object.entries(sourceStats).map(([key, stats]) => (
            <SourceCard key={key} sourceKey={key} stats={stats} />
          ))}
        </div>
      </div>

      {/* Candidate list */}
      {allSources.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 uppercase tracking-wide">
            Candidates ({allSources.length})
          </h4>
          <div className="card p-4">
            <CandidateList sources={allSources} />
          </div>
        </div>
      )}

      {/* No sources found */}
      {allSources.length === 0 && (
        <div className="card p-6 text-center bg-slate-50 dark:bg-slate-800/50">
          <Search className="h-8 w-8 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-500 dark:text-slate-400">
            No source lookups were performed for this document.
          </p>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-slate-500 dark:text-slate-400">
        <div className="flex items-center gap-1.5">
          <span className="text-emerald-500">•</span>
          <span>High match rate (70%+)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-amber-500">•</span>
          <span>Medium match rate (40-69%)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-red-500">•</span>
          <span>Low match rate (&lt;40%)</span>
        </div>
      </div>
    </div>
  );
}
