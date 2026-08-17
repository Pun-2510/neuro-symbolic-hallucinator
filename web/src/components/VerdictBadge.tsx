import type { ValidationLabel } from '@/api/client';
import { cn } from '@/lib/utils';
import { CheckCircle, AlertTriangle, XCircle, HelpCircle } from 'lucide-react';

const LABEL_CONFIG: Record<
  ValidationLabel,
  {
    text: string;
    badgeClass: string;
    icon: React.ReactNode;
    bgClass: string;
    textClass: string;
  }
> = {
  verified: {
    text: 'Verified',
    badgeClass: 'verdict-badge-verified',
    bgClass: 'bg-green-500/10',
    textClass: 'text-green-600',
    icon: <CheckCircle className="h-3 w-3" />,
  },
  metadata_error: {
    text: 'Metadata Error',
    badgeClass: 'verdict-badge-metadata-error',
    bgClass: 'bg-amber-500/10',
    textClass: 'text-amber-600',
    icon: <AlertTriangle className="h-3 w-3" />,
  },
  suspected_hallucination: {
    text: 'Suspected',
    badgeClass: 'verdict-badge-suspected',
    bgClass: 'bg-red-500/10',
    textClass: 'text-red-600',
    icon: <XCircle className="h-3 w-3" />,
  },
  unresolved: {
    text: 'Unresolved',
    badgeClass: 'verdict-badge-unresolved',
    bgClass: 'bg-gray-500/10',
    textClass: 'text-gray-500',
    icon: <HelpCircle className="h-3 w-3" />,
  },
};

export function VerdictBadge({
  label,
  className,
  showIcon = true,
}: {
  label: ValidationLabel;
  className?: string;
  showIcon?: boolean;
}) {
  const config = LABEL_CONFIG[label];

  return (
    <span
      className={cn('verdict-badge', config.badgeClass, className)}
      role="status"
      aria-label={config.text}
    >
      {showIcon && (
        <span className={cn('flex-shrink-0', config.textClass)}>
          {config.icon}
        </span>
      )}
      <span className="font-medium">{config.text}</span>
    </span>
  );
}

export function VerdictBadgeCompact({
  label,
  className,
}: {
  label: ValidationLabel;
  className?: string;
}) {
  const config = LABEL_CONFIG[label];

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-semibold',
        config.bgClass,
        config.textClass,
        className
      )}
      role="status"
      aria-label={config.text}
    >
      {label === 'verified' && '✓'}
      {label === 'metadata_error' && '△'}
      {label === 'suspected_hallucination' && '✗'}
      {label === 'unresolved' && '?'}
    </span>
  );
}

export function getLabelText(label: ValidationLabel): string {
  return LABEL_CONFIG[label].text;
}

export function getLabelColor(label: ValidationLabel): string {
  return LABEL_CONFIG[label].textClass;
}
