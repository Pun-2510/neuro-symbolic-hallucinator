import { useCallback, useState, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, X, Loader2, CheckCircle2, AlertCircle, Clock, RefreshCw, ExternalLink, Trash2 } from 'lucide-react';
import { api } from '../api/client';

/* ============================================================
   Batch Upload Page — v1.0
   Upload multiple PDFs for concurrent analysis
   Sequential processing, frontend-driven
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

// Sequential queue state
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
      return <Clock className="h-5 w-5 text-slate-400" />;
    case 'uploading':
    case 'processing':
      return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
    case 'completed':
      return <CheckCircle2 className="h-5 w-5 text-emerald-500" />;
    case 'failed':
      return <AlertCircle className="h-5 w-5 text-red-500" />;
  }
}

function getStatusColor(status: FileStatus): string {
  switch (status) {
    case 'pending':
      return 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400';
    case 'uploading':
    case 'processing':
      return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300';
    case 'completed':
      return 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300';
    case 'failed':
      return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300';
  }
}

function getStatusText(status: FileStatus, progress: number): string {
  switch (status) {
    case 'pending':
      return 'Pending';
    case 'uploading':
      return 'Uploading...';
    case 'processing':
      return progress > 0 ? `Processing ${progress}%` : 'Processing...';
    case 'completed':
      return 'Complete';
    case 'failed':
      return 'Failed';
  }
}

export function BatchUploadPage() {
  const [files, setFiles] = useState<BatchFileItem[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [queueState, setQueueState] = useState<QueueState>({ isProcessing: false, currentIndex: -1, hasAutoNavigated: false });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const navigate = useNavigate();

  // Calculate summary stats
  const stats = useMemo(() => ({
    pending: files.filter(f => f.status === 'pending').length,
    processing: files.filter(f => f.status === 'uploading' || f.status === 'processing').length,
    completed: files.filter(f => f.status === 'completed').length,
    failed: files.filter(f => f.status === 'failed').length,
  }), [files]);

  // Auto-navigate to report when batch finishes (only if at least one succeeded)
  useEffect(() => {
    if (queueState.hasAutoNavigated) return;
    if (queueState.isProcessing) return;
    if (files.length === 0) return;
    if (stats.processing > 0 || stats.pending > 0) return;

    const firstCompleted = files.find(f => f.status === 'completed' && f.essayId);
    if (!firstCompleted || !firstCompleted.essayId) return;

    // Mark before scheduling so re-renders don't reschedule/clear the timer
    setQueueState(prev => (prev.hasAutoNavigated ? prev : { ...prev, hasAutoNavigated: true }));

    if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current);
    navigateTimerRef.current = setTimeout(() => {
      navigate(`/verification/report/${firstCompleted.essayId}`);
    }, 600);
  }, [stats, queueState.isProcessing, queueState.hasAutoNavigated, files, navigate]);

  // Cleanup pending navigate timer on unmount
  useEffect(() => {
    return () => {
      if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current);
    };
  }, []);

  // Poll for status updates of processing files
  useEffect(() => {
    const processingFiles = files.filter(f => f.status === 'uploading' || f.status === 'processing');
    if (processingFiles.length === 0) return;

    const pollInterval = setInterval(async () => {
      const updated = await Promise.all(
        processingFiles.map(async (fileItem) => {
          if (!fileItem.essayId) return fileItem;
          try {
            const status = await api.getEssayStatus(fileItem.essayId);
            if (status.status === 'completed') {
              return { ...fileItem, status: 'completed' as FileStatus, progress: 100 };
            } else if (status.status === 'failed') {
              return { ...fileItem, status: 'failed' as FileStatus, error: status.error || 'Processing failed' };
            } else {
              // Calculate progress from step_index
              const progress = Math.round((status.step_index / status.total_steps) * 100);
              return { ...fileItem, status: 'processing' as FileStatus, progress };
            }
          } catch {
            return fileItem;
          }
        })
      );

      setFiles(prev => prev.map(f => {
        const updatedFile = updated.find(u => u.id === f.id);
        return updatedFile || f;
      }));
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [files]);

  // Process queue sequentially
  const processQueue = useCallback(async () => {
    const pendingFiles = files.filter(f => f.status === 'pending');
    if (pendingFiles.length === 0) {
      setQueueState({ isProcessing: false, currentIndex: -1, hasAutoNavigated: false });
      return;
    }

    setQueueState({ isProcessing: true, currentIndex: 0, hasAutoNavigated: false });

    for (let i = 0; i < pendingFiles.length; i++) {
      const fileItem = pendingFiles[i];

      // Update status to uploading
      setFiles(prev => prev.map(f =>
        f.id === fileItem.id ? { ...f, status: 'uploading' as FileStatus } : f
      ));

      try {
        const response = await api.uploadEssay(fileItem.file);

        // Update with essay ID and change to processing
        setFiles(prev => prev.map(f =>
          f.id === fileItem.id
            ? { ...f, status: 'processing' as FileStatus, essayId: response.essay_id, progress: 0 }
            : f
        ));

        // Wait for processing to complete
        let attempts = 0;
        const maxAttempts = 150; // 5 minutes at 2s interval
        while (attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, 2000));
          attempts++;

          try {
            const status = await api.getEssayStatus(response.essay_id);
            if (status.status === 'completed') {
              setFiles(prev => prev.map(f =>
                f.id === fileItem.id ? { ...f, status: 'completed' as FileStatus, progress: 100 } : f
              ));
              break;
            } else if (status.status === 'failed') {
              setFiles(prev => prev.map(f =>
                f.id === fileItem.id
                  ? { ...f, status: 'failed' as FileStatus, error: status.error || 'Processing failed' }
                  : f
              ));
              break;
            }
          } catch {
            // Continue polling
          }
        }

        if (attempts >= maxAttempts) {
          setFiles(prev => prev.map(f =>
            f.id === fileItem.id
              ? { ...f, status: 'failed' as FileStatus, error: 'Processing timeout' }
              : f
          ));
        }
      } catch (error) {
        setFiles(prev => prev.map(f =>
          f.id === fileItem.id
            ? { ...f, status: 'failed' as FileStatus, error: error instanceof Error ? error.message : 'Upload failed' }
            : f
        ));
      }
    }

    setQueueState({ isProcessing: false, currentIndex: -1, hasAutoNavigated: false });
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

    const droppedFiles = Array.from(e.dataTransfer.files).filter(file => {
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
    const batchFiles: BatchFileItem[] = newFiles.map(file => ({
      id: crypto.randomUUID(),
      file,
      status: 'pending',
      progress: 0,
    }));
    setFiles(prev => [...prev, ...batchFiles]);
    if (navigateTimerRef.current) {
      clearTimeout(navigateTimerRef.current);
      navigateTimerRef.current = null;
    }
    setQueueState(prev => ({ ...prev, hasAutoNavigated: false }));
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const clearAll = () => {
    setFiles([]);
    if (navigateTimerRef.current) {
      clearTimeout(navigateTimerRef.current);
      navigateTimerRef.current = null;
    }
    setQueueState({ isProcessing: false, currentIndex: -1, hasAutoNavigated: false });
  };

  const retryFile = (id: string) => {
    setFiles(prev => prev.map(f =>
      f.id === id ? { ...f, status: 'pending', progress: 0, error: undefined } : f
    ));
    if (navigateTimerRef.current) {
      clearTimeout(navigateTimerRef.current);
      navigateTimerRef.current = null;
    }
    setQueueState(prev => ({ ...prev, hasAutoNavigated: false }));
  };

  const handleStartVerification = () => {
    if (files.length === 0 || queueState.isProcessing) return;
    if (navigateTimerRef.current) {
      clearTimeout(navigateTimerRef.current);
      navigateTimerRef.current = null;
    }
    setQueueState(prev => ({ ...prev, hasAutoNavigated: false }));
    processQueue();
  };

  const pendingCount = stats.pending;

  return (
    <div className="max-w-4xl mx-auto min-h-[calc(100vh-12rem)] flex flex-col py-8">
      {/* Header */}
      <div className="mb-8 text-center">
        <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-white mb-2">
          Batch Verification
        </h1>
        <p className="text-slate-600 dark:text-slate-400">
          Upload multiple PDFs for concurrent citation analysis
        </p>
      </div>

      {/* Dropzone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-200 cursor-pointer
          ${dragActive
            ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/50 scale-[1.02]'
            : files.length > 0
              ? 'border-slate-300 dark:border-slate-600'
              : 'border-slate-300 dark:border-slate-600 hover:border-indigo-400 dark:hover:border-indigo-500 hover:bg-slate-50 dark:hover:bg-slate-800/50'
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
          Drop PDF files here
        </p>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          or click to browse
        </p>
        <span className="text-sm text-indigo-600 dark:text-indigo-400 font-medium mt-4 block">
          PDF only
        </span>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="mt-8 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Files ({files.length})
            </h2>
            <button
              onClick={clearAll}
              disabled={queueState.isProcessing}
              className="text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 disabled:opacity-50"
            >
              Clear All
            </button>
          </div>

          <div className="space-y-2">
            {files.map((fileItem) => (
              <div
                key={fileItem.id}
                className="flex items-center gap-4 px-4 py-3 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700"
              >
                {/* File icon */}
                <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center shrink-0">
                  <FileText className="h-5 w-5 text-slate-500 dark:text-slate-400" />
                </div>

                {/* File info */}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900 dark:text-white truncate" title={fileItem.file.name}>
                    {fileItem.file.name}
                  </p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {formatBytes(fileItem.file.size)}
                  </p>
                </div>

                {/* Status */}
                <div className="flex items-center gap-2">
                  {getStatusIcon(fileItem.status)}
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${getStatusColor(fileItem.status)}`}>
                    {getStatusText(fileItem.status, fileItem.progress)}
                  </span>
                </div>

                {/* Progress bar for processing */}
                {(fileItem.status === 'processing' || fileItem.status === 'uploading') && (
                  <div className="w-24">
                    <div className="h-2 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 transition-all duration-300"
                        style={{ width: `${fileItem.progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-1">
                  {fileItem.status === 'completed' && fileItem.essayId && (
                    <button
                      onClick={() => navigate(`/verification/report/${fileItem.essayId}`)}
                      className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                      title="View Report"
                    >
                      <ExternalLink className="h-4 w-4 text-slate-500 dark:text-slate-400" />
                    </button>
                  )}
                  {fileItem.status === 'failed' && (
                    <button
                      onClick={() => retryFile(fileItem.id)}
                      disabled={queueState.isProcessing}
                      className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
                      title="Retry"
                    >
                      <RefreshCw className="h-4 w-4 text-slate-500 dark:text-slate-400" />
                    </button>
                  )}
                  {!queueState.isProcessing && (
                    <button
                      onClick={() => removeFile(fileItem.id)}
                      className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      title="Remove"
                    >
                      <Trash2 className="h-4 w-4 text-slate-500 dark:text-slate-400 hover:text-red-500" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Error messages */}
          {files.filter(f => f.error).map(f => (
            <div key={f.id} className="text-sm text-red-600 dark:text-red-400 pl-4">
              {f.file.name}: {f.error}
            </div>
          ))}
        </div>
      )}

      {/* Summary Stats */}
      {files.length > 0 && (
        <div className="mt-6 grid grid-cols-4 gap-4">
          <div className="bg-slate-100 dark:bg-slate-800 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-slate-600 dark:text-slate-300">{stats.pending}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400">Pending</p>
          </div>
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-blue-600 dark:text-blue-300">{stats.processing}</p>
            <p className="text-sm text-blue-600 dark:text-blue-400">Processing</p>
          </div>
          <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-300">{stats.completed}</p>
            <p className="text-sm text-emerald-600 dark:text-emerald-400">Completed</p>
          </div>
          <div className="bg-red-50 dark:bg-red-900/20 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-red-600 dark:text-red-300">{stats.failed}</p>
            <p className="text-sm text-red-600 dark:text-red-400">Failed</p>
          </div>
        </div>
      )}

      {/* Start Button */}
      <div className="mt-8 flex flex-col items-center gap-3">
        <button
          onClick={handleStartVerification}
          disabled={pendingCount === 0 || queueState.isProcessing}
          className={`
            inline-flex items-center gap-2 px-8 py-3 rounded-xl font-semibold transition-all
            ${pendingCount === 0 || queueState.isProcessing
              ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed'
              : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm hover:shadow-md'
            }
          `}
        >
          {queueState.isProcessing ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              Start Verification
              <Upload className="h-5 w-5" />
            </>
          )}
        </button>

        {/* Auto-navigate hint / all-failed notice */}
        {!queueState.isProcessing && files.length > 0 && stats.pending === 0 && stats.processing === 0 && (
          <>
            {stats.completed > 0 ? (
              <p className="text-sm text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                All files processed — opening report…
              </p>
            ) : (
              <p className="text-sm text-red-600 dark:text-red-400">
                All files failed to process. Check the errors above and retry.
              </p>
            )}
          </>
        )}
      </div>

      {/* Disclaimer */}
      <div className="mt-12 text-center">
        <p className="text-xs text-slate-400 dark:text-slate-500">
          This is a decision-support tool. All results should be reviewed by experts.
        </p>
      </div>
    </div>
  );
}
