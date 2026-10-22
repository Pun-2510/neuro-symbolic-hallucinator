import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, FileText, Quote, Clock, Download } from 'lucide-react';
import { api } from '@/api/client';

/* ============================================================
   EssayHeader
   ------------------------------------------------------------
   Breadcrumb back-link + filename title + meta line + export buttons.
   Pure presentational: nhận `report` qua props, không tự fetch.
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
          className="inline-flex items-center gap-1 text-sm text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 mb-3 transition-colors"
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
          <span className="flex items-center gap-1.5">
            <FileText className="h-4 w-4" />
            {numPages} {t('history.pages')}
          </span>
          <span className="text-slate-300 dark:text-slate-600">·</span>
          <span className="flex items-center gap-1.5">
            <Quote className="h-4 w-4" />
            {numCitations} {t('essay.citationsTab').toLowerCase()}
          </span>
          {styleName && (
            <>
              <span className="text-slate-300 dark:text-slate-600">·</span>
              <span className="tag tag-primary">{styleName}</span>
            </>
          )}
          <span className="text-slate-300 dark:text-slate-600">·</span>
          <span className="flex items-center gap-1.5">
            <Clock className="h-4 w-4" />
            ID #{essayId}
          </span>
        </div>
      </div>

      {/* Export Actions */}
      <div className="flex gap-2 flex-wrap">
        <a
          href={api.downloadReport(essayId, 'json')}
          className="btn-ghost btn-sm"
          download
          aria-label={`Download ${filename} as JSON`}
        >
          <Download className="h-3.5 w-3.5" />
          JSON
        </a>
        <a
          href={api.downloadReport(essayId, 'csv')}
          className="btn-ghost btn-sm"
          download
          aria-label={`Download ${filename} as CSV`}
        >
          <Download className="h-3.5 w-3.5" />
          CSV
        </a>
        <a
          href={api.downloadReport(essayId, 'pdf')}
          className="btn-primary btn-sm"
          download
          aria-label={`Download ${filename} as PDF`}
        >
          <Download className="h-3.5 w-3.5" />
          PDF
        </a>
        <a
          href={api.downloadReport(essayId, 'docx')}
          className="btn-ghost btn-sm"
          download
          aria-label={`Download ${filename} as DOCX`}
        >
          <Download className="h-3.5 w-3.5" />
          DOCX
        </a>
      </div>
    </div>
  );
}
