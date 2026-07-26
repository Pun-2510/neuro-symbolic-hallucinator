import { X } from 'lucide-react';
import type { Verdict } from '@/api/client';
import { VerdictBadge } from './VerdictBadge';

export function CitationDetailDrawer({
  verdict,
  onClose,
}: {
  verdict: Verdict;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-end md:items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-background rounded-t-lg md:rounded-lg w-full md:max-w-2xl max-h-[85vh] overflow-y-auto p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-lg font-bold">Citation Detail</h2>
          <button onClick={onClose} aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4 text-sm">
          <div>
            <div className="text-muted-foreground mb-1">Raw text</div>
            <div className="p-2 bg-muted rounded font-mono">{verdict.citation_raw}</div>
          </div>

          <div className="flex items-center gap-4">
            <VerdictBadge label={verdict.label} />
            <span>
              Confidence: <strong>{(verdict.confidence * 100).toFixed(0)}%</strong>
            </span>
          </div>

          <div>
            <div className="text-muted-foreground mb-1">Reasoning</div>
            <p>{verdict.reasoning}</p>
          </div>

          {verdict.triggered_rules.length > 0 && (
            <div>
              <div className="text-muted-foreground mb-1">Rules triggered</div>
              <div className="flex flex-wrap gap-1">
                {verdict.triggered_rules.map((r) => (
                  <span key={r} className="px-2 py-1 bg-muted rounded text-xs font-mono">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}

          {verdict.mismatched_fields.length > 0 && (
            <div>
              <div className="text-muted-foreground mb-1">Mismatched fields</div>
              <div className="flex flex-wrap gap-1">
                {verdict.mismatched_fields.map((f) => (
                  <span
                    key={f}
                    className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs"
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}

          {Object.keys(verdict.matched_sources).length > 0 && (
            <div>
              <div className="text-muted-foreground mb-1">Features</div>
              <pre className="p-2 bg-muted rounded text-xs overflow-x-auto">
                {JSON.stringify(verdict.matched_sources, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}