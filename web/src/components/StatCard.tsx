import type { LucideIcon } from 'lucide-react';

type Color = 'indigo' | 'green' | 'amber' | 'violet' | 'rose' | 'slate';

const COLOR_MAP: Record<Color, { bg: string; text: string; ring: string }> = {
  indigo: { bg: 'bg-indigo-50 dark:bg-indigo-950', text: 'text-indigo-600 dark:text-indigo-400', ring: 'ring-indigo-200 dark:ring-indigo-800' },
  green:  { bg: 'bg-emerald-50 dark:bg-emerald-950', text: 'text-emerald-600 dark:text-emerald-400', ring: 'ring-emerald-200 dark:ring-emerald-800' },
  amber:  { bg: 'bg-amber-50 dark:bg-amber-950', text: 'text-amber-600 dark:text-amber-400', ring: 'ring-amber-200 dark:ring-amber-800' },
  violet: { bg: 'bg-violet-50 dark:bg-violet-950', text: 'text-violet-600 dark:text-violet-400', ring: 'ring-violet-200 dark:ring-violet-800' },
  rose:   { bg: 'bg-rose-50 dark:bg-rose-950', text: 'text-rose-600 dark:text-rose-400', ring: 'ring-rose-200 dark:ring-rose-800' },
  slate:  { bg: 'bg-slate-50 dark:bg-slate-900', text: 'text-slate-600 dark:text-slate-400', ring: 'ring-slate-200 dark:ring-slate-800' },
};

export interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  color?: Color;
  hint?: string;
}

export function StatCard({ label, value, icon: Icon, color = 'indigo', hint }: StatCardProps) {
  const c = COLOR_MAP[color];
  return (
    <div className={`rounded-xl ring-1 ${c.ring} bg-white dark:bg-slate-900 p-5`}>
      <div className="flex items-start gap-3">
        {Icon && (
          <div className={`w-10 h-10 rounded-lg ${c.bg} flex items-center justify-center`}>
            <Icon className={`h-5 w-5 ${c.text}`} />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">{label}</p>
          <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
          {hint && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
        </div>
      </div>
    </div>
  );
}
