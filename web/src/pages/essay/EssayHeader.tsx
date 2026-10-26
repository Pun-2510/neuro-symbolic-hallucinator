import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, FileText, Quote, Clock, Download, ShieldCheck, Lock } from 'lucide-react';
import { api } from '@/api/client';
import { useRole } from '@/hooks/useRole';
import { UpgradeModal } from '@/components/UpgradeModal';
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
  const { isUser, isBasic } = useRole();
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [lockedFormat, setLockedFormat] = useState<string>('PDF');
  const lang = i18n.language?.startsWith('vi') ? 'vi' : 'en';

  const handleDownload = (
    e: React.MouseEvent<HTMLAnchorElement>,
    fmt: 'json' | 'csv' | 'pdf' | 'docx',
  ) => {
    e.preventDefault();
    if (isBasic && fmt !== 'json') {
      setLockedFormat(fmt.toUpperCase());
      setUpgradeOpen(true);
      return;
    }
    void api.downloadReportFile(essayId, fmt, filename);
  };

  return (
    <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 p-4 sm:p-6 shadow-xs overflow-hidden">
      <div className="flex flex-col sm:flex-row items-start justify-between gap-4 w-full min-w-0">
        <div className="w-full min-w-0 flex-1">
          <div className="flex items-center gap-3 flex-wrap mb-2.5">
            <Link
              to="/history"
              className="inline-flex items-center gap-1.5 text-xs font-mono font-semibold text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700 transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              {t('essay.backToReports').replace(/^←\s*/, '')}
            </Link>
            {!isUser && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200/70 dark:border-indigo-800/70 text-[11px] font-mono font-semibold text-indigo-700 dark:text-indigo-300">
                <ShieldCheck className="h-3.5 w-3.5" />
                {lang === 'vi' ? 'BÁO CÁO KIỂM CHỨNG HỌC THUẬT' : 'VERIFICATION REPORT IDE'}
              </span>
            )}
          </div>

          <h1
            className="font-display text-xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100 truncate tracking-tight max-w-full"
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
            {!isUser && (
              <span className="inline-flex items-center gap-1.5 font-mono text-xs text-slate-500 dark:text-slate-400">
                <Clock className="h-3.5 w-3.5 text-slate-400" />
                ID #{essayId}
              </span>
            )}
          </div>
        </div>

        {/* Export Actions */}
        <div className="flex flex-col items-start sm:items-end gap-1.5 shrink-0 w-full sm:w-auto">
          {!isUser && (
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 dark:text-slate-500">
              {lang === 'vi' ? 'Xuất Báo Cáo Chuẩn Hóa' : 'Export Audit Artifact'}
            </span>
          )}
          <div className="grid grid-cols-2 sm:flex gap-2 w-full sm:w-auto">
            {!isUser && (
              <>
                <Button asChild variant="outline" size="sm" className="h-8 font-mono text-xs rounded-xl w-full sm:w-auto">
                  <a
                    href={api.downloadReport(essayId, 'json')}
                    onClick={(e) => handleDownload(e, 'json')}
                    download
                    aria-label={`Download ${filename} as JSON`}
                  >
                    <Download className="h-3.5 w-3.5" />
                    JSON
                  </a>
                </Button>
                <Button asChild variant="outline" size="sm" className="h-8 font-mono text-xs rounded-xl w-full sm:w-auto">
                  <a
                    href={api.downloadReport(essayId, 'csv')}
                    onClick={(e) => handleDownload(e, 'csv')}
                    download
                    aria-label={`Download ${filename} as CSV`}
                  >
                    <Download className="h-3.5 w-3.5" />
                    CSV
                  </a>
                </Button>
              </>
            )}
            <Button asChild size="sm" className="h-8 font-mono text-xs rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white w-full sm:w-auto">
              <a
                href={api.downloadReport(essayId, 'pdf')}
                onClick={(e) => handleDownload(e, 'pdf')}
                download
                data-testid="export-pdf-btn"
                aria-label={`Download ${filename} as PDF`}
              >
                {isBasic ? <Lock className="h-3.5 w-3.5 text-amber-300" /> : <Download className="h-3.5 w-3.5" />}
                PDF
                {isBasic && (
                  <span className="ml-1 px-1 py-0.2 rounded bg-amber-400/20 text-amber-200 text-[9px] font-bold">
                    PRO
                  </span>
                )}
              </a>
            </Button>
            <Button asChild variant="outline" size="sm" className="h-8 font-mono text-xs rounded-xl w-full sm:w-auto">
              <a
                href={api.downloadReport(essayId, 'docx')}
                onClick={(e) => handleDownload(e, 'docx')}
                download
                data-testid="export-docx-btn"
                aria-label={`Download ${filename} as DOCX`}
              >
                {isBasic ? <Lock className="h-3.5 w-3.5 text-amber-500" /> : <Download className="h-3.5 w-3.5" />}
                DOCX
                {isBasic && (
                  <span className="ml-1 px-1 py-0.2 rounded bg-indigo-500/15 text-indigo-600 dark:text-indigo-300 text-[9px] font-bold">
                    PRO
                  </span>
                )}
              </a>
            </Button>
          </div>
        </div>
      </div>

      <UpgradeModal
        open={upgradeOpen}
        onOpenChange={setUpgradeOpen}
        featureName={`Export ${lockedFormat} Report`}
        reasonTitle={
          lang === 'vi'
            ? `Mở khóa xuất báo cáo học thuật định dạng ${lockedFormat}`
            : `Unlock Academic Report Export (${lockedFormat})`
        }
        reasonDescription={
          lang === 'vi'
            ? `Gói Basic chỉ hỗ trợ xem báo cáo trực tuyến. Nâng cấp lên gói Pro ($16/tháng khi trả năm) để tải xuống báo cáo ${lockedFormat}, Word (DOCX) và CSV đầy đủ.`
            : `The free Basic tier supports web viewing only. Upgrade to Pro ($16/mo billed annually) to export formatted ${lockedFormat}, Word (DOCX), and CSV reports.`
        }
      />
    </div>
  );
}
