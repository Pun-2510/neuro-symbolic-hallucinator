/**
 * ConfirmationModal — Accessible confirmation dialog built on Radix UI Dialog.
 *
 * Replaces native `window.confirm()` so destructive actions follow the design
 * system (toast + dialog ARIA + focus trap + Escape close).
 *
 * Usage:
 *   <ConfirmationModal
 *     isOpen={open}
 *     title="Delete this document?"
 *     message="This cannot be undone."
 *     confirmLabel="Delete"
 *     variant="danger"
 *     onConfirm={async () => { await api.delete(); }}
 *     onCancel={() => setOpen(false)}
 *   />
 */
import * as Dialog from '@radix-ui/react-dialog';
import { AlertTriangle, X } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface ConfirmationModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** "danger" tints the confirm button red; "default" uses indigo. */
  variant?: 'default' | 'danger';
  onConfirm: () => void | Promise<void>;
  onCancel: () => void;
}

export function ConfirmationModal({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  onConfirm,
  onCancel,
}: ConfirmationModalProps) {
  const [submitting, setSubmitting] = useState(false);

  const handleConfirm = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      await onConfirm();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onCancel()}>
      <Dialog.Portal>
        <Dialog.Overlay
          className={cn(
            'fixed inset-0 z-50 bg-black/40 backdrop-blur-sm',
            'data-[state=open]:animate-fadeIn',
            'data-[state=closed]:animate-fadeOut'
          )}
        />
        <Dialog.Content
          className={cn(
            'fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2',
            'w-full max-w-md p-6 rounded-2xl bg-white dark:bg-slate-900',
            'border border-slate-200 dark:border-slate-700 shadow-2xl',
            'data-[state=open]:animate-fadeIn'
          )}
          onEscapeKeyDown={onCancel}
          onPointerDownOutside={onCancel}
        >
          <div className="flex items-start gap-4">
            {variant === 'danger' && (
              <div
                className="shrink-0 w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center"
                aria-hidden="true"
              >
                <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <Dialog.Title className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                {title}
              </Dialog.Title>
              <Dialog.Description className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                {message}
              </Dialog.Description>
            </div>
            <Dialog.Close
              className="shrink-0 p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label="Close"
              onClick={onCancel}
            >
              <X className="h-4 w-4" />
            </Dialog.Close>
          </div>

          <div className="mt-6 flex justify-end gap-2">
            <button
              type="button"
              onClick={onCancel}
              disabled={submitting}
              className="px-4 py-2 text-sm font-medium rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
            >
              {cancelLabel}
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={submitting}
              className={cn(
                'px-4 py-2 text-sm font-medium rounded-lg text-white transition-colors disabled:opacity-50',
                variant === 'danger'
                  ? 'bg-red-600 hover:bg-red-700'
                  : 'bg-indigo-600 hover:bg-indigo-700'
              )}
            >
              {submitting ? 'Working...' : confirmLabel}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
