import { useEffect, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, type AnalysisReport, type Verdict } from '@/api/client';
import { VerdictBadge } from '@/components/VerdictBadge';
import { MappingStatusBadge } from '@/components/MappingStatusBadge';
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  Link2Off,
  FileText,
  Quote,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
} from 'lucide-react';

/* ============================================================
   SourceLogic — Orphan Detection Page
   Based on UX/UI Concept Section 17: Orphan Detection
   Shows citations without references and references never cited
   ============================================================ */

// Types
interface OrphanCitation {
  citation_id: string;
  citation_raw: string;
  label: string;
  mapping_status: string;
}

interface UncitedReference {
  reference_id: string;
  raw_text: string;
}

function getOrphanStats(verdicts: Verdict[]) {
  // Citations without reference
  const citationsWithoutReference = verdicts.filter(
    (v) => v.mapping_status === 'missing_reference'
  );

  // References never cited
  const uncitedReferences = verdicts.filter(
    (v) => v.mapping_status === 'uncited_reference'
  );

  // Correctly linked
  const correctlyLinked = verdicts.filter(
    (v) => v.mapping_status === 'matched'
  );

  // Ambiguous mappings
  const ambiguousMappings = verdicts.filter(
    (v) => v.mapping_status === 'ambiguous_mapping'
  );

  return {
    citationsWithoutReference,
    uncitedReferences,
    correctlyLinked,
    ambiguousMappings,
    total: verdicts.length,
    correctlyLinkedCount: correctlyLinked.length,
    orphanCount: citationsWithoutReference.length,
    uncitedCount: uncitedReferences.length,
    ambiguousCount: ambiguousMappings.length,
  };
}

// Orphan citation card
function OrphanCitationCard({
  citation,
  index,
}: {
  citation: OrphanCitation;
  index: number;
}) {
  return (
    <div className="border border-red-200 dark:border-red-800 rounded-xl p-4 bg-red-50/50 dark:bg-red-950/30 hover:bg-red-100/50 dark:hover:bg-red-950/50 transition-colors">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-red-100 dark:bg-red-900/50">
          <Link2Off className="h-4 w-4 text-red-600 dark:text-red-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
              #{index + 1}
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 text-xs font-medium">
              <Link2Off className="h-3 w-3" />
              No Reference
            </span>
          </div>
          <p className="text-sm text-slate-700 dark:text-slate-300 line-clamp-2">
            {citation.citation_raw}
          </p>
          <div className="flex items-center gap-2 mt-2">
            <VerdictBadge verdict={citation.label} size="sm" />
            <MappingStatusBadge status={citation.mapping_status as any} size="sm" />
          </div>
        </div>
      </div>
    </div>
  );
}

// Uncited reference card
function UncitedReferenceCard({
  reference,
  index,
}: {
  reference: UncitedReference;
  index: number;
}) {
  return (
    <div className="border border-amber-200 dark:border-amber-800 rounded-xl p-4 bg-amber-50/50 dark:bg-amber-950/30 hover:bg-amber-100/50 dark:hover:bg-amber-950/50 transition-colors">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/50">
          <FileText className="h-4 w-4 text-amber-600 dark:text-amber-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
              #{index + 1}
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 text-xs font-medium">
              <Link2Off className="h-3 w-3" />
              Uncited
            </span>
          </div>
          <p className="text-sm text-slate-700 dark:text-slate-300 line-clamp-2">
            {reference.raw_text}
          </p>
        </div>
      </div>
    </div>
  );
}

