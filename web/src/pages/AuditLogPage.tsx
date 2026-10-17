import { useEffect, useState, useCallback } from 'react';
import { FileText, Search } from 'lucide-react';
import { api, type AuditLogEntry } from '@/api/client';

/**
 * AuditLogPage — admin-only audit log (Phase 4).
 *
 * Lists override events recorded by Task 1 (`Repository.log_audit`).
 * Filter by username; default limit 100 newest-first.
 */
export function AuditLogPage() {
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
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Audit Log</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Lịch sử override verdict & system events.
          </p>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
        <input
          type="text"
          value={userFilter}
          onChange={(e) => setUserFilter(e.target.value)}
          placeholder="Lọc theo username…"
          aria-label="Filter audit log by username"
          className="w-full pl-10 pr-3 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {error && (
        <p className="text-sm text-rose-600 dark:text-rose-400" role="alert">
          {error}
        </p>
      )}

      <div className="rounded-xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 overflow-hidden">
        {loading ? (
          <p className="px-4 py-8 text-center text-slate-500 text-sm">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800/50 text-xs uppercase text-slate-500">
              <tr>
                <th className="text-left px-4 py-3 font-semibold">When</th>
                <th className="text-left px-4 py-3 font-semibold">User</th>
                <th className="text-left px-4 py-3 font-semibold">Verdict</th>
                <th className="text-left px-4 py-3 font-semibold">From → To</th>
                <th className="text-left px-4 py-3 font-semibold">Note</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {entries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                    Chưa có audit log.
                  </td>
                </tr>
              ) : (
                entries.map((e) => (
                  <tr key={e.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                      {e.logged_at ? new Date(e.logged_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                      {e.user}
                    </td>
                    <td className="px-4 py-3 text-slate-500 font-mono text-xs">
                      #{e.verdict_id}
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs">
                        <span className="text-rose-600 dark:text-rose-400">
                          {e.original_label}
                        </span>
                        {' → '}
                        <span className="text-emerald-600 dark:text-emerald-400">
                          {e.new_label}
                        </span>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400 max-w-xs truncate">
                      {e.note ?? '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
