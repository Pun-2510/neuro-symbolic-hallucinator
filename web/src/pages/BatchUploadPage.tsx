import { useCallback, useState, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import {
  Upload,
  FileText,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  RefreshCw,
  ExternalLink,
  Trash2,
} from 'lucide-react';
import { api } from '../api/client';
import { useRole } from '@/hooks/useRole';
import type { Class } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Select } from '@/components/ui/select';
import { Label } from '@/components/ui/label';

/* ============================================================
   Batch Upload Page (shadcn/ui v2.0)
   Upload multiple PDFs for concurrent analysis
   ============================================================ */

const ACCEPTED_EXTENSIONS = ['.pdf'];

type FileStatus = 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';

interface BatchFileItem {
  id: string;
  file: File;
  status: FileStatus;
  progress: number;
  essayId?: number;
  error?: string;
}

interface QueueState {
  isProcessing: boolean;
  currentIndex: number;
  hasAutoNavigated: boolean;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1024 / 1024).toFixed(2) + ' MB';
}

function getStatusIcon(status: FileStatus) {
  switch (status) {
    case 'pending':
      return <Clock className="h-4 w-4 text-slate-400" />;
    case 'uploading':
    case 'processing':
      return <Loader2 className="h-4 w-4 text-indigo-500 animate-spin" />;
    case 'completed':
      return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
    case 'failed':
      return <AlertCircle className="h-4 w-4 text-red-500" />;
  }
}

function getStatusVariant(status: FileStatus): 'muted' | 'default' | 'verified' | 'destructive' {
  switch (status) {
    case 'pending':
      return 'muted';
    case 'uploading':
    case 'processing':
      return 'default';
    case 'completed':
      return 'verified';
    case 'failed':
      return 'destructive';
  }
}

function getStatusText(status: FileStatus, progress: number, t: TFunction): string {
  switch (status) {
    case 'pending':
      return t('batchUpload.pending');
    case 'uploading':
      return t('batchUpload.uploading');
    case 'processing':
      return progress > 0
        ? `${t('batchUpload.processing')} ${progress}%`
        : `${t('batchUpload.processing')}...`;
    case 'completed':
      return t('batchUpload.complete');
    case 'failed':
      return t('batchUpload.failed');
  }
}

