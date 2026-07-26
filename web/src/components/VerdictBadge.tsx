import type { ValidationLabel } from '@/api/client';
import { cn } from '@/lib/utils';

const LABEL_MAP: Record<
  ValidationLabel,
  { text: string; bg: string; symbol: string }
> = {
  verified: { text: 'Verified', bg: 'bg-verdict_verified', symbol: '✓' },
  metadata_error: {
    text: 'Metadata error',
    bg: 'bg-verdict_metadata_error',
    symbol: '△',
  },
  suspected_hallucination: {
    text: 'Suspected hallucination',
    bg: 'bg-verdict_suspected',
    symbol: '✗',
  },
  unresolved: { text: 'Unresolved', bg: 'bg-verdict_unresolved', symbol: '?' },
};

export function VerdictBadge({
  label,
  className,
}: {
  label: ValidationLabel;
  className?: string;
}) {
  const info = LABEL_MAP[label];
  return (
    <span className={cn('verdict-badge', info.bg, className)}>
      <span className="mr-1">{info.symbol}</span>
      {info.text}
    </span>
  );
}

export function getLabelText(label: ValidationLabel): string {
  return LABEL_MAP[label].text;
}