import { useMemo } from 'react';
import { AlertCircle, FileText, Link, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import type { AnalysisReport, Verdict, CitationMappingStatus } from '@/api/client';
import { VerdictBadge } from './VerdictBadge';
import { cn } from '@/lib/utils';

/* ============================================================
   SourceLogic — Orphan Detection Component
   Based on UX/UI Concept Section 17: Orphan Detection
   Detects citations without references and references never cited
   ============================================================ */

interface OrphanDetectionProps {
  report: AnalysisReport;
  onCitationClick?: (verdict: Verdict) => void;
  className?: string;
}

interface OrphanGroup {
  type: 'citation_without_reference' | 'reference_never_cited';
  verdicts: Verdict[];
  count: number;
}

/* ============================================================
   Orphan Item Component
   ============================================================ */

function OrphanItem({
  verdict,
  index,
  onClick,
  isSelected,
}: {
  verdict: Verdict;
  index: number;
  onClick?: () => void;
  isSelected?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-start gap-3 p-3 rounded-xl border text-left transition-all',
        isSelected
          ? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-950'
          : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 bg-white dark:bg-slate-800'
      )}
    >
      {/* Status indicator */}
      <div className="shrink-0 mt-0.5">
        <span className="text-xs font-mono text-slate-400 dark:text-slate-500">
          #{index + 1}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-slate-700 dark:text-slate-300 line-clamp-2">
          {verdict.citation_raw}
        </p>
        <div className="flex items-center gap-2 mt-2">
          <VerdictBadge verdict={verdict.label} size="sm" />
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {verdict.mapping_status.replace(/_/g, ' ')}
          </span>
        </div>
      </div>

      {/* Mapping confidence */}
      {verdict.mapping_confidence !== undefined && (
        <div className="shrink-0 text-right">
          <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
            {Math.round(verdict.mapping_confidence * 100)}%
          </span>
        </div>
      )}
    </button>
  );
}

/* ============================================================
   Orphan Group Component
   ============================================================ */

