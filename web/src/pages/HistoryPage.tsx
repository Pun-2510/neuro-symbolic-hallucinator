import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, FileBarChart, Trash2, Eye, RefreshCw } from 'lucide-react';

interface HistoryItem {
  id: number;
  filename: string;
  num_pages: number;
  uploaded_at: string;
  user_id: number;
}

const REFRESH_INTERVAL_MS = 10_000; // 10 giây auto refresh

export function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

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
        setError(`Lỗi tải lịch sử: ${res.status}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Lỗi kết nối');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load + auto refresh every 10s
  useEffect(() => {
    loadEssays();
    const interval = setInterval(() => loadEssays(true), REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [loadEssays]);

  const handleDelete = async (id: number) => {
    if (!confirm('Xóa essay này?')) return;
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
        alert('Xóa thất bại');
      }
    } catch {
      alert('Xóa thất bại');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">History</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {items.length} essay(s) · Tự động làm mới mỗi {REFRESH_INTERVAL_MS / 1000}s
          </p>
        </div>
        <button
          onClick={() => loadEssays()}
          disabled={loading}
          className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground disabled:opacity-50"
          title="Làm mới"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && items.length === 0 ? (
        <div className="card-elevated p-12 flex flex-col items-center justify-center">
          <Loader2 className="h-8 w-8 text-primary animate-spin mb-3" />
          <p className="text-sm text-muted-foreground">Đang tải lịch sử...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="card-elevated p-12 text-center">
          <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-muted mx-auto mb-4">
            <FileBarChart className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            Chưa có lịch sử
          </h3>
          <p className="text-muted-foreground mb-6">
            Upload essay đầu tiên để bắt đầu
          </p>
          <Link
            to="/upload"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
          >
            Upload Essay
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((essay) => (
            <div key={essay.id} className="card-elevated p-5">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 shrink-0">
                    <FileBarChart className="h-6 w-6 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-semibold text-foreground truncate">
                      {essay.filename}
                    </p>
                    <p className="text-sm text-muted-foreground mt-0.5">
                      {essay.num_pages} trang · ID #{essay.id} ·{' '}
                      {new Date(essay.uploaded_at).toLocaleString('vi-VN')}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Link
                    to={`/essay/${essay.id}`}
                    className="px-3 py-1.5 text-sm font-medium border border-border rounded-xl hover:bg-muted transition-colors flex items-center gap-1"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    Xem
                  </Link>
                  <button
                    onClick={() => handleDelete(essay.id)}
                    disabled={deletingId === essay.id}
                    className="px-3 py-1.5 text-sm font-medium text-red-600 border border-red-200 rounded-xl hover:bg-red-50 transition-colors flex items-center gap-1 disabled:opacity-50"
                  >
                    {deletingId === essay.id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="h-3.5 w-3.5" />
                    )}
                    Xóa
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
