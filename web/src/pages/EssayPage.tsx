import { useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  api,
  type Verdict,
  type Citation,
  type CitationLink,
  type ValidationLabel,
} from '@/api/client';
import { EssayHeader } from './essay/EssayHeader';
import { EssayActionBar } from './essay/EssayActionBar';
import { OverrideControls } from '@/components/OverrideControls';
import { useEssayReport, useOverrideVerdict } from '@/hooks/useEssayReport';
import {
  Loader2,
  AlertCircle,
  FileText,
  Scale,
  Check,
  AlertTriangle,
  XCircle,
  Shield,
  ArrowUpRight,
  Search,
  ExternalLink,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

/* ============================================================
   Helper Types & Functions for the Real Citation Debugger IDE
   ============================================================ */

type FieldStatus = 'match' | 'partial' | 'mismatch' | 'missing';

interface MetadataFields {
  title: string;
  authors: string;
  year: string;
  venue: string;
  doi: string;
}

interface SymbolicRuleDisplay {
  code: string;
  name: string;
  condition: string;
  status: 'passed' | 'warning' | 'failed';
}

interface SourceRetrievalItem {
  name: string;
  status: 'matched' | 'partial' | 'not_found';
  score: string;
  matchedFields: string[];
  url?: string;
  doi?: string;
}

interface EnrichedCitationItem {
  verdict: Verdict;
  index: number;
  marker: string;
  inText: string;
  pageLabel: string;
  verdictText: string;
  verdictBadgeClass: string;
  mappingText: string;
  mappingBadgeClass: string;
  confidencePct: number;
  citedMeta: MetadataFields;
  retrievedMeta: MetadataFields | null;
  fieldStatus: Record<keyof MetadataFields, { status: FieldStatus; label?: string }>;
  contextBefore: string;
  contextHighlight: string;
  contextAfter: string;
  explanationText: string;
  rules: SymbolicRuleDisplay[];
  sources: SourceRetrievalItem[];
}

const RULE_CATALOG: Record<
  string,
  {
    nameVi: string;
    nameEn: string;
    condition: string;
    status: 'passed' | 'warning' | 'failed';
  }
> = {
  'R-DOI-TITLE-AUTHOR': {
    nameVi: 'Xác thực tuyệt đối DOI + Tiêu đề + Tác giả',
    nameEn: 'Exact DOI + Title + Author Match',
    condition: 'IF doi_exact_match == 1.0 AND title_sim >= 0.90 AND author_jaccard >= 0.70 THEN VERIFIED',
    status: 'passed',
  },
  'R-WELL-LINKED': {
    nameVi: 'Khớp đa trường độ tin cậy cao',
    nameEn: 'High-Confidence Multi-Field Match',
    condition: 'IF title_sim_fuzzy >= 0.88 AND author_jaccard >= 0.75 AND year_distance == 0 THEN VERIFIED',
    status: 'passed',
  },
  'R-WELL-LINKED-MODERATE': {
    nameVi: 'Khớp tiêu đề & tác giả mức khá',
    nameEn: 'Moderate Title & Author Match',
    condition: 'IF title_sim_fuzzy >= 0.80 AND author_jaccard >= 0.60 AND year_distance <= 1 THEN VERIFIED',
    status: 'passed',
  },
  'R-LOCAL_DB_VERIFIED': {
    nameVi: 'Xác thực trực tiếp từ CSDL ACL / Known Papers nội bộ',
    nameEn: 'Verified in Local ACL / Known Papers Index',
    condition: 'IF local_fts5_hit == TRUE AND title_sim >= 0.90 AND year_distance == 0 THEN VERIFIED',
    status: 'passed',
  },
  'R-LOCAL_DB_GOOD_MATCH': {
    nameVi: 'Khớp tốt trong CSDL nội bộ',
    nameEn: 'Strong Local Index Candidate Match',
    condition: 'IF local_fts5_hit == TRUE AND title_sim >= 0.82 AND author_jaccard >= 0.65 THEN VERIFIED',
    status: 'passed',
  },
  'R-LOCAL_DB': {
    nameVi: 'Truy hồi từ chỉ mục SQLite FTS5 nội bộ',
    nameEn: 'Local SQLite FTS5 Index Hit',
    condition: 'IF source IN ("local_db", "known_papers") AND candidate_confidence >= 0.70 THEN PASS',
    status: 'passed',
  },
  'R-LOCAL_DB_ONLY': {
    nameVi: 'Đối chiếu độc lập trên CSDL nội bộ',
    nameEn: 'Standalone Local Database Verification',
    condition: 'IF external_apis == OFFLINE AND local_db_confidence >= 0.80 THEN VERIFIED',
    status: 'passed',
  },
  'R-KNOWN-PAPER': {
    nameVi: 'Công trình kinh điển trong tập chuẩn',
    nameEn: 'Canonical Benchmark Publication Match',
    condition: 'IF source == "known_papers" AND title_sim >= 0.92 THEN VERIFIED',
    status: 'passed',
  },
  'R-CONSENSUS-FULL': {
    nameVi: 'Đồng thuận đa nguồn học thuật (≥ 2 CSDL)',
    nameEn: 'Multi-Source Scholarly Consensus (≥ 2 DBs)',
    condition: 'IF source_consensus >= 2 AND metadata_conflict == FALSE THEN BOOST_CONFIDENCE(+0.10)',
    status: 'passed',
  },
  'R-CONSENSUS-PARTIAL': {
    nameVi: 'Đồng thuận một phần giữa các nguồn',
    nameEn: 'Partial Cross-Database Consensus',
    condition: 'IF matched_sources >= 1 AND partial_field_agreement == TRUE THEN WARN',
    status: 'warning',
  },
  'R-DOI-TITLE-MISMATCH': {
    nameVi: 'Xung đột giữa DOI và Tiêu đề bài báo',
    nameEn: 'DOI vs. Title Cross-Check Conflict',
    condition: 'IF doi_resolved == TRUE AND title_sim_fuzzy < 0.65 THEN METADATA_ERROR',
    status: 'warning',
  },
  'R-KNOWN-AUTHOR-TITLE-MISMATCH': {
    nameVi: 'Tác giả có thật nhưng sai lệch Metadata / Năm / Tiêu đề',
    nameEn: 'Known Author with Metadata / Year / Title Drift',
    condition: 'IF author_matched == TRUE AND (year_distance > 0 OR title_sim < 0.85) THEN METADATA_ERROR',
    status: 'warning',
  },
  'R-KNOWN-AUTHOR-WEAK-EVIDENCE': {
    nameVi: 'Tác giả khớp một phần nhưng thiếu bằng chứng nguồn',
    nameEn: 'Known Author with Weak Bibliographic Evidence',
    condition: 'IF author_jaccard >= 0.50 AND candidate_confidence < 0.65 THEN METADATA_ERROR',
    status: 'warning',
  },
  'R-WEAK-EVIDENCE': {
    nameVi: 'Độ tương đồng ứng viên thấp (Weak Evidence)',
    nameEn: 'Low Candidate Similarity Score',
    condition: 'IF max_candidate_confidence BETWEEN [0.40, 0.70) THEN METADATA_ERROR',
    status: 'warning',
  },
  'R-CONTENT-ALIGNMENT': {
    nameVi: 'Ngữ cảnh trích dẫn khớp nội dung nguồn',
    nameEn: 'In-Text Context Semantic Alignment',
    condition: 'IF context_abstract_cosine >= 0.65 THEN PASS',
    status: 'passed',
  },
  'R-CONTENT-MISMATCH': {
    nameVi: 'Ngữ cảnh trích dẫn mâu thuẫn với tóm tắt bài gốc',
    nameEn: 'In-Text Claim vs. Source Abstract Mismatch',
    condition: 'IF context_abstract_cosine < 0.30 THEN WARN_CONTENT_DRIFT',
    status: 'warning',
  },
  'R-STYLE-INCONSISTENT': {
    nameVi: 'Sai lệch chuẩn định dạng trích dẫn (APA/IEEE)',
    nameEn: 'Citation Formatting Style Inconsistency',
    condition: 'IF citation_style != dominant_document_style THEN APPLY_STYLE_PENALTY',
    status: 'warning',
  },
  'R-WEB-RESOURCE': {
    nameVi: 'Tài nguyên Web / URL phi học thuật',
    nameEn: 'Non-Scholarly Web URL Resource',
    condition: 'IF has_url == TRUE AND no_doi == TRUE AND no_academic_venue == TRUE THEN RESOURCE',
    status: 'passed',
  },
  'R-URL-RESOURCE': {
    nameVi: 'Liên kết URL trực tiếp',
    nameEn: 'Direct URL Reference',
    condition: 'IF citation_type == "url" THEN RESOURCE',
    status: 'passed',
  },
  'R-FAKE-URL': {
    nameVi: 'URL hoặc tên miền không tồn tại / giả mạo',
    nameEn: 'Unresolvable or Fabricated URL',
    condition: 'IF url_status >= 400 OR domain_resolvable == FALSE THEN SUSPECTED_HALLUCINATION',
    status: 'failed',
  },
  'R-FABRICATED-DOI': {
    nameVi: 'Mã DOI không tồn tại trên hệ thống Crossref/DataCite',
    nameEn: 'Non-Existent / Fabricated DOI Prefix',
    condition: 'IF cited_doi != NULL AND crossref_doi_lookup == 404 THEN SUSPECTED_HALLUCINATION',
    status: 'failed',
  },
  'R-FAKE-AUTHOR': {
    nameVi: 'Tổ hợp Tác giả + Công trình không tồn tại',
    nameEn: 'Unverifiable Author-Publication Combination',
    condition: 'IF author_jaccard == 0.0 AND max_title_sim < 0.45 THEN SUSPECTED_HALLUCINATION',
    status: 'failed',
  },
  'R-FUTURE-YEAR': {
    nameVi: 'Năm xuất bản vượt quá thời điểm hiện tại',
    nameEn: 'Impossibly Future Publication Year',
    condition: 'IF cited_year > current_year + 1 THEN SUSPECTED_HALLUCINATION',
    status: 'failed',
  },
  'R-FUTURE-YEAR-KNOWN-AUTHOR': {
    nameVi: 'Sai năm xuất bản (lệch năm so với bản gốc)',
    nameEn: 'Publication Year Discrepancy on Known Work',
    condition: 'IF title_sim >= 0.85 AND abs(cited_year - actual_year) >= 1 THEN METADATA_ERROR',
    status: 'warning',
  },
  'R-NO-CANDIDATE': {
    nameVi: 'Không tìm thấy ứng viên nào trên 5 CSDL học thuật',
    nameEn: 'Zero Candidates Retrieved Across 5 Scholarly DBs',
    condition: 'IF count(candidates_across_all_sources) == 0 THEN SUSPECTED_HALLUCINATION',
    status: 'failed',
  },
  'R-FAIL-ALL': {
    nameVi: 'Thất bại toàn bộ kiểm định ngưỡng tối thiểu',
    nameEn: 'All Verification Thresholds Failed',
    condition: 'IF max_title_sim < 0.35 AND doi_exact_match == 0 THEN SUSPECTED_HALLUCINATION',
    status: 'failed',
  },
};

function parseRawCitationMeta(rawText: string): MetadataFields {
  const cleaned = rawText.replace(/^\s*\[\d+\]\s*/, '').trim();

  // Extract DOI if present
  const doiMatch = cleaned.match(/\b(10\.\d{4,9}\/[-._;()/:A-Za-z0-9]+)\b/);
  const doi = doiMatch ? doiMatch[1].replace(/[.,;]+$/, '') : '—';

  // Extract Year
  const yearMatch = cleaned.match(/\b(19\d{2}|20\d{2})[a-z]?\b/);
  const year = yearMatch ? yearMatch[1] : '—';

  // Try quotes for title: "Title" or “Title”
  const quoteMatch = cleaned.match(/[“"]([^”"]{8,220})[”"]/);
  let title = quoteMatch ? quoteMatch[1].replace(/[.,]+$/, '').trim() : '';

  // Try APA style: Authors (Year). Title. Venue.
  let authors = '';
  let venue = '';

  const apaMatch = cleaned.match(/^(.+?)\s*\((?:19|20)\d{2}[a-z]?\)\.\s*([^.]+)\.\s*(.*)$/);
  if (apaMatch) {
    authors = apaMatch[1].trim().replace(/[.,]+$/, '');
    if (!title) title = apaMatch[2].trim();
    venue = apaMatch[3]
      .replace(/\b(?:https?:\/\/\S+|doi:\s*\S+|10\.\d{4,9}\/\S+)/gi, '')
      .trim()
      .replace(/[.,]+$/, '');
  } else {
    // IEEE or general style: Authors, "Title," Venue, Year. OR Authors. Title. Venue, Year.
    const segments = cleaned
      .split(/\.\s+/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (segments.length >= 2) {
      authors = segments[0].replace(/^\[\d+\]\s*/, '').trim();
      if (!title) {
        title = segments[1].replace(/^[“"]|[”"]$/g, '').trim();
      }
      if (segments.length >= 3) {
        venue = segments
          .slice(2)
          .join('. ')
          .replace(/\b(?:https?:\/\/\S+|doi:\s*\S+|10\.\d{4,9}\/\S+)/gi, '')
          .trim();
      }
    } else {
      const commaParts = cleaned.split(/,\s+/);
      if (commaParts.length >= 2) {
        authors = commaParts[0].trim();
        if (!title) title = commaParts.slice(1).join(', ').slice(0, 140);
      } else {
        title = cleaned.slice(0, 140);
      }
    }
  }

  const cleanVenue = venue
    .replace(/^(?:,\s*)?(?:[^.()]*?\)\.\s*)+/, '')
    .replace(/^[,.;:)\s]+/, '')
    .trim();

  return {
    title: title || cleaned.slice(0, 120) || '—',
    authors: authors || '—',
    year: year || '—',
    venue: cleanVenue || venue || '—',
    doi,
  };
}

function formatShortInText(authors: string, year: string, rawText: string): string {
  if (authors && authors !== '—') {
    const firstAuthor = authors.split(/,|&|\band\b/i)[0].trim();
    const hasMore = /,|&|\band\b|\bet\s+al/i.test(authors);
    const shortAuthor =
      firstAuthor.length > 28 ? firstAuthor.slice(0, 28) + '…' : firstAuthor;
    const suffix =
      hasMore && !/et\s+al/i.test(shortAuthor) ? ' et al.' : '';
    return year && year !== '—'
      ? `${shortAuthor}${suffix} (${year})`
      : `${shortAuthor}${suffix}`;
  }
  return rawText.slice(0, 42);
}

function getVerdictBadgeVisuals(label: ValidationLabel): {
  text: string;
  badgeClass: string;
} {
  switch (label) {
    case 'verified':
      return {
        text: '✓ VERIFIED',
        badgeClass:
          'verdict-badge-verified bg-emerald-100/90 text-emerald-800 border border-emerald-300 dark:bg-emerald-950/90 dark:text-emerald-300 dark:border-emerald-700 font-bold',
      };
    case 'metadata_error':
      return {
        text: '⚠ METADATA_ERROR',
        badgeClass:
          'verdict-badge-metadata-error bg-amber-100/90 text-amber-800 border border-amber-300 dark:bg-amber-950/90 dark:text-amber-300 dark:border-amber-700 font-bold',
      };
    case 'suspected_hallucination':
      return {
        text: '✕ HALLUCINATION',
        badgeClass:
          'verdict-badge-hallucinated bg-red-100/90 text-red-800 border border-red-300 dark:bg-red-950/90 dark:text-red-300 dark:border-red-700 font-bold',
      };
    case 'resource':
      return {
        text: '↗ URL_RESOURCE',
        badgeClass:
          'bg-violet-100/90 text-violet-800 border border-violet-300 dark:bg-violet-950/90 dark:text-violet-300 dark:border-violet-700 font-bold',
      };
    default:
      return {
        text: '— UNRESOLVED',
        badgeClass:
          'verdict-badge-unverifiable bg-slate-200/80 text-slate-700 border border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700 font-bold',
      };
  }
}

function getMappingBadgeVisuals(status: Verdict['mapping_status']): {
  text: string;
  badgeClass: string;
} {
  switch (status) {
    case 'matched':
      return {
        text: 'MATCHED',
        badgeClass:
          'bg-indigo-50 text-indigo-700 border border-indigo-200/90 dark:bg-indigo-950/70 dark:text-indigo-300 dark:border-indigo-800 font-semibold',
      };
    case 'missing_reference':
      return {
        text: 'MISSING_REF',
        badgeClass:
          'mapping-badge-missing bg-red-50 text-red-700 border border-red-200 dark:bg-red-950/70 dark:text-red-300 dark:border-red-800 font-semibold',
      };
    case 'uncited_reference':
      return {
        text: 'UNCITED_REF',
        badgeClass:
          'mapping-badge-uncited bg-sky-50 text-sky-700 border border-sky-200 dark:bg-sky-950/70 dark:text-sky-300 dark:border-sky-800 font-semibold',
      };
    case 'in_text_mismatch':
    case 'ambiguous_mapping':
    case 'duplicate_reference':
    case 'style_inconsistent':
      return {
        text: status.toUpperCase().replace('_REFERENCE', '_REF'),
        badgeClass:
          'mapping-badge-mismatch bg-orange-50 text-orange-700 border border-orange-200 dark:bg-orange-950/70 dark:text-orange-300 dark:border-orange-800 font-semibold',
      };
    default:
      return {
        text: 'UNRESOLVED',
        badgeClass:
          'bg-slate-100 text-slate-600 border border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700 font-semibold',
      };
  }
}

function buildLocalizedReasoning(verdict: Verdict, lang: 'vi' | 'en'): string {
  const sourceMapVi: Record<string, string> = {
    local_db: 'Thư viện học thuật nội bộ (ACL / SQLite FTS5)',
    known_papers: 'CSDL công trình kinh điển (Known Papers)',
    crossref: 'Crossref',
    openalex: 'OpenAlex',
    s2: 'Semantic Scholar',
    semantic_scholar: 'Semantic Scholar',
    arxiv: 'arXiv',
    core: 'CORE',
  };
  const sourceMapEn: Record<string, string> = {
    local_db: 'the local scholarly index (ACL / SQLite FTS5)',
    known_papers: 'the canonical Known Papers index',
    crossref: 'Crossref',
    openalex: 'OpenAlex',
    s2: 'Semantic Scholar',
    semantic_scholar: 'Semantic Scholar',
    arxiv: 'arXiv',
    core: 'CORE',
  };

  const fieldMapVi: Record<string, string> = {
    title: 'tiêu đề',
    authors: 'nhóm tác giả',
    author: 'tác giả',
    year: 'năm xuất bản',
    venue: 'nơi công bố',
    doi: 'mã DOI',
    url: 'đường dẫn URL',
  };
  const fieldMapEn: Record<string, string> = {
    title: 'title',
    authors: 'authors',
    author: 'authors',
    year: 'publication year',
    venue: 'venue',
    doi: 'DOI',
    url: 'URL',
  };

  const sources = [
    ...new Set(
      (verdict.matched_sources ?? []).map((s) =>
        lang === 'vi'
          ? sourceMapVi[s.source.toLowerCase()] ?? s.source
          : sourceMapEn[s.source.toLowerCase()] ?? s.source
      )
    ),
  ];

  const matchedFields = [
    ...new Set(
      (verdict.matched_sources ?? []).flatMap((s) =>
        (s.matched_fields ?? []).map((f) =>
          lang === 'vi'
            ? fieldMapVi[f.toLowerCase()] ?? f
            : fieldMapEn[f.toLowerCase()] ?? f
        )
      )
    ),
  ];

  const mismatchedFields = [
    ...new Set(
      (verdict.mismatched_fields ?? []).map((f) =>
        lang === 'vi'
          ? fieldMapVi[f.toLowerCase()] ?? f
          : fieldMapEn[f.toLowerCase()] ?? f
      )
    ),
  ];

  // Extract neural context alignment score from raw reasoning if present
  const neuralMatch = verdict.reasoning?.match(
    /content alignment score=([\d.]+)\s*\((low|medium|high)\)/i
  );
  const neuralScore = neuralMatch ? neuralMatch[1] : null;
  const neuralLevel = neuralMatch ? neuralMatch[2].toLowerCase() : null;

  const titleSim = verdict.features?.title_sim_fuzzy;
  const authorSim = verdict.features?.author_jaccard;

  if (lang === 'vi') {
    const telemetryParts: string[] = [];
    if (titleSim !== undefined) {
      telemetryParts.push(`độ tương đồng tiêu đề = ${titleSim.toFixed(2)}`);
    }
    if (authorSim !== undefined) {
      telemetryParts.push(`tác giả = ${authorSim.toFixed(2)}`);
    }
    if (neuralScore) {
      const levelVi =
        neuralLevel === 'high'
          ? 'cao'
          : neuralLevel === 'medium'
            ? 'trung bình'
            : 'thấp';
      telemetryParts.push(
        `điểm căn chỉnh ngữ cảnh Neural = ${neuralScore} (${levelVi}) — nội dung trích dẫn tương thích ngữ nghĩa với nguồn`
      );
    }
    const telemetrySuffix =
      telemetryParts.length > 0 ? ` (${telemetryParts.join(' · ')})` : '';

    let mainText = '';
    if (verdict.label === 'resource') {
      mainText = `Phát hiện tài nguyên Web / API phi học thuật (${verdict.citation_raw}). Mục này được phân loại là đường dẫn tài nguyên tham khảo và không tính điểm phạt vào chỉ số CIS.`;
    } else if (verdict.mapping_status === 'missing_reference') {
      mainText =
        'Trích dẫn xuất hiện trong phần nội dung bài viết nhưng bị khuyết mục tương ứng trong danh mục tài liệu tham khảo cuối bài.';
    } else if (verdict.label === 'verified') {
      const srcStr =
        sources.length > 0
          ? sources.join(' và ')
          : 'cơ sở dữ liệu học thuật';
      const fldStr =
        matchedFields.length > 0
          ? matchedFields.join(', ')
          : 'tiêu đề, tác giả và năm xuất bản';
      mainText = `Trích dẫn khớp chính xác với công trình trong ${srcStr}. Các trường thông tin (${fldStr}) hoàn toàn nhất quán với bản ghi gốc.${telemetrySuffix}`;
    } else if (verdict.label === 'metadata_error') {
      const srcStr =
        sources.length > 0 ? ` trên ${sources.join(' và ')}` : '';
      const errFldStr =
        mismatchedFields.length > 0
          ? mismatchedFields.join(', ')
          : 'siêu dữ liệu (năm xuất bản / tiêu đề)';
      mainText = `Tìm thấy công trình học thuật tương ứng${srcStr}, nhưng phát hiện sai lệch ở trường: ${errFldStr}. Vui lòng đối chiếu và hiệu đính lại theo bản ghi gốc.${telemetrySuffix}`;
    } else if (verdict.label === 'suspected_hallucination') {
      mainText = `Không tìm thấy bất kỳ công trình học thuật nào khớp với trích dẫn này trên cả 5 cơ sở dữ liệu (ACL, Crossref, OpenAlex, Semantic Scholar, CORE). Nghi ngờ trích dẫn suy diễn (hallucination) hoặc thông tin không có thật.${telemetrySuffix}`;
    } else {
      const srcStr =
        sources.length > 0
          ? `Tìm thấy ứng viên tiềm năng trên ${sources.join(', ')}, nhưng bằng chứng siêu dữ liệu chưa đủ mạnh để xác nhận tự động.`
          : 'Chưa đủ bằng chứng siêu dữ liệu từ các nguồn truy hồi để xác minh tự động trích dẫn này.';
      mainText = `${srcStr} Khuyến nghị giảng viên kiểm tra thủ công.${telemetrySuffix}`;
    }

    return verdict.override_note
      ? `[Ghi đè bởi Giảng viên: ${verdict.override_note}] — ${mainText}`
      : mainText;
  }

  // English ('en') — 100% pure English
  const telemetryPartsEn: string[] = [];
  if (titleSim !== undefined) {
    telemetryPartsEn.push(`title similarity = ${titleSim.toFixed(2)}`);
  }
  if (authorSim !== undefined) {
    telemetryPartsEn.push(`author similarity = ${authorSim.toFixed(2)}`);
  }
  if (neuralScore) {
    telemetryPartsEn.push(
      `Neural context alignment = ${neuralScore} (${neuralLevel}) — semantically aligned with source`
    );
  }
  const telemetrySuffixEn =
    telemetryPartsEn.length > 0 ? ` (${telemetryPartsEn.join(' · ')})` : '';

  let mainTextEn = '';
  if (verdict.label === 'resource') {
    mainTextEn = `Non-scholarly Web / API resource detected (${verdict.citation_raw}). Classified as a web resource and excluded from the CIS penalty calculation.`;
  } else if (verdict.mapping_status === 'missing_reference') {
    mainTextEn =
      'This in-text citation does not have a corresponding entry in the bibliography section.';
  } else if (verdict.label === 'verified') {
    const srcStr =
      sources.length > 0 ? sources.join(' and ') : 'scholarly databases';
    const fldStr =
      matchedFields.length > 0
        ? matchedFields.join(', ')
        : 'title, authors, and publication year';
    mainTextEn = `The citation matches a canonical publication in ${srcStr}. Verified fields (${fldStr}) are consistent with the source record.${telemetrySuffixEn}`;
  } else if (verdict.label === 'metadata_error') {
    const srcStr = sources.length > 0 ? ` in ${sources.join(' and ')}` : '';
    const errFldStr =
      mismatchedFields.length > 0
        ? mismatchedFields.join(', ')
        : 'metadata fields (year / title)';
    mainTextEn = `Found a corresponding publication${srcStr}, but detected discrepancies in: ${errFldStr}. Please review against the canonical record.${telemetrySuffixEn}`;
  } else if (verdict.label === 'suspected_hallucination') {
    mainTextEn = `No matching publication was found across all 5 scholarly databases (ACL, Crossref, OpenAlex, Semantic Scholar, CORE). Suspected hallucinated or fabricated reference.${telemetrySuffixEn}`;
  } else {
    mainTextEn =
      sources.length > 0
        ? `A potential candidate was found in ${sources.join(', ')}, but bibliographic evidence is insufficient for automatic verification. Manual review recommended.${telemetrySuffixEn}`
        : `Insufficient bibliographic evidence across queried databases to automatically verify this citation. Manual review recommended.${telemetrySuffixEn}`;
  }

  return verdict.override_note
    ? `[Instructor Override: ${verdict.override_note}] — ${mainTextEn}`
    : mainTextEn;
}

function enrichVerdictItem(
  verdict: Verdict,
  index: number,
  references: Citation[],
  extractedCitations: Citation[],
  lang: 'vi' | 'en'
): EnrichedCitationItem {
  const marker = `[${index + 1}]`;
  const parsedFallback = parseRawCitationMeta(verdict.citation_raw);

  // Find corresponding Reference entry if available
  const refId = verdict.citation_link?.reference_id;
  let matchedRef: Citation | undefined;
  if (refId) {
    const idxNum = parseInt(refId.replace(/^ref-/, ''), 10);
    if (!Number.isNaN(idxNum) && idxNum >= 1 && idxNum <= references.length) {
      matchedRef = references[idxNum - 1];
    }
  }
  if (!matchedRef) {
    matchedRef = references.find(
      (r) =>
        r.raw_text.trim() === verdict.citation_raw.trim() ||
        (r.title &&
          verdict.citation_raw.toLowerCase().includes(r.title.toLowerCase().slice(0, 35)))
    );
  }

  // Find corresponding in-text Citation entry for page number & manuscript context
  const matchedInText = extractedCitations.find(
    (c) =>
      c.citation_link?.reference_id === refId ||
      c.raw_text.trim() === verdict.citation_raw.trim() ||
      (matchedRef?.authors?.[0] &&
        c.raw_text.toLowerCase().includes(matchedRef.authors[0].split(',')[0].toLowerCase()))
  );

  const citedMeta: MetadataFields = {
    title: matchedRef?.title || parsedFallback.title || verdict.citation_raw,
    authors:
      (matchedRef?.authors && matchedRef.authors.length > 0
        ? matchedRef.authors.join(', ')
        : parsedFallback.authors) || '—',
    year:
      (matchedRef?.year ? String(matchedRef.year) : parsedFallback.year) || '—',
    venue: matchedRef?.venue || parsedFallback.venue || '—',
    doi: matchedRef?.doi || parsedFallback.doi || '—',
  };

  const inTextDisplay = formatShortInText(
    citedMeta.authors,
    citedMeta.year,
    verdict.citation_raw
  );

  const pageNum =
    matchedInText?.page_num ||
    matchedRef?.cited_on_pages?.[0] ||
    matchedRef?.page_num ||
    1;
  const pageLabel = `p. ${pageNum}`;

  // Determine Canonical Retrieved Metadata from matched_sources[0]
  const bestSource =
    verdict.matched_sources && verdict.matched_sources.length > 0
      ? verdict.matched_sources[0]
      : null;

  const matchedFieldsSet = new Set(
    (bestSource?.matched_fields ?? []).map((f) => f.toLowerCase())
  );
  const mismatchedFieldsSet = new Set(
    (verdict.mismatched_fields ?? []).map((f) => f.toLowerCase())
  );

  // Parse actual year from reasoning if year was mismatched and not explicitly in bestSource
  let inferredActualYear: string | null = null;
  if (verdict.reasoning) {
    const actualYearMatch =
      verdict.reasoning.match(/(?:actual|published|canonical|real)\s+year[:\s]+(\d{4})/i) ||
      verdict.reasoning.match(/\b(?:in|year)\s+(\d{4})\s*\((?:cited|vs)/i);
    if (actualYearMatch) {
      inferredActualYear = actualYearMatch[1];
    }
  }
  if (
    !inferredActualYear &&
    verdict.features?.year_distance &&
    verdict.features.year_distance > 0 &&
    citedMeta.year !== '—'
  ) {
    const citedYrNum = parseInt(citedMeta.year, 10);
    if (!Number.isNaN(citedYrNum)) {
      inferredActualYear = `${citedYrNum - Math.round(verdict.features.year_distance)} (Δ=${verdict.features.year_distance}y)`;
    }
  }

  const hasCanonicalRecord =
    Boolean(bestSource) &&
    verdict.label !== 'suspected_hallucination' &&
    verdict.label !== 'resource' &&
    (bestSource?.confidence ?? verdict.confidence) >= 0.25;

  const retrievedMeta: MetadataFields | null = hasCanonicalRecord && bestSource
    ? {
        title:
          bestSource.title ||
          (matchedFieldsSet.has('title') && !mismatchedFieldsSet.has('title')
            ? citedMeta.title
            : '—'),
        authors:
          bestSource.authors && bestSource.authors.length > 0
            ? bestSource.authors.join(', ')
            : matchedFieldsSet.has('authors') && !mismatchedFieldsSet.has('authors')
              ? citedMeta.authors
              : mismatchedFieldsSet.has('authors')
                ? lang === 'vi'
                  ? 'Khác danh sách tác giả gốc'
                  : 'Author list discrepancy in source'
                : citedMeta.authors !== '—' && verdict.label === 'verified'
                  ? citedMeta.authors
                  : '—',
        year: bestSource.year
          ? String(bestSource.year)
          : mismatchedFieldsSet.has('year')
            ? inferredActualYear ||
              (lang === 'vi' ? 'Lệch năm xuất bản' : 'Year mismatch in source')
            : matchedFieldsSet.has('year') || verdict.label === 'verified'
              ? citedMeta.year
              : '—',
        venue:
          bestSource.venue ||
          (matchedFieldsSet.has('venue') && !mismatchedFieldsSet.has('venue')
            ? citedMeta.venue !== '—'
              ? citedMeta.venue
              : `Indexed in ${bestSource.source}`
            : bestSource.source
              ? `Indexed in ${bestSource.source}`
              : '—'),
        doi:
          bestSource.doi ||
          (Boolean(verdict.features?.doi_exact_match) || matchedFieldsSet.has('doi')
            ? citedMeta.doi
            : '—'),
      }
    : null;

  // Compute field-by-field status
  const titleSim =
    verdict.features?.title_sim_fuzzy ??
    verdict.features?.title_sim_semantic ??
    (matchedFieldsSet.has('title') ? 1 : 0);
  const authorSim =
    verdict.features?.author_jaccard ??
    (matchedFieldsSet.has('authors') ? 1 : 0);

  const computeTitleStatus = (): { status: FieldStatus; label?: string } => {
    if (!retrievedMeta) return { status: 'mismatch', label: 'Diff' };
    if (mismatchedFieldsSet.has('title')) {
      if (titleSim >= 0.5) {
        return { status: 'partial', label: `${Math.round(titleSim * 100)}% Sim` };
      }
      return { status: 'mismatch', label: 'Diff' };
    }
    if (titleSim >= 0.96 || matchedFieldsSet.has('title')) {
      return { status: 'match', label: '100% Match' };
    }
    if (titleSim >= 0.65) {
      return { status: 'partial', label: `${Math.round(titleSim * 100)}% Sim` };
    }
    return verdict.label === 'verified'
      ? { status: 'match', label: '100% Match' }
      : { status: 'mismatch', label: 'Diff' };
  };

  const computeAuthorsStatus = (): { status: FieldStatus; label?: string } => {
    if (citedMeta.authors === '—') return { status: 'missing' };
    if (!retrievedMeta) return { status: 'mismatch', label: 'Diff' };
    if (mismatchedFieldsSet.has('authors')) {
      return authorSim >= 0.45
        ? { status: 'partial', label: `${Math.round(authorSim * 100)}% Sim` }
        : { status: 'mismatch', label: 'Diff' };
    }
    if (authorSim >= 0.95 || matchedFieldsSet.has('authors') || verdict.label === 'verified') {
      return { status: 'match', label: '100% Match' };
    }
    if (authorSim >= 0.5) {
      return { status: 'partial', label: `${Math.round(authorSim * 100)}% Sim` };
    }
    return { status: 'mismatch', label: 'Diff' };
  };

  const computeYearStatus = (): { status: FieldStatus; label?: string } => {
    if (citedMeta.year === '—') return { status: 'missing' };
    if (!retrievedMeta) return { status: 'mismatch', label: 'Diff' };
    if (
      mismatchedFieldsSet.has('year') ||
      (verdict.features?.year_distance !== undefined &&
        verdict.features.year_distance > 0)
    ) {
      return { status: 'mismatch', label: 'Diff' };
    }
    if (matchedFieldsSet.has('year') || verdict.label === 'verified') {
      return { status: 'match', label: '100% Match' };
    }
    return { status: 'partial', label: 'Checked' };
  };

  const computeVenueStatus = (): { status: FieldStatus; label?: string } => {
    if (citedMeta.venue === '—' && (!retrievedMeta || retrievedMeta.venue === '—')) {
      return { status: 'missing' };
    }
    if (!retrievedMeta) return { status: 'mismatch', label: 'Diff' };
    if (mismatchedFieldsSet.has('venue')) return { status: 'mismatch', label: 'Diff' };
    if (citedMeta.venue === '—') return { status: 'missing' };
    if (matchedFieldsSet.has('venue') || verdict.label === 'verified') {
      return { status: 'match', label: '100% Match' };
    }
    return { status: 'partial', label: 'Indexed' };
  };

  const computeDoiStatus = (): { status: FieldStatus; label?: string } => {
    if (citedMeta.doi === '—' && (!retrievedMeta || retrievedMeta.doi === '—')) {
      return { status: 'missing' };
    }
    if (!retrievedMeta) return { status: 'mismatch', label: 'Diff' };
    if (mismatchedFieldsSet.has('doi')) return { status: 'mismatch', label: 'Diff' };
    if (
      Boolean(verdict.features?.doi_exact_match) ||
      matchedFieldsSet.has('doi') ||
      (citedMeta.doi !== '—' &&
        retrievedMeta.doi !== '—' &&
        citedMeta.doi.toLowerCase() === retrievedMeta.doi.toLowerCase())
    ) {
      return { status: 'match', label: '100% Match' };
    }
    if (citedMeta.doi === '—' && retrievedMeta.doi !== '—') {
      return { status: 'partial', label: 'Retrieved' };
    }
    return { status: 'missing' };
  };

  // Build Manuscript Context with highlighted citation
  const rawContext =
    matchedInText?.context ||
    verdict.context ||
    matchedRef?.context ||
    verdict.citation_raw;
  const highlightTarget = matchedInText?.raw_text || inTextDisplay;
  let contextBefore = '“... ';
  let contextHighlight = highlightTarget;
  let contextAfter = ' ...”';

  const pos = rawContext.indexOf(highlightTarget);
  if (pos !== -1) {
    contextBefore = '“' + rawContext.slice(0, pos);
    contextHighlight = highlightTarget;
    contextAfter = rawContext.slice(pos + highlightTarget.length) + '”';
  } else {
    contextBefore = `“${rawContext} `;
    contextHighlight = marker;
    contextAfter = '”';
  }

  // Build localized explanation text (pure VI when lang==='vi', pure EN when lang==='en')
  const explanationText = buildLocalizedReasoning(verdict, lang);

  // Build Symbolic Rules Trace
  const triggeredCodes =
    verdict.triggered_rules && verdict.triggered_rules.length > 0
      ? verdict.triggered_rules
      : verdict.label === 'verified'
        ? ['R-WELL-LINKED']
        : verdict.label === 'metadata_error'
          ? ['R-KNOWN-AUTHOR-TITLE-MISMATCH']
          : verdict.label === 'suspected_hallucination'
            ? ['R-NO-CANDIDATE']
            : ['R-WEAK-EVIDENCE'];

  const rules: SymbolicRuleDisplay[] = triggeredCodes.map((code) => {
    const cleanCode = code.trim();
    const meta = RULE_CATALOG[cleanCode];
    if (meta) {
      return {
        code: cleanCode,
        name: lang === 'vi' ? meta.nameVi : meta.nameEn,
        condition: meta.condition,
        status: meta.status,
      };
    }
    const fallbackStatus: 'passed' | 'warning' | 'failed' =
      verdict.label === 'verified'
        ? 'passed'
        : verdict.label === 'metadata_error'
          ? 'warning'
          : 'failed';
    return {
      code: cleanCode,
      name:
        lang === 'vi'
          ? `Quy tắc kiểm định ${cleanCode}`
          : `Symbolic Verification Rule ${cleanCode}`,
      condition: `IF rule_triggered("${cleanCode}") == TRUE THEN ${verdict.label.toUpperCase()}`,
      status: fallbackStatus,
    };
  });

  // Build Federated Sources List (combining actual matched_sources with the 5 standard engines)
  const standardEngines = [
    { key: 'local', label: 'Local ACL / Known Papers (SQLite FTS5)', matchTokens: ['local', 'known', 'acl'] },
    { key: 'crossref', label: 'Crossref REST API', matchTokens: ['crossref'] },
    { key: 'openalex', label: 'OpenAlex Scholarly Graph', matchTokens: ['openalex'] },
    { key: 's2', label: 'Semantic Scholar (S2)', matchTokens: ['semantic', 's2'] },
    { key: 'core', label: 'CORE / arXiv Open Access', matchTokens: ['core', 'arxiv'] },
  ];

  const usedSourceIndices = new Set<number>();
  const sources: SourceRetrievalItem[] = standardEngines.map((engine) => {
    const foundIdx = (verdict.matched_sources ?? []).findIndex((ms, idx) => {
      if (usedSourceIndices.has(idx)) return false;
      const lower = ms.source.toLowerCase();
      return engine.matchTokens.some((tok) => lower.includes(tok));
    });

    if (foundIdx !== -1 && verdict.matched_sources) {
      usedSourceIndices.add(foundIdx);
      const ms = verdict.matched_sources[foundIdx];
      const conf = ms.confidence ?? verdict.confidence;
      return {
        name: engine.label,
        status: conf >= 0.7 ? 'matched' : 'partial',
        score: conf.toFixed(2),
        matchedFields: ms.matched_fields ?? [],
        url: ms.url ?? undefined,
        doi: ms.doi ?? undefined,
      };
    }

    return {
      name: engine.label,
      status: 'not_found',
      score: '0.00',
      matchedFields: [],
    };
  });

  // Append any additional custom matched sources not covered above
  (verdict.matched_sources ?? []).forEach((ms, idx) => {
    if (!usedSourceIndices.has(idx)) {
      const conf = ms.confidence ?? verdict.confidence;
      sources.unshift({
        name: ms.source,
        status: conf >= 0.7 ? 'matched' : 'partial',
        score: conf.toFixed(2),
        matchedFields: ms.matched_fields ?? [],
        url: ms.url ?? undefined,
        doi: ms.doi ?? undefined,
      });
    }
  });

  const verdictVisual = getVerdictBadgeVisuals(verdict.label);
  const mappingVisual = getMappingBadgeVisuals(verdict.mapping_status);

  return {
    verdict,
    index,
    marker,
    inText: inTextDisplay,
    pageLabel,
    verdictText: verdictVisual.text,
    verdictBadgeClass: verdictVisual.badgeClass,
    mappingText: mappingVisual.text,
    mappingBadgeClass: mappingVisual.badgeClass,
    confidencePct: Math.round((verdict.confidence ?? 0) * 100),
    citedMeta,
    retrievedMeta,
    fieldStatus: {
      title: computeTitleStatus(),
      authors: computeAuthorsStatus(),
      year: computeYearStatus(),
      venue: computeVenueStatus(),
      doi: computeDoiStatus(),
    },
    contextBefore,
    contextHighlight,
    contextAfter,
    explanationText,
    rules,
    sources,
  };
}

/* ============================================================
   SourceLogic — Real Interactive Citation Debugger IDE Page
   ============================================================ */

export function EssayPage() {
  const { t, i18n } = useTranslation();
  const lang: 'vi' | 'en' = i18n.language?.startsWith('en') ? 'en' : 'vi';

  const { id } = useParams<{ id: string }>();
  const numericId = id ? parseInt(id, 10) : null;
  const essayId =
    numericId !== null && !Number.isNaN(numericId) && numericId > 0
      ? numericId
      : null;

  const { data: report, isLoading, error } = useEssayReport(essayId);
  const overrideMutation = useOverrideVerdict();

  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);
  const [filterLabel, setFilterLabel] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const errorMessage =
    essayId === null
      ? t('essay.invalidEssayId')
      : error
        ? error instanceof Error
          ? error.message
          : t('essay.failedLoadReport')
        : null;

  const enrichedItems = useMemo(() => {
    if (!report) return [];
    return (report.verdicts ?? []).map((v, idx) =>
      enrichVerdictItem(
        v,
        idx,
        report.references ?? [],
        report.extracted_citations ?? [],
        lang
      )
    );
  }, [report, lang]);

  const filteredItems = useMemo(() => {
    return enrichedItems.filter((item) => {
      if (filterLabel !== 'all' && item.verdict.label !== filterLabel) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          item.citedMeta.title.toLowerCase().includes(q) ||
          item.citedMeta.authors.toLowerCase().includes(q) ||
          item.inText.toLowerCase().includes(q) ||
          item.verdict.citation_raw.toLowerCase().includes(q) ||
          item.marker.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [enrichedItems, filterLabel, searchQuery]);

  async function handleOverride(
    verdict: Verdict,
    req: Parameters<typeof api.overrideVerdict>[1]
  ) {
    const targetEssayId = report?.essay_id ?? essayId ?? 0;
    await overrideMutation.mutateAsync({
      essayId: targetEssayId,
      verdictId: verdict.citation_id,
      req,
    });
  }

  const renderFieldStatusBadge = (fieldInfo: {
    status: FieldStatus;
    label?: string;
  }) => {
    switch (fieldInfo.status) {
      case 'match':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            <Check className="h-3 w-3" /> {fieldInfo.label || '100% Match'}
          </span>
        );
      case 'partial':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
            <AlertTriangle className="h-3 w-3" /> {fieldInfo.label || 'Partial'}
          </span>
        );
      case 'mismatch':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300 border border-red-200 dark:border-red-800">
            <XCircle className="h-3 w-3" /> {fieldInfo.label || 'Diff'}
          </span>
        );
      case 'missing':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
            — Missing
          </span>
        );
    }
  };

  if (errorMessage) {
    return (
      <Alert variant="destructive" className="card p-6">
        <AlertCircle className="h-5 w-5" />
        <AlertTitle className="font-medium">
          {t('common.error')}: {errorMessage}
        </AlertTitle>
        <AlertDescription>
          <Link
            to="/history"
            className="text-indigo-600 dark:text-indigo-400 hover:underline mt-2 inline-block"
          >
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

  // Pick active citation item (defaulting to first academic issue or [1])
  const defaultItem =
    filteredItems.find(
      (i) =>
        i.verdict.label === 'metadata_error' ||
        i.verdict.label === 'suspected_hallucination'
    ) ||
    filteredItems[0] ||
    enrichedItems[0];

  const activeItem =
    filteredItems.find((i) => i.verdict.citation_id === selectedCitationId) ||
    enrichedItems.find((i) => i.verdict.citation_id === selectedCitationId) ||
    defaultItem;

  const counts = {
    all: enrichedItems.length,
    verified: enrichedItems.filter((i) => i.verdict.label === 'verified').length,
    metadata_error: enrichedItems.filter((i) => i.verdict.label === 'metadata_error')
      .length,
    suspected_hallucination: enrichedItems.filter(
      (i) => i.verdict.label === 'suspected_hallucination'
    ).length,
    unresolved: enrichedItems.filter(
      (i) => i.verdict.label === 'unresolved' || i.verdict.label === 'resource'
    ).length,
  };

  const linksOf = (c: { citation_links?: CitationLink[]; citation_link?: CitationLink }) =>
    c.citation_links?.length ? c.citation_links : c.citation_link ? [c.citation_link] : [];

  return (
    <div className="space-y-6 pb-10">
      {/* Top Breadcrumb, Filename & Export Buttons */}
      <EssayHeader
        essayId={report.essay_id}
        filename={report.filename}
        numPages={report.num_pages}
        numCitations={report.num_citations}
        styleName={report.style_profile?.style}
      />

      {/* Quick Diagnostic Sub-Pages Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <EssayActionBar essayId={id ?? ''} />
        <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
          Citation Integrity Score (CIS):{' '}
          <strong className="text-indigo-600 dark:text-indigo-400">
            {report.cis.score.toFixed(1)}%
          </strong>{' '}
          · {report.verdicts.length} citations
        </div>
      </div>

      {/* ============================================================
          Interactive Citation Debugger IDE (Real Evaluation Engine)
          ============================================================ */}
      <section className="pt-1">
        {/* IDE Window Container */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950 shadow-xl overflow-hidden">
          {/* Top Window Chrome Bar */}
          <div className="px-4 sm:px-6 py-3.5 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex items-center gap-1.5 shrink-0">
                <span className="w-3 h-3 rounded-full bg-red-400/80 inline-block" />
                <span className="w-3 h-3 rounded-full bg-amber-400/80 inline-block" />
                <span className="w-3 h-3 rounded-full bg-emerald-400/80 inline-block" />
              </div>
              <Separator orientation="vertical" className="h-4" />
              <div className="flex items-center gap-2 font-mono text-xs text-slate-700 dark:text-slate-300 truncate">
                <FileText className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
                <span className="font-semibold truncate" title={report.filename}>
                  {report.filename}
                </span>
                <span className="hidden sm:inline text-slate-400 shrink-0">
                  ({report.num_pages} pages · {report.verdicts.length} citations)
                </span>
              </div>
            </div>

            {/* Right Status Bar in Chrome */}
            <div className="flex items-center gap-2.5 shrink-0">
              <Badge
                variant="outline"
                className="font-mono text-[11px] bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700"
              >
                Style: {report.style_profile?.style || 'Academic'}
              </Badge>
              <div
                className="inline-flex items-center gap-2 px-3 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/90 border border-indigo-200/80 dark:border-indigo-800 text-xs font-mono"
                title="Citation Integrity Score"
              >
                <span className="text-slate-500 dark:text-slate-400">CIS:</span>
                <span className="font-bold text-indigo-700 dark:text-indigo-300">
                  {report.cis.score.toFixed(1)} / 100
                </span>
              </div>
            </div>
          </div>

          {/* Empty State if PDF had zero citations */}
          {enrichedItems.length === 0 ? (
            <div className="p-12 text-center bg-white dark:bg-slate-950">
              <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                {lang === 'vi'
                  ? 'Không phát hiện trích dẫn nào trong tài liệu PDF này.'
                  : 'No citations were extracted from this PDF document.'}
              </p>
            </div>
          ) : (
            /* Split-Pane Debugger Body */
            <div className="grid lg:grid-cols-12">
              {/* Left Pane: Extracted Citations Queue (5 cols) */}
              <div className="lg:col-span-5 border-b lg:border-b-0 lg:border-r border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/50 p-4 sm:p-5 flex flex-col justify-between">
                <div>
                  {/* Search & Verdict Filter Chips */}
                  <div className="space-y-2 mb-3.5">
                    <div className="flex items-center gap-2">
                      <div className="relative flex-1">
                        <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                          type="text"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          placeholder={
                            lang === 'vi'
                              ? 'Tìm theo tiêu đề, tác giả, [số]...'
                              : 'Filter by title, author, [#]...'
                          }
                          className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
                        />
                      </div>
                      <span className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400 shrink-0">
                        {filteredItems.length} / {enrichedItems.length}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-1.5">
                      {(
                        [
                          ['all', `All (${counts.all})`],
                          ['verified', `✓ Verified (${counts.verified})`],
                          ['metadata_error', `⚠ Metadata (${counts.metadata_error})`],
                          [
                            'suspected_hallucination',
                            `✕ Hallucination (${counts.suspected_hallucination})`,
                          ],
                          ...(counts.unresolved > 0
                            ? [['unresolved', `— Other (${counts.unresolved})`]]
                            : []),
                        ] as const
                      ).map(([key, labelText]) => (
                        <button
                          key={key}
                          type="button"
                          onClick={() => setFilterLabel(key)}
                          className={`px-2 py-0.5 rounded-md text-[10px] font-mono font-semibold transition-colors border ${
                            filterLabel === key
                              ? 'bg-indigo-600 text-white border-indigo-600'
                              : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800 hover:border-slate-300'
                          }`}
                        >
                          {labelText}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Clickable Citation Cards List */}
                  <div
                    className="space-y-2.5 max-h-[480px] overflow-y-auto pr-1"
                    role="listbox"
                    aria-label="Extracted Citations"
                  >
                    {filteredItems.map((cit) => {
                      const isSelected =
                        activeItem?.verdict.citation_id === cit.verdict.citation_id;
                      return (
                        <button
                          key={cit.verdict.citation_id}
                          type="button"
                          role="option"
                          aria-selected={isSelected}
                          onClick={() => setSelectedCitationId(cit.verdict.citation_id)}
                          className={`w-full text-left p-3.5 rounded-xl border transition-all duration-150 ${
                            isSelected
                              ? 'bg-indigo-50/70 dark:bg-indigo-950/50 border-indigo-500 dark:border-indigo-500 shadow-sm ring-1 ring-indigo-500/30'
                              : 'bg-white dark:bg-slate-900 border-slate-200/90 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2 mb-1.5">
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 shrink-0">
                                {cit.marker}
                              </span>
                              <span className="font-semibold text-sm text-slate-900 dark:text-white truncate">
                                {cit.inText}
                              </span>
                            </div>
                            <span className="font-mono text-[11px] text-slate-400 shrink-0">
                              {cit.pageLabel}
                            </span>
                          </div>

                          <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-1 mb-2.5 font-serif italic">
                            &ldquo;{cit.citedMeta.title}&rdquo;
                          </p>

                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span
                                className={`verdict-badge ${cit.verdictBadgeClass} text-[10px] px-2.5 py-0.5 font-mono`}
                              >
                                {cit.verdictText}
                              </span>
                              <span
                                className={`mapping-badge ${cit.mappingBadgeClass} text-[10px] px-2 py-0.5 font-mono`}
                              >
                                {cit.mappingText}
                              </span>
                            </div>
                            <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                              Conf:{' '}
                              <strong className="text-slate-800 dark:text-slate-200">
                                {cit.confidencePct}%
                              </strong>
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Document Context Snippet Box */}
                {activeItem && (
                  <div className="mt-5 p-3.5 rounded-xl bg-slate-100/80 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800">
                    <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1.5">
                      <span>MANUSCRIPT CONTEXT ({activeItem.pageLabel})</span>
                      <span>GROBID TEI-XML</span>
                    </div>
                    <p className="document-content text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed line-clamp-4">
                      {activeItem.contextBefore}
                      <mark className="px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-900 dark:text-indigo-200 font-semibold border-b-2 border-indigo-500">
                        {activeItem.contextHighlight}
                      </mark>
                      {activeItem.contextAfter}
                    </p>
                  </div>
                )}
              </div>

              {/* Right Pane: Reference Inspector & Symbolic Trace (7 cols) */}
              {activeItem && (
                <div className="lg:col-span-7 min-w-0 p-4 sm:p-6 bg-white dark:bg-slate-950 flex flex-col justify-between">
                  <div>
                    {/* Inspector Header */}
                    <div className="flex flex-wrap items-start justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-mono text-xs text-slate-400">
                            INSPECTING REFERENCE
                          </span>
                          <span className="font-mono text-xs font-bold text-indigo-600 dark:text-indigo-400">
                            {activeItem.marker}
                          </span>
                          {linksOf(activeItem.verdict)[0]?.reference_id && (
                            <span className="font-mono text-[11px] text-slate-400">
                              · {linksOf(activeItem.verdict)[0]?.reference_id}
                            </span>
                          )}
                        </div>
                        <h3 className="font-display text-lg sm:text-xl font-bold text-slate-900 dark:text-white leading-snug">
                          {activeItem.citedMeta.title}
                        </h3>
                      </div>

                      <div className="flex items-center gap-2 flex-wrap shrink-0">
                        <span
                          className={`verdict-badge ${activeItem.verdictBadgeClass} text-xs px-3 py-1 font-mono`}
                        >
                          {activeItem.verdictText}
                        </span>
                        <span
                          className={`mapping-badge ${activeItem.mappingBadgeClass} text-xs px-2.5 py-1 font-mono`}
                        >
                          {activeItem.mappingText}
                        </span>
                      </div>
                    </div>

                    {/* Explanation Callout */}
                    <div className="my-4 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 flex items-start gap-3">
                      <Scale className="h-4 w-4 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
                      <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                        <span className="font-semibold text-slate-900 dark:text-white mr-1.5">
                          {lang === 'vi'
                            ? 'Kết luận suy diễn:'
                            : 'Neuro-Symbolic Reasoning:'}
                        </span>
                        {activeItem.explanationText}
                      </div>
                    </div>

                    {/* Inspector Tabs: Metadata Diff | Symbolic Rules | Federated Sources */}
                    <Tabs defaultValue="diff" className="w-full">
                      <TabsList className="w-full justify-start bg-slate-100 dark:bg-slate-900 p-1 rounded-xl">
                        <TabsTrigger value="diff" className="flex-1 text-xs font-mono">
                          {lang === 'vi' ? '1. Đối chiếu Metadata' : '1. Metadata Diff'}
                        </TabsTrigger>
                        <TabsTrigger value="rules" className="flex-1 text-xs font-mono">
                          {lang === 'vi'
                            ? `2. Luật Suy diễn (${activeItem.rules.length})`
                            : `2. Symbolic Rules (${activeItem.rules.length})`}
                        </TabsTrigger>
                        <TabsTrigger value="sources" className="flex-1 text-xs font-mono">
                          {lang === 'vi' ? '3. Nguồn Truy hồi' : '3. Source Retrieval'}
                        </TabsTrigger>
                      </TabsList>

                      {/* TAB 1: Side-by-side Metadata Diff */}
                      <TabsContent value="diff" className="mt-4">
                        <div className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
                          <table className="w-full table-fixed text-left border-collapse">
                            <thead>
                              <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] font-mono uppercase text-slate-500 dark:text-slate-400">
                                <th className="py-2.5 px-3 w-[68px]">Field</th>
                                <th className="py-2.5 px-3">Cited in Manuscript</th>
                                <th className="py-2.5 px-3">Canonical Retrieved</th>
                                <th className="py-2.5 px-3 w-[116px] text-right">Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800 text-xs">
                              {(
                                [
                                  ['Title', 'title'],
                                  ['Authors', 'authors'],
                                  ['Year', 'year'],
                                  ['Venue', 'venue'],
                                  ['DOI', 'doi'],
                                ] as const
                              ).map(([label, key]) => (
                                <tr
                                  key={key}
                                  className="hover:bg-slate-50/70 dark:hover:bg-slate-900/40"
                                >
                                  <td className="py-2.5 px-3 font-mono font-medium text-slate-500 dark:text-slate-400 align-top">
                                    {label}
                                  </td>
                                  <td className="py-2.5 px-3 text-slate-800 dark:text-slate-200 font-medium align-top break-words [overflow-wrap:anywhere]">
                                    {activeItem.citedMeta[key]}
                                  </td>
                                  <td className="py-2.5 px-3 font-mono text-slate-600 dark:text-slate-300 align-top break-words [overflow-wrap:anywhere]">
                                    {activeItem.retrievedMeta ? (
                                      key === 'doi' &&
                                      activeItem.retrievedMeta.doi !== '—' ? (
                                        <a
                                          href={
                                            activeItem.retrievedMeta.doi.startsWith('http')
                                              ? activeItem.retrievedMeta.doi
                                              : `https://doi.org/${activeItem.retrievedMeta.doi}`
                                          }
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="inline-flex items-center gap-1 text-indigo-600 dark:text-indigo-400 hover:underline break-all"
                                        >
                                          <span>{activeItem.retrievedMeta.doi}</span>
                                          <ExternalLink className="h-3 w-3 shrink-0" />
                                        </a>
                                      ) : (
                                        activeItem.retrievedMeta[key]
                                      )
                                    ) : (
                                      <span className="text-red-500 dark:text-red-400 italic">
                                        No canonical record found
                                      </span>
                                    )}
                                  </td>
                                  <td className="py-2.5 px-3 text-right whitespace-nowrap align-top">
                                    {renderFieldStatusBadge(activeItem.fieldStatus[key])}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>

                        {/* Raw Bibliography Entry Box */}
                        <div className="mt-3 p-3 rounded-xl bg-slate-50/80 dark:bg-slate-900/60 border border-slate-200/70 dark:border-slate-800 text-xs">
                          <span className="font-mono text-[10px] uppercase tracking-wider text-slate-400 block mb-1">
                            {lang === 'vi'
                              ? 'Chuỗi Trích dẫn Gốc trong Tài liệu (Raw Extracted String)'
                              : 'Raw Extracted Reference String'}
                          </span>
                          <p className="font-mono text-slate-700 dark:text-slate-300 break-words leading-relaxed">
                            {activeItem.verdict.citation_raw}
                          </p>
                        </div>
                      </TabsContent>

                      {/* TAB 2: Symbolic Rules Trace */}
                      <TabsContent value="rules" className="mt-4">
                        <div className="space-y-2.5">
                          {activeItem.rules.map((rule) => (
                            <div
                              key={rule.code}
                              className={`p-3.5 rounded-xl border font-mono text-xs ${
                                rule.status === 'passed'
                                  ? 'bg-emerald-50/50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800/70'
                                  : rule.status === 'warning'
                                    ? 'bg-amber-50/50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800/70'
                                    : 'bg-red-50/50 dark:bg-red-950/30 border-red-200 dark:border-red-800/70'
                              }`}
                            >
                              <div className="flex items-center justify-between gap-2 mb-1">
                                <div className="flex items-center gap-2 min-w-0">
                                  <span className="px-2 py-0.5 rounded bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-bold text-[11px] shrink-0">
                                    {rule.code}
                                  </span>
                                  <span className="font-bold text-slate-900 dark:text-white truncate">
                                    {rule.name}
                                  </span>
                                </div>
                                <span
                                  className={`text-[11px] font-bold uppercase shrink-0 ${
                                    rule.status === 'passed'
                                      ? 'text-emerald-700 dark:text-emerald-400'
                                      : rule.status === 'warning'
                                        ? 'text-amber-700 dark:text-amber-400'
                                        : 'text-red-700 dark:text-red-400'
                                  }`}
                                >
                                  {rule.status === 'passed'
                                    ? '✓ TRIGGERED (PASS)'
                                    : rule.status === 'warning'
                                      ? '⚠ TRIGGERED (WARN)'
                                      : '✕ TRIGGERED (FAIL)'}
                                </span>
                              </div>
                              <p className="text-slate-600 dark:text-slate-300 text-[11px] pl-1">
                                {rule.condition}
                              </p>
                            </div>
                          ))}

                          {/* Neural Feature Vector Telemetry Strip */}
                          {activeItem.verdict.features && (
                            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 font-mono text-[11px] text-slate-600 dark:text-slate-400 flex flex-wrap items-center gap-x-4 gap-y-1">
                              <span className="font-semibold text-slate-800 dark:text-slate-200">
                                Neural Features:
                              </span>
                              {activeItem.verdict.features.title_sim_fuzzy !== undefined && (
                                <span>
                                  title_fuzzy=
                                  {activeItem.verdict.features.title_sim_fuzzy.toFixed(2)}
                                </span>
                              )}
                              {activeItem.verdict.features.author_jaccard !== undefined && (
                                <span>
                                  author_jaccard=
                                  {activeItem.verdict.features.author_jaccard.toFixed(2)}
                                </span>
                              )}
                              {activeItem.verdict.features.year_distance !== undefined && (
                                <span>
                                  year_dist={activeItem.verdict.features.year_distance}
                                </span>
                              )}
                              {activeItem.verdict.features.doi_exact_match !== undefined && (
                                <span>
                                  doi_match={activeItem.verdict.features.doi_exact_match}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </TabsContent>

                      {/* TAB 3: Multi-Source Federation */}
                      <TabsContent value="sources" className="mt-4">
                        <div className="grid sm:grid-cols-2 gap-3">
                          {activeItem.sources.map((src) => (
                            <div
                              key={src.name}
                              className={`p-3.5 rounded-xl border flex items-center justify-between gap-2 ${
                                src.status === 'matched'
                                  ? 'bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800/70'
                                  : src.status === 'partial'
                                    ? 'bg-amber-50/40 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800/70'
                                    : 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800'
                              }`}
                            >
                              <div className="min-w-0">
                                <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                                  {src.name}
                                </p>
                                <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400 mt-0.5">
                                  Sim: {src.score}
                                  {src.matchedFields.length > 0 &&
                                    ` · Fields: ${src.matchedFields.join(', ')}`}
                                </p>
                                {(src.url || src.doi) && (
                                  <a
                                    href={
                                      src.url ||
                                      (src.doi?.startsWith('http')
                                        ? src.doi
                                        : `https://doi.org/${src.doi}`)
                                    }
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1 text-[11px] font-mono text-indigo-600 dark:text-indigo-400 hover:underline mt-1"
                                  >
                                    <span>
                                      {lang === 'vi' ? 'Mở bản ghi nguồn' : 'Open Source Record'}
                                    </span>
                                    <ExternalLink className="h-3 w-3" />
                                  </a>
                                )}
                              </div>
                              <span
                                className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded shrink-0 ${
                                  src.status === 'matched'
                                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200'
                                    : src.status === 'partial'
                                      ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                                      : 'bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                                }`}
                              >
                                {src.status === 'matched'
                                  ? 'MATCH'
                                  : src.status === 'partial'
                                    ? 'CANDIDATE'
                                    : 'NO HIT'}
                              </span>
                            </div>
                          ))}
                        </div>
                      </TabsContent>
                    </Tabs>
                  </div>

                  {/* Inspector Footer Bar with Instructor Override & Full Logic Trace Link */}
                  <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
                    <div className="flex items-center gap-3 flex-wrap">
                      <div className="flex items-center gap-2">
                        <Shield className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                        <span>
                          {lang === 'vi'
                            ? 'Giảng viên có thể Ghi đè nhãn (Override Verdict) kèm lý do kiểm toán.'
                            : 'Instructors can Override Verdicts with mandatory audit logging.'}
                        </span>
                      </div>
                      <OverrideControls
                        verdict={activeItem.verdict}
                        onOverride={(req) => handleOverride(activeItem.verdict, req)}
                      />
                    </div>

                    <Link
                      to={`/verification/report/${report.essay_id}/trace`}
                      className="inline-flex items-center gap-1 font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      <span>
                        {lang === 'vi' ? 'Mở toàn bộ Inspector' : 'Open Full Inspector'}
                      </span>
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
