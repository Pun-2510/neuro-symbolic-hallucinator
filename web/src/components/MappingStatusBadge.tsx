import type { CitationMappingStatus } from '@/api/client';
import { cn } from '@/lib/utils';
import { CheckCircle2, XCircle, AlertTriangle, ArrowLeftRight, Copy, HelpCircle, Minus, FileWarning } from 'lucide-react';

const STATUS_CONFIG: Record<
  CitationMappingStatus,
  {
    text: string;
    bgClass: string;
    textClass: string;
    borderClass: string;
    icon: React.ReactNode;
    shortText: string;
    tooltip: string;  // NEW: explanation tooltip
  }
> = {
  matched: {
    text: 'Matched',
    shortText: 'Match',
    bgClass: 'bg-emerald-50',
    textClass: 'text-emerald-700',
    borderClass: 'border-emerald-200',
    icon: <CheckCircle2 className="h-3 w-3" />,
    tooltip: 'In-text citation đã link đến reference entry ✓',
  },
  missing_reference: {
    text: 'Missing Reference',
    shortText: 'Missing',
    bgClass: 'bg-red-50',
    textClass: 'text-red-700',
    borderClass: 'border-red-200',
    icon: <XCircle className="h-3 w-3" />,
    tooltip: 'In-text citation không tìm thấy reference entry tương ứng ⚠',
  },
  uncited_reference: {
    text: 'Uncited Reference',
    shortText: 'Uncited',
    bgClass: 'bg-amber-50',
    textClass: 'text-amber-700',
    borderClass: 'border-amber-200',
    icon: <FileWarning className="h-3 w-3" />,
    tooltip: 'Reference entry không có in-text citation nào trỏ đến',
  },
  in_text_mismatch: {
    text: 'In-Text Mismatch',
    shortText: 'Mismatch',
    bgClass: 'bg-orange-50',
    textClass: 'text-orange-700',
    borderClass: 'border-orange-200',
    icon: <ArrowLeftRight className="h-3 w-3" />,
    tooltip: 'Citation đã link nhưng thông tin không khớp (tên/tác giả/năm)',
  },
  duplicate_reference: {
    text: 'Duplicate Reference',
    shortText: 'Duplicate',
    bgClass: 'bg-purple-50',
    textClass: 'text-purple-700',
    borderClass: 'border-purple-200',
    icon: <Copy className="h-3 w-3" />,
    tooltip: 'Có 2 reference entries giống nhau',
  },
  ambiguous_mapping: {
    text: 'Ambiguous Mapping',
    shortText: 'Ambiguous',
    bgClass: 'bg-violet-50',
    textClass: 'text-violet-700',
    borderClass: 'border-violet-200',
    icon: <HelpCircle className="h-3 w-3" />,
    tooltip: 'Nhiều reference candidates phù hợp, không chắc chắn',
  },
  style_inconsistent: {
    text: 'Style Inconsistent',
    shortText: 'Style',
    bgClass: 'bg-sky-50',
    textClass: 'text-sky-700',
    borderClass: 'border-sky-200',
    icon: <AlertTriangle className="h-3 w-3" />,
    tooltip: 'Citation style không nhất quán (APA vs IEEE)',
  },
  unresolved: {
    text: 'Unresolved',
    shortText: 'Unresolved',
    bgClass: 'bg-gray-50',
    textClass: 'text-gray-600',
    borderClass: 'border-gray-200',
    icon: <Minus className="h-3 w-3" />,
    tooltip: 'Chưa xác định được trạng thái link',
  },
};

export function MappingStatusBadge({
  status,
  className,
  compact = false,
}: {
  status: CitationMappingStatus;
  className?: string;
  compact?: boolean;
}) {
  const config = STATUS_CONFIG[status];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md text-xs font-medium border transition-all duration-200',
        config.bgClass,
        config.textClass,
        config.borderClass,
        className
      )}
      title={config.tooltip}
      role="status"
      aria-label={config.text}
    >
      <span className="flex-shrink-0">{config.icon}</span>
      {!compact && <span>{config.text}</span>}
    </span>
  );
}

export function MappingStatusBadgePill({
  status,
  className,
}: {
  status: CitationMappingStatus;
  className?: string;
}) {
  const config = STATUS_CONFIG[status];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium transition-all duration-200',
        config.bgClass,
        config.textClass,
        className
      )}
      title={config.tooltip}
      role="status"
      aria-label={config.text}
    >
      <span className="flex-shrink-0">{config.icon}</span>
      <span>{config.shortText}</span>
    </span>
  );
}

export function getMappingStatusColor(status: CitationMappingStatus): string {
  return STATUS_CONFIG[status].textClass;
}

export function getMappingStatusBg(status: CitationMappingStatus): string {
  return STATUS_CONFIG[status].bgClass;
}
