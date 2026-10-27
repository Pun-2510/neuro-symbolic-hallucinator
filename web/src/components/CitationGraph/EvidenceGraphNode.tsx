import {
  GitBranch,
  CheckCircle2,
  XCircle,
  Target,
  Hash,
  ChevronRight,
  ChevronDown as ChevronDownIcon,
  ExternalLink,
  AlertTriangle,
} from 'lucide-react';
import type { GraphNode } from './types';
import { SourceIcon } from './SourceIcon';
import { VERDICT_CONFIG } from './verdictConfig';

interface EvidenceGraphNodeProps {
  node: GraphNode;
  level?: number;
  isLast?: boolean;
  onExpand?: (id: string) => void;
  expandedNodes?: Set<string>;
}

function getNodeStyles(status: GraphNode['status']): string {
  switch (status) {
    case 'success':
      return 'border-emerald-300/90 bg-emerald-50/80 dark:border-emerald-800/80 dark:bg-emerald-950/50';
    case 'warning':
      return 'border-amber-300/90 bg-amber-50/80 dark:border-amber-800/80 dark:bg-amber-950/50';
    case 'error':
      return 'border-red-300/90 bg-red-50/80 dark:border-red-800/80 dark:bg-red-950/50';
    case 'no_match':
      return 'border-slate-200 bg-slate-50/90 dark:border-slate-800 dark:bg-slate-900/60 opacity-75';
    default:
      return 'border-indigo-200/90 bg-indigo-50/70 dark:border-indigo-800/80 dark:bg-indigo-950/50';
  }
}

function getStatusPillStyles(status: GraphNode['status']): { text: string; className: string } {
  switch (status) {
    case 'success':
      return {
        text: 'PASS',
        className:
          'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800',
      };
    case 'warning':
      return {
        text: 'WARN',
        className:
          'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800',
      };
    case 'error':
      return {
        text: 'FAIL',
        className:
          'bg-red-100 text-red-800 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800',
      };
    case 'no_match':
      return {
        text: 'NO HIT',
        className:
          'bg-slate-200/70 text-slate-600 border-slate-300 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700',
      };
    default:
      return {
        text: 'ROOT',
        className:
          'bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-950 dark:text-indigo-300 dark:border-indigo-800',
      };
  }
}

function getNodeIcon(node: GraphNode): React.ReactNode {
  if (node.iconOverride) return node.iconOverride;
  switch (node.type) {
    case 'reference':
      return <GitBranch className="h-4 w-4 text-indigo-600 dark:text-indigo-400 shrink-0" />;
    case 'source':
      return <SourceIcon source={node.label} />;
    case 'candidate':
      return node.status === 'success' ? (
        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
      ) : node.status === 'warning' ? (
        <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0" />
      ) : (
        <XCircle className="h-4 w-4 text-slate-400 dark:text-slate-500 shrink-0" />
      );
    case 'similarity':
      return <Target className="h-4 w-4 text-violet-600 dark:text-violet-400 shrink-0" />;
    case 'rules':
      return <Hash className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0" />;
    case 'verdict': {
      const normalizedKey = node.label.toLowerCase().replace(/\s+/g, '_');
      const config =
        VERDICT_CONFIG[normalizedKey as keyof typeof VERDICT_CONFIG] ??
        VERDICT_CONFIG.unresolved;
      const Icon = config.icon;
      return <Icon className={`h-4 w-4 shrink-0 ${config.color}`} />;
    }
    default:
      return null;
  }
}

export function EvidenceGraphNode({
  node,
  level = 0,
  isLast: _isLast = false,
  onExpand,
  expandedNodes,
}: EvidenceGraphNodeProps) {
  const hasChildren = Boolean(node.children && node.children.length > 0);
  const isExpanded = expandedNodes?.has(node.id) ?? false;
  const matchedUrl =
    node.matchedSource &&
    typeof node.matchedSource === 'object' &&
    'url' in node.matchedSource
      ? (node.matchedSource as { url?: string }).url
      : undefined;
  const statusPill = getStatusPillStyles(node.status);

  return (
    <div className="relative" data-testid={`evidence-node-${node.id}`}>
      {/* Tree connector line */}
      {level > 0 && (
        <div
          className="absolute pointer-events-none"
          style={{
            left: `${level * 22 - 12}px`,
            top: '-10px',
            height: '24px',
            width: '12px',
          }}
        >
          <div className="h-full border-l-2 border-slate-300 dark:border-slate-700 rounded-bl-md" />
          <div className="absolute bottom-0 left-0 w-3 border-b-2 border-slate-300 dark:border-slate-700" />
        </div>
      )}

      {/* Node card */}
      <div
        className={`flex items-center gap-2.5 rounded-xl border px-3 py-2.5 mb-1.5 transition-all ${
          hasChildren ? 'cursor-pointer hover:shadow-xs' : 'cursor-default'
        } ${getNodeStyles(node.status)}`}
        style={{ marginLeft: `${level * 22}px` }}
        onClick={() => hasChildren && onExpand?.(node.id)}
      >
        {getNodeIcon(node)}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
              {node.label}
            </span>
            <span
              className={`px-1.5 py-0.2 rounded text-[9px] font-mono font-bold border ${statusPill.className}`}
            >
              {statusPill.text}
            </span>
            {hasChildren && (
              <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">
                ({node.children!.length})
              </span>
            )}
          </div>
          {node.detail && (
            <span className="text-xs text-slate-600 dark:text-slate-300 break-words leading-snug block mt-0.5">
              {node.detail}
            </span>
          )}
        </div>

        {matchedUrl && /^https?:\/\//i.test(matchedUrl) && (
          <a
            href={matchedUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-white/80 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-700 text-[10px] font-mono text-indigo-600 dark:text-indigo-400 hover:underline shrink-0"
            onClick={(e) => e.stopPropagation()}
            title="Open canonical source record"
          >
            <span>Source</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        )}

        {hasChildren && (
          <span className="text-slate-500 dark:text-slate-400 shrink-0 p-0.5 rounded hover:bg-black/5 dark:hover:bg-white/5">
            {isExpanded ? (
              <ChevronDownIcon className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </span>
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
