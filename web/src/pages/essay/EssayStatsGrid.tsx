import { useTranslation } from 'react-i18next';

interface EssayStatsGridProps {
  total: number;
  verified: number;
  metadataError: number;
  suspectedHallucination: number;
  /** 0-100 percentage */
  coverage: number;
}

/**
 * Stats overview grid (5 cells: Total, Verified, Metadata Error,
 * Suspected, Coverage). All cells use the same stat-card styling.
 */
export function EssayStatsGrid({
  total,
  verified,
  metadataError,
  suspectedHallucination,
  coverage,
}: EssayStatsGridProps) {
  const { t } = useTranslation();

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      <div className="stat-card text-center">
        <p className="text-3xl font-bold text-slate-900 dark:text-slate-100">{total}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t('essay.total')}</p>
      </div>
      <div className="stat-card text-center">
        <p className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">{verified}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t('verdict.verified')}</p>
      </div>
      <div className="stat-card text-center">
        <p className="text-3xl font-bold text-amber-600 dark:text-amber-400">{metadataError}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t('verdict.metadataError')}</p>
      </div>
      <div className="stat-card text-center">
        <p className="text-3xl font-bold text-red-600 dark:text-red-400">{suspectedHallucination}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t('essay.suspected')}</p>
      </div>
      <div className="stat-card text-center">
        <p className="text-3xl font-bold text-indigo-600 dark:text-indigo-400">{coverage}%</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t('essay.coverage')}</p>
      </div>
    </div>
  );
}
