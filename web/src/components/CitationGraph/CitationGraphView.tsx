import { useState, useMemo } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';
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

function SortIcon({ sorted, direction }: { sorted: boolean; direction: 'asc' | 'desc' }) {
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
  const [statusFilters, setStatusFilters] = useState<Set<CitationMappingStatus>>(new Set());
  const [labelFilters, setLabelFilters] = useState<Set<ValidationLabel>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');

  const filtered = useMemo(() => {
    return verdicts.filter((v) => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        if (!v.citation_raw?.toLowerCase().includes(query)) {
          return false;
        }
      }
      const statusOk = statusFilters.size === 0 || statusFilters.has(v.mapping_status);
      const labelOk = labelFilters.size === 0 || labelFilters.has(v.label);
      return statusOk && labelOk;
    });
  }, [verdicts, searchQuery, statusFilters, labelFilters]);

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
      integrityCounts[v.mapping_status] = (integrityCounts[v.mapping_status] ?? 0) + 1;
      sourceCounts[v.label] = (sourceCounts[v.label] ?? 0) + 1;
      if (v.is_overridden) overridden++;
      if (v.domain_exception) domainExc++;
    }

    return { total, integrityCounts, sourceCounts, overridden, domainExc };
  }, [verdicts]);

  const hasFilters = statusFilters.size > 0 || labelFilters.size > 0 || searchQuery.length > 0;

  return (
    <div className="space-y-4">
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

      {filtered.length === 0 ? (
        <div className="text-center py-12 text-slate-500 dark:text-slate-400">
          <p className="text-sm italic">No citations match your filters.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((v, i) => (
            <div
              key={v.citation_id ?? i}
              onClick={() => onSelect(v)}
              className={`border rounded-lg p-3 cursor-pointer transition-colors hover:border-indigo-400 dark:hover:border-indigo-600 hover:bg-slate-50 dark:hover:bg-slate-800/50 ${
                v.is_overridden
                  ? 'border-amber-300 dark:border-amber-700 bg-amber-50/30 dark:bg-amber-950/20'
                  : ''
              } ${v.domain_exception ? 'border-dashed border-amber-300 dark:border-amber-700' : ''}`}
            >
              <div className="flex items-start gap-3">
                <div className="shrink-0">
                  <MappingStatusBadge status={v.mapping_status} size="sm" />
                </div>

                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate"
                    title={v.citation_raw}
                  >
                    {v.citation_raw}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    {viewMode !== 'integrity' && (
                      <VerdictBadge
                        verdict={isUrlResource(v) ? 'resource' : v.label}
                        size="sm"
                      />
                    )}
                    {viewMode === 'combined' && (
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        src: {(v.confidence * 100).toFixed(0)}% | link:{' '}
                        {(v.mapping_confidence * 100).toFixed(0)}%
                      </span>
                    )}
                    {v.is_overridden && (
                      <span className="text-xs text-amber-600 dark:text-amber-400">overridden</span>
                    )}
                  </div>
                </div>

                <div className="shrink-0 w-16 pt-1 hidden sm:block">
                  <div className="flex gap-1 items-end h-6">
                    <div
                      className="flex-1 bg-emerald-400 rounded-t"
                      style={{
                        height: `${(v.confidence * 100).toFixed(0)}%`,
                        minHeight: '2px',
                      }}
                      title={`Source: ${(v.confidence * 100).toFixed(0)}%`}
                    />
                    <div
                      className="flex-1 bg-blue-400 rounded-t"
                      style={{
                        height: `${(v.mapping_confidence * 100).toFixed(0)}%`,
                        minHeight: '2px',
                      }}
                      title={`Link: ${(v.mapping_confidence * 100).toFixed(0)}%`}
                    />
                  </div>
                </div>

                {onOverride && (
                  <div className="shrink-0" onClick={(e) => e.stopPropagation()}>
                    <OverrideControls
                      verdict={v}
                      onOverride={(req) => onOverride(v, req)}
                    />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export { SortIcon };
