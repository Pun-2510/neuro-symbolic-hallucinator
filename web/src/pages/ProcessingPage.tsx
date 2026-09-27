import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Check,
  Circle,
  Database,
  FileCheck,
  FileText,
  GitMerge,
  Loader2,
  Quote,
  AlertTriangle,
} from 'lucide-react';
import { api, type EssayStatus, type AnalysisReport } from '@/api/client';

/* ============================================================
   ProcessingPage — Real-time pipeline progress
   Polls GET /essays/{id}/status for live step/source updates.
   ============================================================ */

const STEP_LABELS: Array<{ label: string; details: string }> = [
  { label: 'Parsing document', details: 'Extracting text and structure from PDF' },
  { label: 'Detecting citation style', details: 'APA · IEEE · Harvard · MLA · Chicago' },
  { label: 'Extracting citations & references', details: 'Scanning for in-text citations and bibliography' },
  { label: 'Linking citations to references', details: 'Bidirectional citation-reference matching' },
  { label: 'Retrieving source metadata', details: 'Querying Crossref, OpenAlex, Semantic Scholar, CORE' },
  { label: 'Comparing candidate publications', details: 'Title, author, year, venue matching' },
  { label: 'Applying neuro-symbolic rules', details: 'Evidence-based verification logic' },
  { label: 'Generating verification report', details: 'Compiling findings and explanations' },
];

// Map backend step keys to our step index
const STEP_KEY_TO_INDEX: Record<string, number> = {
  parsing: 0,
  style_detection: 1,
  extracting: 2,
  linking: 3,
  retrieving: 4,
  comparing: 5,
  checking: 6,
  scoring: 7,
  done: 7, // scoring + done share the last slot
};

function stepStatus(
  idx: number,
  backendIndex: number,
  done: boolean,
): 'completed' | 'active' | 'pending' | 'error' {
  if (done || idx < backendIndex) return 'completed';
  if (idx === backendIndex) return 'active';
  return 'pending';
}

