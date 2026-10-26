import { lazy, Suspense, useEffect } from 'react';
import {
  createBrowserRouter,
  matchPath,
  Navigate,
  Outlet,
  useLocation,
  useParams,
} from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
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
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900" />
      </div>
    );
  }
  if (user) {
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
const PricingPage = lazy(() => import('./pages/PricingPage').then((m) => ({ default: m.PricingPage })));
const StripeDemoCheckoutPage = lazy(() => import('./pages/StripeDemoCheckoutPage').then((m) => ({ default: m.StripeDemoCheckoutPage })));
const BillingSuccessPage = lazy(() => import('./pages/BillingSuccessPage').then((m) => ({ default: m.BillingSuccessPage })));

// Hybrid route: renders inside AppLayout when authenticated, or standalone when visited publicly
function HybridPricingRoute() {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return <PageSkeleton />;
  }
  if (user) {
    return (
      <AppLayout>
        <Suspense fallback={<PageSkeleton />}>
          <PricingPage />
        </Suspense>
      </AppLayout>
    );
  }
  return (
    <div className="min-h-screen bg-slate-50/80 dark:bg-slate-950 px-4 sm:px-6 lg:px-10 py-6">
      <Suspense fallback={<PageSkeleton />}>
        <PricingPage />
      </Suspense>
    </div>
  );
}

// Wrap any lazy component in a Suspense boundary using PageSkeleton as fallback
function withSuspense(LazyComponent: React.ComponentType) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <LazyComponent />
    </Suspense>
  );
}

const PAGE_TITLE_ROUTES: Array<{ pattern: string; title: string }> = [
  { pattern: '/', title: 'Home' },
  { pattern: '/login', title: 'Login' },
  { pattern: '/register', title: 'Register' },
  { pattern: '/forgot-password', title: 'Forgot Password' },
  { pattern: '/activate-account', title: 'Activate Account' },
  { pattern: '/reset-password', title: 'Reset Password' },
  { pattern: '/dashboard', title: 'Dashboard' },
  { pattern: '/upload', title: 'New Check' },
  { pattern: '/batch-upload', title: 'Batch Check' },
  { pattern: '/verification/processing', title: 'Processing' },
  { pattern: '/verification/processing/:id', title: 'Processing' },
  { pattern: '/verification/report/:id', title: 'Verification Report' },
  { pattern: '/verification/report/:id/issues', title: 'Issues' },
  { pattern: '/verification/report/:id/trace', title: 'Logic Trace' },
  { pattern: '/verification/report/:id/document', title: 'Document Inspector' },
  { pattern: '/verification/report/:id/consistency', title: 'Consistency' },
  { pattern: '/history', title: 'History' },
  { pattern: '/profile', title: 'Profile' },
  { pattern: '/admin/users', title: 'Accounts' },
  { pattern: '/admin/system', title: 'System Health' },
  { pattern: '/admin/audit', title: 'Audit Log' },
  { pattern: '/settings', title: 'Settings' },
  { pattern: '/pricing', title: 'Pricing & Plans' },
  { pattern: '/billing/checkout', title: 'Stripe Checkout' },
  { pattern: '/billing/success', title: 'Payment Confirmed' },
  { pattern: '/teacher/classes', title: 'My Classes' },
  { pattern: '/teacher/classes/:classId', title: 'Class Detail' },
  { pattern: '/teacher/reviews', title: 'Pending Reviews' },
];

export function getDocumentTitle(pathname: string): string {
  for (const route of PAGE_TITLE_ROUTES) {
    if (matchPath({ path: route.pattern, end: true }, pathname)) {
      return `CITRA - ${route.title}`;
    }
  }
  return 'CITRA';
}

function syncRobotsMeta(pathname: string): void {
  if (typeof document === 'undefined') return;
  const isPublicIndexable = pathname === '/';
  const content = isPublicIndexable ? 'index, follow' : 'noindex, nofollow';
  let meta = document.querySelector<HTMLMetaElement>('meta[name="robots"]');
  if (!meta) {
    meta = document.createElement('meta');
    meta.name = 'robots';
    document.head.appendChild(meta);
  }
  meta.content = content;

  let canonical = document.querySelector<HTMLLinkElement>('link[rel="canonical"]');
  if (!canonical) {
    canonical = document.createElement('link');
    canonical.rel = 'canonical';
    document.head.appendChild(canonical);
  }
  const normalizedPath = pathname === '/' ? '/' : pathname.replace(/\/+$/, '');
  canonical.href = `https://citra.io.vn${normalizedPath}`;
}

function RootLayout() {
  const { pathname } = useLocation();

  useEffect(() => {
    document.title = getDocumentTitle(pathname);
    syncRobotsMeta(pathname);
  }, [pathname]);

  return <Outlet />;
}

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
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
      {
        path: '/pricing',
        element: <HybridPricingRoute />,
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
          { path: '/billing/checkout', element: withSuspense(StripeDemoCheckoutPage) },
          { path: '/billing/success', element: withSuspense(BillingSuccessPage) },
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
    ],
  },
]);

if (typeof document !== 'undefined' && typeof window !== 'undefined') {
  document.title = getDocumentTitle(window.location.pathname);
  router.subscribe((state) => {
    document.title = getDocumentTitle(state.location.pathname);
  });
}

/* ============================================================
   Router Export with AuthProvider
   Wrap router with AuthProvider for authentication context
   ============================================================ */
export { AuthProvider };
