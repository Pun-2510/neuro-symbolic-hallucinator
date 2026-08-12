import type { CitationMappingStatus } from '@/api/client';
import { cn } from '@/lib/utils';

const STATUS_MAP: Record<
  CitationMappingStatus,
  { text: string; bg: string; textColor: string; icon: string }
> = {
  matched: {
    text: 'Matched',
    bg: 'bg-green-100',
    textColor: 'text-green-800',
    icon: '✓',
  },
  missing_reference: {
    text: 'Missing Ref',
    bg: 'bg-red-100',
    textColor: 'text-red-800',
    icon: '✗',
  },
  uncited_reference: {
    text: 'Uncited Ref',
    bg: 'bg-amber-100',
    textColor: 'text-amber-800',
    icon: '△',
  },
  in_text_mismatch: {
    text: 'Mismatch',
    bg: 'bg-orange-100',
    textColor: 'text-orange-800',
    icon: '↔',
  },
  duplicate_reference: {
    text: 'Duplicate',
    bg: 'bg-purple-100',
    textColor: 'text-purple-800',
    icon: '≡',
  },
  ambiguous_mapping: {
    text: 'Ambiguous',
    bg: 'bg-violet-100',
    textColor: 'text-violet-800',
    icon: '?',
  },
  style_inconsistent: {
    text: 'Style Issue',
    bg: 'bg-sky-100',
    textColor: 'text-sky-800',
    icon: '⋕',
  },
  unresolved: {
    text: 'Unresolved',
    bg: 'bg-gray-100',
    textColor: 'text-gray-600',
    icon: '—',
  },
};

export function MappingStatusBadge({
  status,
  className,
}: {
  status: CitationMappingStatus;
  className?: string;
}) {
  const info = STATUS_MAP[status];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium',
        info.bg,
        info.textColor,
        className
      )}
      title={info.text}
    >
      <span>{info.icon}</span>
      {info.text}
    </span>
  );
}

export function getMappingStatusColor(status: CitationMappingStatus): string {
  return STATUS_MAP[status].textColor.replace('text-', '');
}