// Section header component
function SectionHeader({
  title,
  icon,
  count,
  color,
  description,
}: {
  title: string;
  icon: React.ReactNode;
  count: number;
  color: 'red' | 'amber' | 'green' | 'blue';
  description: string;
}) {
  const colorClasses = {
    red: {
      bg: 'bg-red-50 dark:bg-red-950',
      border: 'border-red-200 dark:border-red-800',
      icon: 'text-red-600 dark:text-red-400',
      text: 'text-red-700 dark:text-red-300',
      count: 'text-red-600 dark:text-red-400',
    },
    amber: {
      bg: 'bg-amber-50 dark:bg-amber-950',
      border: 'border-amber-200 dark:border-amber-800',
      icon: 'text-amber-600 dark:text-amber-400',
      text: 'text-amber-700 dark:text-amber-300',
      count: 'text-amber-600 dark:text-amber-400',
    },
    green: {
      bg: 'bg-emerald-50 dark:bg-emerald-950',
      border: 'border-emerald-200 dark:border-emerald-800',
      icon: 'text-emerald-600 dark:text-emerald-400',
      text: 'text-emerald-700 dark:text-emerald-300',
      count: 'text-emerald-600 dark:text-emerald-400',
    },
    blue: {
      bg: 'bg-blue-50 dark:bg-blue-950',
      border: 'border-blue-200 dark:border-blue-800',
      icon: 'text-blue-600 dark:text-blue-400',
      text: 'text-blue-700 dark:text-blue-300',
      count: 'text-blue-600 dark:text-blue-400',
    },
  };

  const c = colorClasses[color];

  return (
    <div
      className={`flex items-center gap-4 p-4 rounded-xl border ${c.bg} ${c.border}`}
    >
      <div className={`p-3 rounded-xl bg-white/50 dark:bg-slate-900/50 ${c.icon}`}>
        {icon}
      </div>
      <div className="flex-1">
        <h3 className={`font-semibold ${c.text}`}>{title}</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400">{description}</p>
      </div>
      <div className={`text-3xl font-bold ${c.count}`}>{count}</div>
    </div>
  );
}

/* ============================================================
   Main OrphanDetectionPage Component
   ============================================================ */

