import { useState, useMemo } from 'react';
import {
  ChevronUp,
  ChevronDown,
  GitBranch,
  Database,
  Brain,
  Link2,
} from 'lucide-react';
import type {
  Verdict,
  CitationMappingStatus,
  ValidationLabel,
  MappingStatusSummary,
} from '@/api/client';
import { MappingStatusBadge } from '../MappingStatusBadge';
import { VerdictBadge } from '../VerdictBadge';
import { OverrideControls } from '../OverrideControls';
import {
  CitationGraphControls,
  type ViewMode,
  type CitationGraphStats,
} from '../graph/CitationGraphControls';
import { EvidenceGraph } from './EvidenceGraph';
import { isUrlResource } from '@/lib/verdictExplanation';

interface CitationGraphViewProps {
  verdicts: Verdict[];
  linkingSummary?: MappingStatusSummary;
  onSelect: (v: Verdict) => void;
  onOverride?: (
    verdict: Verdict,
    req: Parameters<typeof import('@/api/client').api.overrideVerdict>[1]
  ) => Promise<void>;
}

function SortIcon({
  sorted,
  direction,
}: {
  sorted: boolean;
  direction: 'asc' | 'desc';
}) {
  if (!sorted) return <ChevronUp className="h-3 w-3 text-slate-400" />;
  return direction === 'asc' ? (
    <ChevronUp className="h-3 w-3 text-indigo-600 dark:text-indigo-400" />
  ) : (
    <ChevronDown className="h-3 w-3 text-indigo-600 dark:text-indigo-400" />
  );
}