export function BatchUploadPage() {
  const { t } = useTranslation();
  const { isTeacher, isAdmin } = useRole();
  const [classes, setClasses] = useState<Class[]>([]);
  const [targetClassId, setTargetClassId] = useState<number | null>(null);

  useEffect(() => {
    if (isTeacher || isAdmin) {
      api
        .listMyClasses()
        .then(setClasses)
        .catch(() => setClasses([]));
    }
  }, [isTeacher, isAdmin]);

  const [files, setFiles] = useState<BatchFileItem[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [queueState, setQueueState] = useState<QueueState>({
    isProcessing: false,
    currentIndex: -1,
    hasAutoNavigated: false,
  });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const navigate = useNavigate();

  const stats = useMemo(
    () => ({
      pending: files.filter((f) => f.status === 'pending').length,
      processing: files.filter(
        (f) => f.status === 'uploading' || f.status === 'processing'
      ).length,
      completed: files.filter((f) => f.status === 'completed').length,
      failed: files.filter((f) => f.status === 'failed').length,
    }),
    [files]
  );

  useEffect(() => {
    if (queueState.hasAutoNavigated) return;
    if (queueState.isProcessing) return;
    if (files.length === 0) return;
    if (stats.processing > 0 || stats.pending > 0) return;

    const firstCompleted = files.find(
      (f) => f.status === 'completed' && f.essayId
    );
    if (!firstCompleted || !firstCompleted.essayId) return;

    setQueueState((prev) =>
      prev.hasAutoNavigated ? prev : { ...prev, hasAutoNavigated: true }
    );

    if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current);
    navigateTimerRef.current = setTimeout(() => {
      navigate(`/verification/report/${firstCompleted.essayId}`);
    }, 600);
  }, [
    stats,
    queueState.isProcessing,
    queueState.hasAutoNavigated,
    files,
    navigate,
  ]);

  useEffect(() => {
    return () => {
      if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current);
    };
  }, []);

  useEffect(() => {
    const processingFiles = files.filter(
      (f) => f.status === 'uploading' || f.status === 'processing'
    );
    if (processingFiles.length === 0) return;

    const pollInterval = setInterval(async () => {
      const updated = await Promise.all(
        processingFiles.map(async (fileItem) => {
          if (!fileItem.essayId) return fileItem;
          try {
            const status = await api.getEssayStatus(fileItem.essayId);
            if (status.status === 'completed') {
              return {
                ...fileItem,
                status: 'completed' as FileStatus,
                progress: 100,
              };
            } else if (status.status === 'failed') {
              return {
                ...fileItem,
                status: 'failed' as FileStatus,
                error: status.error || 'Processing failed',
              };
            } else {
              const progress = Math.round(
                (status.step_index / status.total_steps) * 100
              );
              return {
                ...fileItem,
                status: 'processing' as FileStatus,
                progress,
              };
            }
          } catch {
            return fileItem;
          }
        })
      );

      setFiles((prev) =>
        prev.map((f) => {
          const updatedFile = updated.find((u) => u.id === f.id);
          return updatedFile || f;
        })
      );
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [files]);

  const processQueue = useCallback(async () => {
    const pendingFiles = files.filter((f) => f.status === 'pending');
    if (pendingFiles.length === 0) {
      setQueueState({
        isProcessing: false,
        currentIndex: -1,
        hasAutoNavigated: false,
      });
      return;
    }

    setQueueState({
      isProcessing: true,
      currentIndex: 0,
      hasAutoNavigated: false,
    });

    for (let i = 0; i < pendingFiles.length; i++) {
      const fileItem = pendingFiles[i];

      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileItem.id ? { ...f, status: 'uploading' as FileStatus } : f
        )
      );

      try {
        const response = await api.uploadEssay(fileItem.file);

        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileItem.id
              ? {
                  ...f,
                  status: 'processing' as FileStatus,
                  essayId: response.essay_id,
                  progress: 0,
                }
              : f
          )
        );

        let attempts = 0;
        const maxAttempts = 150;
        while (attempts < maxAttempts) {
          await new Promise((resolve) => setTimeout(resolve, 2000));
          attempts++;

          try {
            const status = await api.getEssayStatus(response.essay_id);
            if (status.status === 'completed') {
              setFiles((prev) =>
                prev.map((f) =>
                  f.id === fileItem.id
                    ? { ...f, status: 'completed' as FileStatus, progress: 100 }
                    : f
                )
              );
              break;
            } else if (status.status === 'failed') {
              setFiles((prev) =>
                prev.map((f) =>
                  f.id === fileItem.id
                    ? {
                        ...f,
                        status: 'failed' as FileStatus,
                        error: status.error || 'Processing failed',
                      }
                    : f
                )
              );
              break;
            }
          } catch {
            // Continue polling
          }
        }

        if (attempts >= maxAttempts) {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === fileItem.id
                ? {
                    ...f,
                    status: 'failed' as FileStatus,
                    error: 'Processing timeout',
                  }
                : f
            )
          );
        }
      } catch (error) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileItem.id
              ? {
                  ...f,
                  status: 'failed' as FileStatus,
                  error:
                    error instanceof Error ? error.message : 'Upload failed',
                }
              : f
          )
        );
      }
    }

    setQueueState({
      isProcessing: false,
      currentIndex: -1,
      hasAutoNavigated: false,
    });
  }, [files]);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const droppedFiles = Array.from(e.dataTransfer.files).filter((file) => {
      const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      return ACCEPTED_EXTENSIONS.includes(ext);
    });

    addFiles(droppedFiles);
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      addFiles(selectedFiles);
    }
  };

  const addFiles = (newFiles: File[]) => {
    const batchFiles: BatchFileItem[] = newFiles.map((file) => ({
      id: crypto.randomUUID(),
      file,
      status: 'pending',
      progress: 0,
    }));
    setFiles((prev) => [...prev, ...batchFiles]);
    if (navigateTimerRef.current) {
      clearTimeout(navigateTimerRef.current);
      navigateTimerRef.current = null;
    }
    setQueueState((prev) => ({ ...prev, hasAutoNavigated: false }));
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const clearAll = () => {
    setFiles([]);
    if (navigateTimerRef.current) {
      clearTimeout(navigateTimerRef.current);
      navigateTimerRef.current = null;
    }
    setQueueState({
      isProcessing: false,
      currentIndex: -1,
      hasAutoNavigated: false,
    });
  };

  const retryFile = (id: string) => {
    setFiles((prev) =>
      prev.map((f) =>
        f.id === id
          ? { ...f, status: 'pending', progress: 0, error: undefined }
          : f
      )
    );
    if (navigateTimerRef.current) {
      clearTimeout(navigateTimerRef.current);
      navigateTimerRef.current = null;
    }
    setQueueState((prev) => ({ ...prev, hasAutoNavigated: false }));
  };

  const handleStartVerification = () => {
    if (files.length === 0 || queueState.isProcessing) return;
    if (navigateTimerRef.current) {
      clearTimeout(navigateTimerRef.current);
      navigateTimerRef.current = null;
    }
    setQueueState((prev) => ({ ...prev, hasAutoNavigated: false }));
    processQueue();
  };

  const pendingCount = stats.pending;

  return (
    <div className="max-w-4xl mx-auto min-h-[calc(100vh-12rem)] flex flex-col py-8">
      {/* Header */}
      <div className="mb-8 text-center">
        <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-white mb-2">
          {t('batchUpload.title')}
        </h1>
        <p className="text-slate-600 dark:text-slate-400">
          {t('batchUpload.subtitle')}
        </p>
      </div>

      {/* Class selector (teacher/admin only) */}
      {(isTeacher || isAdmin) && classes.length > 0 && (
        <div className="mb-6 max-w-md mx-auto w-full space-y-1.5">
          <Label htmlFor="batch-class-select">
            {t('batchUpload.assignToClass')}
          </Label>
          <Select
            id="batch-class-select"
            value={targetClassId ?? ''}
            onChange={(e) =>
              setTargetClassId(e.target.value ? Number(e.target.value) : null)
            }
            wrapperClassName="w-full"
          >
            <option value="">{t('batchUpload.noClassAssigned')}</option>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t('batchUpload.assignToClassHint')}
          </p>
        </div>
      )}

      {/* Dropzone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-200 cursor-pointer
          ${
            dragActive
              ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/50 scale-[1.02]'
              : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 hover:border-indigo-400 dark:hover:border-indigo-500 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          onChange={handleFileInput}
          className="hidden"
        />

        <div className="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-indigo-950 flex items-center justify-center mx-auto mb-4">
          <Upload className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
        </div>
        <p className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
          {t('batchUpload.dropPdfs')}
        </p>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {t('batchUpload.orClickBrowse')}
        </p>
        <span className="text-sm text-indigo-600 dark:text-indigo-400 font-medium mt-4 block">
          {t('batchUpload.pdfOnly')}
        </span>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="mt-8 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              {t('batchUpload.files')} ({files.length})
            </h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAll}
              disabled={queueState.isProcessing}
              className="text-red-600 dark:text-red-400 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/40"
            >
              {t('batchUpload.clearAll')}
            </Button>
          </div>

          <div className="space-y-2">
            {files.map((fileItem) => (
              <Card
                key={fileItem.id}
                className="flex items-center gap-4 px-4 py-3"
              >
                <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-950 flex items-center justify-center shrink-0">
                  <FileText className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                </div>

                <div className="flex-1 min-w-0">
                  <p
                    className="font-medium text-slate-900 dark:text-white truncate"
                    title={fileItem.file.name}
                  >
                    {fileItem.file.name}
                  </p>
                  <p className="text-xs font-mono text-slate-500 dark:text-slate-400">
                    {formatBytes(fileItem.file.size)}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {getStatusIcon(fileItem.status)}
                  <Badge variant={getStatusVariant(fileItem.status)}>
                    {getStatusText(fileItem.status, fileItem.progress, t)}
                  </Badge>
                </div>

                {(fileItem.status === 'processing' ||
                  fileItem.status === 'uploading') && (
                  <div className="w-24">
                    <Progress value={fileItem.progress} />
                  </div>
                )}

                <div className="flex items-center gap-1">
                  {fileItem.status === 'completed' && fileItem.essayId && (
                    <button
                      onClick={() =>
                        navigate(`/verification/report/${fileItem.essayId}`)
                      }
                      className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                      title={t('dashboard.viewReport')}
                    >
                      <ExternalLink className="h-4 w-4 text-slate-500 dark:text-slate-400" />
                    </button>
                  )}
                  {fileItem.status === 'failed' && (
                    <button
                      onClick={() => retryFile(fileItem.id)}
                      disabled={queueState.isProcessing}
                      className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
                      title={t('common.retry')}
                    >
                      <RefreshCw className="h-4 w-4 text-slate-500 dark:text-slate-400" />
                    </button>
                  )}
                  {!queueState.isProcessing && (
                    <button
                      onClick={() => removeFile(fileItem.id)}
                      className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      title={t('common.delete')}
                    >
                      <Trash2 className="h-4 w-4 text-slate-500 dark:text-slate-400 hover:text-red-500" />
                    </button>
                  )}
                </div>
              </Card>
            ))}
          </div>

          {files
            .filter((f) => f.error)
            .map((f) => (
              <div
                key={f.id}
                className="text-sm text-red-600 dark:text-red-400 pl-4"
              >
                {f.file.name}: {f.error}
              </div>
            ))}
        </div>
      )}

      {/* Summary Stats */}
      {files.length > 0 && (
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card className="bg-slate-100/80 dark:bg-slate-800/80 p-4 text-center">
            <p className="text-2xl font-bold font-mono tabular-nums text-slate-600 dark:text-slate-300">
              {stats.pending}
            </p>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {t('batchUpload.pending')}
            </p>
          </Card>
          <Card className="bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800 p-4 text-center">
            <p className="text-2xl font-bold font-mono tabular-nums text-blue-600 dark:text-blue-300">
              {stats.processing}
            </p>
            <p className="text-sm text-blue-600 dark:text-blue-400">
              {t('batchUpload.processing')}
            </p>
          </Card>
          <Card className="bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 p-4 text-center">
            <p className="text-2xl font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-300">
              {stats.completed}
            </p>
            <p className="text-sm text-emerald-600 dark:text-emerald-400">
              {t('batchUpload.completed')}
            </p>
          </Card>
          <Card className="bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800 p-4 text-center">
            <p className="text-2xl font-bold font-mono tabular-nums text-red-600 dark:text-red-300">
              {stats.failed}
            </p>
            <p className="text-sm text-red-600 dark:text-red-400">
              {t('batchUpload.failed')}
            </p>
          </Card>
        </div>
      )}

      {/* Start Button */}
      <div className="mt-8 flex flex-col items-center gap-3">
        <Button
          size="lg"
          onClick={handleStartVerification}
          disabled={pendingCount === 0 || queueState.isProcessing}
          className="px-8 py-3 h-auto"
        >
          {queueState.isProcessing ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              {t('batchUpload.processing')}...
            </>
          ) : (
            <>
              {t('batchUpload.startVerification')}
              <Upload className="h-5 w-5" />
            </>
          )}
        </Button>

        {!queueState.isProcessing &&
          files.length > 0 &&
          stats.pending === 0 &&
          stats.processing === 0 && (
            <>
              {stats.completed > 0 ? (
                <p className="text-sm text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('batchUpload.allProcessedOpening')}
                </p>
              ) : (
                <p className="text-sm text-red-600 dark:text-red-400">
                  {t('batchUpload.allFailedNotice')}
                </p>
              )}
            </>
          )}
      </div>

      {/* Disclaimer */}
      <div className="mt-12 text-center">
        <p className="text-xs text-slate-400 dark:text-slate-500">
          {t('batchUpload.disclaimer')}
        </p>
      </div>
    </div>
  );
}
