import { useState, useEffect, useRef } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Loader2 } from 'lucide-react';
import type { User, UserCreate, UserUpdate } from '@/api/client';
import { api } from '@/api/client';

interface UserFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user?: User | null;   // undefined = create mode, User = edit mode
  onSuccess: () => void;
}

export function UserFormDialog({
  open,
  onOpenChange,
  user,
  onSuccess,
}: UserFormDialogProps) {
  const isEdit = Boolean(user);

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'admin' | 'user'>('user');
  const [isActive, setIsActive] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      if (user) {
        setUsername(user.username);
        setEmail(user.email ?? '');
        setFullName(user.full_name ?? '');
        setPassword('');
        setRole(user.role as 'admin' | 'user');
        setIsActive(user.is_active);
      } else {
        setUsername('');
        setEmail('');
        setFullName('');
        setPassword('');
        setRole('user');
        setIsActive(true);
      }
      setError('');
    }
  }, [open, user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const payload: UserCreate | UserUpdate = isEdit
      ? {
          username: username || undefined,
          email: email || undefined,
          full_name: fullName || undefined,
          role: role || undefined,
          is_active: isActive ?? undefined,
          ...(password ? { password } : {}),
        }
      : {
          username,
          password,
          email: email || undefined,
          full_name: fullName || undefined,
          role,
          is_active: isActive,
        };

    setLoading(true);
    try {
      if (isEdit && user) {
        await api.updateUser(user.id, payload as UserUpdate);
      } else {
        await api.createUser(payload as UserCreate);
      }
      onSuccess();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 animate-in fade-in" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-lg bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-xl p-6 animate-in fade-in zoom-in-95 duration-200">
          <div className="flex items-center justify-between mb-6">
            <Dialog.Title className="font-display text-xl font-bold text-slate-900 dark:text-white">
              {isEdit ? 'Edit User' : 'Create New User'}
            </Dialog.Title>
            <Dialog.Close className="p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
              <X className="h-5 w-5" />
            </Dialog.Close>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="input-label">Username *</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required={!isEdit}
                minLength={3}
                maxLength={50}
                disabled={loading}
                className="input"
                placeholder="e.g. john_doe"
              />
            </div>

            {!isEdit && (
              <div>
                <label className="input-label">Password *</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required={!isEdit}
                  minLength={6}
                  maxLength={128}
                  disabled={loading}
                  className="input"
                  placeholder="Minimum 6 characters"
                />
              </div>
            )}

            {isEdit && (
              <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800 text-sm text-amber-700 dark:text-amber-300">
                Leave password blank to keep the current password.
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="input-label">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  maxLength={120}
                  disabled={loading}
                  className="input"
                  placeholder="e.g. John Doe"
                />
              </div>

              <div>
                <label className="input-label">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  className="input"
                  placeholder="e.g. john@example.com"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="input-label">Role</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as 'admin' | 'user')}
                  disabled={loading}
                  className="input"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              <div className="flex items-center gap-3 pt-7">
                <button
                  type="button"
                  onClick={() => setIsActive(!isActive)}
                  disabled={loading}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    isActive ? 'bg-indigo-600' : 'bg-slate-300 dark:bg-slate-600'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                      isActive ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
                <span className="text-sm text-slate-700 dark:text-slate-300">
                  {isActive ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => onOpenChange(false)}
                disabled={loading}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : isEdit ? (
                  'Save Changes'
                ) : (
                  'Create User'
                )}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
