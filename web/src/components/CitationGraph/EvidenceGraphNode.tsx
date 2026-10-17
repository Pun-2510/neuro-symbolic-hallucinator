import {
  GitBranch,
  CheckCircle2,
  XCircle,
  Target,
  Hash,
  ChevronRight,
  ChevronDown as ChevronDownIcon,
  ExternalLink,
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
}

function getNodeIcon(node: GraphNode): React.ReactNode {
  switch (node.type) {
    case 'reference':
      return <GitBranch className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />;
    case 'source':
      return <SourceIcon source={node.label} />;
    case 'candidate':
      return node.status === 'success' ? (
        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
      ) : (
        <XCircle className="h-4 w-4 text-red-400" />
      );
    case 'similarity':
      return <Target className="h-4 w-4 text-purple-600 dark:text-purple-400" />;
    case 'rules':
      return <Hash className="h-4 w-4 text-amber-600 dark:text-amber-400" />;
    case 'verdict': {
      const config = VERDICT_CONFIG[node.label as keyof typeof VERDICT_CONFIG] ?? VERDICT_CONFIG.unresolved;
      const Icon = config.icon;
      return <Icon className={`h-5 w-5 ${config.color}`} />;
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
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded = expandedNodes?.has(node.id) ?? false;
  const matchedUrl =
    node.matchedSource && typeof node.matchedSource === 'object' && 'url' in node.matchedSource
      ? (node.matchedSource as { url?: string }).url
      : undefined;

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
        className={`flex items-center gap-2 rounded-lg border p-2 mb-1 cursor-pointer transition-all hover:shadow-sm ${getNodeStyles(node.status)}`}
        style={{ marginLeft: `${level * 24}px` }}
        onClick={() => hasChildren && onExpand?.(node.id)}
      >
        {getNodeIcon(node)}
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
        {matchedUrl && (
          <a
            href={matchedUrl}
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
