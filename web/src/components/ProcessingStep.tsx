import { Check, Loader2, Circle } from 'lucide-react';

/* ============================================================
   SourceLogic — Processing Step Component
   Based on UX/UI Concept Section 6: Processing Screen
   Visual pipeline for verification process
   ============================================================ */

export type StepStatus = 'completed' | 'active' | 'pending' | 'error';

interface Props {
  label: string;
  status: StepStatus;
  details?: string;
  index?: number;
  totalSteps?: number;
}

/* ============================================================
   ProcessingStep Component
   Displays a single step in the verification pipeline
   ============================================================ */
export function ProcessingStep({ label, status, details, index, totalSteps }: Props) {
  const icons = {
    completed: Check,
    active: Loader2,
    pending: Circle,
    error: Circle,
  };

  const styles = {
    completed: {
      icon: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-100 dark:bg-emerald-900/50',
      label: 'text-emerald-700 dark:text-emerald-300',
    },
    active: {
      icon: 'text-indigo-600 dark:text-indigo-400',
      bg: 'bg-indigo-100 dark:bg-indigo-900/50',
      label: 'text-indigo-700 dark:text-indigo-300 font-semibold',
    },
    pending: {
      icon: 'text-slate-400 dark:text-slate-500',
      bg: 'bg-slate-100 dark:bg-slate-800',
      label: 'text-slate-400 dark:text-slate-500',
    },
    error: {
      icon: 'text-red-600 dark:text-red-400',
      bg: 'bg-red-100 dark:bg-red-900/50',
      label: 'text-red-700 dark:text-red-300',
    },
  };

  const Icon = icons[status];
  const s = styles[status];

  return (
    <div className="pipeline-step flex items-center gap-4 group">
      {/* Connector line (for steps after the first) */}
      {index !== undefined && index > 0 && (
        <div
          className={`absolute left-[18px] top-0 w-px h-0 group-first:h-6 group-[&:not(.group-first)]:-mt-6 ${
            status === 'completed' || status === 'active'
              ? 'bg-emerald-300 dark:bg-emerald-700'
              : 'bg-slate-200 dark:bg-slate-700'
          }`}
        />
      )}

      {/* Step indicator */}
      <div
        className={`relative z-10 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 ${s.bg} ${
          status === 'active' ? 'animate-pulse' : ''
        }`}
      >
        {status === 'active' ? (
          <Loader2 className={`h-5 w-5 animate-spin ${s.icon}`} />
        ) : (
          <Icon className={`h-5 w-5 ${s.icon}`} />
        )}
      </div>

      {/* Step content */}
      <div className="flex-1 min-w-0">
        <p className={`text-sm ${s.label} transition-colors`}>{label}</p>
        {details && status === 'active' && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{details}</p>
        )}
      </div>

      {/* Step counter */}
      {index !== undefined && totalSteps !== undefined && (
        <span className="text-xs text-slate-400 dark:text-slate-500 font-mono">
          {index + 1}/{totalSteps}
        </span>
      )}
    </div>
  );
}

/* ============================================================
   ProcessingPipeline Component
   Displays the full verification pipeline
   Section 6: Processing Screen
   ============================================================ */
export interface PipelineStepData {
  label: string;
  details?: string;
  icon?: React.ElementType;
}

interface PipelineProps {
  steps: PipelineStepData[];
  currentStep?: number;
  showCounters?: boolean;
}

export function ProcessingPipeline({ steps, currentStep, showCounters = true }: PipelineProps) {
  const getStepStatus = (index: number): StepStatus => {
    if (currentStep === undefined) {
      // Default behavior: show all as completed up to a certain point
      if (index < Math.floor(steps.length * 0.4)) return 'completed';
      if (index === Math.floor(steps.length * 0.4)) return 'active';
      return 'pending';
    }

    if (index < currentStep) return 'completed';
    if (index === currentStep) return 'active';
    return 'pending';
  };

  return (
    <div className="card p-6">
      <h3 className="font-display text-base font-semibold mb-5 text-slate-900 dark:text-slate-100">
        Verification Pipeline
      </h3>
      <div className="space-y-1">
        {steps.map((step, i) => (
          <ProcessingStep
            key={i}
            label={step.label}
            details={step.details}
            status={getStepStatus(i)}
            index={i}
            totalSteps={showCounters ? steps.length : undefined}
          />
        ))}
      </div>
    </div>
  );
}

/* ============================================================
   Compact Processing Step
   For inline use in cards and summaries
   ============================================================ */
interface CompactStepProps {
  label: string;
  status: StepStatus;
}

export function CompactStep({ label, status }: CompactStepProps) {
  const icons = {
    completed: Check,
    active: Loader2,
    pending: Circle,
    error: Circle,
  };

  const colorMap = {
    completed: 'text-emerald-600 dark:text-emerald-400',
    active: 'text-indigo-600 dark:text-indigo-400',
    pending: 'text-slate-400 dark:text-slate-500',
    error: 'text-red-600 dark:text-red-400',
  };

  const Icon = icons[status];

  return (
    <div className="flex items-center gap-2">
      <Icon
        className={`h-4 w-4 ${colorMap[status]} ${
          status === 'active' ? 'animate-spin' : ''
        }`}
      />
      <span
        className={`text-sm ${
          status === 'completed'
            ? 'text-emerald-700 dark:text-emerald-300'
            : status === 'active'
            ? 'text-indigo-700 dark:text-indigo-300 font-medium'
            : status === 'error'
            ? 'text-red-700 dark:text-red-300'
            : 'text-slate-400 dark:text-slate-500'
        }`}
      >
        {label}
      </span>
    </div>
  );
}

export default ProcessingStep;
