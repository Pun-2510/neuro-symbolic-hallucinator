import { createBrowserRouter, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { UploadPage } from './pages/UploadPage';
import { EssayPage } from './pages/EssayPage';
import { HistoryPage } from './pages/HistoryPage';
import { DecisionSupportDisclaimer } from './components/DecisionSupportDisclaimer';
import {
  Shield,
  LayoutDashboard,
  Upload,
  History,
  LogOut,
  Menu,
  X,
  User,
  Loader2,
  FileBarChart,
} from 'lucide-react';
import { useState, useEffect, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';

// ============================================================
// Dashboard Layout
// ============================================================

function DashboardLayout() {
  const { user, logout } = useAuth();
  const [essays, setEssays] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    loadEssays();
  }, []);

  const loadEssays = async () => {
    try {
      const res = await fetch('/api/essays', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      if (res.ok) {
        const data = await res.json();
        setEssays(data);
      }
    } catch (err) {
      console.error('Failed to load essays:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this essay?')) return;
    try {
      await fetch(`/api/essays/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setEssays(essays.filter((e) => e.id !== id));
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 border-b border-border/50">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <Link to="/dashboard" className="flex items-center gap-3">
              <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-primary text-primary-foreground">
                <Shield className="h-5 w-5" />
              </div>
              <span className="font-bold text-foreground hidden sm:block">
                Essay Integrity Checker
              </span>
            </Link>

            <nav className="hidden md:flex items-center gap-1">
              <NavLink to="/dashboard" icon={<LayoutDashboard className="h-4 w-4" />}>
                Dashboard
              </NavLink>
              <NavLink to="/upload" icon={<Upload className="h-4 w-4" />}>
                Upload
              </NavLink>
              <NavLink to="/history" icon={<History className="h-4 w-4" />}>
                History
              </NavLink>
            </nav>

            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-2 text-sm text-muted-foreground">
                <User className="h-4 w-4" />
                <span>{user?.username}</span>
              </div>
              <button
                onClick={logout}
                className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                title="Logout"
              >
                <LogOut className="h-4 w-4" />
              </button>
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="md:hidden p-2 rounded-lg hover:bg-muted transition-colors"
              >
                {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
            </div>
          </div>
        </div>

        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-border/50 bg-background">
            <nav className="container mx-auto px-4 py-3 space-y-1">
              <MobileNavLink to="/dashboard" icon={<LayoutDashboard className="h-4 w-4" />} onClick={() => setIsMobileMenuOpen(false)}>
                Dashboard
              </MobileNavLink>
              <MobileNavLink to="/upload" icon={<Upload className="h-4 w-4" />} onClick={() => setIsMobileMenuOpen(false)}>
                Upload
              </MobileNavLink>
              <MobileNavLink to="/history" icon={<History className="h-4 w-4" />} onClick={() => setIsMobileMenuOpen(false)}>
                History
              </MobileNavLink>
            </nav>
          </div>
        )}
      </header>

      <DecisionSupportDisclaimer />

      <main className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground">Your Essays</h1>
          <p className="text-muted-foreground mt-1">{essays.length} essay(s) analyzed</p>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="h-8 w-8 text-primary animate-spin mb-4" />
            <p className="text-muted-foreground">Loading essays...</p>
          </div>
        ) : essays.length === 0 ? (
          <div className="card-elevated p-12 text-center">
            <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-muted mx-auto mb-4">
              <FileBarChart className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">No essays yet</h3>
            <p className="text-muted-foreground mb-6">Upload your first essay to get started</p>
            <Link to="/upload" className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors">
              <Upload className="h-4 w-4" />
              Upload Essay
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {essays.map((essay) => (
              <div key={essay.id} className="card-elevated p-5 group">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 shrink-0">
                      <FileBarChart className="h-6 w-6 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-foreground truncate">{essay.filename}</p>
                      <p className="text-sm text-muted-foreground mt-0.5">
                        {essay.num_pages} pages • {new Date(essay.uploaded_at).toLocaleDateString('vi-VN')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Link to={`/essay/${essay.id}`} className="px-4 py-2 text-sm font-medium border border-border rounded-xl hover:bg-muted transition-colors">
                      View
                    </Link>
                    <button onClick={() => handleDelete(essay.id)} className="px-4 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-xl hover:bg-red-50 transition-colors">
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <footer className="border-t border-border/50 mt-auto py-8">
        <div className="container mx-auto px-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
            <p>Đồ án tốt nghiệp — TDTU. Citation-only validation.</p>
            <p className="text-xs">Hệ thống không tự động kết luận gian lận học thuật.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

// ============================================================
// Helper Components
// ============================================================

function NavLink({ to, icon, children }: { to: string; icon: ReactNode; children: ReactNode }) {
  return (
    <Link to={to} className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
      {icon}
      {children}
    </Link>
  );
}

function MobileNavLink({ to, icon, children, onClick }: { to: string; icon: ReactNode; children: ReactNode; onClick: () => void }) {
  return (
    <Link to={to} onClick={onClick} className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
      {icon}
      {children}
    </Link>
  );
}

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
  {
    path: '/dashboard',
    element: (
      <ProtectedRoute>
        <DashboardLayout />
      </ProtectedRoute>
    ),
  },
  {
    path: '/upload',
    element: (
      <ProtectedRoute>
        <UploadPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/history',
    element: (
      <ProtectedRoute>
        <HistoryPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/essay/:id',
    element: (
      <ProtectedRoute>
        <EssayPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '*',
    element: <Navigate to="/dashboard" replace />,
  },
]);
