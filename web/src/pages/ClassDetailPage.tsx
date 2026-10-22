import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  UserPlus,
  Download,
  Users,
  FileText,
  Trash2,
  AlertCircle,
} from 'lucide-react';
import { api, type Class, type ClassStudent, type ClassEssay } from '@/api/client';
import { useToast } from '@/contexts/ToastContext';
import { ConfirmationModal } from '@/components/ConfirmationModal';
import { AddStudentDialog } from '@/components/AddStudentDialog';

/**
 * ClassDetailPage — manage a single class (Phase 4 / Task 14).
 *
 * 3 sections: header (name, description, CSV export), students (add/remove),
 * essays (click-through to report). Owner-only — 403 redirects to dashboard.
 */
export function ClassDetailPage() {
  const { classId } = useParams<{ classId: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const cid = Number(classId);

  const [cls, setCls] = useState<Class | null>(null);
  const [students, setStudents] = useState<ClassStudent[]>([]);
  const [essays, setEssays] = useState<ClassEssay[]>([]);
  const [addOpen, setAddOpen] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [pendingRemove, setPendingRemove] = useState<ClassStudent | null>(null);

  const load = useCallback(async () => {
    if (!cid || Number.isNaN(cid)) {
      setError('Invalid class id');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');
    try {
      // Try to find the class in teacher's class list to enforce ownership
      const all = await api.listMyClasses();
      const found = all.find((c) => c.id === cid);
      if (!found) {
        setError('Bạn không có quyền truy cập lớp này.');
        setLoading(false);
        return;
      }
      setCls(found);
      // Best-effort: load students + essays in parallel
      const [studentList, essayList] = await Promise.all([
        api.listClassStudents(cid).catch(() => []),
        api.listClassEssays(cid).catch(() => []),
      ]);
      setStudents(studentList);
      setEssays(essayList);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load class');
    } finally {
      setLoading(false);
    }
  }, [cid]);

  useEffect(() => {
    load();
  }, [load]);

  const handleRemove = async () => {
    if (!pendingRemove) return;
    const studentId = pendingRemove.id;
    setPendingRemove(null);
    try {
      await api.removeStudentFromClass(cid, studentId);
      toast.success(`Đã xóa ${pendingRemove.username} khỏi lớp`);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Xóa thất bại');
    }
  };

  const handleExport = async () => {
    try {
      const token = localStorage.getItem('token');
      const resp = await fetch(api.exportClassCSV(cid), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!resp.ok) {
        throw new Error(`API ${resp.status}: ${await resp.text()}`);
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `class_${cid}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Export CSV thất bại');
    }
  };

  if (loading) {
    return <p className="text-slate-500 p-6">Loading…</p>;
  }
  if (error) {
    return (
      <div className="space-y-4 p-6">
        <div
          className="flex items-start gap-2 p-3 rounded-lg bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 text-sm"
          role="alert"
        >
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
        <button
          onClick={() => navigate('/teacher/classes')}
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
        >
          ← Quay lại danh sách lớp
        </button>
      </div>
    );
  }
  if (!cls) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/teacher/classes')}
          aria-label="Back to classes"
          className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white truncate">
            {cls.name}
          </h1>
          {cls.description && (
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{cls.description}</p>
          )}
        </div>
        <button
          onClick={handleExport}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg ring-1 ring-slate-200 dark:ring-slate-700 text-sm hover:bg-slate-50 dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <Download className="h-4 w-4" />
          Export CSV
        </button>
      </div>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold flex items-center gap-2 text-slate-900 dark:text-white">
            <Users className="h-5 w-5" /> Sinh viên ({students.length})
          </h2>
          <button
            onClick={() => setAddOpen(true)}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <UserPlus className="h-4 w-4" />
            Thêm
          </button>
        </div>
        <div className="rounded-xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 divide-y divide-slate-100 dark:divide-slate-800">
          {students.length === 0 ? (
            <p className="p-6 text-center text-sm text-slate-500">Chưa có sinh viên.</p>
          ) : (
            students.map((s) => (
              <div key={s.id} className="flex items-center justify-between p-3">
                <div className="min-w-0">
                  <p className="font-medium text-sm text-slate-900 dark:text-slate-100 truncate">
                    {s.username}
                  </p>
                  {s.full_name && (
                    <p className="text-xs text-slate-500 truncate">{s.full_name}</p>
                  )}
                </div>
                <button
                  onClick={() => setPendingRemove(s)}
                  aria-label={`Remove ${s.username}`}
                  className="p-2 rounded-lg text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 focus:outline-none focus:ring-2 focus:ring-rose-500"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))
          )}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2 text-slate-900 dark:text-white">
          <FileText className="h-5 w-5" /> Bài nộp ({essays.length})
        </h2>
        <div className="rounded-xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 divide-y divide-slate-100 dark:divide-slate-800">
          {essays.length === 0 ? (
            <p className="p-6 text-center text-sm text-slate-500">Chưa có bài nộp.</p>
          ) : (
            essays.map((e) => (
              <Link
                key={e.id}
                to={`/verification/report/${e.id}`}
                className="flex items-center justify-between p-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 focus:outline-none focus:bg-slate-50 dark:focus:bg-slate-800/50"
              >
                <div className="min-w-0">
                  <p className="font-medium text-sm text-slate-900 dark:text-slate-100 truncate">
                    {e.filename}
                  </p>
                  <p className="text-xs text-slate-500">
                    {e.username ?? '—'} • {e.num_pages} trang •{' '}
                    {e.uploaded_at ? new Date(e.uploaded_at).toLocaleDateString() : ''}
                  </p>
                </div>
              </Link>
            ))
          )}
        </div>
      </section>

      <AddStudentDialog
        open={addOpen}
        classId={cid}
        existingStudentIds={students.map((s) => s.id)}
        onClose={() => setAddOpen(false)}
        onAdded={load}
      />

      <ConfirmationModal
        isOpen={pendingRemove !== null}
        title="Xóa sinh viên khỏi lớp"
        message={
          pendingRemove
            ? `Bạn có chắc muốn xóa "${pendingRemove.username}" khỏi lớp "${cls.name}"? Hành động này không thể hoàn tác.`
            : ''
        }
        confirmLabel="Xóa"
        cancelLabel="Hủy"
        variant="danger"
        onConfirm={handleRemove}
        onCancel={() => setPendingRemove(null)}
      />
    </div>
  );
}
