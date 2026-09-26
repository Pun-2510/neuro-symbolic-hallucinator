import { RouterProvider } from 'react-router-dom';
import { router, AuthProvider } from './router';

/* ============================================================
   SourceLogic — Main App Component
   Academic Source Verification Workspace
   Based on UX/UI Concept Specification
   ============================================================ */

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  );
}
