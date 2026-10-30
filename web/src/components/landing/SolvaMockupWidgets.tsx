import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  Database,
  Shield,
  GitBranch,
  Scale,
  Cpu,
  Check,
  Search,
  Layers,
  Sparkles,
} from 'lucide-react';
import { type Lang } from './SolvaPrimitives';

/* ============================================================
   SOLVA FLOATING UI MOCKUP CARDS (WITH 8PX FROSTED GLASS RING)
   Placed over Impressionist Oil Paintings + 5% Film Grain Noise
   ============================================================ */

/**
 * 1. HERO DASHBOARD MOCKUP
 * Cropped off the right and bottom edge of the 660x521px oil painting frame,
 * surrounded by Solva's signature `0 0 0 8px rgba(255,255,255,0.5)` frosted glass ring.
 */
export function HeroVerificationMockup({
  lang,
  activeStep,
}: {
  lang: Lang;
  activeStep: number;
}) {
  const citations = [
    {
      marker: '[1]',
      ref: 'Vaswani et al. (2017)',
      title: 'Attention Is All You Need · NeurIPS',
      doi: '10.48550/arXiv.1706.03762',
      l1: 'MATCHED',
      l2: 'VERIFIED',
      conf: '99%',
      tone: 'emerald',
    },
    {
      marker: '[2]',
      ref: 'Devlin et al. (2019)',
      title: 'BERT: Pre-training of Deep Bidirectional Transformers',
      doi: '10.18653/v1/N19-1423',
      l1: 'MATCHED',
      l2: 'METADATA_ERROR',
      conf: '84%',
      tone: 'amber',
    },
    {
      marker: '[3]',
      ref: 'Robertson & Walker (2024)',
      title: 'Quantum Hyper-Graphs in Zero-Shot Hallucination',
      doi: '10.1038/s41586-024-99999-z',
      l1: 'MATCHED',
      l2: 'SUSPECTED_HALLUCINATION',
      conf: '11%',
      tone: 'red',
    },
  ];

  const selected = citations[activeStep % citations.length];

  return (
    <div
      style={{ backgroundColor: 'var(--solva-card-elevated)' }}
      className="solva-glass-ring rounded-[10px] w-full max-w-full lg:w-[640px] border border-[#E7E3D9]/80 dark:border-[#332F26] overflow-hidden text-left select-none"
    >
      {/* Top Window Chrome */}
      <div
        style={{ borderColor: 'var(--solva-border)' }}
        className="px-3 sm:px-4 py-2.5 sm:py-3 border-b flex items-center justify-between gap-2 bg-[#FBFAF6]/90 dark:bg-[#1E1C17] min-w-0"
      >
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="w-2.5 h-2.5 rounded-full bg-[#1C1A15]/20 dark:bg-white/20" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#1C1A15]/20 dark:bg-white/20" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#1C1A15]/20 dark:bg-white/20" />
          </div>
          <span
            style={{ color: 'var(--solva-ink)' }}
            className="text-[11px] sm:text-[12px] font-medium truncate ml-1"
          >
            thesis_citation_audit_2026.pdf
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="hidden sm:inline-block px-2 py-0.5 rounded-[5px] bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-mono text-[10px] font-medium">
            GROBID TEI · 15 APIs
          </span>
          <span
            style={{
              backgroundColor: 'var(--solva-surface)',
              color: 'var(--solva-ink)',
            }}
            className="px-2 py-0.5 rounded-[5px] font-mono text-[10px] font-semibold"
          >
            CIS: 92.4
          </span>
        </div>
      </div>

      {/* Two-Column Workspace Preview */}
      <div className="grid sm:grid-cols-12 min-w-0">
        {/* Left Queue */}
        <div
          style={{ borderColor: 'var(--solva-border)' }}
          className="sm:col-span-5 min-w-0 p-3 sm:p-3.5 border-b sm:border-b-0 sm:border-r space-y-2"
        >
          <div className="flex items-center justify-between gap-2 text-[10px] sm:text-[11px] font-mono">
            <span style={{ color: 'var(--solva-muted)' }} className="truncate">
              {lang === 'vi' ? 'TRÍCH DẪN BÓC TÁCH' : 'EXTRACTED QUEUE'}
            </span>
            <span style={{ color: 'var(--solva-ink)' }} className="font-semibold shrink-0">
              24 refs
            </span>
          </div>

          {citations.map((item, idx) => {
            const isActive = idx === activeStep % citations.length;
            return (
              <div
                key={item.marker}
                style={{
                  backgroundColor: isActive
                    ? 'var(--solva-surface)'
                    : 'transparent',
                  borderColor: isActive
                    ? 'var(--solva-ink)'
                    : 'var(--solva-border)',
                }}
                className="p-2.5 rounded-[8px] border transition-all duration-300"
              >
                <div className="flex items-center justify-between gap-1.5 mb-1">
                  <span
                    style={{ color: 'var(--solva-ink)' }}
                    className="text-[12px] font-medium truncate"
                  >
                    {item.marker} {item.ref}
                  </span>
                  <span className="font-mono text-[10px] font-semibold text-[#56524A]">
                    {item.conf}
                  </span>
                </div>
                <p
                  style={{ color: 'var(--solva-muted)' }}
                  className="text-[11px] truncate mb-1.5"
                >
                  {item.title}
                </p>
                <div className="flex items-center gap-1.5">
                  <span
                    className={`text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded ${
                      item.tone === 'emerald'
                        ? 'bg-emerald-500/12 text-emerald-700 dark:text-emerald-300'
                        : item.tone === 'amber'
                          ? 'bg-amber-500/12 text-amber-700 dark:text-amber-300'
                          : 'bg-red-500/12 text-red-700 dark:text-red-300'
                    }`}
                  >
                    {item.l2}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Live Verdict Trace */}
        <div className="sm:col-span-7 p-4 space-y-3">
          <div className="flex items-start justify-between gap-2">
            <div>
              <div
                style={{ color: 'var(--solva-muted)' }}
                className="text-[10px] font-mono uppercase tracking-wider"
              >
                {lang === 'vi' ? 'KIỂM CHỨNG ĐA NGUỒN' : 'LIVE VERDICT TRACE'}{' '}
                {selected.marker}
              </div>
              <div
                style={{ color: 'var(--solva-ink)' }}
                className="text-[14px] font-medium leading-snug mt-0.5"
              >
                {selected.title}
              </div>
            </div>
            <span
              style={{
                backgroundColor: 'var(--solva-btn-bg)',
                color: 'var(--solva-btn-fg)',
              }}
              className="px-2 py-0.5 rounded-[5px] text-[10px] font-mono shrink-0"
            >
              {selected.l1}
            </span>
          </div>

          {/* Field-by-field mini diff */}
          <div
            style={{
              backgroundColor: 'var(--solva-surface)',
              borderColor: 'var(--solva-border)',
            }}
            className="rounded-[8px] p-2.5 border space-y-1.5 text-[11px]"
          >
            <div className="flex items-center justify-between">
              <span style={{ color: 'var(--solva-muted)' }} className="font-mono">
                DOI:
              </span>
              <span
                style={{ color: 'var(--solva-ink)' }}
                className="font-mono truncate max-w-[180px]"
              >
                {selected.doi}
              </span>
              <span
                className={`font-mono text-[10px] font-semibold ${
                  selected.tone === 'red'
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-emerald-600 dark:text-emerald-400'
                }`}
              >
                {selected.tone === 'red' ? '404 Ghost' : '100% Match'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ color: 'var(--solva-muted)' }} className="font-mono">
                Rule:
              </span>
              <span style={{ color: 'var(--solva-ink)' }} className="font-mono">
                {selected.tone === 'emerald'
                  ? 'R01_EXACT_DOI_VERIFIED'
                  : selected.tone === 'amber'
                    ? 'R05_YEAR_DRIFT (2018 vs 2019)'
                    : 'R14_HALLUCINATED_SOURCE'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ color: 'var(--solva-muted)' }} className="font-mono">
                NLI Stance:
              </span>
              <span className="font-mono text-emerald-700 dark:text-emerald-300 font-medium">
                {selected.tone === 'red'
                  ? 'UNVERIFIABLE (No Abstract)'
                  : 'SUPPORTS (DeBERTa 0.94)'}
              </span>
            </div>
          </div>

          {/* Source pills */}
          <div className="space-y-1.5">
            <div
              style={{ color: 'var(--solva-muted)' }}
              className="text-[10px] font-mono uppercase"
            >
              {lang === 'vi'
                ? 'ĐỐI CHIẾU TRÊN 15+ CSDL HỌC THUẬT'
                : 'FEDERATED SCHOLARLY API WATERFALL'}
            </div>
            <div className="grid grid-cols-3 gap-1.5 text-[10px] font-mono">
              {[
                { name: 'Crossref', ms: '38ms' },
                { name: 'OpenAlex', ms: '52ms' },
                { name: 'SemanticSch', ms: '61ms' },
              ].map((s) => (
                <div
                  key={s.name}
                  style={{
                    backgroundColor: 'var(--solva-bg)',
                    borderColor: 'var(--solva-border)',
                  }}
                  className="px-2 py-1.5 rounded-[6px] border flex items-center justify-between"
                >
                  <span style={{ color: 'var(--solva-ink)' }}>{s.name}</span>
                  <span style={{ color: 'var(--solva-muted)' }}>{s.ms}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * 2. THREE FEATURE CARD FLOATING WIDGETS (288x288px inside 384x336px oil painting frame)
 */
export function FeatureCardWidget({
  index,
  lang,
}: {
  index: 0 | 1 | 2;
  lang: Lang;
}) {
  if (index === 0) {
    // Widget 1: Two-Layer Orthogonal Matrix
    return (
      <div
        style={{ backgroundColor: 'var(--solva-card-elevated)' }}
        className="solva-glass-ring w-[272px] sm:w-[288px] h-[272px] sm:h-[288px] rounded-[16px] p-4 flex flex-col justify-between text-left border border-[#E7E3D9]/70 dark:border-[#332F26]"
      >
        <div className="flex items-center justify-between">
          <span
            style={{ color: 'var(--solva-ink)' }}
            className="text-[12px] font-medium flex items-center gap-1.5"
          >
            <Layers className="w-3.5 h-3.5" />
            {lang === 'vi' ? 'Mô hình 2 Tầng Độc lập' : '2-Layer Orthogonal Output'}
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#F4F2EC] text-[#56524A]">
            L1 × L2
          </span>
        </div>

        <div className="space-y-2 my-auto">
          <div
            style={{ backgroundColor: 'var(--solva-surface)' }}
            className="p-2.5 rounded-[10px] space-y-1"
          >
            <div className="flex items-center justify-between text-[10px] font-mono">
              <span style={{ color: 'var(--solva-muted)' }}>LAYER 1 · MAPPING</span>
              <span className="text-emerald-700 dark:text-emerald-400 font-semibold">
                MATCHED
              </span>
            </div>
            <p style={{ color: 'var(--solva-ink)' }} className="text-[12px] font-medium">
              In-text [14] ↔ Bibliography #14
            </p>
          </div>

          <div
            style={{ backgroundColor: 'var(--solva-surface)' }}
            className="p-2.5 rounded-[10px] space-y-1"
          >
            <div className="flex items-center justify-between text-[10px] font-mono">
              <span style={{ color: 'var(--solva-muted)' }}>LAYER 2 · EXISTENCE</span>
              <span className="text-amber-700 dark:text-amber-400 font-semibold">
                METADATA_ERROR
              </span>
            </div>
            <p style={{ color: 'var(--solva-ink)' }} className="text-[12px] font-medium">
              DOI valid · Year drift (2020 → 2021)
            </p>
          </div>
        </div>

        <div
          style={{ borderColor: 'var(--solva-border)' }}
          className="pt-2.5 border-t flex items-center justify-between text-[11px]"
        >
          <span style={{ color: 'var(--solva-muted)' }}>
            {lang === 'vi' ? '7 nhãn L1 · 8 nhãn L2' : '7 L1 states · 8 L2 verdicts'}
          </span>
          <span
            style={{ color: 'var(--solva-ink)' }}
            className="font-mono font-semibold"
          >
            100% Orthogonal
          </span>
        </div>
      </div>
    );
  }

  if (index === 1) {
    // Widget 2: 15+ Scholarly APIs Waterfall
    const apis = [
      { name: 'Crossref REST API', status: 'DOI Exact', time: '38ms' },
      { name: 'OpenAlex Works', status: 'Work ID Match', time: '49ms' },
      { name: 'Semantic Scholar', status: 'Embedding 0.96', time: '62ms' },
      { name: 'PubMed / EuropePMC', status: 'PMID Verified', time: '54ms' },
      { name: 'SQLite FTS5 Cache', status: 'Local Hit', time: '3ms' },
    ];
    return (
      <div
        style={{ backgroundColor: 'var(--solva-card-elevated)' }}
        className="solva-glass-ring w-[272px] sm:w-[288px] h-[272px] sm:h-[288px] rounded-[16px] p-4 flex flex-col justify-between text-left border border-[#E7E3D9]/70 dark:border-[#332F26]"
      >
        <div className="flex items-center justify-between">
          <span
            style={{ color: 'var(--solva-ink)' }}
            className="text-[12px] font-medium flex items-center gap-1.5"
          >
            <Database className="w-3.5 h-3.5" />
            {lang === 'vi' ? '15+ Nguồn Học thuật' : '15+ Scholarly Indexes'}
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-semibold">
            PARALLEL
          </span>
        </div>

        <div className="space-y-1.5 my-auto">
          {apis.map((api) => (
            <div
              key={api.name}
              style={{ backgroundColor: 'var(--solva-surface)' }}
              className="px-2.5 py-1.5 rounded-[8px] flex items-center justify-between text-[11px]"
            >
              <span
                style={{ color: 'var(--solva-ink)' }}
                className="font-medium truncate"
              >
                {api.name}
              </span>
              <span className="font-mono text-[10px] text-emerald-700 dark:text-emerald-300 shrink-0 ml-2">
                {api.status} · {api.time}
              </span>
            </div>
          ))}
        </div>

        <div
          style={{ borderColor: 'var(--solva-border)' }}
          className="pt-2 border-t flex items-center justify-between text-[11px]"
        >
          <span style={{ color: 'var(--solva-muted)' }}>
            + arXiv, DBLP, DOAJ, ORCID
          </span>
          <span style={{ color: 'var(--solva-ink)' }} className="font-mono font-semibold">
            200M+ Works
          </span>
        </div>
      </div>
    );
  }

  // Widget 3: Neuro-Symbolic + DeBERTa NLI Stance
  return (
    <div
      style={{ backgroundColor: 'var(--solva-card-elevated)' }}
      className="solva-glass-ring w-[272px] sm:w-[288px] h-[272px] sm:h-[288px] rounded-[16px] p-4 flex flex-col justify-between text-left border border-[#E7E3D9]/70 dark:border-[#332F26]"
    >
      <div className="flex items-center justify-between">
        <span
          style={{ color: 'var(--solva-ink)' }}
          className="text-[12px] font-medium flex items-center gap-1.5"
        >
          <Scale className="w-3.5 h-3.5" />
          {lang === 'vi' ? 'Neuro-Symbolic & NLI' : 'Neuro-Symbolic & NLI'}
        </span>
        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1C1A15] text-[#FBFAF6]">
          R01–R20
        </span>
      </div>

      <div className="space-y-2 my-auto">
        <div
          style={{ backgroundColor: 'var(--solva-surface)' }}
          className="p-2.5 rounded-[10px] space-y-1"
        >
          <div className="flex items-center justify-between text-[10px] font-mono">
            <span style={{ color: 'var(--solva-muted)' }}>SYMBOLIC RULE GRAPH</span>
            <span className="text-emerald-700 dark:text-emerald-300 font-semibold">
              PASSED
            </span>
          </div>
          <p style={{ color: 'var(--solva-ink)' }} className="text-[11px] font-mono">
            R01_DOI ∧ R03_TITLE_SIM (0.97)
          </p>
        </div>

        <div
          style={{ backgroundColor: 'var(--solva-surface)' }}
          className="p-2.5 rounded-[10px] space-y-1.5"
        >
          <div className="flex items-center justify-between text-[10px] font-mono">
            <span style={{ color: 'var(--solva-muted)' }}>DeBERTa-v3 CLAIM STANCE</span>
            <span className="text-emerald-700 dark:text-emerald-300 font-semibold">
              SUPPORTS (94%)
            </span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-[#ECE9E0] dark:bg-[#29261F] overflow-hidden">
            <div className="h-full w-[94%] rounded-full bg-[#1C1A15] dark:bg-[#FBFAF6]" />
          </div>
        </div>
      </div>

      <div
        style={{ borderColor: 'var(--solva-border)' }}
        className="pt-2 border-t flex items-center justify-between text-[11px]"
      >
        <span style={{ color: 'var(--solva-muted)' }}>MiniLM-L6 + CrossEncoder</span>
        <span style={{ color: 'var(--solva-ink)' }} className="font-mono font-semibold">
          Explainable AI
        </span>
      </div>
    </div>
  );
}

/**
 * 3. STICKY CARD FLOATING WIDGETS (340x340px inside 667x548px oil painting frame)
 */
export function StickyCardWidget({
  index,
  lang,
}: {
  index: 0 | 1 | 2;
  lang: Lang;
}) {
  if (index === 0) {
    return (
      <div
        style={{ backgroundColor: 'var(--solva-card-elevated)' }}
        className="solva-glass-ring w-full max-w-[340px] rounded-[12px] p-5 space-y-3.5 text-left border border-[#E7E3D9]/80 dark:border-[#332F26]"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-[#1C1A15] dark:text-[#FBFAF6]" />
            <span
              style={{ color: 'var(--solva-ink)' }}
              className="text-[13px] font-medium"
            >
              GROBID TEI-XML + Cross-Validator
            </span>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/12 text-emerald-700 dark:text-emerald-300 font-semibold">
            ACTIVE
          </span>
        </div>

        <div
          style={{ backgroundColor: 'var(--solva-surface)' }}
          className="p-3 rounded-[8px] font-mono text-[11px] space-y-1.5"
        >
          <div style={{ color: 'var(--solva-muted)' }}>
            &lt;biblStruct xml:id=&quot;b12&quot;&gt;
          </div>
          <div style={{ color: 'var(--solva-ink)' }} className="pl-3">
            &lt;title&gt;Deep Residual Learning&lt;/title&gt;
          </div>
          <div style={{ color: 'var(--solva-ink)' }} className="pl-3">
            &lt;idno type=&quot;DOI&quot;&gt;10.1109/CVPR.2016.90&lt;/idno&gt;
          </div>
          <div style={{ color: 'var(--solva-muted)' }}>&lt;/biblStruct&gt;</div>
        </div>

        <div className="grid grid-cols-2 gap-2 text-[11px]">
          {['IEEE [1]–[N]', 'APA 7th (Author, Yr)', 'Vancouver (1)', 'ACM / Harvard'].map(
            (style) => (
              <div
                key={style}
                style={{
                  backgroundColor: 'var(--solva-bg)',
                  borderColor: 'var(--solva-border)',
                }}
                className="px-2.5 py-1.5 rounded-[6px] border flex items-center gap-1.5"
              >
                <Check className="w-3 h-3 text-emerald-600 shrink-0" />
                <span style={{ color: 'var(--solva-ink)' }} className="truncate">
                  {style}
                </span>
              </div>
            )
          )}
        </div>
      </div>
    );
  }

  if (index === 1) {
    return (
      <div
        style={{ backgroundColor: 'var(--solva-card-elevated)' }}
        className="solva-glass-ring w-full max-w-[340px] rounded-[12px] p-5 space-y-3.5 text-left border border-[#E7E3D9]/80 dark:border-[#332F26]"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-[#1C1A15] dark:text-[#FBFAF6]" />
            <span
              style={{ color: 'var(--solva-ink)' }}
              className="text-[13px] font-medium"
            >
              {lang === 'vi'
                ? 'Đồ thị Suy diễn & Quyền Giảng viên'
                : 'Symbolic Trace & Instructor Override'}
            </span>
          </div>
        </div>

        <div className="space-y-2">
          {[
            {
              code: 'R01_DOI_EXACT',
              desc: 'Canonical DOI verified via Crossref',
              badge: 'PASS',
              ok: true,
            },
            {
              code: 'R05_YEAR_DRIFT',
              desc: 'Cited 2018 · Published 2019 (Δ=1yr)',
              badge: 'WARN',
              ok: false,
            },
            {
              code: 'NLI_CLAIM_STANCE',
              desc: 'Manuscript claim supported by abstract',
              badge: '0.93',
              ok: true,
            },
          ].map((r) => (
            <div
              key={r.code}
              style={{ backgroundColor: 'var(--solva-surface)' }}
              className="p-2.5 rounded-[8px] flex items-center justify-between gap-2"
            >
              <div className="min-w-0">
                <div
                  style={{ color: 'var(--solva-ink)' }}
                  className="text-[11px] font-mono font-semibold"
                >
                  {r.code}
                </div>
                <div
                  style={{ color: 'var(--solva-muted)' }}
                  className="text-[11px] truncate"
                >
                  {r.desc}
                </div>
              </div>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold shrink-0 ${
                  r.ok
                    ? 'bg-emerald-500/12 text-emerald-700 dark:text-emerald-300'
                    : 'bg-amber-500/12 text-amber-700 dark:text-amber-300'
                }`}
              >
                {r.badge}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      style={{ backgroundColor: 'var(--solva-card-elevated)' }}
      className="solva-glass-ring w-full max-w-[340px] rounded-[12px] p-5 space-y-3.5 text-left border border-[#E7E3D9]/80 dark:border-[#332F26]"
    >
      <div className="flex items-center justify-between">
        <span
          style={{ color: 'var(--solva-ink)' }}
          className="text-[13px] font-medium flex items-center gap-1.5"
        >
          <Sparkles className="w-4 h-4" />
          {lang === 'vi'
            ? 'Theo dõi Tiến độ Chỉnh sửa Bản thảo'
            : 'Revision Progress & Integrity Score'}
        </span>
        <span className="text-[11px] font-mono font-bold text-emerald-700 dark:text-emerald-300">
          +26.5 CIS
        </span>
      </div>

      <div
        style={{ backgroundColor: 'var(--solva-surface)' }}
        className="p-3.5 rounded-[10px] flex items-center justify-between"
      >
        <div>
          <div style={{ color: 'var(--solva-muted)' }} className="text-[11px]">
            Draft v1 (Before Audit)
          </div>
          <div
            style={{ color: 'var(--solva-ink)' }}
            className="font-solva-serif text-[26px] leading-tight"
          >
            68.0%
          </div>
        </div>
        <div style={{ color: 'var(--solva-muted)' }} className="font-mono text-sm">
          →
        </div>
        <div className="text-right">
          <div style={{ color: 'var(--solva-muted)' }} className="text-[11px]">
            Draft v2 (Verified)
          </div>
          <div className="font-solva-serif text-[26px] leading-tight text-emerald-700 dark:text-emerald-300">
            94.5%
          </div>
        </div>
      </div>

      <div className="space-y-1.5 text-[11px]">
        <div className="flex items-center justify-between">
          <span style={{ color: 'var(--solva-muted)' }}>
            Hallucinated / Ghost DOIs resolved
          </span>
          <span style={{ color: 'var(--solva-ink)' }} className="font-mono font-semibold">
            3 → 0
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span style={{ color: 'var(--solva-muted)' }}>
            Missing bibliography entries fixed
          </span>
          <span style={{ color: 'var(--solva-ink)' }} className="font-mono font-semibold">
            4 → 0
          </span>
        </div>
      </div>
    </div>
  );
}

/**
 * 4. USE CASES / PIPELINE 4-TAB STAGE VISUAL (`668x446px` style with 8px glass ring)
 */
export function PipelineStageVisual({
  tabIndex,
  lang,
}: {
  tabIndex: number;
  lang: Lang;
}) {
  const stages = [
    {
      badge: 'STAGE 01 · GROBID TEI-XML & CROSS-VALIDATOR',
      title:
        lang === 'vi'
          ? 'Phân vùng cấu trúc bản thảo & Bóc tách tham chiếu đa chuẩn'
          : 'Structural Manuscript Segmentation & Multi-Style Reference Parsing',
      metrics: [
        { k: 'Engine', v: 'GROBID CRF/DL + Regex Cross-Validator' },
        { k: 'Supported Styles', v: 'IEEE, APA 7th, Vancouver, Harvard, ACM' },
        { k: 'Section Filtering', v: 'Body vs. Bibliography Boundary Lock' },
      ],
      sample:
        'Extracted 28 in-text markers ([1]–[28]) and mapped 27 canonical bibliography entries in 340ms.',
    },
    {
      badge: 'STAGE 02 · 15+ FEDERATED SCHOLARLY INDEXES',
      title:
        lang === 'vi'
          ? 'Truy hồi song song bất đồng bộ kèm bộ nhớ đệm SQLite FTS5'
          : 'Async Parallel Bibliographic Retrieval with SQLite FTS5 Cache',
      metrics: [
        { k: 'Primary Tier', v: 'Crossref, OpenAlex, Semantic Scholar, PubMed' },
        { k: 'Specialized Tier', v: 'arXiv, DBLP, Europe PMC, DOAJ, ORCID' },
        { k: 'Cache Hit Latency', v: '3.2 ms (BM25 + Trigram FTS5)' },
      ],
      sample:
        'Queried 15 APIs concurrently · Deduplicated 64 candidate records · Ranked top canonical work.',
    },
    {
      badge: 'STAGE 03 · NEURO-SYMBOLIC RULE GRAPH (R01–R20)',
      title:
        lang === 'vi'
          ? 'Đối chiếu từng trường Metadata & Suy diễn luật hình thức'
          : 'Field-Level Metadata Verification & Deterministic Rule Graph',
      metrics: [
        { k: 'Title Similarity', v: 'Token Jaccard + Levenshtein + MiniLM (0.98)' },
        { k: 'Author & Year Check', v: 'Surname Fuzzy Match · ΔYear Tolerance ±1' },
        { k: 'Ghost DOI Detection', v: 'HTTP/Handle Resolution + Metadata Cross-Check' },
      ],
      sample:
        'Triggered R01_EXACT_DOI & R04_AUTHOR_OVERLAP → Verdict: VERIFIED (Confidence: 98.4%).',
    },
    {
      badge: 'STAGE 04 · SENTENCE-BERT & DeBERTa-v3 NLI STANCE',
      title:
        lang === 'vi'
          ? 'Kiểm chứng ngữ nghĩa câu trích dẫn & Thái độ đồng thuận/bác bỏ'
          : 'Contextual Claim-to-Abstract Semantic & Stance Verification',
      metrics: [
        { k: 'Bi-Encoder', v: 'all-MiniLM-L6-v2 Dense Cosine Similarity' },
        { k: 'Cross-Encoder', v: 'ms-marco-MiniLM-L-6-v2 Precision Re-ranker' },
        { k: 'Stance Classifier', v: 'DeBERTa-v3 NLI (SUPPORTS / REFUTES / NEUTRAL)' },
      ],
      sample:
        'In-text claim entails retrieved abstract (SUPPORTS: 0.94 · REFUTES: 0.01 · NEUTRAL: 0.05).',
    },
  ];

  const active = stages[tabIndex] || stages[0];

  return (
    <div
      style={{ backgroundColor: 'var(--solva-card-elevated)' }}
      className="solva-glass-ring w-full rounded-[8px] p-5 sm:p-6 space-y-4 text-left border border-[#E7E3D9]/80 dark:border-[#332F26]"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-[#E7E3D9] dark:border-[#332F26]">
        <span
          style={{ color: 'var(--solva-muted)' }}
          className="font-mono text-[11px] font-semibold tracking-wider"
        >
          {active.badge}
        </span>
        <span className="px-2 py-0.5 rounded bg-emerald-500/12 text-emerald-700 dark:text-emerald-300 font-mono text-[10px] font-semibold">
          LIVE PIPELINE
        </span>
      </div>

      <h5
        style={{ color: 'var(--solva-ink)' }}
        className="font-solva-serif font-light text-[22px] sm:text-[26px] leading-[1.2] tracking-[-0.04em]"
      >
        {active.title}
      </h5>

      <div className="space-y-2">
        {active.metrics.map((m) => (
          <div
            key={m.k}
            style={{ backgroundColor: 'var(--solva-surface)' }}
            className="px-3.5 py-2.5 rounded-[8px] flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[12px]"
          >
            <span style={{ color: 'var(--solva-muted)' }} className="font-mono">
              {m.k}
            </span>
            <span
              style={{ color: 'var(--solva-ink)' }}
              className="font-medium sm:text-right"
            >
              {m.v}
            </span>
          </div>
        ))}
      </div>

      <div
        style={{
          backgroundColor: 'var(--solva-bg)',
          borderColor: 'var(--solva-border)',
        }}
        className="p-3 rounded-[8px] border font-mono text-[11px] flex items-center gap-2"
      >
        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
        <span style={{ color: 'var(--solva-ink)' }}>{active.sample}</span>
      </div>
    </div>
  );
}

/**
 * 5. BOTTOM CTA MOCKUP CARD (`800x533px` cropped style inside 588x376px painterly frame)
 */
export function BottomCTAMockup({ lang }: { lang: Lang }) {
  return (
    <div
      style={{ backgroundColor: 'var(--solva-card-elevated)' }}
      className="solva-glass-ring rounded-[8px] p-5 space-y-3.5 text-left border border-[#E7E3D9]/80 dark:border-[#332F26]"
    >
      <div className="flex items-center justify-between border-b border-[#E7E3D9] dark:border-[#332F26] pb-3">
        <div>
          <div
            style={{ color: 'var(--solva-muted)' }}
            className="text-[10px] font-mono uppercase"
          >
            {lang === 'vi'
              ? 'BÁO CÁO KIỂM CHỨNG TOÀN DIỆN'
              : 'CITATION INTEGRITY AUDIT REPORT'}
          </div>
          <div
            style={{ color: 'var(--solva-ink)' }}
            className="text-[15px] font-medium mt-0.5"
          >
            graduation_thesis_final_v3.pdf
          </div>
        </div>
        <span
          style={{
            backgroundColor: 'var(--solva-btn-bg)',
            color: 'var(--solva-btn-fg)',
          }}
          className="px-2.5 py-1 rounded-[6px] font-mono text-[11px] font-semibold"
        >
          CIS 96.2 / 100
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        {[
          { label: 'VERIFIED', val: '34', color: 'text-emerald-700 dark:text-emerald-300' },
          { label: 'METADATA DRIFT', val: '2', color: 'text-amber-700 dark:text-amber-300' },
          { label: 'HALLUCINATED', val: '0', color: 'text-[#1C1A15] dark:text-[#FBFAF6]' },
        ].map((stat) => (
          <div
            key={stat.label}
            style={{ backgroundColor: 'var(--solva-surface)' }}
            className="p-2.5 rounded-[8px]"
          >
            <div className={`font-solva-serif text-[24px] leading-none ${stat.color}`}>
              {stat.val}
            </div>
            <div
              style={{ color: 'var(--solva-muted)' }}
              className="text-[9px] font-mono mt-1"
            >
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      <div
        style={{ backgroundColor: 'var(--solva-surface)' }}
        className="p-3 rounded-[8px] flex items-center justify-between text-[11px]"
      >
        <span style={{ color: 'var(--solva-ink)' }} className="font-medium">
          {lang === 'vi'
            ? 'Sẵn sàng xuất báo cáo PDF / JSON & lưu vết Audit'
            : 'Ready for PDF / JSON export & instructor sign-off'}
        </span>
        <span className="font-mono text-emerald-700 dark:text-emerald-300 font-semibold">
          100% Traceable
        </span>
      </div>
    </div>
  );
}
