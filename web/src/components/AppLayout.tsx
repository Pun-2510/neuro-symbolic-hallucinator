import { Link, useLocation, Outlet } from 'react-router-dom';
import {
  Shield,
  LayoutDashboard,
  Upload,
  History,
  LogOut,
  Menu,
  X,
  User as UserIcon,
  FileBarChart,
} from 'lucide-react';
import { useState, ReactNode } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { DecisionSupportDisclaimer } from './DecisionSupportDisclaimer';

function NavLink({
  to,
  icon,
  children,
  active,
}: {
  to: string;
  icon: ReactNode;
  children: ReactNode;
  active: boolean;
}) {
  return (
    <Link
      to={to}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
        active
          ? 'bg-primary/10 text-primary'
          : 'text-muted-foreground hover:text-foreground hover:bg-muted'
      }`}
    >
      {icon}
      {children}
    </Link>
  );
}

function MobileNavLink({
  to,
  icon,
  children,
  active,
  onClick,
}: {
  to: string;
  icon: ReactNode;
  children: ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <Link
      to={to}
      onClick={onClick}
      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
        active
          ? 'bg-primary/10 text-primary'
          : 'text-muted-foreground hover:text-foreground hover:bg-muted'
      }`}
    >
      {icon}
      {children}
    </Link>
  );
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(`${path}/`);

  return (
    <div className="min-h-screen bg-background flex flex-col">
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
              <NavLink
                to="/dashboard"
                icon={<LayoutDashboard className="h-4 w-4" />}
                active={isActive('/dashboard')}
              >
                Dashboard
              </NavLink>
              <NavLink
                to="/upload"
                icon={<Upload className="h-4 w-4" />}
                active={isActive('/upload')}
              >
                Upload
              </NavLink>
              <NavLink
                to="/history"
                icon={<History className="h-4 w-4" />}
                active={isActive('/history')}
              >
                History
              </NavLink>
            </nav>

            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-2 text-sm text-muted-foreground">
                <UserIcon className="h-4 w-4" />
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
                {isMobileMenuOpen ? (
                  <X className="h-5 w-5" />
                ) : (
                  <Menu className="h-5 w-5" />
                )}
              </button>
            </div>
          </div>
        </div>

        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-border/50 bg-background">
            <nav className="container mx-auto px-4 py-3 space-y-1">
              <MobileNavLink
                to="/dashboard"
                icon={<LayoutDashboard className="h-4 w-4" />}
                active={isActive('/dashboard')}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                Dashboard
              </MobileNavLink>
              <MobileNavLink
                to="/upload"
                icon={<Upload className="h-4 w-4" />}
                active={isActive('/upload')}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                Upload
              </MobileNavLink>
              <MobileNavLink
                to="/history"
                icon={<History className="h-4 w-4" />}
                active={isActive('/history')}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                History
              </MobileNavLink>
            </nav>
          </div>
        )}
      </header>

      <DecisionSupportDisclaimer />

      <main className="container mx-auto px-4 py-8 flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-border/50 mt-auto py-8">
        <div className="container mx-auto px-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
            <p>Đồ án tốt nghiệp — TDTU. Citation-only validation.</p>
            <p className="text-xs">
              Hệ thống không tự động kết luận gian lận học thuật.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
