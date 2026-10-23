import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, FileText, Quote, Clock, Download } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

/* ============================================================
   EssayHeader (shadcn/ui v2.0)
   Breadcrumb back-link + filename title + meta line + export buttons.
   ============================================================ */

export interface EssayHeaderProps {
  essayId: number;
  filename: string;
  numPages: number;
  numCitations: number;
  styleName?: string;
}

export function EssayHeader({
  essayId,
  filename,
  numPages,
  numCitations,
  styleName,
}: EssayHeaderProps) {
  const { t } = useTranslation();

  return (
    <div className="flex items-start justify-between flex-wrap gap-4">
      <div className="min-w-0 flex-1">
        <Link
          to="/history"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 mb-3 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('essay.backToReports').replace(/^←\s*/, '')}
        </Link>
        <h1
          className="font-display text-3xl font-bold text-slate-900 dark:text-slate-100 truncate"
          title={filename}
        >
          {filename}
        </h1>
        <div className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-300 mt-2 flex-wrap">
          <span className="flex items-center gap-1.5 font-mono text-xs">
            <FileText className="h-4 w-4 text-slate-400" />
            {numPages} {t('history.pages')}
          </span>
          <span className="text-slate-300 dark:text-slate-600">·</span>
          <span className="flex items-center gap-1.5 font-mono text-xs">
            <Quote className="h-4 w-4 text-slate-400" />
            {numCitations} {t('essay.citationsTab').toLowerCase()}
          </span>
          {styleName && (
            <>
              <span className="text-slate-300 dark:text-slate-600">·</span>
              <Badge variant="secondary" className="font-mono text-xs">
                {styleName}
              </Badge>
            </>
          )}
          <span className="text-slate-300 dark:text-slate-600">·</span>
          <span className="flex items-center gap-1.5 font-mono text-xs">
            <Clock className="h-4 w-4 text-slate-400" />
            ID #{essayId}
          </span>
        </div>
      </div>

      {/* Export Actions */}
      <div className="flex gap-2 flex-wrap">
        <Button asChild variant="outline" size="sm">
          <a
            href={api.downloadReport(essayId, 'json')}
            download
            aria-label={`Download ${filename} as JSON`}
          >
            <Download className="h-3.5 w-3.5" />
            JSON
          </a>
        </Button>
        <Button asChild variant="outline" size="sm">
          <a
            href={api.downloadReport(essayId, 'csv')}
            download
            aria-label={`Download ${filename} as CSV`}
          >
            <Download className="h-3.5 w-3.5" />
            CSV
          </a>
        </Button>
        <Button asChild size="sm">
          <a
            href={api.downloadReport(essayId, 'pdf')}
            download
            aria-label={`Download ${filename} as PDF`}
          >
            <Download className="h-3.5 w-3.5" />
            PDF
          </a>
        </Button>
        <Button asChild variant="outline" size="sm">
          <a
            href={api.downloadReport(essayId, 'docx')}
            download
            aria-label={`Download ${filename} as DOCX`}
          >
            <Download className="h-3.5 w-3.5" />
            DOCX
          </a>
        </Button>
      </div>
    </div>
  );
}
