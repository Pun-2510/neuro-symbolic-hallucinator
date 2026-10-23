import { useTranslation } from 'react-i18next';
import { Card } from '@/components/ui/card';

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
 * Suspected, Coverage) built on shadcn/ui Card.
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
      <Card className="p-5 text-center">
        <p className="text-3xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100">
          {total}
        </p>
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mt-1">
          {t('essay.total')}
        </p>
      </Card>
      <Card className="p-5 text-center border-emerald-200/70 dark:border-emerald-800/70">
        <p className="text-3xl font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400">
          {verified}
        </p>
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mt-1">
          {t('verdict.verified')}
        </p>
      </Card>
      <Card className="p-5 text-center border-amber-200/70 dark:border-amber-800/70">
        <p className="text-3xl font-bold font-mono tabular-nums text-amber-600 dark:text-amber-400">
          {metadataError}
        </p>
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mt-1">
          {t('verdict.metadataError')}
        </p>
      </Card>
      <Card className="p-5 text-center border-red-200/70 dark:border-red-800/70">
        <p className="text-3xl font-bold font-mono tabular-nums text-red-600 dark:text-red-400">
          {suspectedHallucination}
        </p>
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mt-1">
          {t('essay.suspected')}
        </p>
      </Card>
      <Card className="p-5 text-center border-indigo-200/70 dark:border-indigo-800/70">
        <p className="text-3xl font-bold font-mono tabular-nums text-indigo-600 dark:text-indigo-400">
          {coverage}%
        </p>
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mt-1">
          {t('essay.coverage')}
        </p>
      </Card>
    </div>
  );
}