export function OrphanDetectionPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'orphans' | 'uncited' | 'all'>('all');

  useEffect(() => {
    if (!id) return;
    api
      .getEssay(Number(id))
      .then(setReport)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed'));
  }, [id]);

  // Calculate orphan stats
  const stats = useMemo(() => {
    if (!report) return null;
    return getOrphanStats(report.verdicts);
  }, [report]);

  if (error) {
    return (
      <div className="card p-6 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-red-700 dark:text-red-300">Error: {error}</p>
            <Link
              to="/history"
              className="text-indigo-600 dark:text-indigo-400 hover:underline mt-2 inline-block"
            >
              ← Back to Reports
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!report || !stats) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 text-indigo-600 dark:text-indigo-400 animate-spin" />
        <span className="ml-3 text-slate-600 dark:text-slate-400">
          Loading citation data...
        </span>
      </div>
    );
  }

  const hasIssues = stats.orphanCount > 0 || stats.uncitedCount > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          to={`/verification/report/${id}`}
          className="inline-flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 mb-3 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Report
        </Link>
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-slate-100">
              Citation Consistency
            </h1>
            <p className="text-slate-500 dark:text-slate-400 mt-1">
              {report.filename}
            </p>
          </div>
        </div>
      </div>

      {/* Summary stats - UX/UI Concept Section 17 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SectionHeader
          title="Correctly Linked"
          icon={<CheckCircle className="h-6 w-6" />}
          count={stats.correctlyLinkedCount}
          color="green"
          description="Citations with matching references"
        />
        <SectionHeader
          title="Citations Without Reference"
          icon={<Link2Off className="h-6 w-6" />}
          count={stats.orphanCount}
          color="red"
          description="In-text citations without bibliography entry"
        />
        <SectionHeader
          title="Uncited References"
          icon={<FileText className="h-6 w-6" />}
          count={stats.uncitedCount}
          color="amber"
          description="Bibliography entries never cited in document"
        />
      </div>

      {/* Tab navigation */}
      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-700">
        {[
          { id: 'all', label: 'All', count: stats.total },
          { id: 'orphans', label: 'Orphans', count: stats.orphanCount },
          { id: 'uncited', label: 'Uncited', count: stats.uncitedCount },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            {tab.label}
            {tab.count > 0 && (
              <span
                className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                  activeTab === tab.id
                    ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300'
                    : 'bg-slate-100 dark:bg-slate-800'
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {hasIssues ? (
        <div className="space-y-6">
          {/* Citation consistency summary */}
          {(activeTab === 'all' || activeTab === 'orphans') &&
            stats.citationsWithoutReference.length > 0 && (
              <div>
                <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
                  <Link2Off className="h-5 w-5 text-red-600 dark:text-red-400" />
                  Citations Without Reference
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                  These citations appear in the document but no matching entry was
                  found in the bibliography.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {stats.citationsWithoutReference.map((citation, index) => (
                    <OrphanCitationCard
                      key={citation.citation_id}
                      citation={{
                        citation_id: citation.citation_id,
                        citation_raw: citation.citation_raw,
                        label: citation.label,
                        mapping_status: citation.mapping_status,
                      }}
                      index={index}
                    />
                  ))}
                </div>
              </div>
            )}

          {/* Uncited references */}
          {(activeTab === 'all' || activeTab === 'uncited') &&
            stats.uncitedReferences.length > 0 && (
              <div>
                <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
                  <FileText className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                  References Never Cited
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                  These references exist in the bibliography but are never cited in
                  the document.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {stats.uncitedReferences.map((reference, index) => (
                    <UncitedReferenceCard
                      key={reference.citation_id}
                      reference={{
                        reference_id: reference.citation_id,
                        raw_text: reference.citation_raw,
                      }}
                      index={index}
                    />
                  ))}
                </div>
              </div>
            )}

          {/* Ambiguous mappings */}
          {stats.ambiguousMappings.length > 0 && (
            <div>
              <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
                <HelpCircle className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                Ambiguous Mappings
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                These citations have multiple possible reference matches.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {stats.ambiguousMappings.map((citation, index) => (
                  <OrphanCitationCard
                    key={citation.citation_id}
                    citation={{
                      citation_id: citation.citation_id,
                      citation_raw: citation.citation_raw,
                      label: citation.label,
                      mapping_status: citation.mapping_status,
                    }}
                    index={index}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center">
              <CheckCircle className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
            </div>
          </div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            No Consistency Issues
          </h3>
          <p className="text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
            All citations are correctly linked to references and all references are
            cited in the document.
          </p>
        </div>
      )}

      {/* Citation Consistency Summary - UX/UI Concept Section 17 */}
      <div className="card p-5 bg-slate-50 dark:bg-slate-800/50">
        <h3 className="font-display text-sm font-semibold mb-4 text-slate-900 dark:text-slate-100">
          Citation Consistency Summary
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="flex items-center gap-3 p-3 bg-white dark:bg-slate-900 rounded-xl border border-emerald-200 dark:border-emerald-800">
            <CheckCircle className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            <div>
              <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
                {stats.correctlyLinkedCount}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Correctly linked
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-white dark:bg-slate-900 rounded-xl border border-red-200 dark:border-red-800">
            <Link2Off className="h-5 w-5 text-red-600 dark:text-red-400" />
            <div>
              <p className="text-xl font-bold text-red-600 dark:text-red-400">
                {stats.orphanCount}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Without reference
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-white dark:bg-slate-900 rounded-xl border border-amber-200 dark:border-amber-800">
            <FileText className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            <div>
              <p className="text-xl font-bold text-amber-600 dark:text-amber-400">
                {stats.uncitedCount}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Uncited
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-white dark:bg-slate-900 rounded-xl border border-blue-200 dark:border-blue-800">
            <HelpCircle className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <div>
              <p className="text-xl font-bold text-blue-600 dark:text-blue-400">
                {stats.ambiguousCount}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Ambiguous
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
