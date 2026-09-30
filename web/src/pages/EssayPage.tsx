import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, type AnalysisReport, type Verdict, type MatchedSource, type CitationLink } from '@/api/client';
import { CISScoreCard } from '@/components/CISScoreCard';
import { VerdictTable } from '@/components/VerdictTable';
import { CitationDetailDrawer } from '@/components/CitationDetailDrawer';
import { isUrlResource } from '@/lib/verdictExplanation';
import {
  FileText,
  Download,
  ArrowLeft,
  Loader2,
  ChevronRight,
  Clock,
  Quote,
  AlertCircle,
  GitBranch,
  FileSearch,
  Link2
} from 'lucide-react';

/* ============================================================
   SourceLogic — Essay/Report Page Component
   Based on UX/UI Concept Section 7-8: Dashboard + Citations & References
   ============================================================ */

type TabType = 'overview' | 'citations' | 'references';

export function EssayPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Verdict | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  useEffect(() => {
    if (!id) return;
    // Validate essay ID - security: prevent NaN or invalid IDs
    const numericId = parseInt(id, 10);
    if (isNaN(numericId) || numericId <= 0) {
      setError('Invalid essay ID');
      return;
    }

    let cancelled = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    const tryFetch = async () => {
      try {
        const data = await api.getEssay(numericId);
        if (cancelled) return;
        if (data) {
          // Got the report
          setReport(data);
          setError(null);
          if (pollTimer) clearInterval(pollTimer);
        } else {
          // 425 — pipeline still running. Poll status instead.
          const status = await api.getEssayStatus(numericId);
          if (cancelled) return;
          if (status.status === 'failed') {
            setError(status.error ?? 'Pipeline failed.');
            if (pollTimer) clearInterval(pollTimer);
            return;
          }
          if (status.status === 'completed') {
            // Race condition — try once more
            const retry = await api.getEssay(numericId);
            if (retry) {
              setReport(retry);
              setError(null);
              if (pollTimer) clearInterval(pollTimer);
              return;
            }
          }
          // Otherwise keep polling via status
          if (!pollTimer) {
            pollTimer = setInterval(tryFetch, 2000);
          }
        }
      } catch (err) {
        if (!cancelled) setError('Failed to load report. Please try again.');
      }
    };

    tryFetch();

    return () => {
      cancelled = true;
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [id]);

  async function handleOverride(verdict: Verdict, req: Parameters<typeof api.overrideVerdict>[1]) {
    const updated = await api.overrideVerdict(Number(id), req);
    setReport((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        verdicts: prev.verdicts.map((v) =>
          v.citation_id === updated.citation_id ? updated : v
        ),
      };
    });
    setSelected(updated);
  }

  if (error) {
    return (
      <div className="card p-6 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-red-700 dark:text-red-300">Error: {error}</p>
            <Link to="/history" className="text-indigo-600 dark:text-indigo-400 hover:underline mt-2 inline-block">
              ← Back to Reports
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 text-indigo-600 dark:text-indigo-400 animate-spin" />
        <span className="ml-3 text-slate-600 dark:text-slate-400">Loading report...</span>
      </div>
    );
  }

  // Calculate stats based on UX/UI Concept
  const academicVerdicts = report.verdicts.filter((v) => !isUrlResource(v));
  const references = report.references ?? [];
  // Use the backend-extracted citation list when available so repeated
  // occurrences are preserved.  Fall back to deduplicated verdicts only
  // for legacy reports that do not carry extracted_citations.
  const extractedInText = report.extracted_citations ?? [];
  // NEW v1.9 — every reference a citation links to.
  //
  // One occurrence can cite several references at once ("[9, 10]" → ref-0009
  // AND ref-0010). The backend now sends ``citation_links``; reports produced
  // before v1.9 only carry the scalar ``citation_link``, so fall back to it.
  const linksOf = (c: { citation_links?: CitationLink[]; citation_link?: CitationLink }) =>
    c.citation_links?.length ? c.citation_links : c.citation_link ? [c.citation_link] : [];

  const refIds = (c: { citation_links?: CitationLink[]; citation_link?: CitationLink }) =>
    linksOf(c)
      .map((l) => l.reference_id)
      .filter((id): id is string => Boolean(id));

  // FIX v1.7: extractedInText now carries mapping_status from CitationLinker.
  // Map: reference_id → verdict (so in-text can show the linked reference's label).
  // v1.9: a verdict may itself link to several references, so index every edge.
  const verdictByRefId = new Map(
    (report.verdicts ?? []).flatMap((v) =>
      refIds(v).map((refId) => [refId, v] as const)
    )
  );

  // NEW v1.8 — dedupe in-text citations by raw_text.
  // The backend stores EVERY occurrence (66 rows for 33 unique in-text on a
  // typical essay), which made the Citations tab show 4× "[24]". We group by
  // raw_text, keep the first occurrence's linking data, and count occurrences
  // so the row can render a "× N" badge. A row may link to several distinct
  // references (e.g. "[9, 10]"), so we also collect every linked ref id.
  const inTextGroups = new Map<
    string,
    { citation: (typeof extractedInText)[number]; occurrences: number; refIds: string[] }
  >();
  for (const citation of extractedInText) {
    const key = citation.raw_text.trim();
    const existing = inTextGroups.get(key);
    if (existing) {
      existing.occurrences += 1;
      for (const refId of refIds(citation)) {
        if (!existing.refIds.includes(refId)) existing.refIds.push(refId);
      }
      // Prefer a group member that actually carries a link — the linker may
      // match one occurrence but not another with the same raw text.
      if (linksOf(existing.citation).length === 0 && linksOf(citation).length > 0) {
        existing.citation = citation;
      }
    } else {
      inTextGroups.set(key, {
        citation,
        occurrences: 1,
        refIds: refIds(citation),
      });
    }
  }
  const dedupedInText = Array.from(inTextGroups.values());

  // NEW v1.8/FIX — map "ref-NNNN" → the reference it names, and derive the
  // label from the SAME number so the two can never disagree.
  //
  // The backend (``_run_linking``) numbers the bibliography 1-BASED:
  // ``f"ref-{idx + 1:04d}"``, so ``ref-0003`` IS reference #3 — its suffix is
  // the number we display. (Verified against a real report: for all 27
  // references the printed "[N]" marker equals the ``ref-NNNN`` suffix.)
  // Previously this map was keyed 0-based while the label re-added +1, so
  // every row displayed "Ref #25" for ``[24]`` and resolved the wrong entry.
  const refByLinkId = new Map<string, (typeof references)[number]>();
  references.forEach((ref, idx) => {
    refByLinkId.set(`ref-${String(idx + 1).padStart(4, '0')}`, ref);
  });

  /** "Ref #3 — World Health Organization (2023)" for a linked in-text row. */
  const formatLinkedReference = (refIds: string[]): string | null => {
    if (refIds.length === 0) return null;
    const parts = refIds.map((refId) => {
      // The suffix is already the 1-based reference number — never add 1.
      const num = Number.parseInt(refId.replace(/^ref-/, ''), 10);
      const ref = refByLinkId.get(refId);
      if (!ref || Number.isNaN(num)) return refId;
      const author = ref.authors?.length
        ? ref.authors[0].split(',')[0].trim()
        : parseAuthorDisplay(ref.raw_text);
      const year = ref.year || parseYear(ref.raw_text);
      return `Ref #${num} — ${author}${year ? ` (${year})` : ''}`;
    });
    return parts.join(' · ');
  };

  const inTextVerdicts =
    extractedInText.length > 0
      ? extractedInText.map((citation) => {
          // NEW v1.7: read real mapping_status from citation (set by CitationLinker)
          const mappingStatus = citation.mapping_status ?? 'matched';
          // If this in-text citation links to a reference, inherit the reference's label
          const linkedRefIds = refIds(citation);
          const linkedVerdict =
            linkedRefIds.map((id) => verdictByRefId.get(id)).find(Boolean) ?? null;
          return {
            citation_id: `c${citation.id ?? citation.raw_text}`,
            citation_raw: citation.raw_text,
            citation_type: citation.citation_type,
            // In-text inherits mapping_status from CitationLinker
            mapping_status: mappingStatus,
            mapping_confidence: citation.mapping_confidence ?? 0,
            // Inherit label from linked reference verdict if available, otherwise
            // derive from mapping_status (matched → verified, missing → unresolved)
            label: linkedVerdict?.label
              ?? (mappingStatus === 'matched' ? 'verified' : 'unresolved'),
            confidence: citation.mapping_confidence ?? citation.confidence,
            reasoning: linkedVerdict?.reasoning ?? '',
            triggered_rules: linkedVerdict?.triggered_rules ?? [],
            mismatched_fields: linkedVerdict?.mismatched_fields ?? [],
            matched_sources: linkedVerdict?.matched_sources ?? [],
            citation_links: linksOf(citation),
            citation_link: citation.citation_link ?? linksOf(citation)[0],
            is_overridden: false,
          };
        })
      : report.verdicts.filter(
          (v) =>
            v.citation_type === 'in_text' ||
            v.citation_type === 'numeric' ||
            (!v.citation_type && references.length === 0)
        );
  const stats = {
    total: academicVerdicts.length,
    verified: academicVerdicts.filter((v) => v.label === 'verified').length,
    metadataError: academicVerdicts.filter((v) => v.label === 'metadata_error').length,
    suspectedHallucination: academicVerdicts.filter((v) => v.label === 'suspected_hallucination').length,
    unverifiable: academicVerdicts.filter((v) => v.label === 'unresolved').length,
  };

  const coverage = stats.total > 0 ? Math.round((stats.verified / stats.total) * 100) : 0;

  // Section 8: Citations & References data extraction
  const getCitationStatus = (v: Verdict) => {
    if (v.label === 'resource') return 'URL Resource';
    if (v.label === 'verified') return 'Verified';
    if (v.label === 'metadata_error') return 'Metadata Issue';
    if (v.label === 'suspected_hallucination') return 'Hallucination';
    if (v.mapping_status === 'missing_reference') return 'No Reference';
    if (v.mapping_status === 'unresolved') return 'Unresolved';
    return 'Unverifiable';
  };

  const getCitationStatusColor = (v: Verdict) => {
    if (v.label === 'verified') return 'text-emerald-600 dark:text-emerald-400';
    if (v.label === 'metadata_error') return 'text-amber-600 dark:text-amber-400';
    if (v.label === 'suspected_hallucination') return 'text-red-600 dark:text-red-400';
    return 'text-slate-500 dark:text-slate-400';
  };

  const getReferenceStatus = (v: Verdict) => {
    if (v.label === 'resource') return 'URL Resource';
    if (v.label === 'verified') return 'Verified';
    if (v.label === 'metadata_error') return 'Metadata Error';
    if (v.label === 'suspected_hallucination') return 'Likely Hallucinated';
    return 'Unverifiable';
  };

  const getReferenceStatusColor = (v: Verdict) => {
    if (v.label === 'verified') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
    if (v.label === 'metadata_error') return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
    if (v.label === 'suspected_hallucination') return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
    return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400';
  };

  // Parse author names from citation
  const parseAuthorDisplay = (rawText: string): string => {
    // Extract author names from raw citation text
    const etAlMatch = rawText.match(/(\w+)\s*(?:et\.?\s*al\.?)/i);
    if (etAlMatch) return etAlMatch[1] + ' et al.';
    const andMatch = rawText.match(/(\w+)\s*&\s*(\w+)/i);
    if (andMatch) return `${andMatch[1]} & ${andMatch[2]}`;
    const parenMatch = rawText.match(/\(([^)]+)\)/);
    if (parenMatch) return parenMatch[1].split(',')[0].trim();
    return rawText.slice(0, 40);
  };

  // Extract year from citation
  const parseYear = (rawText: string): string | null => {
    const yearMatch = rawText.match(/\(?(19|20)\d{2}[a-z]?\)?/);
    return yearMatch ? yearMatch[0].replace(/[()]/g, '') : null;
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Header - Section 7 */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <Link
            to="/history"
            className="inline-flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 mb-3 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Reports
          </Link>
          <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-slate-100">
            {report.filename}
          </h1>
          <div className="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400 mt-2 flex-wrap">
            <span className="flex items-center gap-1.5">
              <FileText className="h-4 w-4" />
              {report.num_pages} pages
            </span>
            <span className="text-slate-300 dark:text-slate-600">·</span>
            <span className="flex items-center gap-1.5">
              <Quote className="h-4 w-4" />
              {report.num_citations} citations
            </span>
            {report.style_profile && (
              <>
                <span className="text-slate-300 dark:text-slate-600">·</span>
                <span className="tag tag-primary">{report.style_profile.style}</span>
              </>
            )}
            <span className="text-slate-300 dark:text-slate-600">·</span>
            <span className="flex items-center gap-1.5">
              <Clock className="h-4 w-4" />
              ID #{report.essay_id}
            </span>
          </div>
        </div>

        {/* Export Actions */}
        <div className="flex gap-2 flex-wrap">
          <a
            href={api.downloadReport(report.essay_id, 'json')}
            className="btn-ghost btn-sm"
            download
          >
            <Download className="h-3.5 w-3.5" />
            JSON
          </a>
          <a
            href={api.downloadReport(report.essay_id, 'csv')}
            className="btn-ghost btn-sm"
            download
          >
            <Download className="h-3.5 w-3.5" />
            CSV
          </a>
          <a
            href={api.downloadReport(report.essay_id, 'pdf')}
            className="btn-primary btn-sm"
            download
          >
            <Download className="h-3.5 w-3.5" />
            PDF
          </a>
        </div>
      </div>

      {/* Stats Overview - Section 7 */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <div className="stat-card text-center">
          <p className="text-3xl font-bold text-slate-900 dark:text-slate-100">{stats.total}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Total</p>
        </div>
        <div className="stat-card text-center">
          <p className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">{stats.verified}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Verified</p>
        </div>
        <div className="stat-card text-center">
          <p className="text-3xl font-bold text-amber-600 dark:text-amber-400">{stats.metadataError}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Metadata Error</p>
        </div>
        <div className="stat-card text-center">
          <p className="text-3xl font-bold text-red-600 dark:text-red-400">{stats.suspectedHallucination}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Suspected</p>
        </div>
        <div className="stat-card text-center">
          <p className="text-3xl font-bold text-indigo-600 dark:text-indigo-400">{coverage}%</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Coverage</p>
        </div>
      </div>

      {/* CIS Score */}
      {academicVerdicts.length > 0 && <CISScoreCard cis={report.cis.score} />}

      {/* Quick Links - Section 7: Report navigation */}
      <div className="flex gap-3 flex-wrap">
        <Link
          to={`/verification/report/${id}/issues`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors text-sm"
        >
          <AlertCircle className="h-4 w-4" />
          Issues
        </Link>
        <Link
          to={`/verification/report/${id}/document`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors text-sm"
        >
          <FileSearch className="h-4 w-4" />
          Document
        </Link>
        <Link
          to={`/verification/report/${id}/consistency`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors text-sm"
        >
          <Link2 className="h-4 w-4" />
          Consistency
        </Link>
        <Link
          to={`/verification/report/${id}/trace`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors text-sm"
        >
          <GitBranch className="h-4 w-4" />
          Logic Trace
        </Link>
      </div>

      {/* Section 8: Tab Navigation - Citations & References */}
      <div className="border-b border-slate-200 dark:border-slate-700">
        <nav className="flex gap-6" aria-label="Report sections">
          {(['overview', 'citations', 'references'] as TabType[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`relative pb-3 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'text-indigo-600 dark:text-indigo-400'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
              {tab === 'citations' && (
                <span className="ml-2 text-xs bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded-full">
                  {dedupedInText.length}
                </span>
              )}
              {tab === 'references' && (
                <span className="ml-2 text-xs bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded-full">
                  {references.length}
                </span>
              )}
              {activeTab === tab && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-600 dark:bg-indigo-400 rounded-full" />
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Section 8: Citations Tab */}
      {activeTab === 'citations' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100">
              Citations
            </h2>
            <span className="text-sm text-slate-500 dark:text-slate-400">
              {dedupedInText.length} unique ·{' '}
              {dedupedInText.reduce((sum, g) => sum + g.occurrences, 0)} occurrences
            </span>
          </div>

          <div className="card overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Citation
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Linked Reference
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider w-16">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                 {dedupedInText.map((group, index) => {
                  const verdict = inTextVerdicts.find(
                    (v) => v.citation_id === `c${group.citation.id ?? group.citation.raw_text}`
                  );
                  if (!verdict) return null;
                  return (
                  <tr
                    key={group.citation.id ?? `${group.citation.raw_text}-${index}`}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-slate-400 dark:text-slate-500">
                          [{index + 1}]
                        </span>
                        <span className="text-sm text-slate-700 dark:text-slate-300 line-clamp-2">
                          {group.citation.raw_text}
                        </span>
                        {group.occurrences > 1 && (
                          <span
                            className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
                            title={`Xuất hiện ${group.occurrences} lần trong bài`}
                          >
                            ×{group.occurrences}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-slate-600 dark:text-slate-400">
                        {(() => {
                          const linked = formatLinkedReference(group.refIds);
                          if (linked) return linked;
                          if (verdict.mapping_status === 'missing_reference') {
                            return '— No Reference —';
                          }
                          return '—';
                        })()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {verdict.label === 'verified' ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Linked
                        </span>
                      ) : verdict.label === 'metadata_error' ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600 dark:text-amber-400">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          Metadata Issue
                        </span>
                      ) : verdict.label === 'suspected_hallucination' ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600 dark:text-red-400">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                          Hallucination
                        </span>
                      ) : verdict.label === 'resource' ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-violet-600 dark:text-violet-400">
                          URL Resource
                        </span>
                      ) : verdict.mapping_status === 'missing_reference' ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-orange-600 dark:text-orange-400">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          No Reference
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                          Unverifiable
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => setSelected(verdict)}
                        className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 text-sm font-medium"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Section 8: References Tab */}
      {activeTab === 'references' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100">
              References
            </h2>
            <span className="text-sm text-slate-500 dark:text-slate-400">
              {references.length} detected
            </span>
          </div>

          <div className="card overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider w-16">
                    #
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Reference
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Cited in Text
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Verification
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider w-16">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                 {references.map((reference, index) => {
                   const authorDisplay = reference.authors?.join(', ') || parseAuthorDisplay(reference.raw_text);
                   const yearDisplay = reference.year || parseYear(reference.raw_text);
                   const matchingVerdict = report.verdicts.find(
                     (v) => v.citation_raw === reference.raw_text
                   );

                  return (
                    <tr
                       key={reference.id ?? `${reference.raw_text}-${index}`}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <span className="text-sm font-mono text-slate-500 dark:text-slate-400">
                          {index + 1}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="space-y-1">
                          <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                            {authorDisplay}{yearDisplay && ` (${yearDisplay})`}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-1">
                           {reference.raw_text.slice(0, 160)}
                          </p>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {/* NEW v1.8 — is this bibliography entry actually cited
                            anywhere in the body text? Uncited references are a
                            common integrity signal (padding the bibliography). */}
                        {(() => {
                          const count = reference.cited_in_text_count ?? 0;
                          const pages = reference.cited_on_pages ?? [];
                          if (count > 0) {
                            const pageList = pages.length
                              ? `trên trang ${pages.join(', ')}`
                              : 'trong bài';
                            return (
                              <span
                                className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400"
                                title={`Được trích dẫn ${count} lần ${pageList}`}
                              >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                ×{count}
                              </span>
                            );
                          }
                          return (
                            <span
                              className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 dark:text-slate-500"
                              title="Không được trích dẫn trong phần nội dung"
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                              </svg>
                              Not cited
                            </span>
                          );
                        })()}
                      </td>
                      <td className="px-4 py-3 text-center">
                           <span className="inline-block px-2.5 py-1 text-xs font-medium rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                           Reference entry
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                           onClick={() => matchingVerdict && setSelected(matchingVerdict)}
                          className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 text-sm font-medium"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Overview Tab Content - Section 7 Dashboard */}
      {activeTab === 'overview' && (
        <>
          <div>
            <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100">
              Citation Verification Results
            </h2>
          </div>

          <VerdictTable
            verdicts={report.verdicts}
            onSelect={setSelected}
            onOverride={handleOverride}
          />
        </>
      )}

      {/* Detail Drawer - Section 10: Reference Inspector */}
      {selected && (
        <CitationDetailDrawer
          verdict={selected}
          onClose={() => setSelected(null)}
          onOverride={(req) => handleOverride(selected, req)}
        />
      )}
    </div>
  );
}
