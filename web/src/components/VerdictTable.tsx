import { useState } from 'react';
import type { Verdict } from '@/api/client';
import { VerdictBadge } from './VerdictBadge';
import { MappingStatusBadge } from './MappingStatusBadge';
import { CitationDetailDrawer } from './CitationDetailDrawer';
import { OverrideControls } from './OverrideControls';

interface VerdictTableProps {
  verdicts: Verdict[];
  onSelect?: (v: Verdict) => void;
  onOverride?: (verdict: Verdict, req: Parameters<typeof import('@/api/client').api.overrideVerdict>[1]) => Promise<void>;
}

export function VerdictTable({ verdicts, onSelect, onOverride }: VerdictTableProps) {
  const [selected, setSelected] = useState<Verdict | null>(null);

  if (verdicts.length === 0) {
    return (
      <p className="text-muted-foreground italic">Không tìm thấy citation nào.</p>
    );
  }

  function handleSelect(v: Verdict) {
    setSelected(v);
    onSelect?.(v);
  }

  return (
    <>
      <div className="rounded-lg border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left font-medium whitespace-nowrap">Citation</th>
                <th className="px-4 py-3 text-left font-medium whitespace-nowrap">Integrity</th>
                <th className="px-4 py-3 text-left font-medium whitespace-nowrap">Source</th>
                <th className="px-4 py-3 text-left font-medium whitespace-nowrap">Confidence</th>
                <th className="px-4 py-3 text-left font-medium hidden md:table-cell">Reasoning</th>
                <th className="px-4 py-3 text-center font-medium">Override</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {verdicts.map((v, i) => (
                <tr
                  key={v.citation_id ?? i}
                  className={`border-t hover:bg-muted/50 transition-colors ${
                    v.is_overridden ? 'bg-amber-50/40' : ''
                  }`}
                >
                  <td className="px-4 py-3 max-w-xs truncate" title={v.citation_raw}>
                    <span className="font-medium">{v.citation_raw}</span>
                  </td>
                  {/* Integrity layer */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <MappingStatusBadge status={v.mapping_status} />
                    {v.mapping_confidence < 0.5 && (
                      <span className="ml-1 text-xs text-muted-foreground">
                        ({(v.mapping_confidence * 100).toFixed(0)}%)
                      </span>
                    )}
                  </td>
                  {/* Source layer */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <VerdictBadge label={v.label} />
                  </td>
                  {/* Confidence */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-gray-100 rounded-full h-1.5">
                        <div
                          className="h-1.5 rounded-full"
                          style={{
                            width: `${(v.confidence * 100).toFixed(0)}%`,
                            backgroundColor:
                              v.confidence >= 0.8
                                ? '#16a34a'
                                : v.confidence >= 0.5
                                ? '#ca8a04'
                                : '#dc2626',
                          }}
                        />
                      </div>
                      <span className="text-xs tabular-nums">
                        {(v.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  {/* Reasoning */}
                  <td className="px-4 py-3 max-w-md hidden md:table-cell">
                    <span className="text-xs text-muted-foreground truncate block" title={v.reasoning}>
                      {v.reasoning}
                    </span>
                  </td>
                  {/* Override */}
                  <td className="px-4 py-3 text-center">
                    {onOverride ? (
                      <OverrideControls
                        verdict={v}
                        onOverride={(req) => onOverride(v, req)}
                      />
                    ) : v.is_overridden ? (
                      <span className="text-xs text-amber-600">↻</span>
                    ) : null}
                  </td>
                  {/* Detail */}
                  <td className="px-4 py-3">
                    <button
                      className="text-primary hover:underline text-sm whitespace-nowrap"
                      onClick={() => handleSelect(v)}
                    >
                      Chi tiết
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {selected && onOverride && (
        <CitationDetailDrawer
          verdict={selected}
          onClose={() => setSelected(null)}
          onOverride={(req) => onOverride(selected, req)}
        />
      )}
      {selected && !onOverride && (
        <CitationDetailDrawer
          verdict={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}