function OrphanGroup({
  group,
  onCitationClick,
  selectedCitation,
  defaultOpen = true,
}: {
  group: OrphanGroup;
  onCitationClick?: (verdict: Verdict) => void;
  selectedCitation?: Verdict | null;
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const config = {
    citation_without_reference: {
      title: 'Citation without Reference',
      description: 'Citations that appear in document but have no matching bibliography entry',
      icon: <AlertCircle className="h-5 w-5" />,
      color: 'orange',
      bgLight: 'bg-orange-50',
      bgDark: 'dark:bg-orange-950',
      borderLight: 'border-orange-200',
      borderDark: 'dark:border-orange-800',
      textLight: 'text-orange-600',
      textDark: 'dark:text-orange-400',
    },
    reference_never_cited: {
      title: 'Reference Never Cited',
      description: 'References in bibliography that are never cited in the document',
      icon: <FileText className="h-5 w-5" />,
      color: 'slate',
      bgLight: 'bg-slate-50',
      bgDark: 'dark:bg-slate-800',
      borderLight: 'border-slate-200',
      borderDark: 'dark:border-slate-700',
      textLight: 'text-slate-600',
      textDark: 'dark:text-slate-400',
    },
  };

  const style = config[group.type];

  return (
    <div className="space-y-3">
      {/* Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'w-full flex items-center justify-between p-4 rounded-xl border transition-all',
          style.bgLight,
          style.bgDark,
          style.borderLight,
          style.borderDark
        )}
      >
        <div className="flex items-center gap-3">
          <div className={cn('p-2 rounded-lg bg-white dark:bg-slate-900 border', style.borderLight, style.borderDark)}>
            <span className={cn(style.textLight, style.textDark)}>{style.icon}</span>
          </div>
          <div className="text-left">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {style.title}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {style.description}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className={cn(
            'text-lg font-bold',
            style.textLight,
            style.textDark
          )}>
            {group.count}
          </span>
          {isOpen ? (
            <ChevronDown className={cn('h-5 w-5', style.textLight, style.textDark)} />
          ) : (
            <ChevronRight className={cn('h-5 w-5', style.textLight, style.textDark)} />
          )}
        </div>
      </button>

      {/* Items */}
      {isOpen && (
        <div className="space-y-2 pl-2">
          {group.verdicts.map((verdict, idx) => (
            <OrphanItem
              key={verdict.citation_id}
              verdict={verdict}
              index={idx}
              onClick={() => onCitationClick?.(verdict)}
              isSelected={selectedCitation?.citation_id === verdict.citation_id}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ============================================================
   useState import for local state
   ============================================================ */

import { useState } from 'react';

/* ============================================================
   Main OrphanDetection Component
   ============================================================ */

export function OrphanDetection({
  report,
  onCitationClick,
  className = '',
}: OrphanDetectionProps) {
  // Analyze orphan cases from report data
  const orphanGroups = useMemo(() => {
    const groups: OrphanGroup[] = [];

    // Citations without references
    const citationsWithoutRef = report.verdicts.filter(
      (v) => v.mapping_status === 'missing_reference'
    );

    // References never cited (uncited references)
    const uncitedRefs = report.verdicts.filter(
      (v) => v.mapping_status === 'uncited_reference'
    );

    // In-text mismatch (citation exists but doesn't match reference)
    const inTextMismatches = report.verdicts.filter(
      (v) => v.mapping_status === 'in_text_mismatch'
    );

    if (citationsWithoutRef.length > 0) {
      groups.push({
        type: 'citation_without_reference',
        verdicts: citationsWithoutRef,
        count: citationsWithoutRef.length,
      });
    }

    if (uncitedRefs.length > 0) {
      groups.push({
        type: 'reference_never_cited',
        verdicts: uncitedRefs,
        count: uncitedRefs.length,
      });
    }

    return groups;
  }, [report.verdicts]);

  // Calculate total orphan count
  const totalOrphans = orphanGroups.reduce((sum, g) => sum + g.count, 0);

  // Calculate linked count
  const linkedCount = report.verdicts.filter(
    (v) => v.mapping_status === 'matched'
  ).length;

  // Calculate consistency score
  const consistencyScore = report.verdicts.length > 0
    ? Math.round((linkedCount / report.verdicts.length) * 100)
    : 100;

  if (orphanGroups.length === 0) {
    return (
      <div className={cn('space-y-4', className)}>
        {/* Summary */}
        <div className="card p-6 text-center">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center">
              <Link className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
            </div>
          </div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            Citation Consistency Check
          </h3>
          <p className="text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
            All citations are properly linked to references. No orphan citations or uncited references detected.
          </p>
          <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-emerald-50 dark:bg-emerald-950 rounded-lg">
            <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              {consistencyScore}%
            </span>
            <span className="text-sm text-slate-500 dark:text-slate-400">consistency</span>
          </div>
        </div>

        {/* Consistency stats */}
        <div className="grid grid-cols-3 gap-3">
          <div className="stat-card text-center">
            <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{linkedCount}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Properly Linked</p>
          </div>
          <div className="stat-card text-center">
            <p className="text-2xl font-bold text-slate-600 dark:text-slate-400">0</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Missing Refs</p>
          </div>
          <div className="stat-card text-center">
            <p className="text-2xl font-bold text-slate-600 dark:text-slate-400">0</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Uncited Refs</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Summary */}
      <div className={cn(
        'card p-4 border-l-4 border-l-orange-500',
      )}>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-orange-100 dark:bg-orange-900">
            <AlertCircle className="h-5 w-5 text-orange-600 dark:text-orange-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Citation Consistency Issues
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {totalOrphans} issues detected in citation-reference linking
            </p>
          </div>
          <div className="text-right">
            <span className="text-2xl font-bold text-orange-600 dark:text-orange-400">
              {consistencyScore}%
            </span>
            <p className="text-xs text-slate-500 dark:text-slate-400">consistency</p>
          </div>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="stat-card text-center">
          <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{linkedCount}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Properly Linked</p>
        </div>
        <div className="stat-card text-center border-orange-200 dark:border-orange-800">
          <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {orphanGroups.find(g => g.type === 'citation_without_reference')?.count || 0}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Missing Refs</p>
        </div>
        <div className="stat-card text-center border-slate-200 dark:border-slate-700">
          <p className="text-2xl font-bold text-slate-600 dark:text-slate-400">
            {orphanGroups.find(g => g.type === 'reference_never_cited')?.count || 0}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Uncited Refs</p>
        </div>
        <div className="stat-card text-center">
          <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">{report.verdicts.length}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Total Citations</p>
        </div>
      </div>

      {/* Orphan groups */}
      <div className="space-y-4">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">
          Orphan Cases
        </h4>
        {orphanGroups.map((group) => (
          <OrphanGroup
            key={group.type}
            group={group}
            onCitationClick={onCitationClick}
          />
        ))}
      </div>

      {/* Recommendations */}
      <div className="card p-4 bg-slate-50 dark:bg-slate-800/50">
        <h4 className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-2">
          Recommendations
        </h4>
        <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
          {orphanGroups.some(g => g.type === 'citation_without_reference') && (
            <li className="flex items-start gap-2">
              <span className="text-orange-500">•</span>
              <span>Add missing references to bibliography or verify citation accuracy</span>
            </li>
          )}
          {orphanGroups.some(g => g.type === 'reference_never_cited') && (
            <li className="flex items-start gap-2">
              <span className="text-orange-500">•</span>
              <span>Either cite these references in the document or remove them from bibliography</span>
            </li>
          )}
          <li className="flex items-start gap-2">
            <span className="text-indigo-500">•</span>
            <span>Review citation style consistency throughout the document</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
