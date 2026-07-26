import type { CIS } from '@/api/client';

export function CISScoreCard({ cis }: { cis: CIS }) {
  const score = cis.score;
  const color =
    score >= 80 ? '#16a34a' : score >= 60 ? '#ca8a04' : score >= 40 ? '#f59e0b' : '#dc2626';

  return (
    <div className="rounded-lg border p-6 bg-card">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold">Citation Integrity Score</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Đo lường độ tin cậy trích dẫn — <strong>KHÔNG phải điểm tiểu luận</strong>
          </p>
        </div>
        <div className="text-4xl font-bold" style={{ color }}>
          {score.toFixed(1)}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
        {Object.entries(cis.components).map(([k, v]) => (
          <div key={k} className="p-2 bg-muted rounded">
            <div className="font-mono text-muted-foreground">{k}</div>
            <div className="font-bold">{(v * 100).toFixed(0)}%</div>
            <div className="text-muted-foreground">
              w={((cis.weights_used[k] ?? 0) * 100).toFixed(0)}%
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 text-xs text-muted-foreground">
        Tổng {cis.num_citations} citation · {cis.num_unresolved} unresolved
      </div>
    </div>
  );
}