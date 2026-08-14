import { BrowserRouter, Routes, Route, Navigate, Link, Outlet } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { DecisionSupportDisclaimer } from '@/components/DecisionSupportDisclaimer';
// Import existing pages - these will need to be wrapped
import { UploadPage } from './pages/UploadPage';
import { HistoryPage } from './pages/HistoryPage';
import { EssayPage } from './pages/EssayPage';
import { useAuth } from './contexts/AuthContext';
import { useState, useEffect } from 'react';

function DashboardLayout() {
  const { user, logout, isAdmin } = useAuth();
  const [essays, setEssays] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

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
      setEssays(essays.filter(e => e.id !== id));
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2">
            <span className="text-xl font-bold">Essay Integrity Checker</span>
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link to="/dashboard" className="hover:underline">Dashboard</Link>
            <Link to="/upload" className="hover:underline">Upload</Link>
            <Link to="/history" className="hover:underline">History</Link>
            {isAdmin && (
              <Link to="/admin" className="hover:underline font-semibold">Admin</Link>
            )}
            <span className="text-muted-foreground">{user?.username}</span>
            <button onClick={logout} className="hover:underline">Logout</button>
          </nav>
        </div>
      </header>

      <DecisionSupportDisclaimer />

      <main className="container mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold mb-4">Your Essays</h1>
        <p className="text-muted-foreground mb-6">{essays.length} essay(s)</p>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
          </div>
        ) : essays.length === 0 ? (
          <div className="text-center py-12 bg-muted rounded-lg">
            <p className="text-muted-foreground">No essays yet.</p>
            <Link to="/upload" className="text-blue-600 hover:underline mt-2 inline-block">
              Upload your first essay
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {essays.map((essay) => (
              <div key={essay.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium">{essay.filename}</p>
                  <p className="text-sm text-muted-foreground">
                    {essay.num_pages} pages • {new Date(essay.uploaded_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Link
                    to={`/essay/${essay.id}`}
                    className="px-3 py-1 text-sm border rounded hover:bg-muted"
                  >
                    View
                  </Link>
                  <button
                    onClick={() => handleDelete(essay.id)}
                    className="px-3 py-1 text-sm text-red-600 border rounded hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <footer className="border-t mt-12 py-6">
        <div className="container mx-auto px-4 text-sm text-muted-foreground">
          <p>
            Đồ án tốt nghiệp — TDTU. Citation-only validation. Hệ thống không tự
            động kết luận gian lận học thuật.
          </p>
        </div>
      </footer>
    </div>
  );
}

function AdminLayout() {
  const { user, logout } = useAuth();
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReport();
  }, []);

  const loadReport = async () => {
    try {
      const res = await fetch('/api/export/report', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      if (res.ok) {
        const data = await res.json();
        setReport(data);
      }
    } catch (err) {
      console.error('Failed to load report:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleClearCache = async () => {
    if (!confirm('Clear all cache?')) return;
    try {
      await fetch('/api/cache', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      loadReport();
    } catch (err) {
      console.error('Failed to clear cache:', err);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/admin" className="flex items-center gap-2">
            <span className="text-xl font-bold">Admin Dashboard</span>
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link to="/dashboard" className="hover:underline">Dashboard</Link>
            <Link to="/admin" className="hover:underline font-semibold">Admin</Link>
            <Link to="/admin/users" className="hover:underline">Manage Users</Link>
            <span className="text-muted-foreground">{user?.username}</span>
            <button onClick={logout} className="hover:underline">Logout</button>
          </nav>
        </div>
      </header>

      <DecisionSupportDisclaimer />

      <main className="container mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold mb-6">System Overview</h1>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
          </div>
        ) : report ? (
          <div className="space-y-6">
            <div className="grid grid-cols-4 gap-4">
              <div className="border rounded-lg p-4">
                <p className="text-sm text-muted-foreground">Users</p>
                <p className="text-3xl font-bold">{report.users.total}</p>
                <p className="text-xs text-muted-foreground">
                  {report.users.admins} admins, {report.users.users} users
                </p>
              </div>
              <div className="border rounded-lg p-4">
                <p className="text-sm text-muted-foreground">Essays</p>
                <p className="text-3xl font-bold">{report.essays.total}</p>
              </div>
              <div className="border rounded-lg p-4">
                <p className="text-sm text-muted-foreground">Verdicts</p>
                <p className="text-3xl font-bold">{report.verdicts.total}</p>
              </div>
              <div className="border rounded-lg p-4">
                <p className="text-sm text-muted-foreground">Cache</p>
                <p className="text-3xl font-bold">{report.cache.total}</p>
              </div>
            </div>

            <div className="border rounded-lg p-4">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-medium">Cache by Source</h2>
                <button
                  onClick={handleClearCache}
                  className="px-3 py-1 text-sm text-red-600 border border-red-600 rounded hover:bg-red-50"
                >
                  Clear Cache
                </button>
              </div>
              <div className="grid grid-cols-4 gap-4">
                {Object.entries(report.cache.by_source || {}).map(([source, count]) => (
                  <div key={source} className="text-center">
                    <p className="text-2xl font-bold">{count as number}</p>
                    <p className="text-sm text-muted-foreground capitalize">
                      {source.replace('_', ' ')}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-muted-foreground">Failed to load report</p>
        )}
      </main>
    </div>
  );
}

function UserManagementPage() {
  const { logout } = useAuth();
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ username: '', password: '', role: 'user' });
  const [error, setError] = useState('');

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const res = await fetch('/api/users', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const res = await fetch('/api/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(formData),
      });
      if (res.ok) {
        setShowForm(false);
        setFormData({ username: '', password: '', role: 'user' });
        loadUsers();
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to create user');
      }
    } catch (err) {
      setError('Failed to create user');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this user?')) return;
    try {
      await fetch(`/api/users/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setUsers(users.filter(u => u.id !== id));
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold">User Management</h1>
          <nav className="flex items-center gap-4 text-sm">
            <Link to="/admin" className="hover:underline">Back to Admin</Link>
            <button onClick={logout} className="hover:underline">Logout</button>
          </nav>
        </div>
      </header>

      <DecisionSupportDisclaimer />

      <main className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-lg font-medium">Users ({users.length})</h2>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            {showForm ? 'Cancel' : 'Add User'}
          </button>
        </div>

        {showForm && (
          <div className="bg-muted p-6 rounded-lg mb-6">
            <h3 className="font-medium mb-4">Create New User</h3>
            {error && (
              <div className="bg-red-50 text-red-600 p-3 rounded mb-4">{error}</div>
            )}
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm mb-1">Username</label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    required
                    className="w-full px-3 py-2 border rounded"
                  />
                </div>
                <div>
                  <label className="block text-sm mb-1">Password</label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required
                    className="w-full px-3 py-2 border rounded"
                  />
                </div>
                <div>
                  <label className="block text-sm mb-1">Role</label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full px-3 py-2 border rounded"
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              </div>
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">
                Create User
              </button>
            </form>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
          </div>
        ) : (
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-muted">
                <tr>
                  <th className="px-4 py-2 text-left text-sm">ID</th>
                  <th className="px-4 py-2 text-left text-sm">Username</th>
                  <th className="px-4 py-2 text-left text-sm">Role</th>
                  <th className="px-4 py-2 text-left text-sm">Created</th>
                  <th className="px-4 py-2 text-left text-sm">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-t">
                    <td className="px-4 py-2 text-sm">{user.id}</td>
                    <td className="px-4 py-2 text-sm font-medium">{user.username}</td>
                    <td className="px-4 py-2">
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          user.role === 'admin'
                            ? 'bg-purple-100 text-purple-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-sm text-muted-foreground">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-2">
                      <button
                        onClick={() => handleDelete(user.id)}
                        className="text-sm text-red-600 hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          />
          <Route
            path="/"
            element={<Navigate to="/dashboard" replace />}
          />

          {/* Admin routes */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute adminOnly>
                <AdminLayout />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute adminOnly>
                <UserManagementPage />
              </ProtectedRoute>
            }
          />

          {/* Existing routes */}
          <Route
            path="/upload"
            element={
              <ProtectedRoute>
                <UploadPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/history"
            element={
              <ProtectedRoute>
                <HistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/essay/:id"
            element={
              <ProtectedRoute>
                <EssayPage />
              </ProtectedRoute>
            }
          />

          {/* Catch all */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
