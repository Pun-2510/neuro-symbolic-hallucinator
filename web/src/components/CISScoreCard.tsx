import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { CheckCircle2, AlertTriangle, AlertCircle, XCircle } from 'lucide-react';

/* ============================================================
   SourceLogic — Citation Integrity Score Card
   Based on UX/UI Concept Section 7: Verification Dashboard
   ============================================================ */

interface CISScoreCardProps {
  cis: number;
  showDetails?: boolean;
}

/* ============================================================
   CIS Status Configuration
   Based on SourceLogic verification coverage thresholds
   ============================================================ */
const getStatus = (score: number, t: TFunction) => {
  if (score >= 90) {
    return {
      label: t('essay.cisExcellent'),
      description: t('essay.cisExcellentDesc'),
      color: 'emerald',
      bg: 'bg-emerald-50 dark:bg-emerald-950/40',
      border: 'border-emerald-200 dark:border-emerald-800',
      text: 'text-emerald-700 dark:text-emerald-300',
      iconBg: 'bg-emerald-100 dark:bg-emerald-900/60',
      icon: CheckCircle2,
    };
  }
  if (score >= 75) {
    return {
      label: t('essay.cisGood'),
      description: t('essay.cisGoodDesc'),
      color: 'green',
      bg: 'bg-green-50 dark:bg-green-950/40',
      border: 'border-green-200 dark:border-green-800',
      text: 'text-green-700 dark:text-green-300',
      iconBg: 'bg-green-100 dark:bg-green-900/60',
      icon: CheckCircle2,
    };
  }
  if (score >= 50) {
    return {
      label: t('essay.cisFair'),
      description: t('essay.cisFairDesc'),
      color: 'amber',
      bg: 'bg-amber-50 dark:bg-amber-950/40',
      border: 'border-amber-200 dark:border-amber-800',
      text: 'text-amber-700 dark:text-amber-300',
      iconBg: 'bg-amber-100 dark:bg-amber-900/60',
      icon: AlertTriangle,
    };
  }
  if (score >= 25) {
    return {
      label: t('essay.cisConcerning'),
      description: t('essay.cisConcerningDesc'),
      color: 'orange',
      bg: 'bg-orange-50 dark:bg-orange-950/40',
      border: 'border-orange-200 dark:border-orange-800',
      text: 'text-orange-700 dark:text-orange-300',
      iconBg: 'bg-orange-100 dark:bg-orange-900/60',
      icon: AlertCircle,
    };
  }
  return {
    label: t('essay.cisCritical'),
    description: t('essay.cisCriticalDesc'),
    color: 'red',
    bg: 'bg-red-50 dark:bg-red-950/40',
    border: 'border-red-200 dark:border-red-800',
    text: 'text-red-700 dark:text-red-300',
    iconBg: 'bg-red-100 dark:bg-red-900/60',
    icon: XCircle,
  };
};

// Progress bar color based on score
const getProgressColor = (score: number) => {
  if (score >= 90) return 'bg-gradient-to-r from-emerald-500 to-emerald-400';
  if (score >= 75) return 'bg-gradient-to-r from-green-500 to-green-400';
  if (score >= 50) return 'bg-gradient-to-r from-amber-500 to-amber-400';
  if (score >= 25) return 'bg-gradient-to-r from-orange-500 to-orange-400';
  return 'bg-gradient-to-r from-red-500 to-red-400';
};

export function CISScoreCard({ cis, showDetails = true }: CISScoreCardProps) {
  const { t } = useTranslation();
  const status = getStatus(cis, t);
  const Icon = status.icon;

  // Calculate progress percentage
  const progressPercent = Math.min(100, Math.max(0, cis));

  return (
    <div className={`card p-6 ring-1 ${status.border} ${status.bg}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex-1">
          <h3 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100 mb-1">
            {t('essay.cisTitle')}
          </h3>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {t('essay.cisSubtitle')}
          </p>
        </div>

        {/* Status Badge */}
        <div className={`
          inline-flex items-center gap-2 px-3 py-1.5 rounded-lg
          ${status.iconBg} ${status.border} border
          ${status.text} font-semibold text-sm
        `}>
          <Icon className="h-4 w-4" />
          {status.label}
        </div>
      </div>

      {/* Score Display */}
      <div className="flex items-end gap-6">
        <div className="flex-1">
          {/* Large score */}
          <div className="flex items-baseline gap-2 mb-4">
            <span className="text-6xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              {cis.toFixed(1)}
            </span>
            <span className="text-xl text-slate-500 dark:text-slate-400">/ 100</span>
          </div>

          {/* Progress bar */}
          <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ease-out ${getProgressColor(cis)}`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Progress markers */}
          <div className="flex justify-between mt-2 text-xs text-slate-500 dark:text-slate-400">
            <span>0</span>
            <span>50</span>
            <span>100</span>
          </div>
        </div>

        {/* Shield Icon */}
        <div className={`
          w-20 h-20 rounded-2xl
          ${status.iconBg} ${status.border} border
          flex items-center justify-center
          shadow-sm
        `}>
          <Icon className={`h-10 w-10 ${status.text}`} />
        </div>
      </div>

      {/* Explanation */}
      {showDetails && (
        <div className="mt-6 pt-4 border-t border-slate-200/80 dark:border-slate-700/80">
          <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
            {status.description}
          </p>
        </div>
      )}
    </div>
  );
}

// Compact version for inline use
export function CISScoreCompact({ cis }: { cis: number }) {
  const getColor = (score: number) => {
    if (score >= 90) return 'text-emerald-600 dark:text-emerald-400';
    if (score >= 75) return 'text-green-600 dark:text-green-400';
    if (score >= 50) return 'text-amber-600 dark:text-amber-400';
    if (score >= 25) return 'text-orange-600 dark:text-orange-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <span className={`font-bold ${getColor(cis)}`}>
      {cis.toFixed(1)}
    </span>
  );
}
