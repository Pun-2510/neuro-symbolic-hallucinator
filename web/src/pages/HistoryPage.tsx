import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Loader2,
  FileText,
  Trash2,
  Search,
  Clock,
  Upload,
  XCircle,
  RefreshCw,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';

/* ============================================================
   SourceLogic — History Page Component
   Based on UX/UI Concept Section 19: Global Navigation - Reports
   Academic Source Verification Workspace

   Mental Model: "Debugger cho citation"
   - Reports = compilation output history
   ============================================================ */

interface HistoryItem {
  id: number;
  filename: string;
  num_pages: number;
  uploaded_at: string;
  user_id: number;
}

const REFRESH_INTERVAL_MS = 10_000;

export function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const loadEssays = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const token = localStorage.getItem('token');
      const res = await fetch('/api/essays', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setItems(data);
        setError(null);
      } else {
        setError(`Error loading history: ${res.status}`);
      }
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

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this document?')) return;
    setDeletingId(id);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`/api/essays/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setItems((prev) => prev.filter((e) => e.id !== id));
      } else {
        alert('Delete failed');
      }
    } catch {
      alert('Delete failed');
    } finally {
      setDeletingId(null);
    }
  };

  // Filter items by search query
  const filteredItems = items.filter((item) =>
    item.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header - UX/UI Concept Section 19 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-slate-100">
            Verification Reports
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            {items.length} document{items.length !== 1 ? 's' : ''} · Auto-refresh every 10s
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
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 disabled:opacity-50 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400 dark:text-slate-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search documents..."
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

      {/* Loading */}
      {loading && items.length === 0 ? (
        <div className="card p-12 flex flex-col items-center justify-center">
          <Loader2 className="h-8 w-8 text-indigo-600 dark:text-indigo-400 animate-spin mb-4" />
          <p className="text-sm text-slate-500 dark:text-slate-400">Loading documents...</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="flex items-center justify-center w-20 h-20 rounded-2xl bg-slate-100 dark:bg-slate-800 mx-auto mb-5">
            <FileText className="h-10 w-10 text-slate-400 dark:text-slate-500" />
          </div>
          {searchQuery ? (
            <>
              <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
                No documents found
              </h3>
              <p className="text-slate-500 dark:text-slate-400 mb-4">
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
              <p className="text-slate-500 dark:text-slate-400 mb-6">
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
        <div className="space-y-3">
          {filteredItems.map((essay) => (
            <Link
              key={essay.id}
              to={`/verification/report/${essay.id}`}
              className="card-interactive block p-5 group"
            >
              <div className="flex items-center justify-between gap-4">
                {/* Left: Icon + Info */}
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-50 dark:bg-indigo-950 group-hover:bg-indigo-600 transition-colors shrink-0">
                    <FileText className="h-7 w-7 text-indigo-600 dark:text-indigo-400 group-hover:text-white transition-colors" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-slate-900 dark:text-slate-100 truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      {essay.filename}
                    </p>
                    <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400 mt-1">
                      <span className="flex items-center gap-1.5">
                        <FileText className="h-3.5 w-3.5" />
                        {essay.num_pages} pages
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" />
                        {new Date(essay.uploaded_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </span>
                      <span className="text-slate-400 dark:text-slate-500">ID #{essay.id}</span>
                    </div>
                  </div>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <span className="hidden sm:inline-flex px-3 py-1.5 text-sm border border-slate-200 dark:border-slate-700 rounded-lg text-slate-600 dark:text-slate-400 group-hover:border-indigo-300 dark:group-hover:border-indigo-600 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                    View Report
                  </span>
                  <button
                    onClickCapture={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      handleDelete(essay.id);
                    }}
                    disabled={deletingId === essay.id}
                    className="p-2.5 rounded-lg text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/50 transition-colors disabled:opacity-50"
                    title="Delete"
                  >
                    {deletingId === essay.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                  <ChevronRight className="h-5 w-5 text-slate-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Stats Footer */}
      {items.length > 0 && (
        <div className="flex items-center justify-between text-sm text-slate-500 dark:text-slate-400 pt-4 border-t border-slate-200 dark:border-slate-700">
          <p>
            Showing {filteredItems.length} of {items.length} documents
          </p>
          <p className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 dark:text-emerald-400" />
            Auto-refresh active
          </p>
        </div>
      )}
    </div>
  );
}
