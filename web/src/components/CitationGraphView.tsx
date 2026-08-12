import { useState, useMemo } from 'react';
import type {
  Verdict,
  CitationMappingStatus,
  ValidationLabel,
  MappingStatusSummary,
} from '@/api/client';
import { MappingStatusBadge } from './MappingStatusBadge';
import { VerdictBadge } from './VerdictBadge';
import { OverrideControls } from './OverrideControls';
import { cn } from '@/lib/utils';

interface CitationGraphViewProps {
  verdicts: Verdict[];
  linkingSummary?: MappingStatusSummary;
  onSelect: (v: Verdict) => void;
  onOverride?: (
    verdict: Verdict,
    req: Parameters<typeof import('@/api/client').api.overrideVerdict>[1]
  ) => Promise<void>;
}

const STATUS_FILTERS: { value: CitationMappingStatus; label: string }[] = [
  { value: 'matched', label: 'Matched' },
  { value: 'missing_reference', label: 'Missing Ref' },
  { value: 'uncited_reference', label: 'Uncited Ref' },
  { value: 'in_text_mismatch', label: 'Mismatch' },
  { value: 'duplicate_reference', label: 'Duplicate' },
  { value: 'ambiguous_mapping', label: 'Ambiguous' },
  { value: 'style_inconsistent', label: 'Style Issue' },
  { value: 'unresolved', label: 'Unresolved' },
];

const LABEL_FILTERS: { value: ValidationLabel; label: string }[] = [
  { value: 'verified', label: 'Verified' },
  { value: 'metadata_error', label: 'Meta Error' },
  { value: 'suspected_hallucination', label: 'Suspected' },
  { value: 'unresolved', label: 'Unresolved' },
];

type ViewMode = 'integrity' | 'source' | 'combined';

