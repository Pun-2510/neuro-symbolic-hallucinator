import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  GraduationCap,
  Plus,
  Users,
  FileCheck,
  ClipboardCheck,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';
import { api, type Class, type TeacherDashboard } from '@/api/client';
import { StatCard } from '@/components/StatCard';
import { CreateClassDialog } from '@/components/CreateClassDialog';

/**
 * MyClassesPage — teacher dashboard (Phase 4).
 *
 * Shows aggregate stats + class list. Click into a class to manage students
 * and essays (ClassDetailPage, Task 14).
 */
export function MyClassesPage() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<TeacherDashboard | null>(null);
  const [error, setError] = useState('');
  const [createOpen, setCreateOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api.getTeacherDashboard();
      setDashboard(data);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load dashboard');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-950 flex items-center justify-center">
            <GraduationCap className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">My Classes</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Quản lý lớp học và theo dõi bài nộp.
            </p>
          </div>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          <Plus className="h-4 w-4" />
          Tạo lớp
        </button>
      </div>

      {error && (
        <div
          className="flex items-start gap-2 p-3 rounded-lg bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 text-sm"
          role="alert"
        >
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {dashboard && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Lớp"
            value={dashboard.total_classes}
            icon={GraduationCap}
            color="indigo"
          />
          <StatCard
            label="Sinh viên"
            value={dashboard.total_students}
            icon={Users}
            color="green"
          />
          <StatCard
            label="Bài nộp"
            value={dashboard.total_essays}
            icon={FileCheck}
            color="amber"
          />
          <StatCard
            label="Cần xem xét"
            value={dashboard.pending_reviews}
            icon={ClipboardCheck}
            color="rose"
            hint="metadata_error / suspected_hallucination"
          />
        </div>
      )}

      <div className="space-y-2">
        {dashboard?.classes.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 p-12 text-center">
            <p className="text-slate-700 dark:text-slate-300 font-medium">Chưa có lớp nào.</p>
            <p className="text-sm text-slate-500 mt-1">Bấm "Tạo lớp" để bắt đầu.</p>
          </div>
        ) : (
          dashboard?.classes.map((c: Class) => (
            <button
              key={c.id}
              onClick={() => navigate(`/teacher/classes/${c.id}`)}
              className="w-full text-left rounded-xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 p-4 hover:ring-indigo-300 dark:hover:ring-indigo-700 transition-all flex items-center justify-between group focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-slate-900 dark:text-white truncate">
                  {c.name}
                </h3>
                {c.description && (
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5 truncate">
                    {c.description}
                  </p>
                )}
                <div className="flex gap-4 mt-2 text-xs text-slate-500">
                  <span>
                    <Users className="inline h-3 w-3 mr-1" />
                    {c.student_count} SV
                  </span>
                  <span>
                    <FileCheck className="inline h-3 w-3 mr-1" />
                    {c.essay_count} bài
                  </span>
                </div>
              </div>
              <ChevronRight className="h-5 w-5 text-slate-400 group-hover:text-indigo-500 shrink-0" />
            </button>
          ))
        )}
      </div>

      <CreateClassDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={load}
      />
    </div>
  );
}
