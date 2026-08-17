import type { CIS } from '@/api/client';
import { cn } from '@/lib/utils';
import { Shield, Info, TrendingUp } from 'lucide-react';

interface CISScoreCardProps {
  cis: CIS;
}

export function CISScoreCard({ cis }: CISScoreCardProps) {
  const score = cis.score;
  const scoreColor = score >= 80 ? 'text-emerald-600' : score >= 60 ? 'text-amber-600' : 'text-red-600';
  const scoreBg = score >= 80 ? 'bg-emerald-50' : score >= 60 ? 'bg-amber-50' : 'bg-red-50';

  const componentEntries = Object.entries(cis.components);
  const maxValue = Math.max(...Object.values(cis.components), 0.01);

  return (
    <div className="card-elevated p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10">
            <Shield className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">Citation Integrity Score</h3>
            <p className="text-sm text-muted-foreground flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5" />
              Đo lường độ tin cậy trích dẫn học thuật
            </p>
          </div>
        </div>

        {/* Score Display */}
        <div className={cn('flex flex-col items-center px-6 py-4 rounded-2xl', scoreBg)}>
          <span className={cn('text-4xl font-bold tracking-tight', scoreColor)}>
            {score.toFixed(1)}
          </span>
          <span className="text-xs text-muted-foreground font-medium">/ 100</span>
        </div>
      </div>

      {/* Component Bars */}
      <div className="space-y-3 mb-6">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-foreground">Thành phần đánh giá</span>
          <span className="text-xs text-muted-foreground">Trọng số</span>
        </div>
        {componentEntries.map(([key, value]) => {
          const weight = cis.weights_used[key] ?? 0;
          const barWidth = (value / maxValue) * 100;
          const barColor = value >= 0.8 ? 'bg-emerald-500' : value >= 0.6 ? 'bg-amber-500' : 'bg-red-500';

          return (
            <div key={key} className="group">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-mono text-muted-foreground capitalize">
                  {key.replace(/_/g, ' ')}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-semibold text-foreground">
                    {(value * 100).toFixed(0)}%
                  </span>
                  <span className="text-xs text-muted-foreground w-8 text-right">
                    {(weight * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className={cn('absolute inset-y-0 left-0 rounded-full transition-all duration-700 ease-out', barColor)}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer Stats */}
      <div className="flex items-center justify-between pt-4 border-t border-border/50">
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Tổng citations:</span>
            <span className="font-semibold text-foreground">{cis.num_citations}</span>
          </div>
          {cis.num_unresolved > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Unresolved:</span>
              <span className="font-semibold text-amber-600">{cis.num_unresolved}</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <TrendingUp className="h-3.5 w-3.5" />
          <span>Không phải điểm tiểu luận</span>
        </div>
      </div>
    </div>
  );
}
