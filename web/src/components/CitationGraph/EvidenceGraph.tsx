import { useState, useMemo } from 'react';
import { Layers, ListChecks } from 'lucide-react';
import type { Verdict } from '@/api/client';
import { getFieldDisplayName, getRuleDisplayName, getVerdictExplanation } from '@/lib/verdictExplanation';
import { EvidenceGraphNode } from './EvidenceGraphNode';
import type { GraphNode } from './types';
import { SOURCE_CONFIG } from './types';
import { VERDICT_CONFIG } from './verdictConfig';

interface EvidenceGraphProps {
  verdict: Verdict;
  onClose?: () => void;
}

interface CandidateInfo {
  source: string;
  matched: boolean;
  fields?: string[];
  url?: string;
}

const EXTERNAL_DBS = ['crossref', 'openalex', 's2', 'arxiv', 'core'];
const SOURCE_FLOW_ORDER = ['local_db', 'known_papers', 'crossref', 'openalex', 's2', 'arxiv', 'core'];

/**
 * Build the hierarchical evidence graph for a single verdict.
 * Exported for unit tests.
 */
export function buildEvidenceGraph(
  verdict: Verdict,
): { graph: GraphNode; isLocalOnly: boolean } {
  // Group matched sources by database
  const sourcesByDatabase: Record<string, CandidateInfo[]> = {};
  for (const source of verdict.matched_sources ?? []) {
    const dbKey = source.source.toLowerCase();
    const entry: CandidateInfo = {
      source: dbKey,
      matched: source.matched_fields.length > 0,
      fields: source.matched_fields,
      url: source.url,
    };
    if (sourcesByDatabase[dbKey]) {
      sourcesByDatabase[dbKey].push(entry);
    } else {
      sourcesByDatabase[dbKey] = [entry];
    }
  }

  const queriedExternalDbs = EXTERNAL_DBS.filter((key) => sourcesByDatabase[key]);

  const databasesWithResults = Object.entries(sourcesByDatabase)
    .filter(([, candidates]) => candidates.length > 0)
    .sort(([a], [b]) => {
      const ai = SOURCE_FLOW_ORDER.indexOf(a);
      const bi = SOURCE_FLOW_ORDER.indexOf(b);
      return (ai === -1 ? SOURCE_FLOW_ORDER.length : ai) - (bi === -1 ? SOURCE_FLOW_ORDER.length : bi);
    });

  const databasesWithoutResults: [string, CandidateInfo[]][] =
    Object.keys(sourcesByDatabase).length === 0
      ? EXTERNAL_DBS.map((db) => [db, []])
      : [];

  const isLocalOnly =
    databasesWithResults.length > 0 && queriedExternalDbs.length === 0;

  const graph: GraphNode = {
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
        detail: isLocalOnly
          ? 'Local database cache hit — no external APIs queried'
          : `${databasesWithResults.length} sources queried`,
        children: [
          ...databasesWithResults.flatMap(([db, candidates]) => {
            const config = SOURCE_CONFIG[db] ?? SOURCE_CONFIG.s2;
            return candidates.map((c, idx) => ({
              id: `${db}-${idx}`,
              label: config.label,
              type: 'candidate' as const,
              status: (c.matched ? 'success' : 'no_match') as GraphNode['status'],
              detail: c.matched
                ? `The ${(c.fields || []).map(getFieldDisplayName).join(', ') || 'available details'} match the citation.`
                : 'No match found',
              matchedSource: { source: db, matched_fields: c.fields || [], checked_at: '' },
              children: c.matched && c.url
                ? [{
                    id: `${db}-${idx}-link`,
                    label: 'View Publication',
                    type: 'candidate' as const,
                    status: 'success' as GraphNode['status'],
                    detail: c.url,
                    matchedSource: { source: db, matched_fields: c.fields || [], checked_at: '', url: c.url },
                  }]
                : undefined,
            }));
          }),
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
          ? verdict.triggered_rules.map(getRuleDisplayName).join('. ')
          : 'No additional warnings were raised.',
        children: verdict.triggered_rules.length > 0
          ? [
              {
                id: 'rules-list',
                label: `${verdict.triggered_rules.length} rules triggered`,
                type: 'rules' as const,
                status: 'warning' as GraphNode['status'],
                detail: getVerdictExplanation(verdict),
              },
              ...verdict.mismatched_fields.map((field, idx) => ({
                id: `mismatch-${idx}`,
                label: `${getFieldDisplayName(field).replace(/^the /, '')} needs review`,
                type: 'rules' as const,
                status: 'error' as GraphNode['status'],
                detail: 'This detail differs from the publication record we found.',
              })),
            ]
          : undefined,
      },
      {
        id: 'verdict',
        label: verdict.label.toUpperCase().replace('_', ' '),
        type: 'verdict',
        status: (verdict.label === 'verified' ? 'success'
          : verdict.label === 'metadata_error' ? 'warning'
          : verdict.label === 'suspected_hallucination' ? 'error'
          : 'neutral') as GraphNode['status'],
        detail: getVerdictExplanation(verdict),
      },
    ],
  };

  return { graph, isLocalOnly };
}

export function EvidenceGraph({ verdict, onClose }: EvidenceGraphProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(
    new Set(['reference', 'sources', 'rules'])
  );

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

  const { graph: graphData } = useMemo(
    () => buildEvidenceGraph(verdict),
    [verdict]
  );

  const verdictConfig = VERDICT_CONFIG[verdict.label] ?? VERDICT_CONFIG.unresolved;
  const Icon = verdictConfig.icon;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${verdictConfig.bgColor}`}>
            <Layers className={`h-5 w-5 ${verdictConfig.color}`} />
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
      <div className={`p-4 rounded-lg border ${verdictConfig.bgColor} ${verdictConfig.borderColor}`}>
        <div className="flex items-center gap-2 mb-2">
          <Icon className={`h-5 w-5 ${verdictConfig.color}`} />
          <span className={`font-bold text-sm ${verdictConfig.color}`}>
            {verdictConfig.label}
          </span>
        </div>
        <p className="text-sm text-slate-700 dark:text-slate-300">
          {getVerdictExplanation(verdict)}
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
      <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 bg-slate-50 dark:bg-slate-900 overflow-x-auto">
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
          <div className="w-3 h-3 rounded border border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-950" />
          <span>Match found</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded border border-slate-300 dark:border-slate-600 bg-slate-100 dark:bg-slate-800" />
          <span>No match</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950" />
          <span>Warning</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-950" />
          <span>Error/Issue</span>
        </div>
      </div>

      {/* Mismatched fields */}
      {verdict.mismatched_fields.length > 0 && (
        <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-3">
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
