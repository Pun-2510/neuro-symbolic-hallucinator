import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AlertCircle, FileSearch, Link2, GitBranch } from 'lucide-react';
import { useRole } from '@/hooks/useRole';
import { Button } from '@/components/ui/button';

interface EssayActionBarProps {
  essayId: string;
}

/**
 * Quick navigation row beneath the report header. Links to companion pages
 * (Issues, Document, Consistency, Logic Trace) using shadcn/ui Button.
 */
export function EssayActionBar({ essayId }: EssayActionBarProps) {
  const { t } = useTranslation();
  const { has } = useRole();

  return (
    <div className="flex gap-2.5 flex-wrap">
      <Button asChild variant="outline" size="sm">
        <Link to={`/verification/report/${essayId}/issues`}>
          <AlertCircle className="h-4 w-4 text-amber-500" />
          {t('essay.issues')}
        </Link>
      </Button>
      {has('view_document_inspector') && (
        <Button asChild variant="outline" size="sm">
          <Link to={`/verification/report/${essayId}/document`}>
            <FileSearch className="h-4 w-4 text-indigo-500" />
            {t('essay.document')}
          </Link>
        </Button>
      )}
      {has('view_orphan_detection') && (
        <Button asChild variant="outline" size="sm">
          <Link to={`/verification/report/${essayId}/consistency`}>
            <Link2 className="h-4 w-4 text-emerald-500" />
            {t('essay.consistency')}
          </Link>
        </Button>
      )}
      {has('view_logic_trace') && (
        <Button asChild variant="outline" size="sm">
          <Link to={`/verification/report/${essayId}/trace`}>
            <GitBranch className="h-4 w-4 text-violet-500" />
            {t('essay.logicTrace')}
          </Link>
        </Button>
      )}
    </div>
  );
}
