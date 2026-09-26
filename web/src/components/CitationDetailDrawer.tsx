import { X, ExternalLink, CheckCircle, AlertTriangle, XCircle, HelpCircle, Database, Quote, FileText, GitBranch, ArrowRight, Search, Shield, Network } from 'lucide-react';
import type { Verdict, MatchedSource, ValidationLabel, OverrideRequest } from '@/api/client';
import { VerdictBadge } from './VerdictBadge';
import { MappingStatusBadge } from './MappingStatusBadge';
import { EvidenceGraph } from './CitationGraphView';
import { cn } from '@/lib/utils';

/* ============================================================
   SourceLogic — Citation Detail Drawer Component
   Based on UX/UI Concept Section 10: Reference Inspector
   ============================================================ */

const LABEL_ICONS: Record<ValidationLabel, React.ReactNode> = {
  verified: <CheckCircle className="h-4 w-4" />,
  metadata_error: <AlertTriangle className="h-4 w-4" />,
  suspected_hallucination: <XCircle className="h-4 w-4" />,
  unresolved: <HelpCircle className="h-4 w-4" />,
};

/* ============================================================
   Source Badge Component - Database source identifier
   ============================================================ */
function SourceBadge({ src }: { src: MatchedSource }) {
  const colorMap: Record<string, { bg: string; text: string }> = {
    crossref: { bg: 'bg-emerald-100 dark:bg-emerald-900', text: 'text-emerald-800 dark:text-emerald-200' },
    openalex: { bg: 'bg-indigo-100 dark:bg-indigo-900', text: 'text-indigo-800 dark:text-indigo-200' },
    s2: { bg: 'bg-amber-100 dark:bg-amber-900', text: 'text-amber-800 dark:text-amber-200' },
    core: { bg: 'bg-orange-100 dark:bg-orange-900', text: 'text-orange-800 dark:text-orange-200' },
  };

  const colors = colorMap[src.source] || { bg: 'bg-slate-100 dark:bg-slate-800', text: 'text-slate-800 dark:text-slate-200' };
  const matchedFields = src.matched_fields ?? [];

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-xl p-4 bg-white dark:bg-slate-800 hover:border-indigo-300 dark:hover:border-indigo-600 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={cn('text-xs font-bold px-2 py-0.5 rounded uppercase', colors.bg, colors.text)}>
            {src.source}
          </span>
          {src.checked_at && (
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {new Date(src.checked_at).toLocaleString()}
            </span>
          )}
        </div>
        {src.url && (
          <a
            href={src.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
            title="Open in browser"
          >
            <ExternalLink className="h-3 w-3" />
            Open
          </a>
        )}
      </div>

      {/* Matched fields */}
      {matchedFields.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {matchedFields.map((field) => (
            <span
              key={field}
              className="px-2 py-0.5 bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 rounded text-xs font-mono"
            >
              {field}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/* ============================================================
   Logic Trace Step Component
   Section 14: Logic Trace
   ============================================================ */
function LogicTraceStep({
  step,
  isActive = false,
  isComplete = false,
  isError = false,
}: {
  step: string;
  isActive?: boolean;
  isComplete?: boolean;
  isError?: boolean;
}) {
  return (
    <div
      className={cn(
        'border-l-2 pl-4 py-3 transition-colors',
        isActive && 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950',
        isComplete && 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950',
        isError && 'border-red-500 bg-red-50 dark:bg-red-950',
        !isActive && !isComplete && !isError && 'border-slate-200 dark:border-slate-700'
      )}
    >
      <p className="text-sm text-slate-900 dark:text-slate-100">{step}</p>
    </div>
  );
}

/* ============================================================
   Main CitationDetailDrawer Component
   ============================================================ */
export function CitationDetailDrawer({
  verdict,
  onClose,
  onOverride,
}: {
  verdict: Verdict;
  onClose: () => void;
  onOverride?: (req: OverrideRequest) => Promise<void>;
}) {
  // Defensive: ensure arrays are always defined
  const triggeredRules = verdict.triggered_rules ?? [];
  const mismatchedFields = verdict.mismatched_fields ?? [];
  const matchedSources = verdict.matched_sources ?? [];

  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 animate-fadeIn"
      onClick={onClose}
    >
      <div
        className="absolute right-0 top-0 h-full w-full md:max-w-2xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700 shadow-2xl overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header - Section 10: Reference Inspector */}
        <div className="sticky top-0 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-6 py-4 flex items-start justify-between gap-4 z-10">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-100 dark:bg-indigo-900">
              <Quote className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h2 className="font-display text-lg font-bold text-slate-900 dark:text-white">
                Citation Detail
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Reference verification analysis
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Citation Text - Section 10 */}
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-3">
              <FileText className="h-4 w-4 text-slate-400" />
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                In-text Citation
              </span>
            </div>
            <p className="text-sm text-slate-900 dark:text-slate-100 font-medium">
              {verdict.citation_raw || 'Unknown citation'}
            </p>
            {verdict.citation_id && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                Citation ID: {verdict.citation_id}
              </p>
            )}
          </div>

          {/* Two-layer badges - Section 11: Verification Status */}
          <div className="flex flex-wrap gap-4">
            {/* Verification Status */}
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500 dark:text-slate-400">Verification:</span>
              <VerdictBadge verdict={verdict.label || 'UNVERIFIABLE'} size="md" />
              {verdict.confidence !== undefined && (
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  {Math.round(verdict.confidence * 100)}% confidence
                </span>
              )}
            </div>
            {/* Mapping Status */}
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500 dark:text-slate-400">Mapping:</span>
              <MappingStatusBadge status={verdict.mapping_status} />
              {verdict.mapping_confidence !== undefined && (
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  {Math.round(verdict.mapping_confidence * 100)}%
                </span>
              )}
            </div>
          </div>

          {/* Override indicator */}
          {verdict.is_overridden && (
            <div className="flex items-start gap-3 p-4 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-xl">
              <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
                  Human Override Applied
                </p>
                {verdict.override_record && (
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                    Changed from {verdict.override_record.previous_label} to {verdict.override_record.new_label}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Reasoning */}
          {verdict.reasoning && (
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-3">
                <GitBranch className="h-4 w-4 text-slate-400" />
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Reasoning
                </span>
              </div>
              <p className="text-sm text-slate-900 dark:text-slate-100 leading-relaxed">
                {verdict.reasoning}
              </p>
            </div>
          )}

          {/* Logic Trace - Section 14 */}
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="h-4 w-4 text-slate-400" />
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Verification Logic Trace
              </span>
            </div>
            <div className="space-y-2">
              <LogicTraceStep step="Reference parsed from bibliography" isComplete />
              <LogicTraceStep step="Academic search across 4 databases" isComplete />
              <LogicTraceStep step="Semantic similarity comparison" isActive />
              {triggeredRules.length > 0 && (
                <LogicTraceStep
                  step={`Rules triggered: ${triggeredRules.join(', ')}`}
                  isComplete={verdict.label === 'verified'}
                  isError={verdict.label === 'suspected_hallucination'}
                />
              )}
              <LogicTraceStep
                step={`Final verdict: ${verdict.label || 'UNVERIFIABLE'}`}
                isComplete
              />
            </div>
          </div>

          {/* Evidence Graph - Section 16: Full visual evidence chain */}
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-4">
              <Network className="h-4 w-4 text-slate-400" />
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Evidence Graph
              </span>
            </div>
            <EvidenceGraph verdict={verdict} />
          </div>

          {/* Triggered Rules */}
          {triggeredRules.length > 0 && (
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Rules Triggered
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {triggeredRules.map((r) => (
                  <span
                    key={r}
                    className="px-3 py-1 bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 rounded-lg text-xs font-mono font-medium"
                  >
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Mismatched Fields - Section 10: Metadata Comparison */}
          {mismatchedFields.length > 0 && (
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Mismatched Fields
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {mismatchedFields.map((f) => (
                  <span
                    key={f}
                    className="px-3 py-1 bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 rounded-lg text-xs font-mono"
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Evidence Sources - Section 10: Sources */}
          {matchedSources.length > 0 && (
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-3">
                <Database className="h-4 w-4 text-slate-400" />
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Evidence Sources ({matchedSources.length})
                </span>
              </div>
              <div className="space-y-3">
                {matchedSources.map((src, i) => (
                  <SourceBadge key={i} src={src} />
                ))}
              </div>
            </div>
          )}

          {/* No sources found - Section 10 */}
          {matchedSources.length === 0 && (
            <div className="card p-4 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800">
              <div className="flex items-center gap-2 mb-2">
                <XCircle className="h-4 w-4 text-red-500" />
                <span className="text-xs font-semibold text-red-600 dark:text-red-400 uppercase tracking-wider">
                  No Evidence Found
                </span>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                No matching sources were found across Crossref, OpenAlex, Semantic Scholar, or CORE databases.
              </p>
            </div>
          )}

          {/* Domain Exception */}
          {verdict.domain_exception && (
            <div className="card p-4 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
                    Domain Exception Detected
                  </p>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                    DOI matched but title similarity is low. This may be a valid source in a specialized
                    domain where metadata differs across databases.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Style Penalty */}
          {verdict.style_penalty !== undefined && verdict.style_penalty !== 0 && (
            <div className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <span className="text-xs text-slate-500 dark:text-slate-400">Style penalty:</span>
              <span className="text-sm font-mono text-amber-600 dark:text-amber-400">
                {(verdict.style_penalty * 100).toFixed(1)}%
              </span>
            </div>
          )}

          {/* Override History */}
          {verdict.override_record && (
            <div className="card p-4 border-t-4 border-indigo-500">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Override History
                </span>
              </div>
              <div className="space-y-2 text-sm">
                {verdict.override_record.overridden_at && (
                  <p>
                    <span className="text-slate-500 dark:text-slate-400">At:</span>{' '}
                    <span className="text-slate-900 dark:text-slate-100">
                      {new Date(verdict.override_record.overridden_at).toLocaleString()}
                    </span>
                  </p>
                )}
                {verdict.override_record.previous_label && (
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500 dark:text-slate-400">Previous:</span>
                    <VerdictBadge verdict={verdict.override_record.previous_label} size="sm" />
                  </div>
                )}
                {verdict.override_record.new_label && (
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500 dark:text-slate-400">New:</span>
                    <VerdictBadge verdict={verdict.override_record.new_label} size="sm" />
                  </div>
                )}
                {verdict.override_record.reason && (
                  <p className="text-slate-500 dark:text-slate-400 italic">
                    "{verdict.override_record.reason}"
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
