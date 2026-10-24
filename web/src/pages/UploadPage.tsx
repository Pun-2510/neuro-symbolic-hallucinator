import { useCallback, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Upload,
  FileText,
  X,
  Loader2,
  AlertCircle,
  Quote,
  Database,
  GitBranch,
  Layers,
  CheckCircle2,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { api } from '../api/client';
import { useRole } from '@/hooks/useRole';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';

/* ============================================================
   SourceLogic — Upload Page Component (Scholarly Precision v2.0)
   Academic Source Verification Workspace
   ============================================================ */

const ACCEPTED_EXTENSIONS = ['.pdf'];
const ACCEPTED_MIME = { 'application/pdf': ['.pdf'] };

export function UploadPage() {
  const { t, i18n } = useTranslation();
  const { isUser, isTeacher, isAdmin } = useRole();
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const lang = i18n.language?.startsWith('vi') ? 'vi' : 'en';

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        const droppedFile = e.dataTransfer.files[0];
        const ext = droppedFile.name
          .substring(droppedFile.name.lastIndexOf('.'))
          .toLowerCase();
        if (!ACCEPTED_EXTENSIONS.includes(ext)) {
          setError(t('upload.onlyPdfSupported'));
          return;
        }
        setError(null);
        setFile(droppedFile);
      }
    },
    [t]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const picked = e.target.files[0];
      const ext = picked.name
        .substring(picked.name.lastIndexOf('.'))
        .toLowerCase();
      if (!ACCEPTED_EXTENSIONS.includes(ext)) {
        setError(t('upload.onlyPdfSupported'));
        return;
      }
      setError(null);
      setFile(picked);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const response = await api.uploadEssay(file);
      navigate(`/verification/processing/${response.essay_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('upload.uploadFailed'));
      setUploading(false);
    }
  };

  const pipelinePillars = [
    {
      step: '01',
      icon: Quote,
      title: t('auth.featureExtraction'),
      desc: t('auth.featureExtractionDesc'),
      tag: 'GROBID TEI-XML',
      tone: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
    },
    {
      step: '02',
      icon: Database,
      title: t('auth.featureRetrieval'),
      desc: t('auth.featureRetrievalDesc'),
      tag: '7 Scholarly DBs',
      tone: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20',
    },
    {
      step: '03',
      icon: GitBranch,
      title: t('auth.featureVerification'),
      desc: t('auth.featureVerificationDesc'),
      tag: 'Rules R01–R12 · CIS',
      tone: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
    },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-8">
      {/* Executive Header Banner */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 p-5 sm:p-6 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1.5">
          {!isUser && (
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200/70 dark:border-indigo-800/70 text-[11px] font-mono font-semibold text-indigo-700 dark:text-indigo-300">
                <Sparkles className="h-3 w-3" />
                {lang === 'vi'
                  ? 'KIỂM CHỨNG ĐƠN TÀI LIỆU · LAYER 1–2'
                  : 'SINGLE MANUSCRIPT VERIFICATION · LAYER 1–2'}
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700 text-[11px] font-mono text-slate-600 dark:text-slate-300">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                GROBID v0.8.0 ONLINE
              </span>
            </div>
          )}
          <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            {t('upload.title')}
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {t('upload.subtitle')}
          </p>
        </div>

        {(isTeacher || isAdmin) && (
          <Button
            asChild
            variant="outline"
            size="sm"
            className="h-10 rounded-xl font-medium shrink-0"
          >
            <Link to="/batch-upload">
              <Layers className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
              <span>{t('nav.batchCheck')}</span>
            </Link>
          </Button>
        )}
      </div>

      {/* Main IDE Dropzone Container */}
      <Card className="p-0 overflow-hidden rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
        {/* Top Window Chrome */}
        <div className="px-4 sm:px-6 py-3.5 bg-slate-50/80 dark:bg-slate-900/90 border-b border-slate-200/80 dark:border-slate-800 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-400/80 inline-block" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80 inline-block" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80 inline-block" />
            </div>
            <Separator orientation="vertical" className="h-4" />
            <span className="font-mono text-xs text-slate-600 dark:text-slate-300 font-medium">
              manuscript_ingest.pdf
            </span>
          </div>
          <Badge
            variant="outline"
            className="font-mono text-[11px] bg-white dark:bg-slate-950 text-slate-600 dark:text-slate-400"
          >
            {t('upload.maxSize')}
          </Badge>
        </div>

        <div className="p-4 sm:p-8">
          {/* Interactive Dropzone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`
              relative border-2 border-dashed rounded-2xl p-6 sm:p-12 text-center transition-all duration-200 cursor-pointer
              ${
                dragActive
                  ? 'border-indigo-500 bg-indigo-50/70 dark:bg-indigo-950/50 scale-[1.01] shadow-inner'
                  : file
                    ? 'border-emerald-500/80 bg-emerald-50/40 dark:bg-emerald-950/25'
                    : 'border-slate-300 dark:border-slate-700 hover:border-indigo-400 dark:hover:border-indigo-500 bg-slate-50/60 dark:bg-slate-950/60 hover:bg-indigo-50/30 dark:hover:bg-slate-900'
              }
            `}
          >
            <input
              type="file"
              accept={Object.values(ACCEPTED_MIME).flat().join(',')}
              onChange={handleChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />

            {file ? (
              /* File selected state */
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4 max-w-xl mx-auto bg-white dark:bg-slate-900 p-3.5 sm:p-4 rounded-2xl border border-emerald-200 dark:border-emerald-800/80 shadow-xs">
                <div className="flex items-center gap-3 min-w-0 w-full sm:w-auto">
                  <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-emerald-100 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center shrink-0">
                    <FileText className="h-5 w-5 sm:h-6 sm:w-6 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="text-left min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p
                        className="font-semibold text-sm sm:text-base text-slate-900 dark:text-white truncate max-w-[180px] sm:max-w-xs"
                        title={file.name}
                      >
                        {file.name}
                      </p>
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 shrink-0">
                        <CheckCircle2 className="h-3 w-3" /> READY
                      </span>
                    </div>
                    <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-0.5 truncate">
                      {(file.size / 1024 / 1024).toFixed(2)} MB · application/pdf{!isUser ? ' · GROBID TEI' : ''}
                    </p>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                    setError(null);
                  }}
                  aria-label="Remove file"
                  className="relative z-10 shrink-0 p-2 rounded-xl text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/50 transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            ) : (
              /* Dropzone default state */
              <div className="max-w-md mx-auto">
                <div className="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200/70 dark:border-indigo-800/70 flex items-center justify-center mx-auto mb-4 shadow-xs">
                  <Upload className="h-7 w-7 text-indigo-600 dark:text-indigo-400" />
                </div>
                <p className="font-display text-lg sm:text-xl font-bold text-slate-900 dark:text-white mb-1.5">
                  {t('upload.dropDocument')}
                </p>
                <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mb-4">
                  {t('upload.pdfOnly')} · APA, IEEE, MLA, Chicago, Harvard
                </p>
                <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-xs font-semibold text-indigo-600 dark:text-indigo-400 shadow-2xs">
                  {t('upload.orBrowse')}
                </span>
              </div>
            )}
          </div>

          {/* Error message */}
          {error && (
            <Alert variant="destructive" className="mt-4 rounded-xl">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Action Bar */}
          <div className="mt-6 pt-5 border-t border-slate-200/80 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
              {!isUser &&
                (lang === 'vi'
                  ? 'Pipeline: Bóc tách PDF → 7 CSDL Học thuật → Suy diễn Luật R01–R12'
                  : 'Pipeline: PDF Extraction → 7 Scholarly Indexes → Symbolic Rules R01–R12')}
            </div>

            <Button
              size="lg"
              onClick={handleUpload}
              disabled={!file || uploading}
              className="w-full sm:w-auto h-11 px-7 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-md shadow-indigo-600/20 disabled:opacity-50 btn-shimmer"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{t('upload.uploading')}</span>
                </>
              ) : (
                <>
                  <span>{t('upload.startVerification')}</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </div>
        </div>
      </Card>

      {/* 3-Step Verification Pipeline Architecture Strip (Teacher / Admin only) */}
      {!isUser && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {pipelinePillars.map((pillar) => {
            const Icon = pillar.icon;
            return (
              <Card
                key={pillar.step}
                className="p-4 rounded-2xl bg-white/90 dark:bg-slate-900/90 border border-slate-200/80 dark:border-slate-800 shadow-2xs flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className={`p-2 rounded-xl border ${pillar.tone}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      STEP {pillar.step} · {pillar.tag}
                    </span>
                  </div>
                  <h3 className="font-display font-bold text-sm text-slate-900 dark:text-white">
                    {pillar.title}
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 leading-relaxed">
                    {pillar.desc}
                  </p>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
