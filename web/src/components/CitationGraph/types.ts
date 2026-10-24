/**
 * SourceConfig — visual config for retrieval sources.
 * Shared by SourceIcon, EvidenceGraphNode, and the citation graph.
 */

import type { ReactNode } from 'react';

export interface SourceConfig {
  color: string;
  bgColor: string;
  label: string;
}

export const SOURCE_CONFIG: Record<string, SourceConfig> = {
  crossref: { color: 'text-blue-600 dark:text-blue-400', bgColor: 'bg-blue-50 dark:bg-blue-950', label: 'Crossref' },
  openalex: { color: 'text-teal-600 dark:text-teal-400', bgColor: 'bg-teal-50 dark:bg-teal-950', label: 'OpenAlex' },
  dblp: { color: 'text-purple-600 dark:text-purple-400', bgColor: 'bg-purple-50 dark:bg-purple-950', label: 'DBLP' },
  arxiv: { color: 'text-orange-600 dark:text-orange-400', bgColor: 'bg-orange-50 dark:bg-orange-950', label: 'arXiv' },
  openlibrary: { color: 'text-amber-600 dark:text-amber-400', bgColor: 'bg-amber-50 dark:bg-amber-950', label: 'OpenLibrary / Books' },
  europepmc: { color: 'text-green-600 dark:text-green-400', bgColor: 'bg-green-50 dark:bg-green-950', label: 'Europe PMC' },
  serpapi: { color: 'text-sky-600 dark:text-sky-400', bgColor: 'bg-sky-50 dark:bg-sky-950', label: 'Google Scholar' },
  local_db: { color: 'text-indigo-600 dark:text-indigo-400', bgColor: 'bg-indigo-50 dark:bg-indigo-950', label: 'Local Database' },
  known_papers: { color: 'text-cyan-600 dark:text-cyan-400', bgColor: 'bg-cyan-50 dark:bg-cyan-950', label: 'Known Papers' },
};

export interface GraphNode {
  id: string;
  label: string;
  type: 'reference' | 'source' | 'candidate' | 'similarity' | 'rules' | 'verdict';
  status: 'success' | 'warning' | 'error' | 'neutral' | 'no_match';
  detail?: string;
  children?: GraphNode[];
  matchedSource?: unknown;
  similarityScore?: number;
  rulesTriggered?: string[];
  /** Optional icon override (some node types inject their own icon JSX) */
  iconOverride?: ReactNode;
}
