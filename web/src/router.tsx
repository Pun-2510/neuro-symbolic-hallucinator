import { createBrowserRouter, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { UploadPage } from './pages/UploadPage';
import { EssayPage } from './pages/EssayPage';
import { HistoryPage } from './pages/HistoryPage';
import { AppLayout } from './components/AppLayout';

// ============================================================
// Router Configuration
// ============================================================

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  // All authenticated pages share the AppLayout (navbar + footer)
  {
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        path: '/dashboard',
        element: <DashboardHome />,
      },
      {
        path: '/upload',
        element: <UploadPage />,
      },
      {
        path: '/history',
        element: <HistoryPage />,
      },
      {
        path: '/essay/:id',
        element: <EssayPage />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/dashboard" replace />,
  },
]);

// ============================================================
// Dashboard Home Page
// ============================================================

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, FileBarChart, Upload as UploadIcon, Trash2 } from 'lucide-react';

interface DashboardEssay {
  id: number;
  filename: string;
  num_pages: number;
  uploaded_at: string;
  user_id: number;
}

const REFRESH_INTERVAL_MS = 10_000;

function DashboardHome() {
  const [essays, setEssays] = useState<DashboardEssay[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const loadEssays = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const token = localStorage.getItem('token');
      const res = await fetch('/api/essays', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setEssays(await res.json());
      }
    } catch (err) {
      console.error('Failed to load essays:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEssays();
    const interval = setInterval(() => loadEssays(true), REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  const handleDelete = async (id: number) => {
    if (!confirm('Xóa essay này?')) return;
    setDeletingId(id);
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/essays/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      setEssays((prev) => prev.filter((e) => e.id !== id));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Your Essays</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {essays.length} essay(s) analyzed · Tự động cập nhật mỗi {REFRESH_INTERVAL_MS / 1000}s
          </p>
        </div>
        <Link
          to="/upload"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
        >
          <UploadIcon className="h-4 w-4" />
          Upload Essay
        </Link>
      </div>

      {loading && essays.length === 0 ? (
        <div className="card-elevated p-12 flex flex-col items-center justify-center">
          <Loader2 className="h-8 w-8 text-primary animate-spin mb-3" />
          <p className="text-sm text-muted-foreground">Đang tải...</p>
        </div>
      ) : essays.length === 0 ? (
        <div className="card-elevated p-12 text-center">
          <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-muted mx-auto mb-4">
            <FileBarChart className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            No essays yet
          </h3>
          <p className="text-muted-foreground mb-6">
            Upload your first essay to get started
          </p>
          <Link
            to="/upload"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
          >
            <UploadIcon className="h-4 w-4" />
            Upload Essay
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {essays.map((essay) => (
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
                      {essay.num_pages} trang · {new Date(essay.uploaded_at).toLocaleString('vi-VN')}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Link
                    to={`/essay/${essay.id}`}
                    className="px-3 py-1.5 text-sm font-medium border border-border rounded-xl hover:bg-muted transition-colors"
                  >
                    View
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
