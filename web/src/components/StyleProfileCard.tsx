import type { StyleProfile } from '@/api/client';
import { cn } from '@/lib/utils';
import { BookOpen, Code, AlertTriangle, HelpCircle } from 'lucide-react';

const STYLE_CONFIG: Record<
  StyleProfile['style'],
  { label: string; color: string; bg: string; icon: React.ReactNode; desc: string }
> = {
  APA_LIKE: {
    label: 'APA-Like',
    color: 'text-blue-700 dark:text-blue-300',
    bg: 'bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800',
    icon: <BookOpen className="h-4 w-4 text-blue-600 dark:text-blue-400" />,
    desc: 'Nhóm tác giả theo (Author, Year) — phổ biến trong KHXH & Khoa học tự nhiên.',
  },
  IEEE_LIKE: {
    label: 'IEEE-Like',
    color: 'text-green-700 dark:text-green-300',
    bg: 'bg-green-50 dark:bg-green-950/40 border-green-200 dark:border-green-800',
    icon: <Code className="h-4 w-4 text-green-600 dark:text-green-400" />,
    desc: 'Đánh số [1], [2] — phổ biến trong Kỹ thuật & CNTT.',
  },
  MIXED: {
    label: 'Mixed',
    color: 'text-amber-700 dark:text-amber-300',
    bg: 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800',
    icon: <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />,
    desc: 'Cả APA lẫn IEEE trong cùng 1 essay — cần kiểm tra consistency.',
  },
  UNKNOWN: {
    label: 'Unknown',
    color: 'text-gray-600 dark:text-slate-300',
    bg: 'bg-gray-50 dark:bg-slate-800/60 border-gray-200 dark:border-slate-700',
    icon: <HelpCircle className="h-4 w-4 text-gray-500 dark:text-slate-400" />,
    desc: 'Không xác định được style chính — có thể citation quá ít.',
  },
};

export function StyleProfileCard({
  profile,
}: {
  profile: StyleProfile;
}) {
  const cfg = STYLE_CONFIG[profile.style as keyof typeof STYLE_CONFIG] ?? STYLE_CONFIG.UNKNOWN;
  const confPct = (profile.confidence * 100).toFixed(0);

  return (
    <div className={cn('rounded-lg border p-4', cfg.bg)}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {cfg.icon}
          <h3 className={cn('text-base font-bold', cfg.color)}>
            Style: {cfg.label}
          </h3>
          {profile.style === 'MIXED' && (
            <span className="text-xs px-2 py-0.5 bg-amber-200 dark:bg-amber-900 text-amber-900 dark:text-amber-200 rounded font-medium">
              ⚠ Cảnh báo
            </span>
          )}
        </div>
        <div className="text-right">
          <span className={cn('text-2xl font-bold', cfg.color)}>
            {confPct}%
          </span>
          <p className="text-xs text-muted-foreground">confidence</p>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-2 mb-3">
        <div
          className="h-2 rounded-full transition-all"
          style={{
            width: `${confPct}%`,
            backgroundColor: cfg.color.includes('blue')
              ? '#2563eb'
              : cfg.color.includes('green')
              ? '#16a34a'
              : cfg.color.includes('amber')
              ? '#d97706'
              : '#6b7280',
          }}
        />
      </div>

      {/* Style ratios from evidence */}
      <div className="flex gap-4 text-xs mb-2 flex-wrap">
        {profile.ratios && Object.keys(profile.ratios).length > 0 ? (
          <>
            <span className="text-blue-700 dark:text-blue-400">
              <strong>{((profile.ratios.apa_combined ?? 0) * 100).toFixed(0)}%</strong> APA
            </span>
            <span className="text-green-700 dark:text-green-400">
              <strong>{((profile.ratios.ieee_combined ?? 0) * 100).toFixed(0)}%</strong> IEEE
            </span>
            <span className="text-gray-600 dark:text-slate-400">
              <strong>{((profile.ratios.body_apa ?? 0) * 100).toFixed(0)}%</strong> body APA
            </span>
            <span className="text-gray-600 dark:text-slate-400">
              <strong>{((profile.ratios.bib_apa ?? 0) * 100).toFixed(0)}%</strong> bib APA
            </span>
          </>
        ) : (
          <>
            <span className="text-blue-700 dark:text-blue-400">
              <strong>{profile.apa_count}</strong> APA
            </span>
            <span className="text-green-700 dark:text-green-400">
              <strong>{profile.ieee_count}</strong> IEEE
            </span>
            <span className="text-amber-700 dark:text-amber-400">
              <strong>{profile.mixed_count}</strong> mixed
            </span>
          </>
        )}
      </div>

      {/* Explanation */}
      <p className="text-xs text-muted-foreground leading-relaxed">
        {profile.explanation}
      </p>

      {/* Key features */}
      {Object.keys(profile.features).length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {Object.entries(profile.features)
            .filter(([, v]) => v === true)
            .slice(0, 5)
            .map(([k]) => (
              <span
                key={k}
                className="px-1.5 py-0.5 bg-white/70 dark:bg-slate-800 rounded text-xs text-gray-700 dark:text-slate-300 font-mono"
              >
                {k}
              </span>
            ))}
        </div>
      )}
    </div>
  );
}
