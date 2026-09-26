import { useState, useMemo } from 'react';
import { VerdictBadge } from './VerdictBadge';
import { ChevronDown, ChevronUp, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Verdict } from '@/api/client';

/* ============================================================
   SourceLogic — Verdict Table Component
   Based on UX/UI Concept Sections 8: Citations & References
   ============================================================ */

interface VerdictTableProps {
  verdicts: Verdict[];
  onSelect: (verdict: Verdict) => void;
  onOverride?: (verdict: Verdict, req: any) => void;
}

type SortField = 'citation_num' | 'label' | 'confidence' | 'mapping_status';
type SortDirection = 'asc' | 'desc';

/* ============================================================
   SortIcon Component
   ============================================================ */
function SortIcon({ sorted, direction }: { sorted: boolean; direction: 'asc' | 'desc' }) {
  if (!sorted) return <ChevronUp className="h-3 w-3 text-slate-400" />;
  return direction === 'asc'
    ? <ChevronUp className="h-3 w-3 text-indigo-600 dark:text-indigo-400" />
    : <ChevronDown className="h-3 w-3 text-indigo-600 dark:text-indigo-400" />;
}

export function VerdictTable({ verdicts, onSelect, onOverride }: VerdictTableProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [verdictFilter, setVerdictFilter] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('citation_num');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  // Filter and sort verdicts
  const filteredVerdicts = useMemo(() => {
    let result = [...verdicts];

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (v) => v.citation_raw?.toLowerCase().includes(query)
      );
    }

    // Verdict filter
    if (verdictFilter) {
      result = result.filter((v) => v.label === verdictFilter);
    }

    // Sort
    result.sort((a, b) => {
      let aVal: any, bVal: any;
      switch (sortField) {
        case 'citation_num':
          aVal = a.citation_id ? parseInt(a.citation_id.split('-').pop() || '0') : 0;
          bVal = b.citation_id ? parseInt(b.citation_id.split('-').pop() || '0') : 0;
          break;
        case 'label':
          aVal = a.label || '';
          bVal = b.label || '';
          break;
        case 'confidence':
          aVal = a.confidence || 0;
          bVal = b.confidence || 0;
          break;
        case 'mapping_status':
          aVal = a.mapping_status || '';
          bVal = b.mapping_status || '';
          break;
        default:
          return 0;
      }
      if (typeof aVal === 'string') {
        return sortDirection === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    });

    return result;
  }, [verdicts, searchQuery, verdictFilter, sortField, sortDirection]);

  // Count by verdict
  const verdictCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    verdicts.forEach((v) => {
      const label = v.label || 'unresolved';
      counts[label] = (counts[label] || 0) + 1;
    });
    return counts;
  }, [verdicts]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  return (
    <div className="card overflow-hidden">
      {/* Table Header */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search citations..."
              className="input pl-9 py-2 text-sm"
            />
          </div>

          {/* Filter chips */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setVerdictFilter(null)}
              className={cn(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
                !verdictFilter
                  ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                  : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-indigo-300'
              )}
            >
              All
              <span className="text-slate-400">({verdicts.length})</span>
            </button>
            {Object.entries(verdictCounts)
              .filter(([v]) => ['verified', 'metadata_error', 'suspected_hallucination'].includes(v))
              .map(([label, count]) => (
                <button
                  key={label}
                  onClick={() => setVerdictFilter(label)}
                  className={cn(
                    'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
                    verdictFilter === label
                      ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                      : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-indigo-300'
                  )}
                >
                  {label.replace(/_/g, ' ')}
                  <span className="text-slate-400">({count})</span>
                </button>
              ))}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('citation_num')}
                  className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
                >
                  #
                  <SortIcon sorted={sortField === 'citation_num'} direction={sortDirection} />
                </button>
              </th>
              <th className="px-4 py-3 text-left">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Citation
                </span>
              </th>
              <th className="px-4 py-3 text-left">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Source
                </span>
              </th>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('label')}
                  className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
                >
                  Status
                  <SortIcon sorted={sortField === 'label'} direction={sortDirection} />
                </button>
              </th>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={() => handleSort('confidence')}
                  className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
                >
                  Confidence
                  <SortIcon sorted={sortField === 'confidence'} direction={sortDirection} />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredVerdicts.map((verdict, idx) => (
              <tr
                key={verdict.citation_id}
                onClick={() => onSelect(verdict)}
                className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition-colors"
              >
                <td className="px-4 py-3">
                  <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
                    [{idx + 1}]
                  </span>
                </td>
                <td className="px-4 py-3 max-w-xs">
                  <p className="text-sm text-slate-900 dark:text-slate-100 truncate">
                    {verdict.citation_raw || 'Unknown citation'}
                  </p>
                </td>
                <td className="px-4 py-3 max-w-xs">
                  <p className="text-sm text-slate-600 dark:text-slate-400 truncate">
                    {verdict.reasoning ? verdict.reasoning.substring(0, 50) + '...' : 'No reasoning'}
                  </p>
                </td>
                <td className="px-4 py-3">
                  <VerdictBadge verdict={verdict.label} size="sm" />
                </td>
                <td className="px-4 py-3">
                  {verdict.confidence !== undefined && (
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-500 rounded-full"
                          style={{ width: `${(verdict.confidence || 0) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        {Math.round((verdict.confidence || 0) * 100)}%
                      </span>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Showing {filteredVerdicts.length} of {verdicts.length} citations
        </p>
      </div>
    </div>
  );
}
