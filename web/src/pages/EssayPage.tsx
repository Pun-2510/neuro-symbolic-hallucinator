import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, type AnalysisReport, type Verdict } from '@/api/client';
import { CISScoreCard } from '@/components/CISScoreCard';
import { VerdictBadge } from '@/components/VerdictBadge';
import { CitationGraphView } from '@/components/CitationGraphView';
import { VerdictTable } from '@/components/VerdictTable';
import { CitationDetailDrawer } from '@/components/CitationDetailDrawer';
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

type DisplayMode = 'table' | 'graph';
type TabType = 'overview' | 'citations' | 'references';

export function EssayPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Verdict | null>(null);
  const [displayMode, setDisplayMode] = useState<DisplayMode>('graph');
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  useEffect(() => {
    if (!id) return;
    // Validate essay ID - security: prevent NaN or invalid IDs
    const numericId = parseInt(id, 10);
    if (isNaN(numericId) || numericId <= 0) {
      setError('Invalid essay ID');
      return;
    }
    api
      .getEssay(numericId)
      .then(setReport)
      .catch(() => setError('Failed to load report. Please try again.'));
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
  const stats = {
    total: report.verdicts.length,
    verified: report.verdicts.filter((v) => v.label === 'verified').length,
    metadataError: report.verdicts.filter((v) => v.label === 'metadata_error').length,
    suspectedHallucination: report.verdicts.filter((v) => v.label === 'suspected_hallucination').length,
    unverifiable: report.verdicts.filter((v) => v.label === 'unresolved').length,
  };

  const coverage = Math.round((stats.verified / stats.total) * 100);

  // Section 8: Citations & References data extraction
  const getCitationStatus = (v: Verdict) => {
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
      <CISScoreCard cis={report.cis.score} />

      {/* Style Profile */}
      {report.style_profile && (
        <div className="card p-5">
          <h3 className="font-display text-sm font-semibold mb-3 text-slate-900 dark:text-slate-100">
            Citation Style
          </h3>
          <span className="tag tag-primary">{report.style_profile.style}</span>
        </div>
      )}

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
                  {report.verdicts.length}
                </span>
              )}
              {tab === 'references' && (
                <span className="ml-2 text-xs bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded-full">
                  {report.verdicts.length}
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
              {report.verdicts.length} detected
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
                {report.verdicts.map((verdict, index) => (
                  <tr
                    key={verdict.citation_id}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-slate-400 dark:text-slate-500">
                          [{index + 1}]
                        </span>
                        <span className="text-sm text-slate-700 dark:text-slate-300 line-clamp-2">
                          {verdict.citation_raw}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-slate-600 dark:text-slate-400">
                        {verdict.citation_link?.reference_id
                          ? `Ref #${verdict.citation_link.reference_id}`
                          : verdict.mapping_status === 'missing_reference'
                            ? '— No Reference —'
                            : '—'}
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
                ))}
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
              {report.verdicts.length} detected
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
                    Verification
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider w-16">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {report.verdicts.map((verdict, index) => {
                  const authorDisplay = parseAuthorDisplay(verdict.citation_raw);
                  const yearDisplay = parseYear(verdict.citation_raw);

                  return (
                    <tr
                      key={verdict.citation_id}
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
                            {verdict.citation_raw.slice(0, 80)}
                          </p>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`inline-block px-2.5 py-1 text-xs font-medium rounded-full ${getReferenceStatusColor(verdict)}`}>
                          {getReferenceStatus(verdict)}
                        </span>
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

      {/* Overview Tab Content - Section 7 Dashboard */}
      {activeTab === 'overview' && (
        <>
          {/* Linking Summary - Section 9 */}
          {report.linking_summary && (
            <div className="card p-5">
              <h3 className="font-display text-sm font-semibold mb-4 text-slate-900 dark:text-slate-100">
                Citation Mapping Summary
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {Object.entries(report.linking_summary).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl"
                  >
                    <span className="text-sm text-slate-600 dark:text-slate-400 capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="font-bold text-slate-900 dark:text-slate-100">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* View Mode Toggle */}
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100">
              Citation Verification Results
            </h2>
            <div className="flex gap-1 bg-slate-100 dark:bg-slate-800 rounded-xl p-1">
              {(['graph', 'table'] as DisplayMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setDisplayMode(mode)}
                  className={`px-4 py-2 text-sm rounded-lg transition-all font-medium ${
                    displayMode === mode
                      ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-sm'
                      : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                  }`}
                >
                  {mode === 'graph' ? 'Graph' : 'Table'}
                </button>
              ))}
            </div>
          </div>

          {/* Citation View */}
          {displayMode === 'graph' ? (
            <CitationGraphView
              verdicts={report.verdicts}
              linkingSummary={report.linking_summary}
              onSelect={setSelected}
              onOverride={handleOverride}
            />
          ) : (
            <VerdictTable
              verdicts={report.verdicts}
              onSelect={setSelected}
              onOverride={handleOverride}
            />
          )}
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
