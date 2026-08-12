import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import type {
  ValidationLabel,
  CitationMappingStatus,
  Verdict,
  OverrideRequest,
} from '@/api/client';
import { cn } from '@/lib/utils';
import { RefreshCw } from 'lucide-react';

const LABEL_OPTIONS: { value: ValidationLabel; label: string; color: string }[] = [
  { value: 'verified', label: '✓ Verified', color: 'text-green-700' },
  { value: 'metadata_error', label: '△ Metadata Error', color: 'text-amber-700' },
  { value: 'suspected_hallucination', label: '✗ Suspected', color: 'text-red-700' },
  { value: 'unresolved', label: '— Unresolved', color: 'text-gray-600' },
];

const STATUS_OPTIONS: { value: CitationMappingStatus; label: string }[] = [
  { value: 'matched', label: 'Matched' },
  { value: 'missing_reference', label: 'Missing Ref' },
  { value: 'uncited_reference', label: 'Uncited Ref' },
  { value: 'in_text_mismatch', label: 'Mismatch' },
  { value: 'duplicate_reference', label: 'Duplicate' },
  { value: 'ambiguous_mapping', label: 'Ambiguous' },
  { value: 'style_inconsistent', label: 'Style Issue' },
  { value: 'unresolved', label: 'Unresolved' },
];

function OverrideForm({
  verdict,
  onClose,
  onSubmit,
}: {
  verdict: Verdict;
  onClose: () => void;
  onSubmit: (req: OverrideRequest) => Promise<void>;
}) {
  const [label, setLabel] = useState<ValidationLabel>(verdict.label);
  const [status, setStatus] = useState<CitationMappingStatus>(verdict.mapping_status);
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({ verdict_id: verdict.citation_id, new_label: label, new_mapping_status: status, reason });
      setDone(true);
      setTimeout(onClose, 500);
    } finally {
      setSubmitting(false);
    }
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <form
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
        className="bg-background rounded-xl border shadow-2xl w-full max-w-md mx-4 p-6 space-y-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="override-title"
      >
        <h3 id="override-title" className="text-base font-bold flex items-center gap-2">
          <RefreshCw className="h-4 w-4" />
          Override Citation
        </h3>

        {/* Source label */}
        <div>
          <label className="text-sm font-medium block mb-2">Source Label (Nguồn)</label>
          <div className="grid grid-cols-2 gap-2">
            {LABEL_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setLabel(opt.value)}
                className={cn(
                  'px-3 py-2 border rounded text-sm text-left transition-colors',
                  label === opt.value
                    ? 'border-primary bg-primary/10 font-medium ring-1 ring-primary'
                    : 'hover:bg-muted'
                )}
              >
                <span className={opt.color}>{opt.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Mapping status */}
        <div>
          <label className="text-sm font-medium block mb-2">Mapping Status (Integrity)</label>
          <div className="grid grid-cols-4 gap-1">
            {STATUS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setStatus(opt.value)}
                className={cn(
                  'px-2 py-1.5 border rounded text-xs text-center transition-colors',
                  status === opt.value
                    ? 'border-primary bg-primary/10 font-medium ring-1 ring-primary'
                    : 'hover:bg-muted'
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Reason */}
        <div>
          <label className="text-sm font-medium block mb-1">
            Lý do <span className="text-muted-foreground font-normal">(tùy chọn)</span>
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="VD: Kiểm tra thủ công, tác giả xác nhận..."
            rows={2}
            className="w-full px-3 py-2 border rounded text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm border rounded hover:bg-muted transition-colors"
          >
            Hủy
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {submitting ? 'Đang lưu...' : done ? 'Đã lưu!' : 'Xác nhận ghi đè'}
          </button>
        </div>
      </form>
    </div>,
    document.body
  );
}

export function OverrideControls({
  verdict,
  onOverride,
  className,
}: {
  verdict: Verdict;
  onOverride: (req: OverrideRequest) => Promise<void>;
  className?: string;
}) {
  const [open, setOpen] = useState(false);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open]);

  if (verdict.is_overridden) {
    return (
      <div className={cn('flex items-center gap-1 text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded border border-amber-200', className)}>
        <RefreshCw className="h-3 w-3" />
        <span>Đã ghi đè</span>
        {verdict.override_record && (
          <span className="text-muted-foreground ml-1">
            ({new Date(verdict.override_record.overridden_at).toLocaleString('vi-VN')})
          </span>
        )}
      </div>
    );
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className={cn(
          'flex items-center gap-1 px-2 py-1 text-xs border rounded hover:bg-muted transition-colors',
          className
        )}
        title="Ghi đè verdict"
        aria-label="Ghi đè verdict"
      >
        <RefreshCw className="h-3 w-3" />
        Ghi đè
      </button>

      {open && (
        <OverrideForm
          verdict={verdict}
          onClose={() => setOpen(false)}
          onSubmit={async (req) => {
            await onOverride(req);
          }}
        />
      )}
    </>
  );
}
