import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { FileText, Search, AlertCircle } from 'lucide-react';
import { api, type AuditLogEntry } from '@/api/client';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

/**
 * AuditLogPage — admin-only audit log (Phase 4).
 *
 * Lists override events recorded by Task 1 (`Repository.log_audit`).
 * Filter by username; default limit 100 newest-first.
 */
export function AuditLogPage() {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [userFilter, setUserFilter] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.listAuditLog({
        limit: 100,
        user: userFilter.trim() || undefined,
      });
      setEntries(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load audit log');
    } finally {
      setLoading(false);
    }
  }, [userFilter]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
          <FileText className="h-5 w-5 text-slate-600 dark:text-slate-400" />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold text-slate-900 dark:text-white">{t('admin.auditLog')}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t('admin.auditLogSubtitle')}
          </p>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
        <Input
          type="text"
          value={userFilter}
          onChange={(e) => setUserFilter(e.target.value)}
          placeholder={t('admin.filterByUsername')}
          aria-label="Filter audit log by username"
          className="pl-10"
        />
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card className="p-0 overflow-hidden">
        {loading ? (
          <p className="px-4 py-8 text-center text-slate-500 text-sm">{t('common.loading')}</p>
        ) : (
          <Table>
            <TableHeader className="bg-slate-50 dark:bg-slate-800/50 text-xs uppercase text-slate-500">
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-left px-4 py-3 font-semibold">{t('admin.when')}</TableHead>
                <TableHead className="text-left px-4 py-3 font-semibold">{t('admin.tableUser')}</TableHead>
                <TableHead className="text-left px-4 py-3 font-semibold">{t('admin.verdict')}</TableHead>
                <TableHead className="text-left px-4 py-3 font-semibold">{t('admin.fromTo')}</TableHead>
                <TableHead className="text-left px-4 py-3 font-semibold">{t('admin.note')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="divide-y divide-slate-100 dark:divide-slate-800">
              {entries.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="px-4 py-8 text-center text-slate-500">
                    {t('admin.noAuditLogs')}
                  </TableCell>
                </TableRow>
              ) : (
                entries.map((e) => (
                  <TableRow key={e.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                    <TableCell className="px-4 py-3 text-slate-600 dark:text-slate-400 whitespace-nowrap font-mono text-xs">
                      {e.logged_at ? new Date(e.logged_at).toLocaleString() : '—'}
                    </TableCell>
                    <TableCell className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                      {e.user}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-slate-500 font-mono text-xs">
                      <Badge variant="outline" className="font-mono text-xs">
                        #{e.verdict_id}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <span className="font-mono text-xs">
                        <span className="text-rose-600 dark:text-rose-400">
                          {e.original_label}
                        </span>
                        {' → '}
                        <span className="text-emerald-600 dark:text-emerald-400">
                          {e.new_label}
                        </span>
                      </span>
                    </TableCell>
                    <TableCell className="px-4 py-3 text-slate-600 dark:text-slate-400 max-w-xs truncate">
                      {e.note ?? '—'}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </Card>
    </div>
  );
}
