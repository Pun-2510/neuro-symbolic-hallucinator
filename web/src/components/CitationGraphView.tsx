import { useState, useMemo } from 'react';
import type {
  Verdict,
  CitationMappingStatus,
  ValidationLabel,
  MappingStatusSummary,
  MatchedSource,
} from '@/api/client';
import { MappingStatusBadge } from './MappingStatusBadge';
import { VerdictBadge } from './VerdictBadge';
import { OverrideControls } from './OverrideControls';
import { cn } from '@/lib/utils';
import {
  ChevronUp,
  ChevronDown,
  Search,
  Database,
  GitBranch,
  Scale,
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  ChevronRight,
  ChevronDown as ChevronDownIcon,
  ExternalLink,
  Layers,
  Hash,
  ListChecks,
  Target,
} from 'lucide-react';

/* ============================================================
   SourceLogic — Evidence Graph Component
   Based on UX/UI Concept Section 16: Evidence Graph visualization
   Shows: Reference → Database Sources → Candidates → Similarity → Rules → Verdict
   ============================================================ */

interface EvidenceGraphProps {
  verdict: Verdict;
  onClose?: () => void;
}

interface GraphNode {
  id: string;
  label: string;
  type: 'reference' | 'source' | 'candidate' | 'similarity' | 'rules' | 'verdict';
  status: 'success' | 'warning' | 'error' | 'neutral' | 'no_match';
  detail?: string;
  children?: GraphNode[];
  matchedSource?: MatchedSource;
  similarityScore?: number;
  rulesTriggered?: string[];
}

interface CandidateInfo {
  source: string;
  matched: boolean;
  fields?: string[];
  url?: string;
}

const VERDICT_CONFIG: Record<ValidationLabel, { icon: typeof CheckCircle2; color: string; bgColor: string; borderColor: string; label: string }> = {
  verified: {
    icon: CheckCircle2,
    color: 'text-emerald-600 dark:text-emerald-400',
    bgColor: 'bg-emerald-50 dark:bg-emerald-950',
    borderColor: 'border-emerald-300 dark:border-emerald-700',
    label: 'VERIFIED',
  },
  metadata_error: {
    icon: AlertTriangle,
    color: 'text-amber-600 dark:text-amber-400',
    bgColor: 'bg-amber-50 dark:bg-amber-950',
    borderColor: 'border-amber-300 dark:border-amber-700',
    label: 'METADATA ERROR',
  },
  suspected_hallucination: {
    icon: XCircle,
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-950',
    borderColor: 'border-red-300 dark:border-red-700',
    label: 'SUSPECTED HALLUCINATION',
  },
  unresolved: {
    icon: HelpCircle,
    color: 'text-slate-600 dark:text-slate-400',
    bgColor: 'bg-slate-50 dark:bg-slate-800',
    borderColor: 'border-slate-300 dark:border-slate-600',
    label: 'UNRESOLVED',
  },
};

const SOURCE_CONFIG: Record<string, { color: string; bgColor: string; label: string }> = {
  crossref: { color: 'text-blue-600 dark:text-blue-400', bgColor: 'bg-blue-50 dark:bg-blue-950', label: 'Crossref' },
  openalex: { color: 'text-teal-600 dark:text-teal-400', bgColor: 'bg-teal-50 dark:bg-teal-950', label: 'OpenAlex' },
  s2: { color: 'text-purple-600 dark:text-purple-400', bgColor: 'bg-purple-50 dark:bg-purple-950', label: 'Semantic Scholar' },
  arxiv: { color: 'text-orange-600 dark:text-orange-400', bgColor: 'bg-orange-50 dark:bg-orange-950', label: 'arXiv' },
  core: { color: 'text-green-600 dark:text-green-400', bgColor: 'bg-green-50 dark:bg-green-950', label: 'CORE' },
};

