import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate, Outlet, useParams } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { AppLayout } from './components/AppLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { PageSkeleton } from './components/PageSkeleton';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';

/* ============================================================
   SourceLogic — Router Configuration
   Academic Source Verification Workspace
   Code-split with React.lazy so the initial bundle only ships
   the chrome (Landing, Login, Layout). Each page is fetched
   on-demand when the user navigates to it.
   ============================================================ */

// Public route that redirects to dashboard if already authenticated
function PublicRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token');
  if (token) {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}

// Legacy essay redirect with proper parameter handling
function LegacyEssayRedirect() {
  const { id } = useParams();
  return <Navigate to={`/verification/report/${id}`} replace />;
}

// All authenticated pages are lazy-loaded so the initial bundle stays small.
// Each route is fetched on first navigation, then cached by the browser.
const DashboardPage = lazy(() => import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })));
const UploadPage = lazy(() => import('./pages/UploadPage').then((m) => ({ default: m.UploadPage })));
const BatchUploadPage = lazy(() => import('./pages/BatchUploadPage').then((m) => ({ default: m.BatchUploadPage })));
const ProcessingPage = lazy(() => import('./pages/ProcessingPage').then((m) => ({ default: m.ProcessingPage })));
const EssayPage = lazy(() => import('./pages/EssayPage').then((m) => ({ default: m.EssayPage })));
const IssuesPage = lazy(() => import('./pages/IssuesPage').then((m) => ({ default: m.IssuesPage })));
const LogicTracePage = lazy(() => import('./pages/LogicTracePage').then((m) => ({ default: m.LogicTracePage })));
const DocumentInspectorPage = lazy(() => import('./pages/DocumentInspectorPage').then((m) => ({ default: m.DocumentInspectorPage })));
const OrphanDetectionPage = lazy(() => import('./pages/OrphanDetectionPage').then((m) => ({ default: m.OrphanDetectionPage })));
const HistoryPage = lazy(() => import('./pages/HistoryPage').then((m) => ({ default: m.HistoryPage })));
const ProfilePage = lazy(() => import('./pages/ProfilePage').then((m) => ({ default: m.ProfilePage })));
const AccountManagementPage = lazy(() => import('./pages/AccountManagementPage').then((m) => ({ default: m.AccountManagementPage })));
const SettingsPage = lazy(() => import('./pages/SettingsPage').then((m) => ({ default: m.SettingsPage })));

// Wrap any lazy component in a Suspense boundary using PageSkeleton as fallback
function withSuspense(LazyComponent: React.ComponentType) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <LazyComponent />
    </Suspense>
  );
}

export const router = createBrowserRouter([
  // Public routes (eager — small, needed for first paint)
  {
    path: '/',
    element: <LandingPage />,
  },
  {
    path: '/login',
    element: (
      <PublicRoute>
        <LoginPage />
      </PublicRoute>
    ),
  },

  // Protected routes with AppLayout (sidebar navigation) — all lazy
  {
    element: (
      <ProtectedRoute>
        <AppLayout>
          <Outlet />
        </AppLayout>
      </ProtectedRoute>
    ),
    children: [
      { path: '/dashboard', element: withSuspense(DashboardPage) },
      { path: '/upload', element: withSuspense(UploadPage) },
      { path: '/batch-upload', element: withSuspense(BatchUploadPage) },
      { path: '/verification/processing', element: withSuspense(ProcessingPage) },
      { path: '/verification/processing/:id', element: withSuspense(ProcessingPage) },
      { path: '/verification/report/:id', element: withSuspense(EssayPage) },
      { path: '/verification/report/:id/issues', element: withSuspense(IssuesPage) },
      { path: '/verification/report/:id/trace', element: withSuspense(LogicTracePage) },
      { path: '/verification/report/:id/document', element: withSuspense(DocumentInspectorPage) },
      { path: '/verification/report/:id/consistency', element: withSuspense(OrphanDetectionPage) },
      { path: '/essay/:id', element: <LegacyEssayRedirect /> },
      { path: '/history', element: withSuspense(HistoryPage) },
      { path: '/profile', element: withSuspense(ProfilePage) },
      { path: '/admin/users', element: withSuspense(AccountManagementPage) },
      { path: '/settings', element: withSuspense(SettingsPage) },
      // Legacy route redirects
      { path: '/home', element: <Navigate to="/dashboard" replace /> },
    ],
  },

  // Catch-all redirect
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);

/* ============================================================
   Router Export with AuthProvider
   Wrap router with AuthProvider for authentication context
   ============================================================ */
export { AuthProvider };
