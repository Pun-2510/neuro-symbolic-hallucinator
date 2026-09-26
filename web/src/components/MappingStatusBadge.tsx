import { Link, Unlink, AlertTriangle, CheckCircle, XCircle, HelpCircle } from 'lucide-react';

// Mapping status types based on UX/UI concept
export type MappingStatus =
  | 'matched'
  | 'missing_reference'
  | 'uncited_reference'
  | 'in_text_mismatch'
  | 'duplicate_reference'
  | 'ambiguous_mapping'
  | 'style_inconsistent'
  | 'unresolved';

interface Props {
  status: MappingStatus | string;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

// Mapping status configuration based on SourceLogic design system
const config: Record<string, { label: string; className: string; Icon: typeof Link }> = {
  matched: {
    label: 'Linked',
    className: 'mapping-badge-matched',
    Icon: CheckCircle
  },
  missing_reference: {
    label: 'No Reference',
    className: 'mapping-badge-missing',
    Icon: Unlink
  },
  uncited_reference: {
    label: 'Not Cited',
    className: 'mapping-badge-uncited',
    Icon: AlertTriangle
  },
  in_text_mismatch: {
    label: 'Mismatch',
    className: 'mapping-badge-mismatch',
    Icon: XCircle
  },
  duplicate_reference: {
    label: 'Duplicate',
    className: 'mapping-badge-duplicate',
    Icon: AlertTriangle
  },
  ambiguous_mapping: {
    label: 'Ambiguous',
    className: 'mapping-badge-ambiguous',
    Icon: HelpCircle
  },
  style_inconsistent: {
    label: 'Style Issue',
    className: 'mapping-badge-style',
    Icon: AlertTriangle
  },
  unresolved: {
    label: 'Unresolved',
    className: 'mapping-badge-unresolved',
    Icon: Unlink
  },
  // Legacy mappings
  MATCHED: { label: 'Linked', className: 'mapping-badge-matched', Icon: CheckCircle },
  MISSING: { label: 'No Reference', className: 'mapping-badge-missing', Icon: Unlink },
  UNCITED: { label: 'Not Cited', className: 'mapping-badge-uncited', Icon: AlertTriangle },
  MISMATCH: { label: 'Mismatch', className: 'mapping-badge-mismatch', Icon: XCircle },
  UNRESOLVED: { label: 'Unresolved', className: 'mapping-badge-unresolved', Icon: Unlink },
};

const sizeClasses = {
  sm: 'text-[10px] px-2 py-0.5 gap-1',
  md: 'text-xs px-2.5 py-1 gap-1.5',
  lg: 'text-sm px-3 py-1.5 gap-2',
};

export function MappingStatusBadge({ status, showIcon = true, size = 'md' }: Props) {
  const entry = config[status] || config.unresolved;
  const { label, className, Icon } = entry;

  return (
    <span className={`mapping-badge ${className} ${sizeClasses[size]}`}>
      {showIcon && <Icon className="h-3 w-3" />}
      {label}
    </span>
  );
}

// Compact version for inline use
export function MappingStatusBadgeCompact({ status }: { status: MappingStatus | string }) {
  const entry = config[status] || config.unresolved;
  const { className, Icon } = entry;

  return (
    <span
      className={`mapping-badge ${className} w-6 h-6 flex items-center justify-center`}
      title={entry.label}
    >
      <Icon className="h-3 w-3" />
    </span>
  );
}
