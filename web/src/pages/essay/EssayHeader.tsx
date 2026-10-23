import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, FileText, Quote, Clock, Download, ShieldCheck } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

/* ============================================================
   EssayHeader (Scholarly Precision shadcn/ui v2.0)
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
  const { t, i18n } = useTranslation();
  const lang = i18n.language?.startsWith('vi') ? 'vi' : 'en';

  return (
    <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 p-5 sm:p-6 shadow-xs">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3 flex-wrap mb-2.5">
            <Link
              to="/history"
              className="inline-flex items-center gap-1.5 text-xs font-mono font-semibold text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700 transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              {t('essay.backToReports').replace(/^←\s*/, '')}
            </Link>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200/70 dark:border-indigo-800/70 text-[11px] font-mono font-semibold text-indigo-700 dark:text-indigo-300">
              <ShieldCheck className="h-3.5 w-3.5" />
              {lang === 'vi' ? 'BÁO CÁO KIỂM CHỨNG HỌC THUẬT' : 'VERIFICATION REPORT IDE'}
            </span>
          </div>

          <h1
            className="font-display text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100 truncate tracking-tight"
            title={filename}
          >
            {filename}
          </h1>

          <div className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-300 mt-2.5 flex-wrap">
            <span className="inline-flex items-center gap-1.5 font-mono text-xs px-2.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
              <FileText className="h-3.5 w-3.5 text-indigo-500" />
              {numPages} {t('history.pages')}
            </span>
            <span className="inline-flex items-center gap-1.5 font-mono text-xs px-2.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
              <Quote className="h-3.5 w-3.5 text-emerald-500" />
              {numCitations} {t('essay.citationsTab').toLowerCase()}
            </span>
            {styleName && (
              <Badge variant="secondary" className="font-mono text-xs">
                {styleName}
              </Badge>
            )}
            <span className="inline-flex items-center gap-1.5 font-mono text-xs text-slate-500 dark:text-slate-400">
              <Clock className="h-3.5 w-3.5 text-slate-400" />
              ID #{essayId}
            </span>
          </div>
        </div>

        {/* Export Actions */}
        <div className="flex flex-col items-start sm:items-end gap-1.5 shrink-0">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 dark:text-slate-500">
            {lang === 'vi' ? 'Xuất Báo Cáo Chuẩn Hóa' : 'Export Audit Artifact'}
          </span>
          <div className="flex gap-2 flex-wrap">
            <Button asChild variant="outline" size="sm" className="h-8 font-mono text-xs rounded-xl">
              <a
                href={api.downloadReport(essayId, 'json')}
                download
                aria-label={`Download ${filename} as JSON`}
              >
                <Download className="h-3.5 w-3.5" />
                JSON
              </a>
            </Button>
            <Button asChild variant="outline" size="sm" className="h-8 font-mono text-xs rounded-xl">
              <a
                href={api.downloadReport(essayId, 'csv')}
                download
                aria-label={`Download ${filename} as CSV`}
              >
                <Download className="h-3.5 w-3.5" />
                CSV
              </a>
            </Button>
            <Button asChild size="sm" className="h-8 font-mono text-xs rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white">
              <a
                href={api.downloadReport(essayId, 'pdf')}
                download
                aria-label={`Download ${filename} as PDF`}
              >
                <Download className="h-3.5 w-3.5" />
                PDF
              </a>
            </Button>
            <Button asChild variant="outline" size="sm" className="h-8 font-mono text-xs rounded-xl">
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
      </div>
    </div>
  );
}
