import type { Verdict } from '@/api/client';

const SOURCE_LABELS: Record<string, string> = {
  crossref: 'Crossref',
  openalex: 'OpenAlex',
  s2: 'Semantic Scholar',
  semantic_scholar: 'Semantic Scholar',
  arxiv: 'arXiv',
  core: 'CORE',
  local_db: 'the local library',
  known_papers: 'the known-papers library',
};

const FIELD_LABELS: Record<string, string> = {
  title: 'the title',
  authors: 'the authors',
  author: 'the authors',
  year: 'the publication year',
  doi: 'the DOI',
  venue: 'the venue',
  url: 'the link',
};

const RULE_LABELS: Record<string, string> = {
  'R-WELL-LINKED': 'Citation and publication details match closely',
  'R-WELL-LINKED-MODERATE': 'Citation and publication are a reasonable match',
  'R-DOI-TITLE-AUTHOR': 'DOI, title, and author details match',
  'R-CONSENSUS-FULL': 'Multiple sources agree on the publication details',
  'R-CONSENSUS-PARTIAL': 'Sources agree, with some details to review',
  'R-KNOWN-AUTHOR-TITLE-MISMATCH': 'Author matches, but the title needs review',
  'R-KNOWN-AUTHOR-WEAK-EVIDENCE': 'Author is known, but supporting evidence is limited',
  'R-DOI-TITLE-MISMATCH': 'DOI matches, but the title needs review',
  'R-FAKE-URL': 'The link does not look like a real academic source',
  'R-FABRICATED-DOI': 'The DOI has an invalid format',
  'R-FAKE-AUTHOR': 'The author details look unusual or fabricated',
  'R-FUTURE-YEAR': 'The publication year is in the future',
  'R-FUTURE-YEAR-KNOWN-AUTHOR': 'The publication year needs review',
  'R-CONTENT-MISMATCH': 'The citation content does not match the publication',
  'R-STYLE-INCONSISTENT': 'The citation format differs from the document style',
};

export function getSourceDisplayName(source: string): string {
  const key = source.toLowerCase();
  return SOURCE_LABELS[key] ?? source;
}

function matchedSourceNames(verdict: Verdict): string[] {
  return (verdict.matched_sources ?? []).map((source) => getSourceDisplayName(source.source));
}

/** Treat URL-only rows as web resources, including older cached reports. */
export function isUrlResource(verdict: { citation_raw: string; label: string }): boolean {
  if (verdict.label === 'resource') return true;
  const raw = verdict.citation_raw.trim().replace(/[.,;:)"']+$/, '');
  return /^(?:https?:\/\/|www\.)\S+$/i.test(raw);
}

export function getFieldDisplayName(field: string): string {
  return FIELD_LABELS[field.toLowerCase()] ?? field;
}

export function getRuleDisplayName(rule: string): string {
  return RULE_LABELS[rule] ?? 'An additional verification check was applied';
}

export function getVerdictDisplayName(label: string): string {
  const labels: Record<string, string> = {
    verified: 'Verified',
    metadata_error: 'Needs a metadata review',
    suspected_hallucination: 'Could not be verified',
    unresolved: 'Needs manual review',
    resource: 'Web resource',
  };
  return labels[label] ?? 'Needs manual review';
}

function fieldLabels(fields: string[]): string {
  const labels = [...new Set(fields.map((field) => FIELD_LABELS[field.toLowerCase()] ?? field))];
  if (labels.length === 0) return 'the available details';
  if (labels.length === 1) return labels[0];
  if (labels.length === 2) return `${labels[0]} and ${labels[1]}`;
  return `${labels.slice(0, -1).join(', ')}, and ${labels[labels.length - 1]}`;
}

/**
 * Converts internal validation reasoning into a short explanation for people
 * reading the report. The raw reasoning remains available to the backend.
 */
export function getVerdictExplanation(verdict: Verdict): string {
  const sources = matchedSourceNames(verdict);
  const fields = fieldLabels(verdict.mismatched_fields ?? []);
  const matchedFields = fieldLabels(
    (verdict.matched_sources ?? []).flatMap((source) => source.matched_fields ?? [])
  );

  if (isUrlResource(verdict)) {
    return `URL resource detected: ${verdict.citation_raw}. This is not an academic citation and is excluded from the CIS score.`;
  }

  if (verdict.mapping_status === 'missing_reference') {
    return 'This citation does not have a matching entry in the bibliography.';
  }

  if (verdict.mapping_status === 'ambiguous_mapping') {
    return 'The citation could match more than one bibliography entry, so the system did not choose one automatically.';
  }

  switch (verdict.label) {
    case 'verified':
      if (sources.length === 0) {
        return 'The citation is linked to its bibliography entry and passes the available checks.';
      }
      if (sources.every((source) => source === 'the local library' || source === 'the known-papers library')) {
        return `The citation matches a paper in ${sources[0]}. ${matchedFields} are consistent, so no external search was needed.`;
      }
      return `We found a matching publication in ${sources.join(' and ')}. ${matchedFields} are consistent with the citation.`;

    case 'metadata_error':
      return sources.length > 0
        ? `We found a likely publication, but ${fields} do not match the citation. Please review these details.`
        : `The citation could not be confirmed because ${fields} do not match the available record.`;

    case 'suspected_hallucination':
      return sources.length === 0
        ? 'We could not find a matching publication in the checked sources. Please verify this citation manually.'
        : 'The available records do not support this citation. Please verify the source and its details manually.';

    case 'unresolved':
    default:
      return sources.length === 0
        ? 'There was not enough evidence to verify this citation. Please review it manually.'
        : `We found a possible match, but the available details are not strong enough to confirm it. Check ${fields}.`;
  }
}

export function getSourceSummary(verdict: Verdict): string {
  if (isUrlResource(verdict)) return `URL: ${verdict.citation_raw}`;
  const sources = matchedSourceNames(verdict);
  if (sources.length === 0) return 'No matching publication found';
  if (sources.length === 1) return `Found a matching publication in ${sources[0]}`;
  return `Found matching publications in ${sources.join(' and ')}`;
}

export function getSearchStepDescription(verdict: Verdict): string {
  const sources = matchedSourceNames(verdict);
  if (sources.every((source) => source === 'the local library' || source === 'the known-papers library') && sources.length > 0) {
    return 'A saved local record matched, so no external services were contacted.';
  }
  if (sources.length > 0) {
    return `Checked ${sources.join(', ')} for a matching publication.`;
  }
  return 'No matching publication was returned by the available sources.';
}
