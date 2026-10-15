import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FileText,
  Upload,
  Search,
  Clock,
  Trash2,
  RefreshCw,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Eye,
  Scale,
  XCircle,
  TrendingUp,
  FileCheck,
  AlertCircle,
} from 'lucide-react';
import { api, type EssaySummary, type AnalysisReport } from '@/api/client';
import { useToast } from '@/contexts/ToastContext';
import { ConfirmationModal } from '@/components/ConfirmationModal';

/* ============================================================
   SourceLogic — Dashboard Page Component
   Shows overview of all uploaded documents + aggregate stats
   Academic Source Verification Workspace
   ============================================================ */

interface DashboardStats {
  total_documents: number;
  total_citations: number;
  avg_cis_score: number | null;
  verified_rate: number;
}

const REFRESH_INTERVAL_MS = 10_000;

export function DashboardPage() {
  const toast = useToast();
  const [essays, setEssays] = useState<EssaySummary[]>([]);
  const [stats, setStats] = useState<DashboardStats>({
    total_documents: 0,
    total_citations: 0,
    avg_cis_score: null,
    verified_rate: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const loadEssays = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const data = await api.listEssays();
      setEssays(data);

      // Calculate aggregate stats from essays (fetch each report to count verdicts)
      let totalCitations = 0;
      let totalCIS = 0;
      let cisCount = 0;
      let totalVerified = 0;
      let totalVerdicts = 0;

      for (const essay of data) {
        try {
          const report: AnalysisReport | null = await api.getEssay(essay.id);
          if (report) {
            totalCitations += report.num_citations || 0;
            if (report.cis?.score) {
              totalCIS += report.cis.score;
              cisCount++;
            }
            // Compute verified rate from verdicts (single source of truth)
            if (Array.isArray(report.verdicts)) {
              totalVerdicts += report.verdicts.length;
              totalVerified += report.verdicts.filter(
                (v) => v.label === 'verified' || v.is_overridden
              ).length;
            }
          }
        } catch {
          // Skip failed report fetches (e.g. essay still processing → 425)
        }
      }

      setStats({
        total_documents: data.length,
        total_citations: totalCitations,
        avg_cis_score: cisCount > 0 ? Math.round((totalCIS / cisCount) * 100) / 100 : null,
        verified_rate:
          totalVerdicts > 0 ? Math.round((totalVerified / totalVerdicts) * 100) : 0,
      });

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadEssays();
    const interval = setInterval(() => loadEssays(true), REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [loadEssays]);

  const handleDelete = async () => {
    const id = confirmDeleteId;
    if (id == null) return;
    setConfirmDeleteId(null);
    setDeletingId(id);
    try {
      await api.deleteEssay(id);
      setEssays((prev) => prev.filter((e) => e.id !== id));
      setStats((prev) => ({ ...prev, total_documents: prev.total_documents - 1 }));
      toast.success('Document deleted');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Delete failed');
    } finally {
      setDeletingId(null);
    }
  };

  // Filter essays by search query
  const filteredEssays = essays.filter((essay) =>
    essay.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Stat cards data
  const statCards = [
    {
      label: 'Total Documents',
      value: stats.total_documents,
      icon: FileText,
      color: 'text-indigo-600 dark:text-indigo-400',
      bg: 'bg-indigo-50 dark:bg-indigo-950',
    },
    {
      label: 'Total Citations',
      value: stats.total_citations,
      icon: Scale,
      color: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50 dark:bg-emerald-950',
    },
    {
      label: 'Avg CIS Score',
      value: stats.avg_cis_score !== null ? `${stats.avg_cis_score}%` : 'N/A',
      icon: TrendingUp,
      color: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-950',
    },
    {
      label: 'Verified Rate',
      value: stats.verified_rate > 0 ? `${stats.verified_rate}%` : 'N/A',
      icon: CheckCircle2,
      color: 'text-blue-600 dark:text-blue-400',
      bg: 'bg-blue-50 dark:bg-blue-950',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-slate-100">
            Dashboard
          </h1>
          <p className="text-slate-600 dark:text-slate-300 mt-1">
            Overview of your verification workspace
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/upload" className="btn-primary btn-sm">
            <Upload className="h-4 w-4" />
            New Check
          </Link>
          <button
            onClick={() => loadEssays()}
            disabled={loading}
            aria-label="Refresh essays list"
            className="p-2 min-h-11 min-w-11 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 disabled:opacity-50 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <div key={card.label} className={`card p-5 ${card.bg}`}>
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-slate-600 dark:text-slate-300">{card.label}</p>
              <card.icon className={`h-5 w-5 ${card.color}`} />
            </div>
            <p className={`text-2xl font-bold font-display ${card.color}`}>{card.value}</p>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400 dark:text-slate-500" aria-hidden="true" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search documents..."
          aria-label="Search documents"
          className="input pl-12 pr-10"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
          >
            <XCircle className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="card p-5 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Documents Table */}
      <div className="card overflow-hidden">
        {loading && essays.length === 0 ? (
          <div className="p-12 flex flex-col items-center justify-center">
            <Loader2 className="h-8 w-8 text-indigo-600 dark:text-indigo-400 animate-spin mb-4" />
            <p className="text-sm text-slate-600 dark:text-slate-300">Loading documents...</p>
          </div>
        ) : filteredEssays.length === 0 ? (
          <div className="p-12 text-center">
            <div className="flex items-center justify-center w-20 h-20 rounded-2xl bg-slate-100 dark:bg-slate-800 mx-auto mb-5">
              <FileText className="h-10 w-10 text-slate-400 dark:text-slate-500" />
            </div>
            {searchQuery ? (
              <>
                <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
                  No documents found
                </h3>
                <p className="text-slate-600 dark:text-slate-300 mb-4">
                  No documents match "{searchQuery}"
                </p>
                <button
                  onClick={() => setSearchQuery('')}
                  className="text-indigo-600 dark:text-indigo-400 hover:underline"
                >
                  Clear search
                </button>
              </>
            ) : (
              <>
                <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
                  No documents yet
                </h3>
                <p className="text-slate-600 dark:text-slate-300 mb-6">
                  Upload your first document to start verifying citations
                </p>
                <Link to="/upload" className="btn-primary">
                  <Upload className="h-4 w-4" />
                  Upload Document
                </Link>
              </>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">
                    Document
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">
                    Pages
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">
                    Uploaded
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredEssays.map((essay) => (
                  <tr
                    key={essay.id}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-indigo-50 dark:bg-indigo-950 flex items-center justify-center shrink-0">
                          <FileText className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate max-w-md">
                            {essay.filename}
                          </p>
                          <p className="text-xs text-slate-600 dark:text-slate-300">
                            ID #{essay.id}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-sm text-slate-600 dark:text-slate-300">
                        {essay.num_pages}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-300">
                        <Clock className="h-3.5 w-3.5" />
                        {new Date(essay.uploaded_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/verification/report/${essay.id}`}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900 transition-colors"
                        >
                          <Eye className="h-4 w-4" />
                          View Report
                        </Link>
                        <button
                          onClickCapture={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setConfirmDeleteId(essay.id);
                          }}
                          disabled={deletingId === essay.id}
                          className="p-2 rounded-lg text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/50 transition-colors disabled:opacity-50"
                          title="Delete"
                          aria-label={`Delete ${essay.filename}`}
                        >
                          {deletingId === essay.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Stats Footer */}
      {essays.length > 0 && (
        <div className="text-sm text-slate-600 dark:text-slate-300">
          <p>
            Showing {filteredEssays.length} of {essays.length} documents
          </p>
        </div>
      )}

      <ConfirmationModal
        isOpen={confirmDeleteId !== null}
        title="Delete this document?"
        message="This will permanently remove the document and its analysis. This action cannot be undone."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setConfirmDeleteId(null)}
      />
    </div>
  );
}
