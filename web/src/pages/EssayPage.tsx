import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api, type Verdict, type CitationLink } from '@/api/client';
import { CISScoreCard } from '@/components/CISScoreCard';
import { VerdictTable } from '@/components/VerdictTable';
import { CitationDetailDrawer } from '@/components/CitationDetailDrawer';
import { EssayHeader } from './essay/EssayHeader';
import { EssayActionBar } from './essay/EssayActionBar';
import { EssayTabNav, type EssayTab } from './essay/EssayTabNav';
import { EssayStatsGrid } from './essay/EssayStatsGrid';
import { isUrlResource } from '@/lib/verdictExplanation';
import { useEssayReport, useOverrideVerdict } from '@/hooks/useEssayReport';
import { Loader2, AlertCircle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

/* ============================================================
   SourceLogic — Essay/Report Page Component
   Based on UX/UI Concept Section 7-8: Dashboard + Citations & References
   ============================================================ */

export function EssayPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const numericId = id ? parseInt(id, 10) : null;
  const essayId = numericId !== null && !Number.isNaN(numericId) && numericId > 0
    ? numericId
    : null;
  const { data: report, isLoading, error } = useEssayReport(essayId);
  const overrideMutation = useOverrideVerdict();
  const [selected, setSelected] = useState<Verdict | null>(null);
  const [activeTab, setActiveTab] = useState<EssayTab>('overview');

  const errorMessage =
    essayId === null
      ? t('essay.invalidEssayId')
      : error
        ? (error instanceof Error ? error.message : t('essay.failedLoadReport'))
        : null;

  async function handleOverride(verdict: Verdict, req: Parameters<typeof api.overrideVerdict>[1]) {
    const targetEssayId = report?.essay_id ?? essayId ?? 0;
    const updated = await overrideMutation.mutateAsync({
      essayId: targetEssayId,
      verdictId: verdict.citation_id,
      req,
    });
    if (selected && selected.citation_id === verdict.citation_id) {
      setSelected({
        ...selected,
        label: updated?.label ?? req.new_label,
        mapping_status: updated?.mapping_status ?? req.new_mapping_status ?? selected.mapping_status,
        is_overridden: true,
      });
    }
  }

  if (errorMessage) {
    return (
      <Alert variant="destructive" className="card p-6">
        <AlertCircle className="h-5 w-5" />
        <AlertTitle className="font-medium">{t('common.error')}: {errorMessage}</AlertTitle>
        <AlertDescription>
          <Link to="/history" className="text-indigo-600 dark:text-indigo-400 hover:underline mt-2 inline-block">
            {t('essay.backToReports')}
          </Link>
        </AlertDescription>
      </Alert>
    );
  }

  if (!report) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 text-indigo-600 dark:text-indigo-400 animate-spin" />
        <span className="ml-3 text-slate-600 dark:text-slate-400">
          {isLoading ? t('essay.loadingReport') : t('essay.waitingForAnalysis')}
        </span>
      </div>
    );
  }

  // Calculate stats based on UX/UI Concept
  const academicVerdicts = report.verdicts.filter((v) => !isUrlResource(v));
  const references = report.references ?? [];
  const extractedInText = report.extracted_citations ?? [];

  const linksOf = (c: { citation_links?: CitationLink[]; citation_link?: CitationLink }) =>
    c.citation_links?.length ? c.citation_links : c.citation_link ? [c.citation_link] : [];

  const refIds = (c: { citation_links?: CitationLink[]; citation_link?: CitationLink }) =>
    linksOf(c)
      .map((l) => l.reference_id)
      .filter((id): id is string => Boolean(id));

  const verdictByRefId = new Map(
    (report.verdicts ?? []).flatMap((v) =>
      refIds(v).map((refId) => [refId, v] as const)
    )
  );

  const inTextGroups = new Map<
    string,
    { citation: (typeof extractedInText)[number]; occurrences: number; refIds: string[] }
  >();
  for (const citation of extractedInText) {
    const key = citation.raw_text.trim();
    const existing = inTextGroups.get(key);
    if (existing) {
      existing.occurrences += 1;
      for (const refId of refIds(citation)) {
        if (!existing.refIds.includes(refId)) existing.refIds.push(refId);
      }
      if (linksOf(existing.citation).length === 0 && linksOf(citation).length > 0) {
        existing.citation = citation;
      }
    } else {
      inTextGroups.set(key, {
        citation,
        occurrences: 1,
        refIds: refIds(citation),
      });
    }
  }
  const dedupedInText = Array.from(inTextGroups.values());

  const refByLinkId = new Map<string, (typeof references)[number]>();
  references.forEach((ref, idx) => {
    refByLinkId.set(`ref-${String(idx + 1).padStart(4, '0')}`, ref);
  });

  // Parse author names from citation
  const parseAuthorDisplay = (rawText: string): string => {
    const etAlMatch = rawText.match(/(\w+)\s*(?:et\.?\s*al\.?)/i);
    if (etAlMatch) return etAlMatch[1] + ' et al.';
    const andMatch = rawText.match(/(\w+)\s*&\s*(\w+)/i);
    if (andMatch) return `${andMatch[1]} & ${andMatch[2]}`;
    const parenMatch = rawText.match(/\(([^)]+)\)/);
    if (parenMatch) return parenMatch[1].split(',')[0].trim();
    return rawText.slice(0, 40);
  };

  // Extract year from citation
  const parseYear = (rawText: string): string | null => {
    const yearMatch = rawText.match(/\(?(19|20)\d{2}[a-z]?\)?/);
    return yearMatch ? yearMatch[0].replace(/[()]/g, '') : null;
  };

  /** "Ref #3 — World Health Organization (2023)" for a linked in-text row. */
  const formatLinkedReference = (refIds: string[]): string | null => {
    if (refIds.length === 0) return null;
    const parts = refIds.map((refId) => {
      const num = Number.parseInt(refId.replace(/^ref-/, ''), 10);
      const ref = refByLinkId.get(refId);
      if (!ref || Number.isNaN(num)) return refId;
      const author = ref.authors?.length
        ? ref.authors[0].split(',')[0].trim()
        : parseAuthorDisplay(ref.raw_text);
      const year = ref.year || parseYear(ref.raw_text);
      return `Ref #${num} — ${author}${year ? ` (${year})` : ''}`;
    });
    return parts.join(' · ');
  };

  const inTextVerdicts =
    extractedInText.length > 0
      ? extractedInText.map((citation) => {
          const mappingStatus = citation.mapping_status ?? 'matched';
          const linkedRefIds = refIds(citation);
          const linkedVerdict =
            linkedRefIds.map((id) => verdictByRefId.get(id)).find(Boolean) ?? null;
          return {
            citation_id: `c${citation.id ?? citation.raw_text}`,
            citation_raw: citation.raw_text,
            citation_type: citation.citation_type,
            mapping_status: mappingStatus,
            mapping_confidence: citation.mapping_confidence ?? 0,
            label: linkedVerdict?.label
              ?? (mappingStatus === 'matched' ? 'verified' : 'unresolved'),
            confidence: citation.mapping_confidence ?? citation.confidence,
            reasoning: linkedVerdict?.reasoning ?? '',
            triggered_rules: linkedVerdict?.triggered_rules ?? [],
            mismatched_fields: linkedVerdict?.mismatched_fields ?? [],
            matched_sources: linkedVerdict?.matched_sources ?? [],
            citation_links: linksOf(citation),
            citation_link: citation.citation_link ?? linksOf(citation)[0],
            is_overridden: false,
          };
        })
      : report.verdicts.filter(
          (v) =>
            v.citation_type === 'in_text' ||
            v.citation_type === 'numeric' ||
            (!v.citation_type && references.length === 0)
        );
  const stats = {
    total: academicVerdicts.length,
    verified: academicVerdicts.filter((v) => v.label === 'verified').length,
    metadataError: academicVerdicts.filter((v) => v.label === 'metadata_error').length,
    suspectedHallucination: academicVerdicts.filter((v) => v.label === 'suspected_hallucination').length,
    unverifiable: academicVerdicts.filter((v) => v.label === 'unresolved').length,
  };

  const coverage = stats.total > 0 ? Math.round((stats.verified / stats.total) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Header - Section 7 */}
      <EssayHeader
        essayId={report.essay_id}
        filename={report.filename}
        numPages={report.num_pages}
        numCitations={report.num_citations}
        styleName={report.style_profile?.style}
      />

      {/* Stats Overview - Section 7 */}
      <EssayStatsGrid
        total={stats.total}
        verified={stats.verified}
        metadataError={stats.metadataError}
        suspectedHallucination={stats.suspectedHallucination}
        coverage={coverage}
      />

      {/* CIS Score */}
      {academicVerdicts.length > 0 && <CISScoreCard cis={report.cis.score} />}

      {/* Quick Links - Section 7: Report navigation */}
      <EssayActionBar essayId={id ?? ''} />

      {/* Section 8: Tab Navigation - Citations & References */}
      <EssayTabNav
        activeTab={activeTab}
        onChange={setActiveTab}
        citationsCount={dedupedInText.length}
        referencesCount={references.length}
      />

      {/* Section 8: Citations Tab */}
      {activeTab === 'citations' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100">
              {t('essay.citationsTab')}
            </h2>
            <span className="text-sm text-slate-500 dark:text-slate-400">
              {dedupedInText.length} {t('essay.unique')} ·{' '}
              {dedupedInText.reduce((sum, g) => sum + g.occurrences, 0)} {t('essay.occurrences')}
            </span>
          </div>

          <Card className="p-0 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <TableHead className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    {t('essay.citation')}
                  </TableHead>
                  <TableHead className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    {t('essay.linkedReference')}
                  </TableHead>
                  <TableHead className="text-center px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    {t('essay.status')}
                  </TableHead>
                  <TableHead className="text-center px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider w-16">
                    {t('essay.action')}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="divide-y divide-slate-100 dark:divide-slate-800">
                {dedupedInText.map((group, index) => {
                  const verdict = inTextVerdicts.find(
                    (v) => v.citation_id === `c${group.citation.id ?? group.citation.raw_text}`
                  );
                  if (!verdict) return null;
                  return (
                    <TableRow
                      key={group.citation.id ?? `${group.citation.raw_text}-${index}`}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors"
                    >
                      <TableCell className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-slate-400 dark:text-slate-500">
                            [{index + 1}]
                          </span>
                          <span className="text-sm text-slate-700 dark:text-slate-300 line-clamp-2">
                            {group.citation.raw_text}
                          </span>
                          {group.occurrences > 1 && (
                            <Badge
                              variant="secondary"
                              className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
                              title={`Xuất hiện ${group.occurrences} lần trong bài`}
                            >
                              ×{group.occurrences}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="px-4 py-3">
                        <span className="text-sm text-slate-600 dark:text-slate-400">
                          {(() => {
                            const linked = formatLinkedReference(group.refIds);
                            if (linked) return linked;
                            if (verdict.mapping_status === 'missing_reference') {
                              return t('essay.noReference');
                            }
                            return '—';
                          })()}
                        </span>
                      </TableCell>
                      <TableCell className="px-4 py-3 text-center">
                        {verdict.label === 'verified' ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            {t('essay.linked')}
                          </span>
                        ) : verdict.label === 'metadata_error' ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600 dark:text-amber-400">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            {t('essay.metadataIssue')}
                          </span>
                        ) : verdict.label === 'suspected_hallucination' ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600 dark:text-red-400">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                            {t('essay.hallucination')}
                          </span>
                        ) : verdict.label === 'resource' ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-violet-600 dark:text-violet-400">
                            {t('essay.urlResource')}
                          </span>
                        ) : verdict.mapping_status === 'missing_reference' ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-orange-600 dark:text-orange-400">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            {t('essay.noReferenceShort')}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                            {t('essay.unverifiable')}
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="px-4 py-3 text-center">
                        <Button
                          variant="link"
                          size="sm"
                          onClick={() => setSelected(verdict)}
                          className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 text-sm font-medium h-auto p-0"
                        >
                          {t('common.view')}
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}

      {/* Section 8: References Tab */}
      {activeTab === 'references' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100">
              {t('essay.referencesTab')}
            </h2>
            <span className="text-sm text-slate-500 dark:text-slate-400">
              {references.length} {t('essay.detected')}
            </span>
          </div>

          <Card className="p-0 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <TableHead className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider w-16">
                    #
                  </TableHead>
                  <TableHead className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    {t('essay.reference')}
                  </TableHead>
                  <TableHead className="text-center px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    {t('essay.citedInText')}
                  </TableHead>
                  <TableHead className="text-center px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    {t('essay.verification')}
                  </TableHead>
                  <TableHead className="text-center px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider w-16">
                    {t('essay.action')}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="divide-y divide-slate-100 dark:divide-slate-800">
                {references.map((reference, index) => {
                  const authorDisplay = reference.authors?.join(', ') || parseAuthorDisplay(reference.raw_text);
                  const yearDisplay = reference.year || parseYear(reference.raw_text);
                  const matchingVerdict = report.verdicts.find(
                    (v) => v.citation_raw === reference.raw_text
                  );

                  return (
                    <TableRow
                      key={reference.id ?? `${reference.raw_text}-${index}`}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors"
                    >
                      <TableCell className="px-4 py-3">
                        <span className="text-sm font-mono text-slate-500 dark:text-slate-400">
                          {index + 1}
                        </span>
                      </TableCell>
                      <TableCell className="px-4 py-3">
                        <div className="space-y-1">
                          <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                            {authorDisplay}{yearDisplay && ` (${yearDisplay})`}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-1">
                            {reference.raw_text.slice(0, 160)}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell className="px-4 py-3 text-center">
                        {(() => {
                          const count = reference.cited_in_text_count ?? 0;
                          const pages = reference.cited_on_pages ?? [];
                          if (count > 0) {
                            const pageList = pages.length
                              ? `trên trang ${pages.join(', ')}`
                              : 'trong bài';
                            return (
                              <span
                                className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400"
                                title={`Được trích dẫn ${count} lần ${pageList}`}
                              >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                ×{count}
                              </span>
                            );
                          }
                          return (
                            <span
                              className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 dark:text-slate-500"
                              title="Không được trích dẫn trong phần nội dung"
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                              </svg>
                              {t('essay.notCited')}
                            </span>
                          );
                        })()}
                      </TableCell>
                      <TableCell className="px-4 py-3 text-center">
                        <Badge
                          variant="verified"
                          className="inline-block px-2.5 py-1 text-xs font-medium rounded-full"
                        >
                          {t('essay.referenceEntry')}
                        </Badge>
                      </TableCell>
                      <TableCell className="px-4 py-3 text-center">
                        <Button
                          variant="link"
                          size="sm"
                          onClick={() => matchingVerdict && setSelected(matchingVerdict)}
                          className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 text-sm font-medium h-auto p-0"
                        >
                          {t('common.view')}
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}

      {/* Overview Tab Content - Section 7 Dashboard */}
      {activeTab === 'overview' && (
        <>
          <div>
            <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100">
              {t('essay.citationVerificationResults')}
            </h2>
          </div>

          <VerdictTable
            verdicts={report.verdicts}
            onSelect={setSelected}
            onOverride={handleOverride}
          />
        </>
      )}

      {/* Detail Drawer - Section 10: Reference Inspector */}
      {selected && (
        <CitationDetailDrawer
          verdict={selected}
          onClose={() => setSelected(null)}
          onOverride={(req) => handleOverride(selected, req)}
        />
      )}
    </div>
  );
}