export function CitationGraphView({
  verdicts,
  linkingSummary: _linkingSummary,
  onSelect,
  onOverride,
}: CitationGraphViewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('combined');
  const [statusFilters, setStatusFilters] = useState<Set<CitationMappingStatus>>(
    new Set()
  );
  const [labelFilters, setLabelFilters] = useState<Set<ValidationLabel>>(
    new Set()
  );

  const filtered = useMemo(() => {
    return verdicts.filter((v) => {
      const statusOk =
        statusFilters.size === 0 || statusFilters.has(v.mapping_status);
      const labelOk = labelFilters.size === 0 || labelFilters.has(v.label);
      return statusOk && labelOk;
    });
  }, [verdicts, statusFilters, labelFilters]);

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

  const hasFilters = statusFilters.size > 0 || labelFilters.size > 0;

  return (
    <div className="space-y-4">
      {/* Stats bar */}
      <div className="flex flex-wrap gap-3 text-xs items-center">
        <span className="font-semibold text-muted-foreground">
          {filtered.length} / {stats.total} citations
        </span>
        {stats.overridden > 0 && (
          <span className="px-2 py-0.5 bg-amber-50 border border-amber-200 rounded text-amber-700">
            {stats.overridden} overridden
          </span>
        )}
        {stats.domainExc > 0 && (
          <span className="px-2 py-0.5 bg-amber-50 border border-amber-200 rounded text-amber-700">
            {stats.domainExc} domain exception
          </span>
        )}
        {hasFilters && (
          <button
            onClick={clearFilters}
            className="ml-auto text-xs underline hover:text-primary"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* View mode toggle */}
      <div className="flex gap-1 bg-muted rounded-lg p-1 w-fit">
        {(['integrity', 'source', 'combined'] as ViewMode[]).map((mode) => (
          <button
            key={mode}
            onClick={() => setViewMode(mode)}
            className={cn(
              'px-3 py-1 text-xs rounded-md transition-colors capitalize',
              viewMode === mode
                ? 'bg-background shadow-sm font-medium'
                : 'hover:bg-background/50'
            )}
          >
            {mode === 'integrity' ? 'Integrity' : mode === 'source' ? 'Source' : 'Combined'}
          </button>
        ))}
      </div>

      {/* Filter chips */}
      <div className="space-y-2">
        {(viewMode === 'integrity' || viewMode === 'combined') && (
          <div className="flex flex-wrap gap-1.5">
            <span className="text-xs text-muted-foreground w-16 pt-1">Integrity:</span>
            {STATUS_FILTERS.map((f) => {
              const count = stats.integrityCounts[f.value] ?? 0;
              const active = statusFilters.has(f.value);
              return (
                <button
                  key={f.value}
                  onClick={() => toggleStatus(f.value)}
                  className={cn(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors border',
                    active
                      ? 'border-primary bg-primary/10 font-medium'
                      : 'hover:border-primary/50',
                    count === 0 && 'opacity-40'
                  )}
                >
                  {f.label}
                  {count > 0 && (
                    <span className="ml-0.5 text-muted-foreground">({count})</span>
                  )}
                </button>
              );
            })}
          </div>
        )}
        {(viewMode === 'source' || viewMode === 'combined') && (
          <div className="flex flex-wrap gap-1.5">
            <span className="text-xs text-muted-foreground w-16 pt-1">Source:</span>
            {LABEL_FILTERS.map((f) => {
              const count = stats.sourceCounts[f.value] ?? 0;
              const active = labelFilters.has(f.value);
              return (
                <button
                  key={f.value}
                  onClick={() => toggleLabel(f.value)}
                  className={cn(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors border',
                    active
                      ? 'border-primary bg-primary/10 font-medium'
                      : 'hover:border-primary/50',
                    count === 0 && 'opacity-40'
                  )}
                >
                  {f.label}
                  {count > 0 && (
                    <span className="ml-0.5 text-muted-foreground">({count})</span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Verdicts list */}
      {filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground italic py-8 text-center">
          Khong co citation nao phu hop filter.
        </p>
      ) : (
        <div className="space-y-2">
          {filtered.map((v, i) => (
            <div
              key={v.citation_id ?? i}
              onClick={() => onSelect(v)}
              className={cn(
                'border rounded-lg p-3 cursor-pointer transition-colors hover:border-primary/50 hover:bg-muted/30',
                v.is_overridden && 'border-amber-300 bg-amber-50/30',
                v.domain_exception && 'border-dashed border-amber-300'
              )}
            >
              <div className="flex items-start gap-3">
                {/* Status */}
                <div className="shrink-0">
                  <MappingStatusBadge status={v.mapping_status} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm font-medium truncate"
                    title={v.citation_raw}
                  >
                    {v.citation_raw}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    {viewMode !== 'integrity' && (
                      <VerdictBadge label={v.label} />
                    )}
                    {viewMode === 'combined' && (
                      <span className="text-xs text-muted-foreground">
                        src: {(v.confidence * 100).toFixed(0)}% | link: {(v.mapping_confidence * 100).toFixed(0)}%
                      </span>
                    )}
                    {v.is_overridden && (
                      <span className="text-xs text-amber-600">overridden</span>
                    )}
                  </div>
                </div>

                {/* Confidence bar mini */}
                <div className="shrink-0 w-16 pt-1 hidden sm:block">
                  <div className="flex gap-1 items-end h-6">
                    <div
                      className="flex-1 bg-green-400 rounded-t"
                      style={{ height: `${(v.confidence * 100).toFixed(0)}%`, minHeight: '2px' }}
                      title={`Source: ${(v.confidence * 100).toFixed(0)}%`}
                    />
                    <div
                      className="flex-1 bg-blue-400 rounded-t"
                      style={{ height: `${(v.mapping_confidence * 100).toFixed(0)}%`, minHeight: '2px' }}
                      title={`Link: ${(v.mapping_confidence * 100).toFixed(0)}%`}
                    />
                  </div>
                </div>

                {/* Override */}
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
          ))}
        </div>
      )}
    </div>
  );
}
