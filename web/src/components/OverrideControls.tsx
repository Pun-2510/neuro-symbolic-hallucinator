import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';
import type {
  ValidationLabel,
  CitationMappingStatus,
  Verdict,
  OverrideRequest,
} from '@/api/client';
import { cn } from '@/lib/utils';
import { RefreshCw } from 'lucide-react';
import { useRole } from '@/hooks/useRole';
import { useToast } from '@/contexts/ToastContext';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

const LABEL_OPTIONS: { value: ValidationLabel; label: string; color: string }[] = [
  { value: 'verified', label: '✓ Verified', color: 'text-green-700 dark:text-green-400' },
  { value: 'metadata_error', label: '△ Metadata Error', color: 'text-amber-700 dark:text-amber-400' },
  { value: 'suspected_hallucination', label: '✗ Suspected', color: 'text-red-700 dark:text-red-400' },
  { value: 'unresolved', label: '— Unresolved', color: 'text-gray-600 dark:text-slate-400' },
  { value: 'resource', label: '↗ URL Resource', color: 'text-violet-700 dark:text-violet-400' },
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
  const { t } = useTranslation();
  const toast = useToast();
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
      toast.success(t('override.successToast'));
      setDone(true);
      setTimeout(onClose, 500);
    } finally {
      setSubmitting(false);
    }
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <form
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
        className="bg-background rounded-2xl border shadow-2xl w-full max-w-md mx-4 p-6 space-y-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="override-title"
      >
        <h3 id="override-title" className="text-base font-bold flex items-center gap-2">
          <RefreshCw className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          {t('override.title')}
        </h3>

        {/* Source label */}
        <div>
          <Label className="text-sm font-medium block mb-2">{t('override.sourceLabel')}</Label>
          <div className="grid grid-cols-2 gap-2">
            {LABEL_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setLabel(opt.value)}
                className={cn(
                  'px-3 py-2 border rounded-lg text-sm text-left transition-colors',
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
          <Label className="text-sm font-medium block mb-2">{t('override.mappingStatus')}</Label>
          <div className="grid grid-cols-4 gap-1">
            {STATUS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setStatus(opt.value)}
                className={cn(
                  'px-2 py-1.5 border rounded-lg text-xs text-center transition-colors',
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
          <Label className="text-sm font-medium block mb-1">
            {t('override.reason')} <span className="text-muted-foreground font-normal">{t('override.optional')}</span>
          </Label>
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={t('override.reasonPlaceholder')}
            rows={2}
            className="resize-none"
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
          >
            {t('override.cancel')}
          </Button>
          <Button
            type="submit"
            disabled={submitting}
          >
            {submitting ? t('override.saving') : done ? t('override.saved') : t('override.confirm')}
          </Button>
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
  const { t, i18n } = useTranslation();
  const { has } = useRole();
  if (!has('override_verdict')) return null;

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

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className={cn(
          verdict.is_overridden
            ? 'flex items-center gap-1 text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/50 px-2.5 py-1.5 rounded-lg border border-amber-200 dark:border-amber-800 hover:bg-amber-100 dark:hover:bg-amber-900/50 transition-colors'
            : 'flex items-center gap-1 px-2.5 py-1.5 text-xs border rounded-lg hover:bg-muted transition-colors',
          className
        )}
        title={t('override.overrideBtn')}
        aria-label={t('override.overrideBtn')}
      >
        <RefreshCw className="h-3 w-3" />
        <span>{verdict.is_overridden ? t('override.overriddenBtn') : t('override.overrideBtn')}</span>
        {verdict.is_overridden && verdict.override_record && (
          <span className="text-muted-foreground ml-1">
            ({new Date(verdict.override_record.overridden_at).toLocaleString(i18n.language || 'vi-VN')})
          </span>
        )}
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
