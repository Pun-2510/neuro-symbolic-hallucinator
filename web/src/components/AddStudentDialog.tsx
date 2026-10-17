import { useEffect, useState } from 'react';
import { X, Search } from 'lucide-react';
import { api, type User } from '@/api/client';

export interface AddStudentDialogProps {
  open: boolean;
  classId: number;
  existingStudentIds: number[];
  onClose: () => void;
  onAdded: () => void;
}

/**
 * AddStudentDialog — search and add students to a class (Phase 4).
 *
 * Lists users with role='user' (students), filters out those already enrolled,
 * and supports live search by username/full_name.
 */
export function AddStudentDialog({
  open,
  classId,
  existingStudentIds,
  onClose,
  onAdded,
}: AddStudentDialogProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Load students list when dialog opens
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError('');
    api.listUsers()
      .then((data) => {
        if (!cancelled) setUsers(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load users');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  // Escape to close
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  const q = search.trim().toLowerCase();
  const candidates = users.filter(
    (u) =>
      u.role === 'user' &&
      !existingStudentIds.includes(u.id) &&
      (!q ||
        u.username.toLowerCase().includes(q) ||
        (u.full_name ?? '').toLowerCase().includes(q)),
  );

  const handleAdd = async (studentId: number) => {
    setSubmitting(true);
    setError('');
    try {
      await api.addStudentToClass(classId, studentId);
      onAdded();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add student');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-student-title"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 id="add-student-title" className="text-lg font-bold text-slate-900 dark:text-white">
            Thêm sinh viên
          </h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>

        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm theo username hoặc tên…"
            aria-label="Search students"
            className="w-full pl-10 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {error && (
          <p className="text-sm text-rose-600 dark:text-rose-400 mb-2" role="alert">
            {error}
          </p>
        )}

        <ul className="max-h-80 overflow-y-auto space-y-1" aria-busy={loading}>
          {loading ? (
            <li className="text-sm text-slate-500 px-2 py-4 text-center">Đang tải…</li>
          ) : candidates.length === 0 ? (
            <li className="text-sm text-slate-500 px-2 py-4 text-center">
              Không có sinh viên phù hợp.
            </li>
          ) : (
            candidates.map((u) => (
              <li
                key={u.id}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                    {u.username}
                  </p>
                  {u.full_name && (
                    <p className="text-xs text-slate-500 truncate">{u.full_name}</p>
                  )}
                </div>
                <button
                  onClick={() => handleAdd(u.id)}
                  disabled={submitting}
                  className="px-3 py-1 text-xs rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Thêm
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
