import { X, ExternalLink, CheckCircle, AlertTriangle, XCircle, HelpCircle, Database, Quote, FileText, GitBranch, Shield, Network, Link2 } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import type { Verdict, MatchedSource, ValidationLabel, OverrideRequest } from '@/api/client';
import { VerdictBadge } from './VerdictBadge';
import { MappingStatusBadge } from './MappingStatusBadge';
import { EvidenceGraph } from './CitationGraphView';
import { OverrideControls } from './OverrideControls';
import { cn } from '@/lib/utils';
import { getFieldDisplayName, getRuleDisplayName, getSourceDisplayName, getVerdictDisplayName, getVerdictExplanation, isUrlResource } from '@/lib/verdictExplanation';

/* ============================================================
   SourceLogic — Citation Detail Drawer Component
   Based on UX/UI Concept Section 10: Reference Inspector
   ============================================================ */

const LABEL_ICONS: Record<ValidationLabel, React.ReactNode> = {
  verified: <CheckCircle className="h-4 w-4" />,
  metadata_error: <AlertTriangle className="h-4 w-4" />,
  suspected_hallucination: <XCircle className="h-4 w-4" />,
  unresolved: <HelpCircle className="h-4 w-4" />,
  resource: <Link2 className="h-4 w-4" />,
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
            {getSourceDisplayName(src.source)}
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
              {getFieldDisplayName(field).replace(/^the /, '')}
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
  const { t } = useTranslation();
  const drawerRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      // Focus trap: cycle Tab/Shift+Tab inside the drawer so screen-reader
      // and keyboard users can't escape into the inert page behind.
      if (e.key === 'Tab' && drawerRef.current) {
        const focusable = drawerRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"]), input, select, textarea'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        const active = document.activeElement as HTMLElement | null;
        if (e.shiftKey && active === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && active === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Move focus into the drawer on open; restore the previous focus on close.
  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    // Focus the close button so keyboard users land in a sensible spot.
    const closeBtn = drawerRef.current?.querySelector<HTMLButtonElement>(
      'button[aria-label="Close"]'
    );
    closeBtn?.focus();
    // Lock body scroll while the drawer is open
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prevOverflow;
      previousFocusRef.current?.focus();
    };
  }, []);

  // Defensive: ensure arrays are always defined
  const triggeredRules = verdict.triggered_rules ?? [];
  const mismatchedFields = verdict.mismatched_fields ?? [];
  const matchedSources = verdict.matched_sources ?? [];

  // A local-only hit means every matched source came from an internal cache
  // path (local DB / known papers), so no external API was ever queried.
  const isLocalOnly =
    matchedSources.length > 0 &&
    matchedSources.every((s) => ['local_db', 'known_papers'].includes((s.source || '').toLowerCase()));

  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 animate-fadeIn"
      onClick={onClose}
    >
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="citation-detail-title"
        className="absolute right-0 top-0 h-full w-full md:max-w-2xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700 shadow-2xl overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        tabIndex={-1}
      >
        {/* Header - Section 10: Reference Inspector */}
        <div className="sticky top-0 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-6 py-4 flex items-start justify-between gap-4 z-10">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-100 dark:bg-indigo-900">
              <Quote className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h2
                id="citation-detail-title"
                className="font-display text-lg font-bold text-slate-900 dark:text-white"
              >
                {t('essay.citationDetail')}
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t('essay.referenceVerificationAnalysis')}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            aria-label="Close citation detail"
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
                {t('essay.inTextCitation')}
              </span>
            </div>
            <p className="text-sm text-slate-900 dark:text-slate-100 font-medium">
              {verdict.citation_raw || 'Unknown citation'}
            </p>
            {verdict.citation_id && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                {t('essay.citationId')}: {verdict.citation_id}
              </p>
            )}
          </div>

          {/* Two-layer badges - Section 11: Verification Status */}
          <div className="flex flex-wrap gap-4">
            {/* Verification Status */}
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500 dark:text-slate-400">{t('essay.verification')}:</span>
              <VerdictBadge verdict={isUrlResource(verdict) ? 'resource' : verdict.label || 'UNVERIFIABLE'} size="md" />
              {verdict.confidence !== undefined && (
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  {Math.round(verdict.confidence * 100)}% {t('essay.confidence')}
                </span>
              )}
            </div>
            {/* Mapping Status */}
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500 dark:text-slate-400">{t('essay.mapping')}:</span>
              <MappingStatusBadge status={verdict.mapping_status} />
              {verdict.mapping_confidence !== undefined && (
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  {Math.round(verdict.mapping_confidence * 100)}%
                </span>
              )}
            </div>
            {onOverride && (
              <div className="ml-auto">
                <OverrideControls verdict={verdict} onOverride={onOverride} />
              </div>
            )}
          </div>

          {/* Override indicator */}
          {verdict.is_overridden && (
            <div className="flex items-start gap-3 p-4 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-xl">
              <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
                  {t('essay.humanOverrideApplied')}
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
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-3">
              <GitBranch className="h-4 w-4 text-slate-400" />
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                {t('essay.whatWeFound')}
              </span>
            </div>
            <p className="text-sm text-slate-900 dark:text-slate-100 leading-relaxed">
              {getVerdictExplanation(verdict)}
            </p>
          </div>

          {/* Logic Trace - Section 14 */}
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="h-4 w-4 text-slate-400" />
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                {t('essay.howWeCheckedIt')}
              </span>
            </div>
            <div className="space-y-2">
              <LogicTraceStep step="Matched this citation to your bibliography" isComplete />
              {isLocalOnly ? (
                <LogicTraceStep step="Found a saved match in the local library" isComplete />
              ) : (
                <LogicTraceStep step="Searched academic sources for a matching publication" isComplete />
              )}
              <LogicTraceStep step="Compared the title, authors, year, and identifiers" isComplete />
              {triggeredRules.length > 0 && (
                <LogicTraceStep
                  step={triggeredRules.map(getRuleDisplayName).join('. ')}
                  isComplete={verdict.label === 'verified'}
                  isError={verdict.label === 'suspected_hallucination'}
                />
              )}
              <LogicTraceStep
                step={`Result: ${getVerdictDisplayName(verdict.label)}`}
                isComplete
              />
            </div>
          </div>

          {/* Evidence Graph - Section 16: Full visual evidence chain */}
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-4">
              <Network className="h-4 w-4 text-slate-400" />
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                {t('essay.evidenceGraph')}
              </span>
            </div>
            <EvidenceGraph verdict={verdict} />
          </div>

          {/* Triggered Rules */}
          {triggeredRules.length > 0 && (
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  {t('essay.rulesTriggered')}
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
                  {t('essay.mismatchedFields')}
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
                  {t('essay.evidenceSources')} ({matchedSources.length})
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
                  {t('essay.noEvidenceFound')}
                </span>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {t('essay.noEvidenceFoundDesc')}
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
                    {t('essay.domainException')}
                  </p>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                    {t('essay.domainExceptionDesc')}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Style Penalty */}
          {verdict.style_penalty !== undefined && verdict.style_penalty !== 0 && (
            <div className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
              <span className="text-xs text-slate-500 dark:text-slate-400">{t('essay.stylePenalty')}:</span>
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
                  {t('essay.overrideHistory')}
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
