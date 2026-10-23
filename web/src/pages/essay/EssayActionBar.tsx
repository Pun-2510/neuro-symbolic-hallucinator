import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AlertCircle, FileSearch, Link2, GitBranch, Terminal } from 'lucide-react';
import { useRole } from '@/hooks/useRole';
import { Button } from '@/components/ui/button';

interface EssayActionBarProps {
  essayId: string;
}

/**
 * Quick navigation row beneath the report header. Links to companion pages
 * (Debugger Report, Issues, Document, Consistency, Logic Trace) using shadcn/ui Button.
 */
export function EssayActionBar({ essayId }: EssayActionBarProps) {
  const { t, i18n } = useTranslation();
  const { has, isUser } = useRole();
  const location = useLocation();
  const lang = i18n.language?.startsWith('vi') ? 'vi' : 'en';

  const basePath = `/verification/report/${essayId}`;
  const currentPath = location.pathname;

  const isReportRoot = currentPath === basePath || currentPath === `/essay/${essayId}`;
  const isIssues = currentPath.endsWith('/issues');
  const isDocument = currentPath.endsWith('/document');
  const isConsistency = currentPath.endsWith('/consistency');
  const isTrace = currentPath.endsWith('/trace');

  return (
    <div className="inline-flex flex-wrap items-center gap-2 p-1.5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 shadow-2xs">
      <Button
        asChild
        variant={isReportRoot ? 'default' : 'ghost'}
        size="sm"
        className={`h-8 rounded-xl text-xs font-medium ${
          isReportRoot
            ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-xs'
            : 'text-slate-600 dark:text-slate-400'
        }`}
      >
        <Link to={basePath}>
          <Terminal className={`h-3.5 w-3.5 ${isReportRoot ? 'text-white' : 'text-indigo-500'}`} />
          <span>
            {isUser
              ? t('essay.citationsTab')
              : lang === 'vi'
                ? 'Citation Debugger'
                : 'Citation Debugger'}
          </span>
        </Link>
      </Button>

      <Button
        asChild
        variant={isIssues ? 'default' : 'ghost'}
        size="sm"
        className={`h-8 rounded-xl text-xs font-medium ${
          isIssues
            ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-xs'
            : 'text-slate-600 dark:text-slate-400'
        }`}
      >
        <Link to={`${basePath}/issues`}>
          <AlertCircle className={`h-3.5 w-3.5 ${isIssues ? 'text-white' : 'text-amber-500'}`} />
          <span>{t('essay.issues')}</span>
        </Link>
      </Button>

      {has('view_document_inspector') && (
        <Button
          asChild
          variant={isDocument ? 'default' : 'ghost'}
          size="sm"
          className={`h-8 rounded-xl text-xs font-medium ${
            isDocument
              ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-xs'
              : 'text-slate-600 dark:text-slate-400'
          }`}
        >
          <Link to={`${basePath}/document`}>
            <FileSearch className={`h-3.5 w-3.5 ${isDocument ? 'text-white' : 'text-indigo-500'}`} />
            <span>{t('essay.document')}</span>
          </Link>
        </Button>
      )}

      {has('view_orphan_detection') && (
        <Button
          asChild
          variant={isConsistency ? 'default' : 'ghost'}
          size="sm"
          className={`h-8 rounded-xl text-xs font-medium ${
            isConsistency
              ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-xs'
              : 'text-slate-600 dark:text-slate-400'
          }`}
        >
          <Link to={`${basePath}/consistency`}>
            <Link2 className={`h-3.5 w-3.5 ${isConsistency ? 'text-white' : 'text-emerald-500'}`} />
            <span>{t('essay.consistency')}</span>
          </Link>
        </Button>
      )}

      {has('view_logic_trace') && (
        <Button
          asChild
          variant={isTrace ? 'default' : 'ghost'}
          size="sm"
          className={`h-8 rounded-xl text-xs font-medium ${
            isTrace
              ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-xs'
              : 'text-slate-600 dark:text-slate-400'
          }`}
        >
          <Link to={`${basePath}/trace`}>
            <GitBranch className={`h-3.5 w-3.5 ${isTrace ? 'text-white' : 'text-violet-500'}`} />
            <span>{t('essay.logicTrace')}</span>
          </Link>
        </Button>
      )}
    </div>
  );
}
