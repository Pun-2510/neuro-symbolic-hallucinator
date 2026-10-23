import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
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
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

/**
 * MyClassesPage — teacher dashboard (Phase 4).
 *
 * Shows aggregate stats + class list. Click into a class to manage students
 * and essays (ClassDetailPage, Task 14).
 */
export function MyClassesPage() {
  const { t } = useTranslation();
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
            <h1 className="font-display text-2xl font-bold text-slate-900 dark:text-white">{t('teacher.myClasses')}</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {t('teacher.myClassesSubtitle')}
            </p>
          </div>
        </div>
        <Button
          onClick={() => setCreateOpen(true)}
          aria-label="Tạo lớp"
          className="gap-2"
        >
          <Plus className="h-4 w-4" />
          {t('teacher.createClass')}
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {dashboard && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label={t('teacher.classes')}
            value={dashboard.total_classes}
            icon={GraduationCap}
            color="indigo"
          />
          <StatCard
            label={t('teacher.students')}
            value={dashboard.total_students}
            icon={Users}
            color="green"
          />
          <StatCard
            label={t('teacher.submissions')}
            value={dashboard.total_essays}
            icon={FileCheck}
            color="amber"
          />
          <StatCard
            label={t('teacher.needsReview')}
            value={dashboard.pending_reviews}
            icon={ClipboardCheck}
            color="rose"
            hint="metadata_error / suspected_hallucination"
          />
        </div>
      )}

      <div className="space-y-2.5">
        {dashboard?.classes.length === 0 ? (
          <Card className="border-dashed border-slate-300 dark:border-slate-700 p-12 text-center">
            <p className="text-slate-700 dark:text-slate-300 font-medium">{t('teacher.noClassesYet')}</p>
            <p className="text-sm text-slate-500 mt-1">{t('teacher.noClassesHint')}</p>
          </Card>
        ) : (
          dashboard?.classes.map((c: Class) => (
            <button
              key={c.id}
              onClick={() => navigate(`/teacher/classes/${c.id}`)}
              className="card w-full text-left rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 hover:border-indigo-300 dark:hover:border-indigo-700 transition-all flex items-center justify-between group focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                <div className="flex gap-3 mt-2.5">
                  <Badge variant="secondary" className="font-normal text-xs">
                    <Users className="inline h-3 w-3 mr-1" />
                    {c.student_count} SV
                  </Badge>
                  <Badge variant="secondary" className="font-normal text-xs">
                    <FileCheck className="inline h-3 w-3 mr-1" />
                    {c.essay_count} bài
                  </Badge>
                </div>
              </div>
              <ChevronRight className="h-5 w-5 text-slate-400 group-hover:text-indigo-500 shrink-0 transition-transform group-hover:translate-x-0.5" />
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
