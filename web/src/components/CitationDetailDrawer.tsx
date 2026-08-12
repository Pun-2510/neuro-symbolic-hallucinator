import { X, ExternalLink, CheckCircle, AlertTriangle, XCircle, HelpCircle } from 'lucide-react';
import type { Verdict, MatchedSource, ValidationLabel, OverrideRequest } from '@/api/client';
import { VerdictBadge } from './VerdictBadge';
import { MappingStatusBadge } from './MappingStatusBadge';
import { cn } from '@/lib/utils';

const LABEL_ICONS: Record<ValidationLabel, React.ReactNode> = {
  verified: <CheckCircle className="h-4 w-4 text-green-600" />,
  metadata_error: <AlertTriangle className="h-4 w-4 text-amber-600" />,
  suspected_hallucination: <XCircle className="h-4 w-4 text-red-600" />,
  unresolved: <HelpCircle className="h-4 w-4 text-gray-400" />,
};

function SourceBadge({ src }: { src: MatchedSource }) {
  const urlMap: Record<string, string> = {
    crossref: 'https://api.crossref.org/works/',
    openalex: 'https://openalex.org/',
    s2: 'https://www.semanticscholar.org/',
    arxiv: 'https://arxiv.org/',
  };

  const colorMap: Record<string, string> = {
    crossref: 'bg-blue-100 text-blue-800',
    openalex: 'bg-teal-100 text-teal-800',
    s2: 'bg-gray-100 text-gray-800',
    arxiv: 'bg-orange-100 text-orange-800',
  };

  return (
    <div className="border rounded p-3 bg-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={cn('text-xs font-bold px-2 py-0.5 rounded uppercase', colorMap[src.source] ?? 'bg-gray-100')}>
            {src.source}
          </span>
          {src.checked_at && (
            <span className="text-xs text-muted-foreground">
              {new Date(src.checked_at).toLocaleString('vi-VN')}
            </span>
          )}
        </div>
        {src.url && (
          <a
            href={src.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-primary hover:underline"
            title="Open in browser"
          >
            <ExternalLink className="h-3 w-3" />
            Open
          </a>
        )}
      </div>

      {/* Matched fields */}
      {src.matched_fields.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {src.matched_fields.map((field) => (
            <span
              key={field}
              className="px-2 py-0.5 bg-green-50 text-green-700 border border-green-200 rounded text-xs font-mono"
            >
              ✓ {field}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function CitationDetailDrawer({
  verdict,
  onClose,
  onOverride,
}: {
  verdict: Verdict;
  onClose: () => void;
  onOverride?: (req: OverrideRequest) => Promise<void>;
}) {
  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-end md:items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-background rounded-t-xl md:rounded-xl w-full md:max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-background border-b px-6 py-4 flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-bold mb-1">Citation Detail</h2>
            <p className="text-xs text-muted-foreground font-mono truncate" title={verdict.citation_raw}>
              {verdict.citation_raw}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-muted rounded transition-colors shrink-0"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-5 text-sm">
          {/* Two-layer badges */}
          <div className="flex flex-wrap gap-3">
            {/* Source layer */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Source:</span>
              <VerdictBadge label={verdict.label} />
              <span className="text-xs font-medium">
                {(verdict.confidence * 100).toFixed(0)}%
              </span>
            </div>
            {/* Integrity layer */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Integrity:</span>
              <MappingStatusBadge status={verdict.mapping_status} />
              <span className="text-xs font-medium">
                {(verdict.mapping_confidence * 100).toFixed(0)}%
              </span>
            </div>
            {verdict.is_overridden && (
              <span className="flex items-center gap-1 text-xs text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
                <AlertTriangle className="h-3 w-3" />
                Đã ghi đè
              </span>
            )}
          </div>

          {/* Domain exception */}
          {verdict.domain_exception && (
            <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded text-xs">
              <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
              <div>
                <strong>Domain Exception:</strong> DOI matched nhưng title similarity thấp.
                Đây có thể là nguồn hợp lệ trong domain chuyên ngành (ví dụ: bài báo
                conference có metadata khác biệt trên Crossref).
              </div>
            </div>
          )}

          {/* Reasoning */}
          {verdict.reasoning && (
            <div>
              <div className="font-semibold mb-1.5 flex items-center gap-1.5">
                {LABEL_ICONS[verdict.label]}
                Reasoning
              </div>
              <p className="text-muted-foreground leading-relaxed">{verdict.reasoning}</p>
            </div>
          )}

          {/* Triggered rules */}
          {verdict.triggered_rules.length > 0 && (
            <div>
              <div className="font-semibold mb-1.5">Rules triggered</div>
              <div className="flex flex-wrap gap-1.5">
                {verdict.triggered_rules.map((r) => (
                  <span
                    key={r}
                    className="px-2 py-1 bg-muted rounded text-xs font-mono text-indigo-700"
                  >
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Mismatched fields */}
          {verdict.mismatched_fields.length > 0 && (
            <div>
              <div className="font-semibold mb-1.5">Mismatched fields</div>
              <div className="flex flex-wrap gap-1.5">
                {verdict.mismatched_fields.map((f) => (
                  <span
                    key={f}
                    className="px-2 py-1 bg-yellow-50 text-yellow-800 border border-yellow-200 rounded text-xs font-mono"
                  >
                    ✗ {f}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Evidence sources */}
          {verdict.matched_sources.length > 0 && (
            <div>
              <div className="font-semibold mb-2">
                Evidence ({verdict.matched_sources.length} source
                {verdict.matched_sources.length > 1 ? 's' : ''})
              </div>
              <div className="space-y-2">
                {verdict.matched_sources.map((src, i) => (
                  <SourceBadge key={i} src={src} />
                ))}
              </div>
            </div>
          )}

          {/* Style penalty */}
          {verdict.style_penalty !== undefined && verdict.style_penalty !== 0 && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground">Style penalty:</span>
              <span className="font-mono text-amber-600">
                {(verdict.style_penalty * 100).toFixed(1)}%
              </span>
            </div>
          )}

          {/* Override history */}
          {verdict.override_record && (
            <div className="border-t pt-4 mt-4">
              <div className="font-semibold mb-2 text-xs text-muted-foreground uppercase tracking-wider">
                Override History
              </div>
              <div className="text-xs space-y-1">
                <p>
                  <strong>At:</strong>{' '}
                  {new Date(verdict.override_record.overridden_at).toLocaleString('vi-VN')}
                </p>
                {verdict.override_record.previous_label && (
                  <p>
                    <strong>Previous label:</strong>{' '}
                    <VerdictBadge label={verdict.override_record.previous_label} />
                  </p>
                )}
                {verdict.override_record.new_label && (
                  <p>
                    <strong>New label:</strong>{' '}
                    <VerdictBadge label={verdict.override_record.new_label} />
                  </p>
                )}
                {verdict.override_record.reason && (
                  <p className="text-muted-foreground italic">
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
