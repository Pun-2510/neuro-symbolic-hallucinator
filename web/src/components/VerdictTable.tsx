import { useState } from 'react';
import type { Verdict, ValidationLabel } from '@/api/client';
import { VerdictBadge } from './VerdictBadge';
import { CitationDetailDrawer } from './CitationDetailDrawer';

export function VerdictTable({ verdicts }: { verdicts: Verdict[] }) {
  const [selected, setSelected] = useState<Verdict | null>(null);

  if (verdicts.length === 0) {
    return (
      <p className="text-muted-foreground italic">Không tìm thấy citation nào.</p>
    );
  }

  return (
    <>
      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Citation</th>
              <th className="px-4 py-3 text-left font-medium">Verdict</th>
              <th className="px-4 py-3 text-left font-medium">Confidence</th>
              <th className="px-4 py-3 text-left font-medium">Lý do</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {verdicts.map((v, i) => (
              <tr key={i} className="border-t hover:bg-muted/50">
                <td className="px-4 py-3 max-w-md truncate" title={v.citation_raw}>
                  {v.citation_raw}
                </td>
                <td className="px-4 py-3">
                  <VerdictBadge label={v.label as ValidationLabel} />
                </td>
                <td className="px-4 py-3">{(v.confidence * 100).toFixed(0)}%</td>
                <td className="px-4 py-3 max-w-md truncate" title={v.reasoning}>
                  {v.reasoning}
                </td>
                <td className="px-4 py-3">
                  <button
                    className="text-primary hover:underline text-sm"
                    onClick={() => setSelected(v)}
                  >
                    Chi tiết
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {selected && (
        <CitationDetailDrawer
          verdict={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}