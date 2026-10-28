import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  api,
  type RemediatedBibliographyResponse,
} from '@/api/client';
import {
  Sparkles,
  Copy,
  Check,
  Download,
  X,
  Loader2,
  BookOpen,
  ArrowRight,
  FileCode2,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface BibliographyRemediationModalProps {
  open: boolean;
  essayId: number;
  filename: string;
  lang: 'vi' | 'en';
  onClose: () => void;
}

type StyleOption = 'apa' | 'ieee' | 'tdtu' | 'bibtex' | 'ris';

const STYLE_LABELS: { id: StyleOption; label: string; ext: string }[] = [
  { id: 'apa', label: 'APA 7th Edition', ext: 'txt' },
  { id: 'ieee', label: 'IEEE Numeric', ext: 'txt' },
  { id: 'tdtu', label: 'Harvard / TDTU', ext: 'txt' },
  { id: 'bibtex', label: 'BibTeX (.bib)', ext: 'bib' },
  { id: 'ris', label: 'RIS (.ris)', ext: 'ris' },
];

export function BibliographyRemediationModal({
  open,
  essayId,
  filename,
  lang,
  onClose,
}: BibliographyRemediationModalProps) {
  const [selectedStyle, setSelectedStyle] = useState<StyleOption>('apa');
  const [data, setData] = useState<RemediatedBibliographyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [onlyModified, setOnlyModified] = useState(false);

  useEffect(() => {
    if (!open || !essayId) return;
    let active = true;
    setLoading(true);
    setError(null);
    api
      .getRemediatedBibliography(essayId, selectedStyle)
      .then((res) => {
        if (active) setData(res);
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to load remediated bibliography');
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [open, essayId, selectedStyle]);

  if (!open) return null;

  const handleCopy = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    } catch {
      // ignore clipboard errors
    }
  };

  const handleDownloadFile = (content: string, ext: string, suffix: string) => {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    const cleanBase = (filename || `essay_${essayId}`).replace(/\.[^/.]+$/, '');
    a.href = url;
    a.download = `${cleanBase}_${suffix}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  const visibleEntries = data
    ? onlyModified
      ? data.entries.filter((e) => e.was_modified)
      : data.entries
    : [];

  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/65 backdrop-blur-xs p-3 sm:p-4"
      onClick={onClose}
      data-testid="bibliography-remediation-modal"
    >
      <div
        className="w-full max-w-5xl max-h-[90dvh] flex flex-col rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-indigo-950 via-slate-900 to-violet-950 text-white flex flex-wrap items-center justify-between gap-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-indigo-500/20 border border-indigo-400/30 flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-indigo-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base sm:text-lg font-display font-bold tracking-tight">
                  {lang === 'vi'
                    ? '1-Click Chuẩn hóa & Sửa lỗi Danh mục Tài liệu Tham khảo'
                    : '1-Click Bibliography Auto-Remediation & Export Studio'}
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-500/30 border border-indigo-400/40 text-indigo-200">
                  PRO STUDIO
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-0.5">
                {lang === 'vi'
                  ? 'Tự động đối chiếu & khôi phục Năm xuất bản, Tiêu đề, Tác giả, Tạp chí và DOI chuẩn xác từ 9 CSDL học thuật.'
                  : 'Automatically repairs mismatched Year, Title, Authors, Venue & DOI using canonical records from 9 scholarly databases.'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Close studio"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Toolbar: Style Selector + Bulk Export Actions */}
        <div className="px-6 py-3.5 bg-slate-50 dark:bg-slate-900/90 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Target citation style">
            {STYLE_LABELS.map((st) => (
              <button
                key={st.id}
                type="button"
                data-testid={`remediate-style-${st.id}`}
                onClick={() => setSelectedStyle(st.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all ${
                  selectedStyle === st.id
                    ? 'bg-indigo-600 text-white shadow-2xs'
                    : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:border-indigo-400'
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {data && (
              <>
                <button
                  type="button"
                  onClick={() => setOnlyModified((v) => !v)}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-mono font-medium border transition-colors ${
                    onlyModified
                      ? 'bg-amber-50 dark:bg-amber-950/60 border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-300'
                      : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300'
                  }`}
                >
                  {lang === 'vi'
                    ? `Đã tự động sửa (${data.remediated_count}/${data.total_entries})`
                    : `Auto-Repaired (${data.remediated_count}/${data.total_entries})`}
                </button>

                <button
                  type="button"
                  data-testid="copy-all-remediated-btn"
                  onClick={() => handleCopy(data.combined_text, 'all')}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 hover:border-indigo-400 transition-colors"
                >
                  {copiedKey === 'all' ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-500" />
                      <span>{lang === 'vi' ? 'Đã sao chép!' : 'Copied All!'}</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
                      <span>{lang === 'vi' ? 'Sao chép toàn bộ' : 'Copy All'}</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  data-testid="download-bibtex-btn"
                  onClick={() => handleDownloadFile(data.combined_bibtex, 'bib', 'references')}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-2xs transition-colors"
                >
                  <Download className="h-3.5 w-3.5" />
                  <span>.BIB</span>
                </button>

                <button
                  type="button"
                  data-testid="download-ris-btn"
                  onClick={() => handleDownloadFile(data.combined_ris, 'ris', 'references')}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-violet-600 hover:bg-violet-700 text-white shadow-2xs transition-colors"
                >
                  <FileCode2 className="h-3.5 w-3.5" />
                  <span>.RIS</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50/50 dark:bg-slate-950/60">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-indigo-600 dark:text-indigo-400" />
              <p className="text-xs font-mono text-slate-500 dark:text-slate-400">
                {lang === 'vi'
                  ? 'Đang tổng hợp metadata chuẩn và định dạng lại danh mục tài liệu tham khảo...'
                  : 'Synthesizing canonical scholarly metadata & formatting bibliography...'}
              </p>
            </div>
          ) : error ? (
            <div className="p-6 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
              {error}
            </div>
          ) : visibleEntries.length === 0 ? (
            <div className="p-12 text-center text-sm text-slate-500 dark:text-slate-400">
              {lang === 'vi'
                ? 'Không có mục tài liệu tham khảo nào cần sửa đổi trong bộ lọc hiện tại.'
                : 'No bibliography entries match the current filter.'}
            </div>
          ) : (
            visibleEntries.map((entry) => (
              <div
                key={entry.verdict_id}
                className="rounded-xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 p-4 shadow-2xs space-y-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-xs font-bold text-slate-700 dark:text-slate-300">
                      #{entry.index}
                    </span>
                    {entry.was_modified ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold bg-amber-50 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                        <AlertTriangle className="h-3 w-3" />
                        {lang === 'vi' ? 'Đã tự động sửa lỗi Metadata' : 'Metadata Auto-Repaired'}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                        <CheckCircle2 className="h-3 w-3" />
                        {lang === 'vi' ? 'Chuẩn xác & Đã chuẩn hóa' : 'Verified & Standardized'}
                      </span>
                    )}
                    {entry.diff_fields.map((field) => (
                      <Badge
                        key={field}
                        variant="outline"
                        className="text-[10px] font-mono uppercase bg-indigo-50/70 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800"
                      >
                        +{field}
                      </Badge>
                    ))}
                    {entry.source_used && (
                      <span className="text-[11px] font-mono text-slate-400">
                        via {entry.source_used}
                      </span>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={() => handleCopy(entry.remediated_text, entry.verdict_id)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-mono text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  >
                    {copiedKey === entry.verdict_id ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-500" />
                        <span>{lang === 'vi' ? 'Đã chép' : 'Copied'}</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        <span>{lang === 'vi' ? 'Sao chép' : 'Copy'}</span>
                      </>
                    )}
                  </button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-11 gap-3 items-stretch">
                  {/* Original Raw Text */}
                  <div className="lg:col-span-5 rounded-lg p-3 bg-slate-50 dark:bg-slate-950/70 border border-slate-200/70 dark:border-slate-800">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-1">
                      {lang === 'vi' ? 'Bản gốc trong bài nộp (Before)' : 'Original in Manuscript (Before)'}
                    </div>
                    <p className="text-xs font-serif text-slate-600 dark:text-slate-400 break-words leading-relaxed">
                      {entry.original_raw}
                    </p>
                  </div>

                  <div className="hidden lg:flex lg:col-span-1 items-center justify-center text-indigo-500">
                    <ArrowRight className="h-4 w-4" />
                  </div>

                  {/* Remediated Canonical Output */}
                  <div className="lg:col-span-5 rounded-lg p-3 bg-indigo-50/50 dark:bg-indigo-950/30 border border-indigo-200/80 dark:border-indigo-800/80">
                    <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-1">
                      <span>
                        {lang === 'vi'
                          ? `Bản chuẩn hóa (${selectedStyle.toUpperCase()})`
                          : `Canonical Output (${selectedStyle.toUpperCase()})`}
                      </span>
                      <BookOpen className="h-3 w-3" />
                    </div>
                    <pre className="text-xs font-mono whitespace-pre-wrap break-words text-slate-900 dark:text-slate-100 leading-relaxed">
                      {entry.remediated_text}
                    </pre>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
