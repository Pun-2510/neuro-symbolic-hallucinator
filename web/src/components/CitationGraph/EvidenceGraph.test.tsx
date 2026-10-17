import { describe, it, expect } from 'vitest';
import { buildEvidenceGraph } from './EvidenceGraph';
import type { Verdict } from '@/api/client';

function makeVerdict(overrides: Partial<Verdict> = {}): Verdict {
  return {
    citation_id: 'cite-1',
    citation_raw: 'Smith et al., 2023',
    mapping_status: 'matched',
    mapping_confidence: 0.9,
    label: 'verified',
    confidence: 0.85,
    reasoning: 'Match found',
    triggered_rules: [],
    mismatched_fields: [],
    matched_sources: [
      {
        source: 'crossref',
        matched_fields: ['title', 'year'],
        url: 'https://example.com',
        checked_at: '2026-01-01T00:00:00Z',
      },
    ],
    is_overridden: false,
    domain_exception: false,
    style_penalty: 0,
    ...overrides,
  };
}

describe('buildEvidenceGraph', () => {
  it('returns a reference node at the root', () => {
    const { graph } = buildEvidenceGraph(makeVerdict());
    expect(graph.type).toBe('reference');
    expect(graph.label).toBe('Smith et al., 2023');
    expect(graph.children).toBeDefined();
  });

  it('marks confidence detail as percentage', () => {
    const { graph } = buildEvidenceGraph(makeVerdict());
    expect(graph.detail).toContain('85%');
  });

  it('includes sources / similarity / rules / verdict children', () => {
    const { graph } = buildEvidenceGraph(makeVerdict());
    const ids = graph.children!.map((c) => c.id);
    expect(ids).toEqual(['sources', 'similarity', 'rules', 'verdict']);
  });

  it('marks sources as success when matched_sources present', () => {
    const { graph } = buildEvidenceGraph(makeVerdict());
    const sources = graph.children!.find((c) => c.id === 'sources')!;
    expect(sources.status).toBe('success');
  });

  it('marks sources as no_match when no matched_sources', () => {
    const { graph } = buildEvidenceGraph(makeVerdict({ matched_sources: [] }));
    const sources = graph.children!.find((c) => c.id === 'sources')!;
    expect(sources.status).toBe('no_match');
  });

  it('marks similarity as success when confidence >= 0.7', () => {
    const { graph } = buildEvidenceGraph(makeVerdict({ confidence: 0.85 }));
    const sim = graph.children!.find((c) => c.id === 'similarity')!;
    expect(sim.status).toBe('success');
  });

  it('marks similarity as warning when confidence 0.4-0.7', () => {
    const { graph } = buildEvidenceGraph(makeVerdict({ confidence: 0.5 }));
    const sim = graph.children!.find((c) => c.id === 'similarity')!;
    expect(sim.status).toBe('warning');
  });

  it('marks similarity as error when confidence < 0.4', () => {
    const { graph } = buildEvidenceGraph(makeVerdict({ confidence: 0.2 }));
    const sim = graph.children!.find((c) => c.id === 'similarity')!;
    expect(sim.status).toBe('error');
  });

  it('marks rules as success when none triggered', () => {
    const { graph } = buildEvidenceGraph(makeVerdict({ triggered_rules: [] }));
    const rules = graph.children!.find((c) => c.id === 'rules')!;
    expect(rules.status).toBe('success');
  });

  it('marks rules as warning when triggered', () => {
    const { graph } = buildEvidenceGraph(
      makeVerdict({
        triggered_rules: ['rule_a', 'rule_b'],
        mismatched_fields: ['year', 'venue', 'doi'],
      }),
    );
    const rules = graph.children!.find((c) => c.id === 'rules')!;
    expect(rules.status).toBe('warning');
    expect(rules.children).toBeDefined();
    // 1 rules-list + 3 mismatched fields
    expect(rules.children!.length).toBe(4);
  });

  it('uses verdict label for final node status', () => {
    const { graph } = buildEvidenceGraph(makeVerdict({ label: 'suspected_hallucination' }));
    const verdict = graph.children!.find((c) => c.id === 'verdict')!;
    expect(verdict.status).toBe('error');
  });

  it('reports localOnly when only internal cache paths matched', () => {
    const { isLocalOnly } = buildEvidenceGraph(
      makeVerdict({
        matched_sources: [
          {
            source: 'local_db',
            matched_fields: ['title'],
            checked_at: '2026-01-01T00:00:00Z',
          },
        ],
      }),
    );
    expect(isLocalOnly).toBe(true);
  });

  it('reports not localOnly when external APIs were queried', () => {
    const { isLocalOnly } = buildEvidenceGraph(makeVerdict());
    expect(isLocalOnly).toBe(false);
  });
});
