import { useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { type Verdict } from '@/api/client';
import { RuleInspector } from '@/components/RuleInspector';
import { VerdictBadge } from '@/components/VerdictBadge';
import {
  getSearchStepDescription,
  getVerdictExplanation,
  isUrlResource,
} from '@/lib/verdictExplanation';
import { useEssayPolling } from '@/hooks/useEssayPolling';
import { EssayHeader } from './essay/EssayHeader';
import { EssayActionBar } from './essay/EssayActionBar';
import {
  Loader2,
  AlertCircle,
  CheckCircle,
  XCircle,
  HelpCircle,
  ChevronRight,
  Scale,
  GitBranch,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

/* ============================================================
   SourceLogic — Logic Trace Page (Scholarly Precision v2.0)
   Shows step-by-step verification trace for each citation
   ============================================================ */

type TraceStepStatus = 'pending' | 'active' | 'completed' | 'error';

interface TraceStep {
  id: string;
  label: string;
  description?: string;
  status: TraceStepStatus;
  detail?: string;
  tag: string;
}

function getStepStatusColor(status: TraceStepStatus): {
  bg: string;
  border: string;
  icon: React.ReactNode;
  text: string;
} {
  switch (status) {
    case 'completed':
      return {
        bg: 'bg-emerald-50/70 dark:bg-emerald-950/30',
        border: 'border-emerald-200 dark:border-emerald-800',
        icon: <CheckCircle className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />,
        text: 'text-emerald-700 dark:text-emerald-300',
      };
    case 'active':
      return {
        bg: 'bg-amber-50/70 dark:bg-amber-950/30',
        border: 'border-amber-200 dark:border-amber-800',
        icon: <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />,
        text: 'text-amber-700 dark:text-amber-300',
      };
    case 'error':
      return {
        bg: 'bg-red-50/70 dark:bg-red-950/30',
        border: 'border-red-200 dark:border-red-800',
        icon: <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />,
        text: 'text-red-700 dark:text-red-300',
      };
    default:
      return {
        bg: 'bg-slate-50 dark:bg-slate-900',
        border: 'border-slate-200 dark:border-slate-800',
        icon: <HelpCircle className="h-4 w-4 text-slate-400" />,
        text: 'text-slate-600 dark:text-slate-300',
      };
  }
}

function buildTraceSteps(verdict: Verdict, lang: 'vi' | 'en'): TraceStep[] {
  const sources = verdict.matched_sources ?? [];
  const f = verdict.features;
  const urlStatus = verdict.url_status ?? f?.url_status;
  const urlCode = verdict.url_status_code ?? f?.url_status_code;

  const featureParts: string[] = [];
  if (f?.title_sim_fuzzy !== undefined) {
    featureParts.push(`title_fuzzy=${f.title_sim_fuzzy.toFixed(2)}`);
  }
  if (f?.title_sim_semantic !== undefined && f.title_sim_semantic > 0) {
    featureParts.push(`title_semantic=${f.title_sim_semantic.toFixed(2)}`);
  }
  if (f?.author_jaccard !== undefined) {
    featureParts.push(`author_jaccard=${f.author_jaccard.toFixed(2)}`);
  }
  if (f?.year_distance !== undefined) {
    featureParts.push(`year_dist=${f.year_distance}`);
  }
  if (f?.venue_sim !== undefined && f.venue_sim > 0) {
    featureParts.push(`venue_sim=${f.venue_sim.toFixed(2)}`);
  }
  if (f?.doi_exact_match !== undefined) {
    featureParts.push(`doi_match=${String(f.doi_exact_match)}`);
  }
  if (f?.content_alignment_score !== undefined && f.content_alignment_score > 0) {
    featureParts.push(
      `content_align=${f.content_alignment_score.toFixed(2)} (${f.content_alignment_confidence || 'checked'})`
    );
  }
  if (urlStatus) {
    const codeStr = urlCode ? ` HTTP ${urlCode}` : '';
    featureParts.push(`url_status=${urlStatus}${codeStr}`);
  }

  return [
    {
      id: 'parse',
      label: lang === 'vi' ? '1. Bóc tách & Ánh xạ Trích dẫn' : '1. Match the citation',
      description:
        lang === 'vi'
          ? 'Liên kết marker trong bài với mục tài liệu tham khảo tương ứng.'
          : 'Link the in-text citation to the reference in your bibliography.',
      status: 'completed',
      detail: verdict.citation_raw,
      tag: 'LAYER 1 · GROBID TEI',
    },
    {
      id: 'search',
      label:
        lang === 'vi'
          ? '2. Truy hồi Ấn phẩm Đa nguồn'
          : '2. Find the publication',
      description: getSearchStepDescription(verdict),
      status: sources.length > 0 ? 'completed' : 'pending',
      tag: 'FEDERATED RETRIEVAL',
    },
    {
      id: 'compare',
      label:
        lang === 'vi'
          ? '3. Đối chiếu Tương đồng Đa trường & Liên kết'
          : '3. Compare neural features & link status',
      description:
        lang === 'vi'
          ? 'So khớp tiêu đề (fuzzy + semantic), tác giả (Jaccard), năm xuất bản, căn chỉnh ngữ cảnh Neural và kiểm tra HTTP Link.'
          : 'Compare title (fuzzy + semantic), authors (Jaccard), year, neural context alignment, and HTTP link status.',
      status: verdict.confidence > 0 || Boolean(urlStatus) ? 'completed' : 'pending',
      detail: featureParts.length > 0 ? featureParts.join(' · ') : undefined,
      tag: 'NEURAL SIMILARITY & LINK CHECK',
    },
    {
      id: 'rules',
      label:
        lang === 'vi'
          ? '4. Kích hoạt Luật Suy diễn Hình thức'
          : '4. Apply verification checks',
      description:
        verdict.triggered_rules.length > 0
          ? lang === 'vi'
            ? `Đã kích hoạt ${verdict.triggered_rules.length} quy tắc kiểm chứng.`
            : 'Additional checks evaluated symbolic rules.'
          : lang === 'vi'
            ? 'Không phát hiện cảnh báo quy tắc bổ sung.'
            : 'No additional warnings were raised.',
      status: verdict.triggered_rules.length > 0 ? 'completed' : 'pending',
      tag: 'SYMBOLIC RULES R01–R12',
    },
    {
      id: 'verdict',
      label: lang === 'vi' ? '5. Kết luận Xác minh' : '5. Final Result',
      description: getVerdictExplanation(verdict),
      status:
        verdict.label === 'verified'
          ? 'completed'
          : verdict.label === 'suspected_hallucination'
            ? 'error'
            : verdict.label === 'metadata_error'
              ? 'active'
              : 'pending',
      tag: `CONFIDENCE ${Math.round(verdict.confidence * 100)}%`,
    },
  ];
}

function TraceStepCard({ step, isLast }: { step: TraceStep; isLast: boolean }) {
  const colors = getStepStatusColor(step.status);

  return (
    <div className="flex gap-3.5">
      <div className="flex flex-col items-center">
        <div
          className={`w-8 h-8 rounded-xl flex items-center justify-center border ${colors.bg} ${colors.border} shrink-0`}
        >
          {colors.icon}
        </div>
        {!isLast && (
          <div
            className={`w-0.5 flex-1 min-h-[36px] ${
              step.status === 'completed' || step.status === 'active'
                ? 'bg-indigo-300 dark:bg-indigo-800'
                : 'bg-slate-200 dark:bg-slate-800'
            }`}
          />
        )}
      </div>

      <div className="flex-1 pb-4 min-w-0">
        <div className={`rounded-xl border p-3.5 ${colors.bg} ${colors.border}`}>
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <h4 className={`text-xs sm:text-sm font-bold ${colors.text}`}>
              {step.label}
            </h4>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/80 dark:bg-slate-900/80 border border-slate-200/70 dark:border-slate-700 text-slate-600 dark:text-slate-300">
              {step.tag}
            </span>
          </div>
          {step.description && (
            <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">
              {step.description}
            </p>
          )}
          {step.detail && (
            <p className="text-xs text-slate-700 dark:text-slate-300 mt-2 font-mono bg-white/80 dark:bg-slate-900/80 p-2.5 rounded-lg border border-slate-200/70 dark:border-slate-800 break-words">
              {step.detail}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function VerdictTrace({
  verdict,
  index,
  lang,
  defaultExpanded = false,
}: {
  verdict: Verdict;
  index: number;
  lang: 'vi' | 'en';
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const steps = buildTraceSteps(verdict, lang);
  const urlStatus = verdict.url_status ?? verdict.features?.url_status;
  const urlCode = verdict.url_status_code ?? verdict.features?.url_status_code;

  return (
    <Card className="p-0 overflow-hidden rounded-xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3.5 p-4 bg-white dark:bg-slate-900 hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors text-left"
      >
        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 shrink-0">
          #{index + 1}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate font-serif">
            {verdict.citation_raw}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {urlStatus && (
            <span
              className={`hidden md:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                urlStatus === 'alive' || urlStatus === 'restricted_alive'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/70 dark:text-emerald-300 dark:border-emerald-800'
                  : 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950/70 dark:text-red-300 dark:border-red-800'
              }`}
            >
              {urlStatus === 'alive'
                ? `✓ HTTP ${urlCode || 200} OK`
                : urlStatus === 'restricted_alive'
                  ? `🔒 HTTP ${urlCode || 403} OK`
                  : urlStatus === 'dead_link'
                    ? `✕ HTTP ${urlCode || 404} DEAD`
                    : '✕ FAKE URL'}
            </span>
          )}
          <Badge variant="outline" className="hidden sm:inline-flex font-mono text-[10px]">
            {verdict.triggered_rules.length} rules
          </Badge>
          <VerdictBadge
            verdict={isUrlResource(verdict) ? 'resource' : verdict.label}
            size="sm"
          />
          <ChevronRight
            className={`h-4 w-4 text-slate-400 transition-transform ${
              expanded ? 'rotate-90 text-indigo-600 dark:text-indigo-400' : ''
            }`}
          />
        </div>
      </button>

      {expanded && (
        <div className="border-t border-slate-200/80 dark:border-slate-800 p-4 sm:p-5 bg-slate-50/60 dark:bg-slate-950/60 space-y-5">
          <div>
            <h5 className="text-[11px] font-mono font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
              {lang === 'vi'
                ? 'Chuỗi Suy diễn Neuro-Symbolic 5 Bước'
                : 'How the result was reached (5-Stage Trace)'}
            </h5>
            <div>
              {steps.map((step, idx) => (
                <TraceStepCard
                  key={step.id}
                  step={step}
                  isLast={idx === steps.length - 1}
                />
              ))}
            </div>
          </div>

          {verdict.triggered_rules.length > 0 && (
            <div>
              <h5 className="text-[11px] font-mono font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                {lang === 'vi'
                  ? 'Chi tiết Tập Luật Hình thức (Triggered Rules)'
                  : 'Triggered Symbolic Rules'}
              </h5>
              <RuleInspector
                triggeredRules={verdict.triggered_rules}
                verdictLabel={verdict.label}
              />
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export function LogicTracePage() {
  const { id } = useParams<{ id: string }>();
  const { i18n } = useTranslation();
  const lang: 'vi' | 'en' = i18n.language?.startsWith('vi') ? 'vi' : 'en';
  const [filterMode, setFilterMode] = useState<'all' | 'flagged' | 'verified'>('all');

  const numericId = id ? parseInt(id, 10) : null;
  const { report, error } = useEssayPolling(
    numericId !== null && !Number.isNaN(numericId) && numericId > 0 ? numericId : null,
    { errorMessage: 'Failed to load verification trace. Please try again.' }
  );

  const sortedVerdicts = useMemo(() => {
    if (!report?.verdicts) return [];
    const base = [...report.verdicts].sort((a, b) => {
      if (a.label !== 'verified' && b.label === 'verified') return -1;
      if (a.label === 'verified' && b.label !== 'verified') return 1;
      return a.confidence - b.confidence;
    });
    if (filterMode === 'flagged') {
      return base.filter((v) => v.label !== 'verified');
    }
    if (filterMode === 'verified') {
      return base.filter((v) => v.label === 'verified');
    }
    return base;
  }, [report, filterMode]);

  if (error) {
    return (
      <Alert variant="destructive" className="card p-6 rounded-2xl">
        <AlertCircle className="h-5 w-5" />
        <AlertTitle className="font-medium">Error: {error}</AlertTitle>
        <AlertDescription>
          <Link
            to="/history"
            className="text-indigo-600 dark:text-indigo-400 hover:underline mt-2 inline-block"
          >
            ← Back to Reports
          </Link>
        </AlertDescription>
      </Alert>
    );
  }

  if (!report) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 text-indigo-600 dark:text-indigo-400 animate-spin" />
        <span className="ml-3 text-slate-600 dark:text-slate-400 font-mono text-sm">
          Loading trace data...
        </span>
      </div>
    );
  }

  const totalCount = report.verdicts.length;
  const verifiedCount = report.verdicts.filter((v) => v.label === 'verified').length;
  const metaErrCount = report.verdicts.filter((v) => v.label === 'metadata_error').length;
  const hallucinationCount = report.verdicts.filter(
    (v) => v.label === 'suspected_hallucination'
  ).length;

  return (
    <div className="space-y-6 pb-10">
      {/* Shared Report Header */}
      <EssayHeader
        essayId={report.essay_id}
        filename={report.filename}
        numPages={report.num_pages}
        numCitations={report.num_citations}
        styleName={report.style_profile?.style}
      />

      {/* Shared Multi-Tab Diagnostic Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <EssayActionBar essayId={id ?? ''} />
        <div className="flex items-center gap-2 text-xs font-mono text-slate-500 dark:text-slate-400">
          <Scale className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          <span>{totalCount} citations traced</span>
        </div>
      </div>

      {/* 4 Summary Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
              Total
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              01
            </span>
          </div>
          <p className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100">
            {totalCount}
          </p>
        </Card>

        <Card className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-emerald-200/80 dark:border-emerald-900/70 shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
              Verified
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
              02
            </span>
          </div>
          <p className="text-2xl font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400">
            {verifiedCount}
          </p>
        </Card>

        <Card className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-amber-200/80 dark:border-amber-900/70 shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-amber-600 dark:text-amber-400">
              Meta Errors
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300">
              03
            </span>
          </div>
          <p className="text-2xl font-bold font-mono tabular-nums text-amber-600 dark:text-amber-400">
            {metaErrCount}
          </p>
        </Card>

        <Card className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-red-200/80 dark:border-red-900/70 shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-red-600 dark:text-red-400">
              Suspected
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300">
              04
            </span>
          </div>
          <p className="text-2xl font-bold font-mono tabular-nums text-red-600 dark:text-red-400">
            {hallucinationCount}
          </p>
        </Card>
      </div>

      {/* IDE Window Container for Symbolic Traces */}
      <Card className="p-0 overflow-hidden rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
        {/* Top Window Chrome */}
        <div className="px-4 sm:px-6 py-3.5 bg-slate-50/80 dark:bg-slate-900/90 border-b border-slate-200/80 dark:border-slate-800 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-400/80 inline-block" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80 inline-block" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80 inline-block" />
            </div>
            <Separator orientation="vertical" className="h-4" />
            <div className="flex items-center gap-2 font-mono text-xs font-semibold text-slate-700 dark:text-slate-300">
              <GitBranch className="h-3.5 w-3.5 text-violet-500" />
              <span>symbolic_verifier.py · Citation Traces ({sortedVerdicts.length})</span>
            </div>
          </div>

          <div className="flex gap-1.5 flex-wrap">
            {(
              [
                ['all', `All (${totalCount})`],
                ['flagged', `Flagged (${totalCount - verifiedCount})`],
                ['verified', `Verified (${verifiedCount})`],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setFilterMode(key)}
                className={`px-3 py-1 rounded-lg text-xs font-mono font-semibold transition-all border ${
                  filterMode === key
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'bg-white dark:bg-slate-950 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-800 hover:border-slate-300'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="p-4 sm:p-6 space-y-3">
          {sortedVerdicts.map((verdict, index) => (
            <VerdictTrace
              key={verdict.citation_id}
              verdict={verdict}
              index={index}
              lang={lang}
              defaultExpanded={index === 0}
            />
          ))}
        </div>
      </Card>
    </div>
  );
}
