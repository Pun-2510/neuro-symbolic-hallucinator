import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Activity, Database, FileCheck, Users } from 'lucide-react';
import { api, type SystemHealth } from '@/api/client';
import { StatCard } from '@/components/StatCard';

export function SystemHealthPage() {
  const { t } = useTranslation();
  const [data, setData] = useState<SystemHealth | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getSystemHealth().then(setData).catch((e) => setError(String(e)));
  }, []);

  if (error) return <p className="text-rose-600">{t('common.error')}: {error}</p>;
  if (!data) return <p className="text-slate-500">{t('common.loading')}</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-950 flex items-center justify-center">
          <Activity className="h-5 w-5 text-violet-600 dark:text-violet-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{t('admin.systemHealth')}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">{t('admin.systemHealthSubtitle')}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard label={t('admin.totalUsers')} value={data.totals.users} icon={Users} color="indigo" />
        <StatCard label={t('admin.admins')} value={data.totals.admins} color="violet" />
        <StatCard label={t('admin.teachers')} value={data.totals.teachers} color="green" />
        <StatCard label={t('admin.students')} value={data.totals.students} color="slate" />
        <StatCard label={t('admin.essays')} value={data.totals.essays} icon={FileCheck} color="indigo" />
        <StatCard label={t('admin.verdicts')} value={data.totals.verdicts} icon={Database} color="amber" />
      </div>

      <div className="rounded-xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 p-5">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">{t('admin.verdictsByLabel')}</h2>
        <div className="space-y-2">
          {Object.entries(data.verdict_label_counts).map(([label, count]) => (
            <div key={label} className="flex justify-between text-sm">
              <span className="text-slate-600 dark:text-slate-400 font-mono">{label}</span>
              <span className="font-semibold text-slate-900 dark:text-white">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