export function ProcessingPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [status, setStatus] = useState<EssayStatus | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [redirecting, setRedirecting] = useState(false);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Poll /status every 1.5 s until we know it's done/failed
  useEffect(() => {
    if (!id) return;

    const numericId = parseInt(id, 10);
    if (isNaN(numericId)) return;

    const poll = async () => {
      try {
        const snap = await api.getEssayStatus(numericId);
        setStatus(snap);

        if (snap.status === 'completed') {
          // Stop polling status — fetch the full report once then redirect
          if (pollTimer.current) clearInterval(pollTimer.current);

          const rep = await api.getEssay(numericId);
          if (rep) {
            setReport(rep);
            setRedirecting(true);
            setTimeout(() => navigate(`/verification/report/${id}`), 1500);
          }
        } else if (snap.status === 'failed') {
          if (pollTimer.current) clearInterval(pollTimer.current);
        }
      } catch {
        // Ignore poll errors — keep trying
      }
    };

    poll(); // immediate first poll
    pollTimer.current = setInterval(poll, 1500);

    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, [id, navigate]);

  const backendIndex = status
    ? Math.min(STEP_KEY_TO_INDEX[status.step] ?? 0, STEP_LABELS.length - 1)
    : 0;

  const progress = status
    ? Math.round(((backendIndex + (status.status === 'completed' ? 1 : 0)) / STEP_LABELS.length) * 100)
    : 0;

  const isDone = status?.status === 'completed';
  const isFailed = status?.status === 'failed';

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="text-center mb-10">
        <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-white mb-3">
          {isFailed ? 'Analysis failed' : isDone ? 'Analysis complete' : 'Analyzing document'}
        </h1>
        <p className="text-slate-600 dark:text-slate-400">
          {isFailed
            ? 'An error occurred during processing.'
            : isDone
            ? 'Redirecting to your verification report…'
            : 'This may take a few minutes depending on document size.'}
        </p>
      </div>

      {/* Failed banner */}
      {isFailed && (
        <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-700 dark:text-red-300">
              Pipeline error
            </p>
            <p className="text-xs text-red-500 dark:text-red-400 mt-1">
              {status?.error ?? 'Unknown error — please try uploading the document again.'}
            </p>
          </div>
        </div>
      )}

      {/* Progress bar */}
      <div className="mb-10">
        <div className="h-2.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-indigo-600 to-indigo-500 rounded-full transition-all duration-700 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between items-center mt-2">
          <span className="text-sm text-slate-500 dark:text-slate-400">
            {isFailed ? 'Failed' : isDone ? 'Complete' : 'Processing…'}
          </span>
          <span className="text-sm font-mono font-semibold text-slate-600 dark:text-slate-300">
            {progress}%
          </span>
        </div>
        {/* Live message from backend */}
        {status && !isDone && !isFailed && (
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 italic">
            {status.message}
          </p>
        )}
      </div>

      {/* Pipeline stepper */}
      <div className="card bg-white dark:bg-slate-800/50 p-6 mb-6">
        <div className="flex items-center gap-2 mb-5">
          <GitMerge className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-white">
            Verification Pipeline
          </h2>
        </div>

        <div className="space-y-3">
          {STEP_LABELS.map((step, idx) => {
            const s = stepStatus(idx, backendIndex, isDone || isFailed);

            return (
              <div key={idx} className="flex items-start gap-3">
                <div
                  className={`mt-0.5 w-7 h-7 rounded-lg flex items-center justify-center transition-all duration-300 ${
                    s === 'completed'
                      ? 'bg-emerald-100 dark:bg-emerald-900/50'
                      : s === 'active'
                      ? 'bg-indigo-100 dark:bg-indigo-900/50'
                      : 'bg-slate-100 dark:bg-slate-800'
                  }`}
                >
                  {s === 'completed' ? (
                    <Check className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  ) : s === 'active' ? (
                    <Loader2 className="h-4 w-4 text-indigo-600 dark:text-indigo-400 animate-spin" />
                  ) : (
                    <Circle className="h-4 w-4 text-slate-300 dark:text-slate-600" />
                  )}
                </div>

                <div className="flex-1 min-w-0 pt-1">
                  <p
                    className={`text-sm transition-colors duration-200 ${
                      s === 'completed'
                        ? 'text-emerald-700 dark:text-emerald-300'
                        : s === 'active'
                        ? 'text-indigo-700 dark:text-indigo-300 font-semibold'
                        : 'text-slate-400 dark:text-slate-500'
                    }`}
                  >
                    {step.label}
                  </p>

                  {/* Live stats on the extraction step */}
                  {idx === 2 && status && (
                    <div className="flex gap-4 mt-2 text-xs">
                      <span className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
                        <Quote className="h-3 w-3" />
                        {status.citations_found} citations
                      </span>
                      <span className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
                        <FileText className="h-3 w-3" />
                        {status.references_found} references
                      </span>
                    </div>
                  )}

                  {/* Live stats on the linking step */}
                  {idx === 3 && status && (
                    <div className="flex gap-4 mt-2 text-xs">
                      <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                        <Check className="h-3 w-3" />
                        {status.linked} linked
                      </span>
                    </div>
                  )}

                  {s === 'active' && step.details && (
                    <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                      {step.details}
                    </p>
                  )}
                </div>

                <span className="text-xs font-mono text-slate-400 dark:text-slate-500 pt-1">
                  {idx + 1}/{STEP_LABELS.length}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Live stats grid */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          icon={<Quote className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />}
          value={status?.citations_found ?? '-'}
          label="Citations"
        />
        <StatCard
          icon={<FileText className="h-5 w-5 text-slate-600 dark:text-slate-400" />}
          value={status?.references_found ?? '-'}
          label="References"
        />
        <StatCard
          icon={<GitMerge className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />}
          value={status?.linked ?? '-'}
          label="Linked"
          highlight
        />
        <StatCard
          icon={<Database className="h-5 w-5 text-amber-600 dark:text-amber-400" />}
          value={status?.citations_found ? status.citations_found : '-'}
          label="To verify"
        />
      </div>

      {/* Source retrieval tiles — real backend state */}
      <div className="card bg-white dark:bg-slate-800/50 p-6 mt-6">
        <div className="flex items-center gap-2 mb-4">
          <Database className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          <h3 className="font-display text-base font-semibold text-slate-900 dark:text-slate-100">
            Source Retrieval
          </h3>
          {!isDone && !isFailed && (
            <Loader2 className="h-4 w-4 animate-spin text-indigo-600 ml-2" />
          )}
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {(['crossref', 'openalex', 's2', 'core'] as const).map((db) => (
            <SourceTile
              key={db}
              name={db}
              state={status?.sources_queried[db]}
            />
          ))}
        </div>

        {/* Source retrieval tiles from full report once complete */}
        {report && (
          <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-700 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {(['crossref', 'openalex', 's2', 'core'] as const).map((db) => {
              const count = report.verdicts.filter(
                (v) => (v.matched_sources ?? []).some((s) => s.source === db),
              ).length;
              return (
                <div
                  key={db}
                  className="p-3 rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30"
                >
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-300 capitalize">{db}</p>
                  <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
                    {count} verified
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Completion banner */}
      {(isDone || redirecting) && (
        <div className="mt-8 p-6 rounded-2xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-900/50 mb-3">
            <FileCheck className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
          </div>
          <h3 className="font-display text-lg font-semibold text-emerald-800 dark:text-emerald-200 mb-1">
            Analysis Complete
          </h3>
          <p className="text-sm text-emerald-600 dark:text-emerald-400">
            Redirecting to verification report…
          </p>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ //
// Sub-components                                                          //
// ------------------------------------------------------------------ //

function StatCard({
  icon,
  value,
  label,
  highlight,
}: {
  icon: React.ReactNode;
  value: number | string;
  label: string;
  highlight?: boolean;
}) {
  return (
    <div className="card bg-white dark:bg-slate-800/50 p-4 text-center">
      <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-900/50 mb-3">
        {icon}
      </div>
      <p
        className={`text-2xl font-bold ${
          highlight
            ? 'text-emerald-600 dark:text-emerald-400'
            : 'text-slate-900 dark:text-slate-100'
        }`}
      >
        {value}
      </p>
      <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{label}</p>
    </div>
  );
}

function SourceTile({
  name,
  state,
}: {
  name: string;
  state: string | undefined;
}) {
  const displayName = name === 's2' ? 'Semantic Scholar' : name.charAt(0).toUpperCase() + name.slice(1);

  let color = 'slate';
  let label = 'Pending';

  if (state === 'ok') {
    color = 'emerald';
    label = 'Connected';
  } else if (state === 'partial') {
    color = 'amber';
    label = 'Partial';
  } else if (state?.startsWith('failed')) {
    color = 'red';
    const n = state.split(':')[1];
    label = `Failed${n ? ` (${n})` : ''}`;
  }

  const colors: Record<string, string> = {
    emerald:
      'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300',
    amber:
      'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300',
    red: 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300',
    slate:
      'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400',
  };

  return (
    <div className={`p-3 rounded-xl border transition-all ${colors[color]}`}>
      <p className="text-sm font-medium">{displayName}</p>
      <p className="text-xs mt-1">{label}</p>
    </div>
  );
}
