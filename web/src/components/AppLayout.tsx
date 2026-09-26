import { Link, useLocation, useNavigate } from 'react-router-dom';
import { FileSearch, Upload, History, Settings, HelpCircle, Menu, X, BookOpen, Scale, Database, LogOut, User } from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';

/* ============================================================
   SourceLogic — App Layout Component
   Academic Source Verification Workspace
   Based on UX/UI Concept Section 19: Global Navigation
   ============================================================ */

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: FileSearch },
  { path: '/upload', label: 'New Check', icon: Upload },
  { path: '/history', label: 'History', icon: History },
];

const advancedItems = [
  { path: '/providers', label: 'Retrieval Providers', icon: Database },
  { path: '/rules', label: 'Logic Rules', icon: Scale },
];

export function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const isActive = (path: string) => location.pathname === path;

  const handleLogout = async () => {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Logout failed:', err);
    } finally {
      setLoggingOut(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex">
      {/* Mobile menu button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-lg"
      >
        <Menu className="h-5 w-5 text-slate-600 dark:text-slate-400" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-72 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800
          transform transition-transform duration-300 ease-out
          lg:transform-none
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Mobile close button */}
        <button
          onClick={() => setMobileOpen(false)}
          className="lg:hidden absolute top-4 right-4 p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <X className="h-5 w-5 text-slate-500" />
        </button>

        <div className="flex flex-col h-full">
          {/* Logo & Branding */}
          <div className="p-6 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-4">
              {/* SourceLogic Logo */}
              <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  className="text-white"
                >
                  {/* Citation bracket [1] */}
                  <path
                    d="M4 8C4 6.89543 4.89543 6 6 6H8"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M4 16C4 17.1046 4.89543 18 6 18H8"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                  {/* Link arrow */}
                  <path
                    d="M10 12H14M14 12L12 10M14 12L12 14"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  {/* Checkmark */}
                  <path
                    d="M17 9L19 11L22 8"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <div>
                <h1 className="font-display text-xl font-bold text-slate-900 dark:text-white">
                  SourceLogic
                </h1>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Academic Verification
                </p>
              </div>
            </div>
            {/* Tagline */}
            <p className="mt-3 text-xs text-slate-600 dark:text-slate-400 italic">
              Verify citations. Trace evidence.
            </p>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            <p className="px-4 py-2 text-[11px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
              Workspace
            </p>
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileOpen(false)}
                  className={`
                    flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium
                    transition-all duration-200
                    ${isActive(item.path)
                      ? 'bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
                    }
                  `}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </Link>
              );
            })}

            <div className="pt-4 mt-4 border-t border-slate-200 dark:border-slate-800">
              <p className="px-4 py-2 text-[11px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                Advanced
              </p>
              {advancedItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileOpen(false)}
                    className={`
                      flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium
                      transition-all duration-200
                      ${isActive(item.path)
                        ? 'bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
                      }
                    `}
                  >
                    <Icon className="h-5 w-5" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </nav>

          {/* User Info & Logout */}
          <div className="p-4 border-t border-slate-200 dark:border-slate-800 space-y-2">
            {/* User Info */}
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800/50">
              <div className="w-9 h-9 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center shrink-0">
                <User className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                  {user?.username || 'User'}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 capitalize">
                  {user?.role || 'user'}
                </p>
              </div>
            </div>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              disabled={loggingOut}
              className="w-full flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-all duration-200 disabled:opacity-50"
            >
              {loggingOut ? (
                <div className="h-5 w-5 border-2 border-red-600/30 border-t-red-600 rounded-full animate-spin" />
              ) : (
                <LogOut className="h-5 w-5" />
              )}
              {loggingOut ? 'Signing out...' : 'Sign out'}
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <main className="flex-1 p-6 lg:p-10 pt-16 lg:pt-6">
          <div className="max-w-6xl mx-auto">
            {children}
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-6 py-4">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <p className="flex items-center gap-2">
              <BookOpen className="h-3.5 w-3.5" />
              SourceLogic — Academic Source Verification Workspace
            </p>
            <p>Decision Support System</p>
          </div>
        </footer>
      </div>
    </div>
  );
}
