import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Loader2,
  FileText,
  Trash2,
  Search,
  Clock,
  Upload,
  XCircle,
  RefreshCw,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';
import { useToast } from '@/contexts/ToastContext';
import { ConfirmationModal } from '@/components/ConfirmationModal';
import { useRole } from '@/hooks/useRole';
import { useEssays, useDeleteEssay } from '@/hooks/useEssays';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';

/* ============================================================
   SourceLogic — History Page Component (shadcn/ui v2.0)
   ============================================================ */

export function HistoryPage() {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const { isTeacher, isAdmin } = useRole();
  const {
    data: items = [],
    isLoading,
    error,
    refetch,
    isFetching,
  } = useEssays();
  const deleteMutation = useDeleteEssay();
  const [searchQuery, setSearchQuery] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const errorMessage = error
    ? error instanceof Error
      ? error.message
      : t('error.network')
    : null;
  const deletingId = deleteMutation.isPending
    ? (deleteMutation.variables ?? null)
    : null;

  const handleDelete = async () => {
    const id = confirmDeleteId;
    if (id == null) return;
    setConfirmDeleteId(null);
    try {
      await deleteMutation.mutateAsync(id);
      toast.success(t('dashboard.documentDeleted'));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('dashboard.deleteFailed'));
    }
  };

  const filteredItems = items.filter((item) =>
    item.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const dateLocale = i18n.language?.startsWith('vi') ? 'vi-VN' : 'en-US';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-slate-100">
            {t('history.title')}
          </h1>
          <p className="text-slate-600 dark:text-slate-300 mt-1">
            {t(
              items.length === 1
                ? 'history.documentCountOne'
                : 'history.documentCountOther',
              { count: items.length }
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button asChild size="sm">
            <Link to="/upload">
              <Upload className="h-4 w-4" />
              {t('dashboard.newCheck')}
            </Link>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => refetch()}
            disabled={isFetching}
            aria-label="Refresh history"
            title={t('common.refresh')}
            className="min-h-10 min-w-10"
          >
            <RefreshCw className={`h-5 w-5 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search
          className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400 dark:text-slate-500 pointer-events-none"
          aria-hidden="true"
        />
        <Input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={t('dashboard.searchPlaceholder')}
          aria-label="Search documents"
          className="h-11 pl-12 pr-10"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            aria-label="Clear search"
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
          >
            <XCircle className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Error */}
      {errorMessage && (
        <Alert variant="destructive">
          <AlertTriangle className="h-5 w-5" />
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}

      {/* Loading / Empty / List */}
      {isLoading && items.length === 0 ? (
        <Card className="p-12 flex flex-col items-center justify-center">
          <Loader2 className="h-8 w-8 text-indigo-600 dark:text-indigo-400 animate-spin mb-4" />
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {t('dashboard.loadingDocuments')}
          </p>
        </Card>
      ) : filteredItems.length === 0 ? (
        <Card className="p-12 text-center">
          <div className="flex items-center justify-center w-20 h-20 rounded-2xl bg-slate-100 dark:bg-slate-800 mx-auto mb-5">
            <FileText className="h-10 w-10 text-slate-400 dark:text-slate-500" />
          </div>
          {searchQuery ? (
            <>
              <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
                {t('dashboard.noDocumentsFound')}
              </h3>
              <p className="text-slate-600 dark:text-slate-300 mb-4">
                {t('dashboard.noDocumentsMatch', { query: searchQuery })}
              </p>
              <Button variant="link" onClick={() => setSearchQuery('')}>
                {t('dashboard.clearSearch')}
              </Button>
            </>
          ) : (
            <>
              <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
                {t('dashboard.noDocumentsYet')}
              </h3>
              <p className="text-slate-600 dark:text-slate-300 mb-6">
                {isAdmin
                  ? t('dashboard.noDocumentsAdmin')
                  : isTeacher
                    ? t('dashboard.noDocumentsTeacher')
                    : t('dashboard.noDocumentsStudent')}
              </p>
              {!(isTeacher || isAdmin) && (
                <Button asChild>
                  <Link to="/upload">
                    <Upload className="h-4 w-4" />
                    {t('dashboard.uploadDocument')}
                  </Link>
                </Button>
              )}
            </>
          )}
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredItems.map((essay) => (
            <Link
              key={essay.id}
              to={`/verification/report/${essay.id}`}
              className="card-interactive block p-5 group"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-50 dark:bg-indigo-950 group-hover:bg-indigo-600 transition-colors shrink-0">
                    <FileText className="h-7 w-7 text-indigo-600 dark:text-indigo-400 group-hover:text-white transition-colors" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-slate-900 dark:text-slate-100 truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      {essay.filename}
                    </p>
                    <div className="flex items-center gap-4 text-sm text-slate-600 dark:text-slate-300 mt-1">
                      <span className="flex items-center gap-1.5 font-mono text-xs">
                        <FileText className="h-3.5 w-3.5" />
                        {essay.num_pages} {t('history.pages')}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" />
                        {new Date(essay.uploaded_at).toLocaleDateString(
                          dateLocale,
                          {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          }
                        )}
                      </span>
                      <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
                        ID #{essay.id}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className="hidden sm:inline-flex px-3 py-1.5 text-sm font-medium border border-slate-200 dark:border-slate-700 rounded-lg text-slate-600 dark:text-slate-400 group-hover:border-indigo-300 dark:group-hover:border-indigo-600 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                    {t('dashboard.viewReport')}
                  </span>
                  <button
                    onClickCapture={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setConfirmDeleteId(essay.id);
                    }}
                    disabled={deletingId === essay.id}
                    className="p-2.5 min-h-11 min-w-11 rounded-lg text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/50 transition-colors disabled:opacity-50"
                    title={t('common.delete')}
                    aria-label={`Delete ${essay.filename}`}
                  >
                    {deletingId === essay.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                  <ChevronRight className="h-5 w-5 text-slate-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Stats Footer */}
      {items.length > 0 && (
        <div className="flex items-center justify-between text-sm text-slate-600 dark:text-slate-300 pt-4 border-t border-slate-200 dark:border-slate-700">
          <p>
            {t('dashboard.showingCount', {
              shown: filteredItems.length,
              total: items.length,
            })}
          </p>
          <p className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 dark:text-emerald-400" />
            {t('history.autoRefreshActive')}
          </p>
        </div>
      )}

      <ConfirmationModal
        isOpen={confirmDeleteId !== null}
        title={t('dashboard.deleteConfirmTitle')}
        message={t('dashboard.deleteConfirmMessage')}
        confirmLabel={t('common.delete')}
        cancelLabel={t('common.cancel')}
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setConfirmDeleteId(null)}
      />
    </div>
  );
}
