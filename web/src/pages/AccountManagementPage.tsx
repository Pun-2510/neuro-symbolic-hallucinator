import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserPlus, Search, Loader2, UserCog, Shield, ShieldCheck, ShieldAlert, ImageIcon, X } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { UserFormDialog } from '@/components/UserFormDialog';
import { DeleteUserDialog } from '@/components/DeleteUserDialog';
import type { User } from '@/api/client';
import { api } from '@/api/client';

export function AccountManagementPage() {
  const { user: currentUser, isAdmin } = useAuth();
  const navigate = useNavigate();

  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<'all' | 'admin' | 'user'>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');

  // Dialogs
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [deletingUser, setDeletingUser] = useState<User | null>(null);

  // Redirect non-admins to dashboard (ProtectedRoute already ensures auth)
  useEffect(() => {
    if (!isAdmin) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAdmin, navigate]);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.listUsers();
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // Filtered users
  const filtered = users.filter((u) => {
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      !q ||
      u.username.toLowerCase().includes(q) ||
      (u.full_name ?? '').toLowerCase().includes(q) ||
      (u.email ?? '').toLowerCase().includes(q);

    const matchesRole = roleFilter === 'all' || u.role === roleFilter;
    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'active' && u.is_active) ||
      (statusFilter === 'inactive' && !u.is_active);

    return matchesSearch && matchesRole && matchesStatus;
  });

  const handleEdit = (user: User) => {
    setEditingUser(user);
    setFormDialogOpen(true);
  };

  const handleDelete = (user: User) => {
    setDeletingUser(user);
    setDeleteDialogOpen(true);
  };

  const RoleBadge = ({ role }: { role: string }) => (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${
        role === 'admin'
          ? 'bg-violet-100 text-violet-700 dark:bg-violet-900 dark:text-violet-300'
          : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
      }`}
    >
      {role === 'admin' ? <Shield className="h-3 w-3" /> : <ShieldAlert className="h-3 w-3" />}
      {role}
    </span>
  );

  const StatusBadge = ({ active }: { active: boolean }) => (
    <span
      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
        active
          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'
          : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
      }`}
    >
      {active ? 'Active' : 'Inactive'}
    </span>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-slate-100">
            Account Management
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Manage user accounts, roles, and permissions
          </p>
        </div>
        <button
          onClick={() => {
            setEditingUser(null);
            setFormDialogOpen(true);
          }}
          className="btn-primary btn-sm"
        >
          <UserPlus className="h-4 w-4" />
          Create User
        </button>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by username, name, or email..."
              className="input pl-10"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value as typeof roleFilter)}
            className="input sm:w-40"
          >
            <option value="all">All Roles</option>
            <option value="admin">Admin</option>
            <option value="user">User</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
            className="input sm:w-40"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card p-4 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-12 flex flex-col items-center justify-center">
            <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-4" />
            <p className="text-sm text-slate-500">Loading users...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-16 h-16 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto mb-4">
              <UserCog className="h-8 w-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              {searchQuery || roleFilter !== 'all' || statusFilter !== 'all'
                ? 'No users match your filters'
                : 'No users yet'}
            </h3>
            <p className="text-slate-500 dark:text-slate-400 text-sm">
              {searchQuery || roleFilter !== 'all' || statusFilter !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Create the first user to get started'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    User
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Last Login
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Member Since
                  </th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filtered.map((u) => (
                  <tr
                    key={u.id}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full overflow-hidden bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center shrink-0">
                          {u.avatar_url ? (
                            <img
                              src={u.avatar_url}
                              alt={u.username}
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <ImageIcon className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                            {u.full_name || u.username}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                            {u.username}
                            {u.email && ` · ${u.email}`}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <RoleBadge role={u.role} />
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge active={u.is_active} />
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-500 dark:text-slate-400">
                      {u.last_login_at
                        ? new Date(u.last_login_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })
                        : '—'}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-500 dark:text-slate-400">
                      {u.created_at
                        ? new Date(u.created_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })
                        : '—'}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleEdit(u)}
                          className="p-2 rounded-lg text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 transition-colors"
                          title="Edit user"
                        >
                          <UserCog className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(u)}
                          disabled={u.id === currentUser?.id}
                          className="p-2 rounded-lg text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/50 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                          title={u.id === currentUser?.id ? 'Cannot delete yourself' : 'Delete user'}
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer count */}
      {!loading && (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Showing {filtered.length} of {users.length} users
        </p>
      )}

      {/* Dialogs */}
      <UserFormDialog
        open={formDialogOpen}
        onOpenChange={(open) => {
          setFormDialogOpen(open);
          if (!open) setEditingUser(null);
        }}
        user={editingUser}
        onSuccess={loadUsers}
      />

      <DeleteUserDialog
        open={deleteDialogOpen}
        onOpenChange={(open) => {
          setDeleteDialogOpen(open);
          if (!open) setDeletingUser(null);
        }}
        user={deletingUser}
        currentUserId={currentUser?.id}
        onSuccess={loadUsers}
      />
    </div>
  );
}
