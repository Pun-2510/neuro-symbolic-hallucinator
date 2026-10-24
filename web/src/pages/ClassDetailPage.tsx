import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  ArrowLeft,
  UserPlus,
  Download,
  Users,
  FileText,
  Trash2,
  AlertCircle,
  Terminal,
  ShieldCheck,
  ExternalLink,
  Loader2,
} from 'lucide-react';
import { api, type Class, type ClassStudent, type ClassEssay } from '@/api/client';
import { useToast } from '@/contexts/ToastContext';
import { ConfirmationModal } from '@/components/ConfirmationModal';
import { AddStudentDialog } from '@/components/AddStudentDialog';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';

/**
 * ClassDetailPage — manage a single class (Scholarly Precision shadcn/ui v2.0).
 *
 * 3 sections: header (name, description, CSV export), students (add/remove),
 * essays (click-through to report). Owner-only — 403 redirects to dashboard.
 */
export function ClassDetailPage() {
  const { classId } = useParams<{ classId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
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
      const all = await api.listMyClasses();
      const found = all.find((c) => c.id === cid);
      if (!found) {
        setError(t('teacher.classAccessDenied'));
        setLoading(false);
        return;
      }
      setCls(found);
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
  }, [cid, t]);

  useEffect(() => {
    load();
  }, [load]);

  const handleRemove = async () => {
    if (!pendingRemove) return;
    const studentId = pendingRemove.id;
    setPendingRemove(null);
    try {
      await api.removeStudentFromClass(cid, studentId);
      toast.success(
        t('teacher.studentRemovedSuccess', { username: pendingRemove.username })
      );
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t('teacher.studentRemoveFailed'));
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
      toast.error(e instanceof Error ? e.message : t('teacher.exportCsvFailed'));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 text-indigo-600 dark:text-indigo-400 animate-spin" />
        <span className="ml-3 text-slate-500 font-mono text-sm">
          {t('common.loading')}
        </span>
      </div>
    );
  }
  if (error) {
    return (
      <div className="space-y-4 p-6">
        <Alert variant="destructive" className="rounded-2xl">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button
          variant="link"
          onClick={() => navigate('/teacher/classes')}
          className="px-0"
        >
          {t('teacher.backToClasses')}
        </Button>
      </div>
    );
  }
  if (!cls) return null;

  return (
    <div className="space-y-6 pb-10">
      {/* Executive Header Card */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 p-5 sm:p-6 shadow-xs">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2.5 flex-wrap mb-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate('/teacher/classes')}
                aria-label="Back to classes"
                className="h-7 px-2.5 rounded-lg text-xs font-mono gap-1.5"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                {t('common.back')}
              </Button>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200/70 dark:border-indigo-800/70 text-[11px] font-mono font-semibold text-indigo-700 dark:text-indigo-300">
                <ShieldCheck className="h-3.5 w-3.5" />
                COHORT #{cls.id}
              </span>
            </div>

            <h1 className="font-display text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white truncate tracking-tight">
              {cls.name}
            </h1>
            {cls.description && (
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                {cls.description}
              </p>
            )}
          </div>

          <Button
            variant="outline"
            onClick={handleExport}
            className="gap-2 rounded-xl font-mono text-xs h-9 shrink-0"
          >
            <Download className="h-3.5 w-3.5" />
            {t('teacher.exportCsv')}
          </Button>
        </div>
      </div>

      {/* Architectural Metric Cards */}
      <div className="grid grid-cols-2 gap-4">
        <Card className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
              {t('teacher.enrolledStudents')}
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/80 text-indigo-600 dark:text-indigo-400">
              01
            </span>
          </div>
          <p className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100">
            {students.length}
          </p>
        </Card>

        <Card className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
              {t('teacher.cohortSubmissions')}
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/80 text-emerald-600 dark:text-emerald-400">
              02
            </span>
          </div>
          <p className="text-2xl font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400">
            {essays.length}
          </p>
        </Card>
      </div>

      {/* Students Roster IDE Container */}
      <section className="rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-3 bg-slate-50/90 dark:bg-slate-900/90 border-b border-slate-200/80 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-400/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80" />
            </div>
            <Separator orientation="vertical" className="h-4" />
            <Users className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            <h2 className="text-sm font-display font-semibold text-slate-900 dark:text-white">
              {t('teacher.students')} ({students.length})
            </h2>
          </div>
          <Button
            size="sm"
            onClick={() => setAddOpen(true)}
            className="gap-1.5 rounded-xl h-8 text-xs"
          >
            <UserPlus className="h-3.5 w-3.5" />
            {t('teacher.addStudent')}
          </Button>
        </div>

        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {students.length === 0 ? (
            <p className="p-8 text-center text-sm text-slate-500 font-mono">
              {t('teacher.noStudentsYet')}
            </p>
          ) : (
            students.map((s, idx) => (
              <div
                key={s.id}
                className="flex items-center justify-between px-5 py-3.5 hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-xs font-mono text-slate-400 dark:text-slate-500">
                    #{String(idx + 1).padStart(2, '0')}
                  </span>
                  <div className="min-w-0">
                    <p className="font-medium text-sm text-slate-900 dark:text-slate-100 truncate">
                      {s.username}
                    </p>
                    {s.full_name && (
                      <p className="text-xs text-slate-500 truncate">{s.full_name}</p>
                    )}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setPendingRemove(s)}
                  aria-label={`Remove ${s.username}`}
                  className="text-rose-600 hover:bg-rose-50 hover:text-rose-700 dark:hover:bg-rose-950/30 rounded-lg"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Submissions IDE Container */}
      <section className="rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-3 bg-slate-50/90 dark:bg-slate-900/90 border-b border-slate-200/80 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-400/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80" />
            </div>
            <Separator orientation="vertical" className="h-4" />
            <FileText className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            <h2 className="text-sm font-display font-semibold text-slate-900 dark:text-white">
              {t('teacher.submissions')} ({essays.length})
            </h2>
          </div>
          <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
            <Terminal className="h-3 w-3" />
            cohort_submissions.log
          </span>
        </div>

        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {essays.length === 0 ? (
            <p className="p-8 text-center text-sm text-slate-500 font-mono">
              {t('teacher.noSubmissionsYet')}
            </p>
          ) : (
            essays.map((e, idx) => (
              <Link
                key={e.id}
                to={`/verification/report/${e.id}`}
                className="flex items-center justify-between px-5 py-3.5 hover:bg-slate-50 dark:hover:bg-slate-800/50 focus:outline-none focus:bg-slate-50 dark:focus:bg-slate-800/50 transition-colors group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-xs font-mono text-slate-400 dark:text-slate-500">
                    #{String(idx + 1).padStart(2, '0')}
                  </span>
                  <div className="min-w-0">
                    <p className="font-medium text-sm text-slate-900 dark:text-slate-100 truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      {e.filename}
                    </p>
                    <p className="text-xs font-mono text-slate-500 mt-0.5">
                      {e.username ?? '—'} • {e.num_pages} {t('teacher.pages')} •{' '}
                      {e.uploaded_at
                        ? new Date(e.uploaded_at).toLocaleDateString()
                        : ''}
                    </p>
                  </div>
                </div>
                <ExternalLink className="h-4 w-4 text-slate-400 group-hover:text-indigo-500 shrink-0 transition-colors" />
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
        title={t('teacher.removeStudentTitle')}
        message={
          pendingRemove
            ? t('teacher.removeStudentConfirm', {
                username: pendingRemove.username,
                className: cls.name,
              })
            : ''
        }
        confirmLabel={t('common.delete')}
        cancelLabel={t('common.cancel')}
        variant="danger"
        onConfirm={handleRemove}
        onCancel={() => setPendingRemove(null)}
      />
    </div>
  );
}