export function CitationGraphView({
  verdicts,
  linkingSummary: _linkingSummary,
  onSelect,
  onOverride,
}: CitationGraphViewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('combined');
  const [statusFilters, setStatusFilters] = useState<
    Set<CitationMappingStatus>
  >(new Set());
  const [labelFilters, setLabelFilters] = useState<Set<ValidationLabel>>(
    new Set(),
  );
  const [searchQuery, setSearchQuery] = useState('');
  const [activeId, setActiveId] = useState<string | null>(
    verdicts[0]?.citation_id ?? null,
  );

  const filtered = useMemo(() => {
    return verdicts.filter((v) => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        if (!v.citation_raw?.toLowerCase().includes(query)) {
          return false;
        }
      }
      const statusOk =
        statusFilters.size === 0 || statusFilters.has(v.mapping_status);
      const labelOk = labelFilters.size === 0 || labelFilters.has(v.label);
      return statusOk && labelOk;
    });
  }, [verdicts, searchQuery, statusFilters, labelFilters]);

  const activeVerdict = useMemo(() => {
    return (
      filtered.find((v) => v.citation_id === activeId) ||
      filtered[0] ||
      verdicts[0] ||
      null
    );
  }, [filtered, verdicts, activeId]);

  function toggleStatus(s: CitationMappingStatus) {
    setStatusFilters((prev) => {
      const next = new Set(prev);
      next.has(s) ? next.delete(s) : next.add(s);
      return next;
    });
  }

  function toggleLabel(l: ValidationLabel) {
    setLabelFilters((prev) => {
      const next = new Set(prev);
      next.has(l) ? next.delete(l) : next.add(l);
      return next;
    });
  }

  function clearFilters() {
    setStatusFilters(new Set());
    setLabelFilters(new Set());
    setSearchQuery('');
  }

  const stats = useMemo(() => {
    const total = verdicts.length;
    const integrityCounts: Partial<Record<CitationMappingStatus, number>> = {};
    const sourceCounts: Partial<Record<ValidationLabel, number>> = {};
    let overridden = 0;
    let domainExc = 0;

    for (const v of verdicts) {
      integrityCounts[v.mapping_status] =
        (integrityCounts[v.mapping_status] ?? 0) + 1;
      sourceCounts[v.label] = (sourceCounts[v.label] ?? 0) + 1;
      if (v.is_overridden) overridden++;
      if (v.domain_exception) domainExc++;
    }

    return { total, integrityCounts, sourceCounts, overridden, domainExc };
  }, [verdicts]);

  const hasFilters =
    statusFilters.size > 0 || labelFilters.size > 0 || searchQuery.length > 0;

  return (
    <div className="space-y-5 p-4 sm:p-6 bg-white dark:bg-slate-950" data-testid="citation-graph-view">
      {/* Top Architecture Header & Controls */}
      <div className="rounded-xl border border-slate-200/90 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-200/80 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/90 border border-indigo-200/70 dark:border-indigo-800">
              <GitBranch className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Two-Layer Citation &amp; Source Network Explorer
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Filter across Layer 1 (In-Text ↔ Bibliography Mapping) and Layer 2 (Scholarly Registry Verification)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-200/70 dark:border-emerald-800">
              <Link2 className="h-3 w-3" />
              Matched: {stats.integrityCounts.matched ?? 0}/{stats.total}
            </span>
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-200/70 dark:border-indigo-800">
              <Database className="h-3 w-3" />
              Verified: {stats.sourceCounts.verified ?? 0}/{stats.total}
            </span>
          </div>
        </div>

        <CitationGraphControls
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          statusFilters={statusFilters}
          onToggleStatus={toggleStatus}
          labelFilters={labelFilters}
          onToggleLabel={toggleLabel}
          filteredCount={filtered.length}
          stats={stats satisfies CitationGraphStats}
          hasFilters={hasFilters}
          onClearFilters={clearFilters}
        />
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-12 text-slate-500 dark:text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
          <p className="text-sm italic">No citations match your filters.</p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-12 gap-5 items-start">
          {/* Left Column: Interactive Node Stream (5 cols) */}
          <div className="lg:col-span-5 space-y-2 max-h-[620px] overflow-y-auto pr-1">
            {filtered.map((v, i) => {
              const isSelected = activeVerdict?.citation_id === v.citation_id;
              return (
                <div
                  key={v.citation_id ?? i}
                  onClick={() => {
                    setActiveId(v.citation_id);
                    onSelect(v);
                  }}
                  className={`border rounded-xl p-3.5 cursor-pointer transition-all ${
                    isSelected
                      ? 'border-indigo-500 bg-indigo-50/60 dark:bg-indigo-950/50 ring-1 ring-indigo-500/30 shadow-xs'
                      : 'border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-indigo-300 dark:hover:border-indigo-700'
                  } ${
                    v.is_overridden
                      ? 'border-amber-300 dark:border-amber-700 bg-amber-50/30 dark:bg-amber-950/20'
                      : ''
                  } ${
                    v.domain_exception
                      ? 'border-dashed border-amber-300 dark:border-amber-700'
                      : ''
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="shrink-0 pt-0.5">
                      <MappingStatusBadge status={v.mapping_status} size="sm" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <p
                        className="text-xs sm:text-sm font-medium text-slate-900 dark:text-slate-100 line-clamp-2 font-serif leading-snug"
                        title={v.citation_raw}
                      >
                        {v.citation_raw}
                      </p>
                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        {viewMode !== 'integrity' && (
                          <VerdictBadge
                            verdict={isUrlResource(v) ? 'resource' : v.label}
                            size="sm"
                          />
                        )}
                        {viewMode === 'combined' && (
                          <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                            src: {(v.confidence * 100).toFixed(0)}% | link:{' '}
                            {(v.mapping_confidence * 100).toFixed(0)}%
                          </span>
                        )}
                        {v.features?.content_alignment_score !== undefined &&
                          v.features.content_alignment_score > 0 && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-violet-50 dark:bg-violet-950/70 text-violet-700 dark:text-violet-300">
                              <Brain className="h-2.5 w-2.5" />
                              {Math.round(v.features.content_alignment_score * 100)}%
                            </span>
                          )}
                        {v.is_overridden && (
                          <span className="text-[10px] font-mono font-semibold text-amber-600 dark:text-amber-400">
                            OVERRIDDEN
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Dual Telemetry Mini Bar */}
                    <div className="shrink-0 w-10 pt-1 hidden sm:block">
                      <div className="flex gap-1 items-end h-7 bg-slate-100 dark:bg-slate-800 p-1 rounded">
                        <div
                          className="flex-1 bg-emerald-500 rounded-t"
                          style={{
                            height: `${Math.max(8, Math.round(v.confidence * 100))}%`,
                          }}
                          title={`Source Confidence: ${(v.confidence * 100).toFixed(0)}%`}
                        />
                        <div
                          className="flex-1 bg-indigo-500 rounded-t"
                          style={{
                            height: `${Math.max(8, Math.round(v.mapping_confidence * 100))}%`,
                          }}
                          title={`Link Confidence: ${(v.mapping_confidence * 100).toFixed(0)}%`}
                        />
                      </div>
                    </div>

                    {onOverride && (
                      <div
                        className="shrink-0"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <OverrideControls
                          verdict={v}
                          onOverride={(req) => onOverride(v, req)}
                        />
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right Column: Live Interactive Evidence Graph DAG (7 cols) */}
          <div className="lg:col-span-7 rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 p-4 sm:p-5">
            {activeVerdict && <EvidenceGraph verdict={activeVerdict} />}
          </div>
        </div>
      )}
    </div>
  );
}

export { SortIcon };
