import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate, Outlet, useParams } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { AppLayout } from './components/AppLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { PageSkeleton } from './components/PageSkeleton';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ActivateAccountPage } from './pages/ActivateAccountPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';

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
const MyClassesPage = lazy(() => import('./pages/MyClassesPage').then((m) => ({ default: m.MyClassesPage })));
const ClassDetailPage = lazy(() => import('./pages/ClassDetailPage').then((m) => ({ default: m.ClassDetailPage })));
const PendingReviewsPage = lazy(() => import('./pages/PendingReviewsPage').then((m) => ({ default: m.PendingReviewsPage })));
const SystemHealthPage = lazy(() => import('./pages/SystemHealthPage').then((m) => ({ default: m.SystemHealthPage })));
const AuditLogPage = lazy(() => import('./pages/AuditLogPage').then((m) => ({ default: m.AuditLogPage })));

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
  {
    path: '/register',
    element: (
      <PublicRoute>
        <RegisterPage />
      </PublicRoute>
    ),
  },
  {
    path: '/forgot-password',
    element: (
      <PublicRoute>
        <ForgotPasswordPage />
      </PublicRoute>
    ),
  },
  {
    path: '/activate-account',
    element: <ActivateAccountPage />,
  },
  {
    path: '/reset-password',
    element: <ResetPasswordPage />,
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
      {
        path: '/batch-upload',
        element: (
          <ProtectedRoute requiredCapabilities={['view_class_history']}>
            <Suspense fallback={<PageSkeleton />}>
              <BatchUploadPage />
            </Suspense>
          </ProtectedRoute>
        ),
      },
      { path: '/verification/processing', element: withSuspense(ProcessingPage) },
      { path: '/verification/processing/:id', element: withSuspense(ProcessingPage) },
      { path: '/verification/report/:id', element: withSuspense(EssayPage) },
      { path: '/verification/report/:id/issues', element: withSuspense(IssuesPage) },
      {
        path: '/verification/report/:id/trace',
        element: (
          <ProtectedRoute requiredCapabilities={['view_logic_trace']}>
            <Suspense fallback={<PageSkeleton />}>
              <LogicTracePage />
            </Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: '/verification/report/:id/document',
        element: (
          <ProtectedRoute requiredCapabilities={['view_document_inspector']}>
            <Suspense fallback={<PageSkeleton />}>
              <DocumentInspectorPage />
            </Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: '/verification/report/:id/consistency',
        element: (
          <ProtectedRoute requiredCapabilities={['view_orphan_detection']}>
            <Suspense fallback={<PageSkeleton />}>
              <OrphanDetectionPage />
            </Suspense>
          </ProtectedRoute>
        ),
      },
      { path: '/essay/:id', element: <LegacyEssayRedirect /> },
      { path: '/history', element: withSuspense(HistoryPage) },
      { path: '/profile', element: withSuspense(ProfilePage) },
      {
        path: '/admin/users',
        element: (
          <ProtectedRoute requiredCapabilities={['manage_users']}>
            <Suspense fallback={<PageSkeleton />}>
              <AccountManagementPage />
            </Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: '/admin/system',
        element: (
          <ProtectedRoute requiredCapabilities={['view_system_health']}>
            <Suspense fallback={<PageSkeleton />}>
              <SystemHealthPage />
            </Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: '/admin/audit',
        element: (
          <ProtectedRoute requiredCapabilities={['view_audit_log']}>
            <Suspense fallback={<PageSkeleton />}>
              <AuditLogPage />
            </Suspense>
          </ProtectedRoute>
        ),
      },
      { path: '/settings', element: withSuspense(SettingsPage) },
      // Teacher (v1.15 / Phase 3) — gated by view_class_history capability
      {
        path: '/teacher/classes',
        element: (
          <ProtectedRoute requiredCapabilities={['view_class_history']}>
            <Suspense fallback={<PageSkeleton />}>
              <MyClassesPage />
            </Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: '/teacher/classes/:classId',
        element: (
          <ProtectedRoute requiredCapabilities={['view_class_history']}>
            <Suspense fallback={<PageSkeleton />}>
              <ClassDetailPage />
            </Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: '/teacher/reviews',
        element: (
          <ProtectedRoute requiredCapabilities={['override_verdict']}>
            <Suspense fallback={<PageSkeleton />}>
              <PendingReviewsPage />
            </Suspense>
          </ProtectedRoute>
        ),
      },
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
