import { useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import type { User } from '@/api/client';
import { api } from '@/api/client';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';

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
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" hideCloseButton>
        <div className="flex items-start gap-4 mb-3">
          <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950 shrink-0">
            <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
          </div>
          <div>
            <DialogTitle className="text-lg font-bold mb-1">
              Delete User
            </DialogTitle>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              You are about to delete the user{' '}
              <span className="font-semibold text-slate-900 dark:text-white">
                {user.username}
              </span>
              . This action cannot be undone.
            </p>
          </div>
        </div>

        {error && (
          <Alert variant="destructive" className="mb-3">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isSelf && (
          <Alert variant="warning" className="mb-3">
            <AlertDescription>
              You cannot delete your own account.
            </AlertDescription>
          </Alert>
        )}

        <div className="flex justify-end gap-2.5">
          <DialogClose asChild>
            <Button type="button" variant="secondary">
              Cancel
            </Button>
          </DialogClose>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={loading || isSelf}
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete User'
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