function SourceIcon({ source }: { source: string }) {
  const config = SOURCE_CONFIG[source.toLowerCase()] ?? SOURCE_CONFIG.s2;
  return (
    <Database className={cn('h-4 w-4', config.color)} />
  );
}

function EvidenceGraphNode({
  node,
  level = 0,
  isLast = false,
  onExpand,
  expandedNodes,
}: {
  node: GraphNode;
  level?: number;
  isLast?: boolean;
  onExpand?: (id: string) => void;
  expandedNodes?: Set<string>;
}) {
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded = expandedNodes?.has(node.id) ?? false;

  const getNodeStyles = () => {
    switch (node.status) {
      case 'success':
        return 'border-emerald-300 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950';
      case 'warning':
        return 'border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950';
      case 'error':
        return 'border-red-300 bg-red-50 dark:border-red-700 dark:bg-red-950';
      case 'no_match':
        return 'border-slate-300 bg-slate-100 dark:border-slate-600 dark:bg-slate-800';
      default:
        return 'border-indigo-200 bg-indigo-50 dark:border-indigo-700 dark:bg-indigo-950';
    }
  };

  const getNodeIcon = () => {
    switch (node.type) {
      case 'reference':
        return <GitBranch className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />;
      case 'source':
        return <SourceIcon source={node.label} />;
      case 'candidate':
        return node.status === 'success'
          ? <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          : <XCircle className="h-4 w-4 text-red-400" />;
      case 'similarity':
        return <Target className="h-4 w-4 text-purple-600 dark:text-purple-400" />;
      case 'rules':
        return <Hash className="h-4 w-4 text-amber-600 dark:text-amber-400" />;
      case 'verdict':
        const config = VERDICT_CONFIG[node.label as ValidationLabel] ?? VERDICT_CONFIG.unresolved;
        const Icon = config.icon;
        return <Icon className={cn('h-5 w-5', config.color)} />;
      default:
        return null;
    }
  };

  return (
    <div className="relative">
      {/* Connection line */}
      {level > 0 && (
        <div
          className="absolute"
          style={{
            left: `${level * 24 - 12}px`,
            top: '-12px',
            height: '12px',
            width: '12px',
          }}
        >
          <div className="h-full border-l-2 border-slate-300 dark:border-slate-600" />
          <div className="absolute bottom-0 left-0 w-6 border-b-2 border-slate-300 dark:border-slate-600" />
        </div>
      )}

      {/* Node content */}
      <div
        className={cn(
          'flex items-center gap-2 rounded-lg border p-2 mb-1 cursor-pointer transition-all hover:shadow-sm',
          getNodeStyles()
        )}
        style={{ marginLeft: `${level * 24}px` }}
        onClick={() => hasChildren && onExpand?.(node.id)}
      >
        {getNodeIcon()}
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate block">
            {node.label}
          </span>
          {node.detail && (
            <span className="text-xs text-slate-500 dark:text-slate-400 truncate block">
              {node.detail}
            </span>
          )}
        </div>
        {hasChildren && (
          <span className="text-slate-400">
            {isExpanded ? (
              <ChevronDownIcon className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </span>
        )}
        {node.matchedSource?.url && (
          <a
            href={node.matchedSource.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div className="relative">
          {node.children!.map((child, idx) => (
            <EvidenceGraphNode
              key={child.id}
              node={child}
              level={level + 1}
              isLast={idx === node.children!.length - 1}
              onExpand={onExpand}
              expandedNodes={expandedNodes}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function EvidenceGraph({ verdict, onClose }: EvidenceGraphProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(
    new Set(['reference', 'sources', 'rules'])
  );
  const [showAllCandidates, setShowAllCandidates] = useState(false);

  const toggleExpand = (id: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Group matched sources by database
  const sourcesByDatabase = useMemo(() => {
    const grouped: Record<string, CandidateInfo[]> = {
      crossref: [],
      openalex: [],
      s2: [],
      core: [],
      arxiv: [],
    };

    for (const source of verdict.matched_sources) {
      const dbKey = source.source.toLowerCase();
      if (grouped[dbKey]) {
        grouped[dbKey].push({
          source: dbKey,
          matched: source.matched_fields.length > 0,
          fields: source.matched_fields,
          url: source.url,
        });
      }
    }

    return grouped;
  }, [verdict.matched_sources]);

  // Check if any database found candidates
  const databasesWithResults = Object.entries(sourcesByDatabase).filter(
    ([, candidates]) => candidates.length > 0
  );

  const databasesWithoutResults = Object.entries(sourcesByDatabase).filter(
    ([, candidates]) => candidates.length === 0
  );

  // Build graph structure
  const graphData: GraphNode = {
    id: 'reference',
    label: verdict.citation_raw || 'Unknown Citation',
    type: 'reference',
    status: 'neutral',
    detail: `Confidence: ${(verdict.confidence * 100).toFixed(0)}%`,
    children: [
      {
        id: 'sources',
        label: 'Academic Databases',
        type: 'source',
        status: (databasesWithResults.length > 0 ? 'success' : 'no_match') as GraphNode['status'],
        detail: `${databasesWithResults.length} sources queried`,
        children: [
          // Sources with results
          ...databasesWithResults.flatMap(([db, candidates]) => {
            const config = SOURCE_CONFIG[db] ?? SOURCE_CONFIG.s2;
            return candidates.map((c, idx) => ({
              id: `${db}-${idx}`,
              label: config.label,
              type: 'candidate' as const,
              status: (c.matched ? 'success' : 'no_match') as GraphNode['status'],
              detail: c.matched
                ? `Matched: ${c.fields?.join(', ') || 'fields'}`
                : 'No match found',
              matchedSource: { source: db, matched_fields: c.fields || [], checked_at: '' },
              children: c.matched && c.url ? [{
                id: `${db}-${idx}-link`,
                label: 'View Publication',
                type: 'candidate' as const,
                status: 'success' as GraphNode['status'],
                detail: c.url,
                matchedSource: { source: db, matched_fields: c.fields || [], checked_at: '', url: c.url },
              }] : undefined,
            }));
          }),
          // Sources without results
          ...databasesWithoutResults.map(([db]) => {
            const config = SOURCE_CONFIG[db] ?? SOURCE_CONFIG.s2;
            return {
              id: `no-${db}`,
              label: config.label,
              type: 'candidate' as const,
              status: 'no_match' as GraphNode['status'],
              detail: 'No results',
            };
          }),
        ],
      },
      {
        id: 'similarity',
        label: 'Semantic Matching',
        type: 'similarity',
        status: (verdict.confidence >= 0.7 ? 'success' : verdict.confidence >= 0.4 ? 'warning' : 'error') as GraphNode['status'],
        detail: `Best match: ${(verdict.confidence * 100).toFixed(0)}%`,
      },
      {
        id: 'rules',
        label: 'Verification Rules',
        type: 'rules',
        status: (verdict.triggered_rules.length > 0 ? 'warning' : 'success') as GraphNode['status'],
        detail: verdict.triggered_rules.length > 0
          ? verdict.triggered_rules.join(', ')
          : 'No rules triggered',
        children: verdict.triggered_rules.length > 0 ? [
          {
            id: 'rules-list',
            label: `${verdict.triggered_rules.length} rules triggered`,
            type: 'rules' as const,
            status: 'warning' as GraphNode['status'],
            detail: verdict.reasoning,
          },
          ...verdict.mismatched_fields.map((field, idx) => ({
            id: `mismatch-${idx}`,
            label: `${field} mismatch`,
            type: 'rules' as const,
            status: 'error' as GraphNode['status'],
            detail: 'Field does not match retrieved source',
          })),
        ] : undefined,
      },
      {
        id: 'verdict',
        label: verdict.label.toUpperCase().replace('_', ' '),
        type: 'verdict',
        status: (verdict.label === 'verified' ? 'success'
          : verdict.label === 'metadata_error' ? 'warning'
          : verdict.label === 'suspected_hallucination' ? 'error'
          : 'neutral') as GraphNode['status'],
        detail: verdict.reasoning,
      },
    ],
  };

  const verdictConfig = VERDICT_CONFIG[verdict.label] ?? VERDICT_CONFIG.unresolved;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={cn('p-2 rounded-lg', verdictConfig.bgColor)}>
            <Layers className={cn('h-5 w-5', verdictConfig.color)} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Evidence Graph
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Click nodes to expand details
            </p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
          >
            Close
          </button>
        )}
      </div>

      {/* Verdict summary */}
      <div className={cn('p-4 rounded-lg border', verdictConfig.bgColor, verdictConfig.borderColor)}>
        <div className="flex items-center gap-2 mb-2">
          {(() => {
            const Icon = verdictConfig.icon;
            return <Icon className={cn('h-5 w-5', verdictConfig.color)} />;
          })()}
          <span className={cn('font-bold text-sm', verdictConfig.color)}>
            {verdictConfig.label}
          </span>
        </div>
        <p className="text-sm text-slate-700 dark:text-slate-300">
          {verdict.reasoning}
        </p>
        {verdict.triggered_rules.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {verdict.triggered_rules.map((rule) => (
              <span
                key={rule}
                className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded text-xs font-mono"
              >
                <ListChecks className="h-3 w-3" />
                {rule}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Graph */}
      <div className="border rounded-lg p-4 bg-slate-50 dark:bg-slate-900 overflow-x-auto">
        <div className="min-w-fit">
          <EvidenceGraphNode
            node={graphData}
            level={0}
            onExpand={toggleExpand}
            expandedNodes={expandedNodes}
          />
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 text-xs text-slate-500 dark:text-slate-400">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded border border-emerald-300 bg-emerald-50" />
          <span>Match found</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded border border-slate-300 bg-slate-100" />
          <span>No match</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded border border-amber-300 bg-amber-50" />
          <span>Warning</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded border border-red-300 bg-red-50" />
          <span>Error/Issue</span>
        </div>
      </div>

      {/* Mismatched fields */}
      {verdict.mismatched_fields.length > 0 && (
        <div className="border rounded-lg p-3">
          <h4 className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-2">
            Mismatched Fields
          </h4>
          <div className="flex flex-wrap gap-2">
            {verdict.mismatched_fields.map((field) => (
              <span
                key={field}
                className="px-2 py-1 bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-400 rounded text-xs border border-red-200 dark:border-red-800"
              >
                {field}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Raw source details */}
      <details className="group">
        <summary className="text-xs text-slate-500 dark:text-slate-400 cursor-pointer hover:text-slate-700 dark:hover:text-slate-300">
          View raw source data ({verdict.matched_sources.length} sources)
        </summary>
        <pre className="mt-2 p-3 bg-slate-100 dark:bg-slate-800 rounded-lg text-xs overflow-x-auto">
          {JSON.stringify(verdict.matched_sources, null, 2)}
        </pre>
      </details>
    </div>
  );
}

/* ============================================================
   SourceLogic — Citation Graph View Component
   Based on UX/UI Concept Section 9: Citation ↔ Reference Mapping
   ============================================================ */

interface CitationGraphViewProps {
  verdicts: Verdict[];
  linkingSummary?: MappingStatusSummary;
  onSelect: (v: Verdict) => void;
  onOverride?: (
    verdict: Verdict,
    req: Parameters<typeof import('@/api/client').api.overrideVerdict>[1]
  ) => Promise<void>;
}

/* ============================================================
   Filter Configuration
   ============================================================ */
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

/* ============================================================
   SortIcon Component
   ============================================================ */
function SortIcon({ sorted, direction }: { sorted: boolean; direction: 'asc' | 'desc' }) {
  if (!sorted) return <ChevronUp className="h-3 w-3 text-slate-400" />;
  return direction === 'asc'
    ? <ChevronUp className="h-3 w-3 text-indigo-600 dark:text-indigo-400" />
    : <ChevronDown className="h-3 w-3 text-indigo-600 dark:text-indigo-400" />;
}

/* ============================================================
   Main CitationGraphView Component
   ============================================================ */
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
  const [searchQuery, setSearchQuery] = useState('');

  // Filter verdicts based on search and filters
  const filtered = useMemo(() => {
    return verdicts.filter((v) => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        if (!v.citation_raw?.toLowerCase().includes(query)) {
          return false;
        }
      }
      // Status filter
      const statusOk = statusFilters.size === 0 || statusFilters.has(v.mapping_status);
      // Label filter
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

  // Calculate stats
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
      {/* Stats bar */}
      <div className="flex flex-wrap gap-3 text-xs items-center">
        <span className="font-semibold text-slate-600 dark:text-slate-400">
          {filtered.length} / {stats.total} citations
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
            onClick={clearFilters}
            className="ml-auto text-xs underline hover:text-indigo-600 dark:hover:text-indigo-400"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* View mode toggle */}
      <div className="flex gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1 w-fit">
        {(['integrity', 'source', 'combined'] as ViewMode[]).map((mode) => (
          <button
            key={mode}
            onClick={() => setViewMode(mode)}
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
      <div className="space-y-2">
        {(viewMode === 'integrity' || viewMode === 'combined') && (
          <div className="flex flex-wrap gap-1.5">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-16 pt-1">Integrity:</span>
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
                      ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950 font-medium'
                      : 'hover:border-indigo-300 dark:hover:border-indigo-600',
                    count === 0 && 'opacity-40'
                  )}
                >
                  {f.label}
                  {count > 0 && (
                    <span className="text-slate-400">({count})</span>
                  )}
                </button>
              );
            })}
          </div>
        )}
        {(viewMode === 'source' || viewMode === 'combined') && (
          <div className="flex flex-wrap gap-1.5">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-16 pt-1">Source:</span>
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
                      ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950 font-medium'
                      : 'hover:border-indigo-300 dark:hover:border-indigo-600',
                    count === 0 && 'opacity-40'
                  )}
                >
                  {f.label}
                  {count > 0 && (
                    <span className="text-slate-400">({count})</span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Verdicts list */}
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
              className={cn(
                'border rounded-lg p-3 cursor-pointer transition-colors hover:border-indigo-400 dark:hover:border-indigo-600 hover:bg-slate-50 dark:hover:bg-slate-800/50',
                v.is_overridden && 'border-amber-300 dark:border-amber-700 bg-amber-50/30 dark:bg-amber-950/20',
                v.domain_exception && 'border-dashed border-amber-300 dark:border-amber-700'
              )}
            >
              <div className="flex items-start gap-3">
                {/* Status */}
                <div className="shrink-0">
                  <MappingStatusBadge status={v.mapping_status} size="sm" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate"
                    title={v.citation_raw}
                  >
                    {v.citation_raw}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    {viewMode !== 'integrity' && (
                      <VerdictBadge verdict={v.label} size="sm" />
                    )}
                    {viewMode === 'combined' && (
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        src: {(v.confidence * 100).toFixed(0)}% | link: {(v.mapping_confidence * 100).toFixed(0)}%
                      </span>
                    )}
                    {v.is_overridden && (
                      <span className="text-xs text-amber-600 dark:text-amber-400">overridden</span>
                    )}
                  </div>
                </div>

                {/* Confidence bar mini */}
                <div className="shrink-0 w-16 pt-1 hidden sm:block">
                  <div className="flex gap-1 items-end h-6">
                    <div
                      className="flex-1 bg-emerald-400 rounded-t"
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
