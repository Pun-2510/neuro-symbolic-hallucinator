import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { AlertTriangle, Loader2 } from 'lucide-react';
import type { User } from '@/api/client';
import { api } from '@/api/client';

interface DeleteUserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: User | null;
  currentUserId?: number;
  onSuccess: () => void;
}

export function DeleteUserDialog({
  open,
  onOpenChange,
  user,
  currentUserId,
  onSuccess,
}: DeleteUserDialogProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const isSelf = currentUserId !== undefined && user?.id === currentUserId;

  const handleDelete = async () => {
    if (!user || isSelf) return;
    setLoading(true);
    setError('');
    try {
      await api.deleteUser(user.id);
      onSuccess();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    } finally {
      setLoading(false);
    }
  };

  if (!user) return null;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 animate-in fade-in" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-xl p-6 animate-in fade-in zoom-in-95 duration-200">
          <div className="flex items-start gap-4 mb-5">
            <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950 shrink-0">
              <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <Dialog.Title className="font-display text-lg font-bold text-slate-900 dark:text-white mb-1">
                Delete User
              </Dialog.Title>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                You are about to delete the user{' '}
                <span className="font-semibold text-slate-900 dark:text-white">{user.username}</span>.
                This action cannot be undone.
              </p>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
              {error}
            </div>
          )}

          {isSelf && (
            <div className="mb-4 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800 text-sm text-amber-700 dark:text-amber-300">
              You cannot delete your own account.
            </div>
          )}

          <div className="flex justify-end gap-3">
            <Dialog.Close asChild>
              <button type="button" className="btn-secondary">
                Cancel
              </button>
            </Dialog.Close>
            <button
              onClick={handleDelete}
              disabled={loading || isSelf}
              className="btn-danger disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete User'
              )}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
