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

/* ============================================================
   SourceLogic — Router Configuration
   Academic Source Verification Workspace
   Based on UX/UI Concept Section 19: Global Navigation
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
        element: <BatchUploadPage />,
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
        element: <LogicTracePage />,
      },
      {
        path: '/verification/report/:id/document',
        element: <DocumentInspectorPage />,
      },
      {
        path: '/verification/report/:id/consistency',
        element: <OrphanDetectionPage />,
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
        element: <AccountManagementPage />,
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
