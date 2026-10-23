import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import type { User, UserCreate, UserUpdate } from '@/api/client';
import { api } from '@/api/client';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface UserFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user?: User | null; // undefined = create mode, User = edit mode
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
  const [institution, setInstitution] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'user' | 'teacher' | 'admin'>('user');
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
        setInstitution(user.institution ?? '');
        setPassword('');
        setRole(user.role as 'user' | 'teacher' | 'admin');
        setIsActive(user.is_active);
      } else {
        setUsername('');
        setEmail('');
        setFullName('');
        setInstitution('');
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
          institution: institution || undefined,
          role: role || undefined,
          is_active: isActive ?? undefined,
          ...(password ? { password } : {}),
        }
      : {
          username,
          password,
          email: email || undefined,
          full_name: fullName || undefined,
          institution: institution || undefined,
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
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader className="mb-2">
          <DialogTitle className="text-xl font-bold">
            {isEdit ? 'Edit User' : 'Create New User'}
          </DialogTitle>
        </DialogHeader>

        {error && (
          <Alert variant="destructive" className="mb-2">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Username *</Label>
            <Input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required={!isEdit}
              minLength={3}
              maxLength={50}
              disabled={loading}
              placeholder="e.g. john_doe"
            />
          </div>

          {!isEdit && (
            <div className="space-y-1.5">
              <Label>Password *</Label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required={!isEdit}
                minLength={6}
                maxLength={128}
                disabled={loading}
                placeholder="Minimum 6 characters"
              />
            </div>
          )}

          {isEdit && (
            <Alert variant="warning">
              <AlertDescription>
                Leave password blank to keep the current password.
              </AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Full Name</Label>
              <Input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                maxLength={120}
                disabled={loading}
                placeholder="e.g. John Doe"
              />
            </div>

            <div className="space-y-1.5">
              <Label>Email</Label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                placeholder="e.g. john@example.com"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Role</Label>
              <Select
                value={role}
                onChange={(e) =>
                  setRole(e.target.value as 'user' | 'teacher' | 'admin')
                }
                disabled={loading}
                wrapperClassName="w-full"
              >
                <option value="user">User</option>
                <option value="teacher">Teacher</option>
                <option value="admin">Admin</option>
              </Select>
            </div>

            <div className="flex items-center gap-3 pt-7">
              <Switch
                checked={isActive}
                onCheckedChange={setIsActive}
                disabled={loading}
              />
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {isActive ? 'Active' : 'Inactive'}
              </span>
            </div>
          </div>

          <div className="flex justify-end gap-2.5 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
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
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
