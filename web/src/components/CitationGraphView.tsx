/**
 * Backward-compatibility shim.
 *
 * The implementation has been split into sub-files under ./CitationGraph/
 * (CitationGraphView, EvidenceGraph, EvidenceGraphNode, SourceIcon,
 * verdictConfig, types). This module re-exports them so existing imports
 * keep working.
 */
export {
  CitationGraphView,
  EvidenceGraph,
  EvidenceGraphNode,
  SourceIcon,
  SortIcon,
  VERDICT_CONFIG,
  SOURCE_CONFIG,
  buildEvidenceGraph,
} from './CitationGraph';
export type { GraphNode, SourceConfig, VerdictConfig } from './CitationGraph';
