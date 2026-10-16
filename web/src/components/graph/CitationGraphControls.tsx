import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CitationMappingStatus, ValidationLabel } from '@/api/client';

/* ============================================================
   Filter Configuration (shared with parent)
   ============================================================ */

export const STATUS_FILTERS: { value: CitationMappingStatus; label: string }[] = [
  { value: 'matched', label: 'Matched' },
  { value: 'missing_reference', label: 'Missing Ref' },
  { value: 'uncited_reference', label: 'Uncited Ref' },
  { value: 'in_text_mismatch', label: 'Mismatch' },
  { value: 'duplicate_reference', label: 'Duplicate' },
  { value: 'ambiguous_mapping', label: 'Ambiguous' },
  { value: 'style_inconsistent', label: 'Style Issue' },
  { value: 'unresolved', label: 'Unresolved' },
];

export const LABEL_FILTERS: { value: ValidationLabel; label: string }[] = [
  { value: 'verified', label: 'Verified' },
  { value: 'metadata_error', label: 'Meta Error' },
  { value: 'suspected_hallucination', label: 'Suspected' },
  { value: 'unresolved', label: 'Unresolved' },
];

export type ViewMode = 'integrity' | 'source' | 'combined';

/* ============================================================
   CitationGraphControls
   ------------------------------------------------------------
   Search + view-mode toggle + integrity/label filter chips.
   Pure presentational: tất cả state + setters do parent quản lý.
   ============================================================ */

export interface CitationGraphStats {
  total: number;
  integrityCounts: Partial<Record<CitationMappingStatus, number>>;
  sourceCounts: Partial<Record<ValidationLabel, number>>;
  overridden: number;
  domainExc: number;
}

export interface CitationGraphControlsProps {
  // Search
  searchQuery: string;
  onSearchChange: (q: string) => void;

  // View mode
  viewMode: ViewMode;
  onViewModeChange: (m: ViewMode) => void;

  // Filter state
  statusFilters: Set<CitationMappingStatus>;
  onToggleStatus: (s: CitationMappingStatus) => void;
  labelFilters: Set<ValidationLabel>;
  onToggleLabel: (l: ValidationLabel) => void;

  // Stats + clear
  filteredCount: number;
  stats: CitationGraphStats;
  hasFilters: boolean;
  onClearFilters: () => void;
}

export function CitationGraphControls({
  searchQuery,
  onSearchChange,
  viewMode,
  onViewModeChange,
  statusFilters,
  onToggleStatus,
  labelFilters,
  onToggleLabel,
  filteredCount,
  stats,
  hasFilters,
  onClearFilters,
}: CitationGraphControlsProps) {
  return (
    <div className="space-y-3">
      {/* Stats bar */}
      <div
        role="group"
        aria-label="Filter and search controls"
        className="flex flex-wrap gap-3 text-xs items-center"
      >
        <span className="font-semibold text-slate-600 dark:text-slate-300">
          {filteredCount} / {stats.total} citations
        </span>
        {stats.overridden > 0 && (
          <span className="px-2 py-0.5 bg-amber-50 border border-amber-200 dark:bg-amber-950 dark:border-amber-800 rounded text-amber-700 dark:text-amber-300">
            {stats.overridden} overridden
          </span>
        )}
        {stats.domainExc > 0 && (
          <span className="px-2 py-0.5 bg-amber-50 border border-amber-200 dark:bg-amber-950 dark:border-amber-800 rounded text-amber-700 dark:text-amber-300">
            {stats.domainExc} domain exception
          </span>
        )}
        {hasFilters && (
          <button
            onClick={onClearFilters}
            className="ml-auto text-xs underline hover:text-indigo-600 dark:hover:text-indigo-400"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* View mode toggle */}
      <div
        role="group"
        aria-label="Citation view mode"
        className="flex gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1 w-fit"
      >
        {(['integrity', 'source', 'combined'] as ViewMode[]).map((mode) => (
          <button
            key={mode}
            onClick={() => onViewModeChange(mode)}
            aria-pressed={viewMode === mode}
            className={cn(
              'px-3 py-1 text-xs rounded-md transition-colors capitalize',
              viewMode === mode
                ? 'bg-white dark:bg-slate-700 shadow-sm font-medium'
                : 'hover:bg-white/50 dark:hover:bg-slate-700/50'
            )}
          >
            {mode === 'integrity' ? 'Integrity' : mode === 'source' ? 'Source' : 'Combined'}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search
          className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"
          aria-hidden="true"
        />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search citations..."
          aria-label="Search citations"
          className="input pl-9 py-2 text-sm"
        />
      </div>

      {/* Filter chips */}
      <div className="space-y-2">
        {(viewMode === 'integrity' || viewMode === 'combined') && (
          <div
            role="group"
            aria-label="Filter by integrity status"
            className="flex flex-wrap gap-1.5"
          >
            <span className="text-xs text-slate-600 dark:text-slate-300 w-16 pt-1">
              Integrity:
            </span>
            {STATUS_FILTERS.map((f) => {
              const count = stats.integrityCounts[f.value] ?? 0;
              const active = statusFilters.has(f.value);
              return (
                <button
                  key={f.value}
                  onClick={() => onToggleStatus(f.value)}
                  aria-pressed={active}
                  className={cn(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors border',
                    active
                      ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950 font-medium'
                      : 'hover:border-indigo-300 dark:hover:border-indigo-600',
                    count === 0 && 'opacity-40'
                  )}
                >
                  {f.label}
                  {count > 0 && <span className="text-slate-400">({count})</span>}
                </button>
              );
            })}
          </div>
        )}
        {(viewMode === 'source' || viewMode === 'combined') && (
          <div
            role="group"
            aria-label="Filter by validation label"
            className="flex flex-wrap gap-1.5"
          >
            <span className="text-xs text-slate-600 dark:text-slate-300 w-16 pt-1">
              Source:
            </span>
            {LABEL_FILTERS.map((f) => {
              const count = stats.sourceCounts[f.value] ?? 0;
              const active = labelFilters.has(f.value);
              return (
                <button
                  key={f.value}
                  onClick={() => onToggleLabel(f.value)}
                  aria-pressed={active}
                  className={cn(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors border',
                    active
                      ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950 font-medium'
                      : 'hover:border-indigo-300 dark:hover:border-indigo-600',
                    count === 0 && 'opacity-40'
                  )}
                >
                  {f.label}
                  {count > 0 && <span className="text-slate-400">({count})</span>}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
