import { createBrowserRouter, Navigate, Outlet, useParams } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { AppLayout } from './components/AppLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LandingPage } from './pages/LandingPage';
import { UploadPage } from './pages/UploadPage';
import { ProcessingPage } from './pages/ProcessingPage';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from './pages/LoginPage';
import { HistoryPage } from './pages/HistoryPage';
import { EssayPage } from './pages/EssayPage';
import { IssuesPage } from './pages/IssuesPage';
import { LogicTracePage } from './pages/LogicTracePage';
import { DocumentInspectorPage } from './pages/DocumentInspectorPage';
import { OrphanDetectionPage } from './pages/OrphanDetectionPage';
import { BatchUploadPage } from './pages/BatchUploadPage';
import { ProfilePage } from './pages/ProfilePage';
import { AccountManagementPage } from './pages/AccountManagementPage';
import { SettingsPage } from './pages/SettingsPage';
import { MyClassesPage } from './pages/MyClassesPage';
import { PendingReviewsPage } from './pages/PendingReviewsPage';

/* ============================================================
   SourceLogic — Router Configuration
   Academic Source Verification Workspace
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

export const router = createBrowserRouter([
  // Public routes
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

  // Protected routes with AppLayout (sidebar navigation)
  {
    element: (
      <ProtectedRoute>
        <AppLayout>
          <Outlet />
        </AppLayout>
      </ProtectedRoute>
    ),
    children: [
      {
        path: '/dashboard',
        element: <DashboardPage />,
      },
      {
        path: '/upload',
        element: <UploadPage />,
      },
      {
        path: '/batch-upload',
        element: (
          <ProtectedRoute requiredCapabilities={['view_class_history']}>
            <BatchUploadPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/verification/processing',
        element: <ProcessingPage />,
      },
      {
        path: '/verification/processing/:id',
        element: <ProcessingPage />,
      },
      {
        path: '/verification/report/:id',
        element: <EssayPage />,
      },
      {
        path: '/verification/report/:id/issues',
        element: <IssuesPage />,
      },
      {
        path: '/verification/report/:id/trace',
        element: (
          <ProtectedRoute requiredCapabilities={['view_logic_trace']}>
            <LogicTracePage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/verification/report/:id/document',
        element: (
          <ProtectedRoute requiredCapabilities={['view_document_inspector']}>
            <DocumentInspectorPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/verification/report/:id/consistency',
        element: (
          <ProtectedRoute requiredCapabilities={['view_orphan_detection']}>
            <OrphanDetectionPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/essay/:id',
        element: <LegacyEssayRedirect />,
      },
      {
        path: '/history',
        element: <HistoryPage />,
      },
      {
        path: '/profile',
        element: <ProfilePage />,
      },
      {
        path: '/admin/users',
        element: (
          <ProtectedRoute requiredCapabilities={['manage_users']}>
            <AccountManagementPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/settings',
        element: <SettingsPage />,
      },
      // Teacher (v1.15 / Phase 3) — gated by view_class_history capability
      {
        path: '/teacher/classes',
        element: (
          <ProtectedRoute requiredCapabilities={['view_class_history']}>
            <MyClassesPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/teacher/reviews',
        element: (
          <ProtectedRoute requiredCapabilities={['override_verdict']}>
            <PendingReviewsPage />
          </ProtectedRoute>
        ),
      },
      // Legacy route redirects
      {
        path: '/home',
        element: <Navigate to="/dashboard" replace />,
      },
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
