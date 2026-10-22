import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AlertCircle, FileSearch, Link2, GitBranch } from 'lucide-react';

interface EssayActionBarProps {
  essayId: string;
}

/**
 * Quick navigation row beneath the report header. Links to companion pages
 * (Issues, Document, Consistency, Logic Trace) without consuming any state.
 */
export function EssayActionBar({ essayId }: EssayActionBarProps) {
  const { t } = useTranslation();

  return (
    <div className="flex gap-3 flex-wrap">
      <Link
        to={`/verification/report/${essayId}/issues`}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors text-sm"
      >
        <AlertCircle className="h-4 w-4" />
        {t('essay.issues')}
      </Link>
      <Link
        to={`/verification/report/${essayId}/document`}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors text-sm"
      >
        <FileSearch className="h-4 w-4" />
        {t('essay.document')}
      </Link>
      <Link
        to={`/verification/report/${essayId}/consistency`}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors text-sm"
      >
        <Link2 className="h-4 w-4" />
        {t('essay.consistency')}
      </Link>
      <Link
        to={`/verification/report/${essayId}/trace`}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-indigo-300 dark:hover:border-indigo-600 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors text-sm"
      >
        <GitBranch className="h-4 w-4" />
        {t('essay.logicTrace')}
      </Link>
    </div>
  );
}
