import { useState, useEffect, useContext } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AuthContext } from '@/contexts/AuthContext';
import {
  FileSearch,
  Database,
  Shield,
  ArrowRight,
  CheckCircle2,
  GitBranch,
  Scale,
  AlertTriangle,
  XCircle,
  Layers,
  FileText,
  Users,
  GraduationCap,
  Sliders,
  Check,
  BookOpen,
  Cpu,
  ChevronRight,
  ChevronDown,
  Globe,
  Play,
  Pause,
  Menu,
  X,
  Plus,
  Minus,
  Sparkles,
  Lock,
  Eye,
} from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ThemeToggle } from '@/contexts/ThemeContext';
import {
  type Lang,
  SolvaScrollReveal,
  SolvaEyebrow,
  SolvaTwoToneHeading,
  SolvaButton,
  SolvaPainterlyFrame,
  SolvaStickyStackCard,
  SolvaAnimatedMetric,
} from '@/components/landing/SolvaPrimitives';
import {
  HeroVerificationMockup,
  FeatureCardWidget,
  StickyCardWidget,
  PipelineStageVisual,
  BottomCTAMockup,
  CohortBatchAuditWidget,
  SolvaLiveNumber,
  useFloralCardAnimation,
} from '@/components/landing/SolvaMockupWidgets';
import { ScholarlySourceLogo } from '@/components/landing/ScholarlySourceLogos';

/* ============================================================
   CITRA (SourceLogic) — Warm Editorial AI SaaS Landing Page
   1:1 Architectural & Visual Implementation of Solva Template
   ============================================================ */

interface DemoCitation {
  id: string;
  marker: string;
  inText: string;
  page: string;
  contextBefore: string;
  contextAfter: string;
  verdict: 'VERIFIED' | 'METADATA_ERROR' | 'SUSPECTED_HALLUCINATION' | 'UNRESOLVED';
  verdictBadgeClass: string;
  mappingStatus: 'MATCHED' | 'MISSING_REFERENCE' | 'IN_TEXT_MISMATCH';
  mappingBadgeClass: string;
  confidence: number;
  citedMeta: {
    title: string;
    authors: string;
    year: string;
    venue: string;
    doi: string;
  };
  retrievedMeta: {
    title: string;
    authors: string;
    year: string;
    venue: string;
    doi: string;
  } | null;
  fieldStatus: {
    title: 'match' | 'partial' | 'mismatch' | 'missing';
    authors: 'match' | 'partial' | 'mismatch' | 'missing';
    year: 'match' | 'partial' | 'mismatch' | 'missing';
    venue: 'match' | 'partial' | 'mismatch' | 'missing';
    doi: 'match' | 'partial' | 'mismatch' | 'missing';
  };
  sources: Array<{
    name: string;
    status: 'matched' | 'partial' | 'none';
    latency: string;
    score: string;
  }>;
  rules: Array<{
    code: string;
    name: string;
    condition: string;
    status: 'passed' | 'warning' | 'failed';
  }>;
  explanation: {
    en: string;
    vi: string;
  };
}

const DEMO_CITATIONS: DemoCitation[] = [
  {
    id: 'cit-1',
    marker: '[1]',
    inText: 'Vaswani et al. [1]',
    page: 'p. 2',
    contextBefore:
      'Multi-head self-attention mechanisms have fundamentally replaced recurrent architectures in sequence modeling, as originally formalized by ',
    contextAfter: ' in the Transformer architecture.',
    verdict: 'VERIFIED',
    verdictBadgeClass: 'verdict-badge-verified',
    mappingStatus: 'MATCHED',
    mappingBadgeClass: 'mapping-badge-matched',
    confidence: 99,
    citedMeta: {
      title: 'Attention Is All You Need',
      authors: 'A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit et al.',
      year: '2017',
      venue: 'Advances in Neural Information Processing Systems (NeurIPS)',
      doi: '10.48550/arXiv.1706.03762',
    },
    retrievedMeta: {
      title: 'Attention Is All You Need',
      authors: 'Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit et al.',
      year: '2017',
      venue: 'Advances in Neural Information Processing Systems 30',
      doi: '10.48550/arXiv.1706.03762',
    },
    fieldStatus: {
      title: 'match',
      authors: 'match',
      year: 'match',
      venue: 'match',
      doi: 'match',
    },
    sources: [
      { name: 'Crossref', status: 'matched', latency: '42ms', score: '100%' },
      { name: 'Semantic Scholar', status: 'matched', latency: '68ms', score: '100%' },
      { name: 'OpenAlex', status: 'matched', latency: '55ms', score: '99%' },
      { name: 'arXiv API', status: 'matched', latency: '39ms', score: '100%' },
    ],
    rules: [
      {
        code: 'R01_EXACT_DOI',
        name: 'Canonical DOI Resolution',
        condition: 'cited.doi == canonical.doi ∧ title_sim >= 0.95',
        status: 'passed',
      },
      {
        code: 'R04_AUTHOR_OVERLAP',
        name: 'Primary Author Surname Verification',
        condition: 'jaccard(cited.authors, canonical.authors) == 1.00',
        status: 'passed',
      },
      {
        code: 'R09_NLI_STANCE',
        name: 'DeBERTa-v3 Claim-Abstract Entailment',
        condition: 'stance(context, abstract) == SUPPORTS (0.96)',
        status: 'passed',
      },
    ],
    explanation: {
      en: 'Exact DOI resolution and 100% bibliographic alignment across 4 independent scholarly indexes. Claim context is entailed by abstract.',
      vi: 'Khớp chính xác DOI và đồng nhất 100% siêu dữ liệu trên 4 cơ sở dữ liệu học thuật độc lập. Ngữ cảnh trích dẫn được chứng thực bởi tóm tắt bài báo.',
    },
  },
  {
    id: 'cit-2',
    marker: '[2]',
    inText: '(Devlin et al., 2018)',
    page: 'p. 5',
    contextBefore:
      'Bidirectional masked language pre-training significantly improves downstream token-level classification tasks ',
    contextAfter: ' across biomedical and legal corpora.',
    verdict: 'METADATA_ERROR',
    verdictBadgeClass: 'verdict-badge-metadata-error',
    mappingStatus: 'MATCHED',
    mappingBadgeClass: 'mapping-badge-matched',
    confidence: 84,
    citedMeta: {
      title: 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
      authors: 'J. Devlin, M.-W. Chang, K. Lee, K. Toutanova',
      year: '2018',
      venue: 'EMNLP Conference Proceedings',
      doi: '10.18653/v1/N19-1423',
    },
    retrievedMeta: {
      title: 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
      authors: 'Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova',
      year: '2019',
      venue: 'Proceedings of NAACL-HLT 2019',
      doi: '10.18653/v1/N19-1423',
    },
    fieldStatus: {
      title: 'match',
      authors: 'match',
      year: 'mismatch',
      venue: 'mismatch',
      doi: 'match',
    },
    sources: [
      { name: 'Crossref', status: 'matched', latency: '47ms', score: '94%' },
      { name: 'OpenAlex', status: 'matched', latency: '61ms', score: '94%' },
      { name: 'DBLP', status: 'matched', latency: '52ms', score: '92%' },
      { name: 'Semantic Scholar', status: 'matched', latency: '74ms', score: '95%' },
    ],
    rules: [
      {
        code: 'R01_EXACT_DOI',
        name: 'Canonical DOI Resolution',
        condition: 'DOI 10.18653/v1/N19-1423 resolves to ACL Anthology work',
        status: 'passed',
      },
      {
        code: 'R05_YEAR_DRIFT',
        name: 'Publication Year Discrepancy',
        condition: '|cited.year (2018) - canonical.year (2019)| == 1 (arXiv vs Proc.)',
        status: 'warning',
      },
      {
        code: 'R07_VENUE_MISMATCH',
        name: 'Venue / Container Title Drift',
        condition: 'cited.venue ("EMNLP") != canonical.venue ("NAACL-HLT")',
        status: 'failed',
      },
    ],
    explanation: {
      en: 'Paper exists and DOI is valid, but manuscript cites preprint year (2018) and wrong conference venue (EMNLP instead of NAACL-HLT 2019).',
      vi: 'Bài báo có thật và DOI hợp lệ, nhưng bản thảo ghi nhầm năm bản nháp arXiv (2018) và sai tên hội nghị công bố (EMNLP thay vì NAACL-HLT 2019).',
    },
  },
  {
    id: 'cit-3',
    marker: '[3]',
    inText: '(Robertson & Walker, 2024)',
    page: 'p. 9',
    contextBefore:
      'Recent studies claim that zero-shot quantum hyper-graphs eliminate all citation hallucinations without external retrieval ',
    contextAfter: '.',
    verdict: 'SUSPECTED_HALLUCINATION',
    verdictBadgeClass: 'verdict-badge-hallucinated',
    mappingStatus: 'MATCHED',
    mappingBadgeClass: 'mapping-badge-matched',
    confidence: 11,
    citedMeta: {
      title: 'Zero-Shot Quantum Hyper-Graphs for Autonomous Citation Verification',
      authors: 'M. Robertson, L. Walker',
      year: '2024',
      venue: 'Nature Machine Intelligence, Vol. 12',
      doi: '10.1038/s42256-024-99812-x',
    },
    retrievedMeta: null,
    fieldStatus: {
      title: 'missing',
      authors: 'mismatch',
      year: 'mismatch',
      venue: 'partial',
      doi: 'mismatch',
    },
    sources: [
      { name: 'Crossref', status: 'none', latency: '51ms', score: '0%' },
      { name: 'OpenAlex', status: 'none', latency: '63ms', score: '11%' },
      { name: 'PubMed / PMC', status: 'none', latency: '58ms', score: '0%' },
      { name: 'Semantic Scholar', status: 'none', latency: '79ms', score: '9%' },
    ],
    rules: [
      {
        code: 'R12_GHOST_DOI',
        name: 'Non-Existent DOI Handle',
        condition: 'DOI 10.1038/s42256-024-99812-x returns HTTP 404 in Crossref/Handle',
        status: 'failed',
      },
      {
        code: 'R14_ZERO_TITLE_HIT',
        name: 'No Bibliographic Title Match Across 15+ APIs',
        condition: 'max_similarity(title, all_candidates) == 0.11 < threshold (0.45)',
        status: 'failed',
      },
      {
        code: 'R16_SYNTHETIC_PATTERN',
        name: 'Fabricated Reference Signature',
        condition: 'Valid journal prefix (10.1038) paired with non-existent article suffix',
        status: 'failed',
      },
    ],
    explanation: {
      en: 'High-risk AI hallucination signature: Plausible journal prefix (Nature Machine Intelligence) combined with a fabricated DOI suffix and non-existent title.',
      vi: 'Dấu hiệu trích dẫn ảo giác do AI sinh ra: Ghép tiền tố tạp chí có thật (Nature Machine Intelligence) với mã hậu tố DOI giả mạo và tiêu đề không tồn tại.',
    },
  },
  {
    id: 'cit-4',
    marker: '[4]',
    inText: 'Smith et al. (2021)',
    page: 'p. 14',
    contextBefore:
      'Cross-encoder re-ranking substantially improves top-1 candidate precision in noisy OCR documents, as demonstrated by ',
    contextAfter: '.',
    verdict: 'UNRESOLVED',
    verdictBadgeClass: 'verdict-badge-unresolved',
    mappingStatus: 'MISSING_REFERENCE',
    mappingBadgeClass: 'mapping-badge-missing',
    confidence: 0,
    citedMeta: {
      title: '[Missing from Bibliography Section]',
      authors: 'Smith et al.',
      year: '2021',
      venue: '—',
      doi: '—',
    },
    retrievedMeta: null,
    fieldStatus: {
      title: 'missing',
      authors: 'partial',
      year: 'partial',
      venue: 'missing',
      doi: 'missing',
    },
    sources: [
      { name: 'GROBID TEI Linker', status: 'none', latency: '4ms', score: 'Unlinked' },
      { name: 'Regex Cross-Validator', status: 'none', latency: '2ms', score: 'Orphan' },
    ],
    rules: [
      {
        code: 'L1_MISSING_BIB_ENTRY',
        name: 'In-Text Citation Without Bibliography Target',
        condition: 'in_text("Smith et al., 2021") has no matching biblStruct in References',
        status: 'failed',
      },
      {
        code: 'R00_PRECONDITION_HALT',
        name: 'Layer 2 Deferred Pending Reference Metadata',
        condition: 'IF reference_entry == NULL → UNRESOLVED (Requires Bibliography Entry)',
        status: 'warning',
      },
    ],
    explanation: {
      en: 'Layer 1 Consistency Error: Cited in body text on page 14, but corresponding entry is missing from the Bibliography section.',
      vi: 'Lỗi nhất quán Lớp 1: Được trích dẫn trong thân bài tại trang 14 nhưng bị thiếu mục tương ứng trong Danh mục Tài liệu tham khảo cuối bài.',
    },
  },
];

function SourceLogicLogo({ size = 24 }: { size?: number }) {
  return (
    <img
      src="/citra-logo.png"
      alt="CITRA Logo"
      width={size}
      height={size}
      loading="eager"
      decoding="async"
      className="object-contain select-none dark:brightness-150 dark:drop-shadow-[0_0_2px_rgba(255,255,255,0.45)]"
    />
  );
}

export function LandingPage() {
  const { i18n } = useTranslation();
  const lang: Lang = i18n.language?.startsWith('vi') ? 'vi' : 'en';
  const auth = useContext(AuthContext);
  const isAuthenticated = auth
    ? Boolean(
        auth.user ||
          (auth.isLoading && typeof window !== 'undefined' && localStorage.getItem('token')),
      )
    : typeof window !== 'undefined' && Boolean(localStorage.getItem('token'));

  const toggleLanguage = () => {
    const next = lang === 'en' ? 'vi' : 'en';
    void i18n.changeLanguage(next);
  };

  return (
    <div className="solva-editorial-root min-h-screen overflow-x-hidden selection:bg-[#1C1A15] selection:text-[#FBFAF6]">
      <SolvaHeader
        lang={lang}
        onToggleLanguage={toggleLanguage}
        isAuthenticated={isAuthenticated}
      />
      <main id="main-content">
        <SolvaHeroSection lang={lang} isAuthenticated={isAuthenticated} />
        <SolvaFeaturesSection lang={lang} />
        <SolvaStickySection lang={lang} isAuthenticated={isAuthenticated} />
        <SolvaInteractiveDebuggerSection lang={lang} />
        <SolvaUseCasesSection lang={lang} isAuthenticated={isAuthenticated} />
        <SolvaSecuritySection lang={lang} />
        <SolvaTaxonomyPricingSection lang={lang} isAuthenticated={isAuthenticated} />
        <SolvaClientResultsSection lang={lang} />
        <SolvaRoleTestimonialsSection lang={lang} />
        <SolvaFAQSection lang={lang} />
        <SolvaBottomCTASection lang={lang} isAuthenticated={isAuthenticated} />
      </main>
      <SolvaFooter lang={lang} />
    </div>
  );
}

/* ============================================================
   SECTION 0: FIXED SOLVA NAVBAR (`76px` height, Portal Dropdown)
   ============================================================ */
function SolvaHeader({
  lang,
  onToggleLanguage,
  isAuthenticated,
}: {
  lang: Lang;
  onToggleLanguage: () => void;
  isAuthenticated: boolean;
}) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [headerEntered, setHeaderEntered] = useState(false);

  useEffect(() => {
    const closeOnScroll = () => setDropdownOpen(false);
    window.addEventListener('scroll', closeOnScroll, { passive: true });
    let raf1 = 0;
    let raf2 = 0;
    raf1 = window.requestAnimationFrame(() => {
      raf2 = window.requestAnimationFrame(() => {
        setHeaderEntered(true);
      });
    });
    return () => {
      window.removeEventListener('scroll', closeOnScroll);
      window.cancelAnimationFrame(raf1);
      window.cancelAnimationFrame(raf2);
    };
  }, []);

  const dropdownItems =
    lang === 'vi'
      ? [
          {
            title: 'Kiến trúc 2 tầng',
            desc: 'Tách biệt Mapping & Kiểm chứng nguồn',
            href: '#architecture',
            icon: Layers,
          },
          {
            title: 'Trình gỡ lỗi trích dẫn',
            desc: 'Soi chiếu metadata & luật R01–R20',
            href: '#interactive-demo',
            icon: FileSearch,
          },
          {
            title: 'Quy trình 4 giai đoạn',
            desc: 'Từ GROBID TEI tới DeBERTa NLI',
            href: '#how-it-works',
            icon: GitBranch,
          },
          {
            title: 'Phân quyền 3 vai trò',
            desc: 'Sinh viên, Giảng viên & Quản trị',
            href: '#workspaces',
            icon: Users,
          },
        ]
      : [
          {
            title: '2-Layer Architecture',
            desc: 'Orthogonal Mapping & Verification',
            href: '#architecture',
            icon: Layers,
          },
          {
            title: 'Citation Debugger',
            desc: 'Live metadata diff & rules R01–R20',
            href: '#interactive-demo',
            icon: FileSearch,
          },
          {
            title: 'Verification Pipeline',
            desc: 'GROBID TEI to DeBERTa NLI stance',
            href: '#how-it-works',
            icon: GitBranch,
          },
          {
            title: 'Role Workspaces',
            desc: 'Student, Teacher & Admin views',
            href: '#workspaces',
            icon: Users,
          },
        ];

  return (
    <header
      style={{
        backgroundColor: 'var(--solva-bg)',
        opacity: headerEntered ? 1 : 0.001,
        transform: headerEntered ? 'translate3d(0, 0, 0)' : 'translate3d(0, -12px, 0)',
        filter: headerEntered ? 'none' : 'blur(2.5px)',
        transition:
          'opacity 620ms cubic-bezier(0.22, 1, 0.36, 1), transform 620ms cubic-bezier(0.22, 1, 0.36, 1), filter 520ms cubic-bezier(0.22, 1, 0.36, 1), background-color 200ms ease',
      }}
      className="fixed top-0 left-0 right-0 z-50 will-change-[transform,opacity,filter]"
    >
      <div className="max-w-[1280px] mx-auto px-5 sm:px-6 lg:px-[40px] h-[64px] lg:h-[76px] flex items-center justify-between gap-4">
        {/* Left: Brand Logo */}
        <div className="flex items-center lg:w-[190px] shrink-0">
          <Link
            to="/"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="inline-flex items-center gap-[8px] rounded-[6px] focus:outline-none"
          >
            <span className="w-[28px] h-[28px] rounded-[7px] bg-white dark:bg-[#1E1C17] border border-[#E7E3D9] dark:border-[#332F26] shadow-2xs flex items-center justify-center p-1 shrink-0 transition-colors">
              <SourceLogicLogo size={18} />
            </span>
            <span
              style={{ color: 'var(--solva-ink)' }}
              className="font-solva-sans text-[20px] font-medium tracking-[-0.02em] leading-none"
            >
              CITRA
            </span>
          </Link>
        </div>

        {/* Center: Solva Navigation Links + Dropdown */}
        <nav
          aria-label="Primary Navigation"
          className="hidden lg:flex items-center justify-center flex-1 gap-1"
        >
          {/* Dropdown Trigger (`Platform v` / `Kiến trúc v`) */}
          <div
            className="relative"
            onMouseLeave={() => setDropdownOpen(false)}
          >
            <button
              type="button"
              onClick={() => setDropdownOpen((prev) => !prev)}
              aria-expanded={dropdownOpen}
              style={{ color: 'var(--solva-muted)' }}
              className="inline-flex items-center gap-[6px] h-[44px] px-[12px] rounded-[8px] font-solva-sans text-[15px] font-normal hover:opacity-80 transition-opacity cursor-pointer"
            >
              <span>{lang === 'vi' ? 'Nền tảng' : 'Platform'}</span>
              <ChevronDown
                className={`w-3.5 h-3.5 transition-transform duration-200 ${
                  dropdownOpen ? 'rotate-180' : ''
                }`}
              />
            </button>

            {dropdownOpen && (
              <div className="absolute left-0 top-[44px] pt-1 z-50 animate-debugger-switch">
                <div
                  style={{
                    backgroundColor: 'var(--solva-bg)',
                    borderColor: 'var(--solva-border)',
                  }}
                  className="w-[264px] p-[8px] rounded-[12px] border shadow-[0_4px_16px_rgba(0,0,0,0.06)] space-y-0.5"
                >
                  {dropdownItems.map((item) => {
                    const Icon = item.icon;
                    return (
                      <a
                        key={item.href}
                        href={item.href}
                        onClick={() => setDropdownOpen(false)}
                        className="flex items-start gap-3 p-[10px_12px] rounded-[8px] hover:bg-[#F4F2EC] dark:hover:bg-[#1E1C17] transition-colors"
                      >
                        <Icon
                          style={{ color: 'var(--solva-ink)' }}
                          className="w-[18px] h-[18px] mt-0.5 shrink-0"
                        />
                        <div className="min-w-0">
                          <div
                            style={{ color: 'var(--solva-ink)' }}
                            className="font-solva-sans text-[14px] font-medium leading-tight"
                          >
                            {item.title}
                          </div>
                          <div
                            style={{ color: 'var(--solva-muted)' }}
                            className="font-solva-sans text-[12px] leading-snug mt-0.5"
                          >
                            {item.desc}
                          </div>
                        </div>
                      </a>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          <a
            href="#interactive-demo"
            style={{ color: 'var(--solva-muted)' }}
            className="inline-flex items-center h-[44px] px-[12px] rounded-[8px] font-solva-sans text-[15px] font-normal hover:opacity-80 transition-opacity"
          >
            {lang === 'vi' ? 'Trình gỡ lỗi' : 'Inspector'}
          </a>

          <a
            href="#how-it-works"
            style={{ color: 'var(--solva-muted)' }}
            className="inline-flex items-center h-[44px] px-[12px] rounded-[8px] font-solva-sans text-[15px] font-normal hover:opacity-80 transition-opacity"
          >
            {lang === 'vi' ? 'Quy trình' : 'Pipeline'}
          </a>

          <a
            href="#taxonomy"
            style={{ color: 'var(--solva-muted)' }}
            className="inline-flex items-center h-[44px] px-[12px] rounded-[8px] font-solva-sans text-[15px] font-normal hover:opacity-80 transition-opacity"
          >
            {lang === 'vi' ? 'Phân loại nhãn' : 'Taxonomy'}
          </a>

          <Link
            to="/pricing"
            data-testid="landing-pricing-link"
            style={{ color: 'var(--solva-muted)' }}
            className="inline-flex items-center h-[44px] px-[12px] rounded-[8px] font-solva-sans text-[15px] font-normal hover:opacity-80 transition-opacity"
          >
            {lang === 'vi' ? 'Bảng giá' : 'Pricing'}
          </Link>
        </nav>

        {/* Right: Lang, Theme, Sign In, Primary Double-Slide CTA */}
        <div className="flex items-center justify-end gap-1.5 sm:gap-2 shrink-0">
          <button
            type="button"
            onClick={onToggleLanguage}
            style={{
              backgroundColor: 'var(--solva-surface)',
              color: 'var(--solva-ink)',
            }}
            className="inline-flex items-center gap-1 h-[36px] px-2.5 rounded-[8px] font-mono text-[12px] font-medium hover:opacity-85 transition-opacity cursor-pointer"
            title={lang === 'vi' ? 'Switch to English' : 'Chuyển sang Tiếng Việt'}
          >
            <Globe className="w-3.5 h-3.5" />
            <span>{lang === 'vi' ? 'VI' : 'EN'}</span>
          </button>

          <ThemeToggle size="sm" />

          <Link
            to={isAuthenticated ? '/dashboard' : '/login'}
            style={{ color: 'var(--solva-muted)' }}
            className="hidden sm:inline-flex items-center h-[44px] px-[12px] rounded-[8px] font-solva-sans text-[15px] font-normal hover:opacity-80 transition-opacity"
          >
            Sign in
          </Link>

          <SolvaButton
            to={isAuthenticated ? '/dashboard' : '/login'}
            variant="primary"
            className="hidden sm:inline-flex"
          >
            {isAuthenticated
              ? lang === 'vi'
                ? 'Vào Workspace'
                : 'Open Workspace'
              : lang === 'vi'
                ? 'Dùng thử miễn phí'
                : 'Try CITRA Free'}
          </SolvaButton>

          {/* Mobile Hamburger Button (Solva 2-bar minimalist style) */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
            style={{
              backgroundColor: 'var(--solva-surface)',
              color: 'var(--solva-ink)',
            }}
            className="lg:hidden inline-flex items-center justify-center w-[40px] h-[40px] rounded-[8px] cursor-pointer"
          >
            {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <nav
          aria-label="Mobile Navigation"
          style={{
            backgroundColor: 'var(--solva-bg)',
            borderColor: 'var(--solva-border)',
          }}
          className="lg:hidden border-t border-b px-5 py-4 space-y-2 shadow-lg animate-debugger-switch"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
            {[
              {
                label: lang === 'vi' ? 'Kiến trúc 2 tầng' : '2-Layer Architecture',
                href: '#architecture',
              },
              {
                label: lang === 'vi' ? 'Trình gỡ lỗi trích dẫn' : 'Interactive Inspector',
                href: '#interactive-demo',
              },
              {
                label: lang === 'vi' ? 'Quy trình xử lý' : 'Verification Pipeline',
                href: '#how-it-works',
              },
              {
                label: lang === 'vi' ? 'Phân loại nhãn' : 'Verdict Taxonomy',
                href: '#taxonomy',
              },
              {
                label: lang === 'vi' ? 'Phân quyền 3 vai trò' : 'Role Workspaces',
                href: '#workspaces',
              },
              {
                label: lang === 'vi' ? 'Câu hỏi thường gặp' : 'FAQ',
                href: '#faq',
              },
            ].map((item) => (
              <a
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                style={{
                  backgroundColor: 'var(--solva-surface)',
                  color: 'var(--solva-ink)',
                }}
                className="flex items-center justify-between px-3.5 py-2.5 rounded-[10px] font-solva-sans text-[14px] font-medium"
              >
                <span>{item.label}</span>
                <ChevronRight className="w-4 h-4 opacity-60" />
              </a>
            ))}
          </div>

          <div className="pt-2 flex items-center gap-2">
            <SolvaButton
              to={isAuthenticated ? '/dashboard' : '/login'}
              variant="outline"
              fullWidth
              onClick={() => setMobileMenuOpen(false)}
            >
              Sign in
            </SolvaButton>
            <SolvaButton
              to={isAuthenticated ? '/dashboard' : '/register'}
              variant="primary"
              fullWidth
              onClick={() => setMobileMenuOpen(false)}
            >
              {lang === 'vi' ? 'Bắt đầu ngay' : 'Try CITRA Free'}
            </SolvaButton>
          </div>
        </nav>
      )}
    </header>
  );
}

/* ============================================================
   SECTION 1: HERO SECTION (`#hero`)
   2-Column Split + Painterly Oil Frame + Infinite API Ticker
   ============================================================ */
function SolvaHeroSection({
  lang,
  isAuthenticated,
}: {
  lang: Lang;
  isAuthenticated: boolean;
}) {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveStep((prev) => (prev + 1) % 3);
    }, 3200);
    return () => window.clearInterval(timer);
  }, [activeStep]);

  const scholarlyApis = [
    'Crossref',
    'OpenAlex',
    'Semantic Scholar',
    'PubMed NCBI',
    'arXiv',
    'Europe PMC',
    'DBLP',
    'DOAJ',
    'ORCID',
    'Unpaywall',
    'DataCite',
    'GROBID TEI',
  ];

  return (
    <section
      id="hero"
      className="pt-[76px] sm:pt-[88px] lg:pt-[136px] pb-[24px] sm:pb-[36px] lg:pb-[64px] px-5 sm:px-6 lg:px-[40px]"
    >
      <div className="max-w-[1200px] mx-auto flex flex-col gap-[28px] sm:gap-[36px] lg:gap-[56px]">
        {/* Top 2-Column Content */}
        <div className="flex flex-col lg:flex-row items-center justify-between gap-[28px] sm:gap-[32px] lg:gap-[24px] pt-0 lg:pt-[12px]">
          {/* Left Column (540px on Desktop) */}
          <div className="w-full lg:w-[516px] xl:w-[540px] flex flex-col items-start gap-[22px] sm:gap-[28px] lg:gap-[32px] lg:pb-[24px]">
            <div className="flex flex-col items-start gap-[16px] sm:gap-[20px] lg:gap-[24px]">
              {/* Announcement Badge (`NEW | Neuro-Symbolic v2.3 is live ->`) */}
              <SolvaScrollReveal delayMs={40} yOffset={20} blurPx={3}>
                <a
                  href="#interactive-demo"
                  className="group inline-flex items-center gap-[8px] font-solva-sans"
                >
                  <span
                    style={{
                      backgroundColor: 'var(--solva-surface)',
                      color: 'var(--solva-muted)',
                    }}
                    className="px-[6px] pt-[5px] pb-[4px] rounded-[4px] text-[12px] font-medium leading-[12px]"
                  >
                    NEW
                  </span>
                  <span
                    style={{ color: 'var(--solva-muted)' }}
                    className="text-[15px] sm:text-[16px] font-normal leading-[21px] group-hover:underline"
                  >
                    {lang === 'vi'
                      ? 'Kiểm chứng Neuro-Symbolic 2 tầng & 15+ API đã sẵn sàng'
                      : 'Two-layer Neuro-Symbolic & 15+ API engine is live'}
                  </span>
                  <ArrowRight
                    style={{ color: 'var(--solva-muted)' }}
                    className="w-[14px] h-[14px] transition-transform duration-200 group-hover:translate-x-0.5 shrink-0"
                  />
                </a>
              </SolvaScrollReveal>

              {/* H1 Two-Tone Editorial Split */}
              <SolvaTwoToneHeading
                as="h1"
                size="h1"
                delayMs={85}
                primary={
                  lang === 'vi'
                    ? 'Trợ lý kiểm chứng trích dẫn'
                    : 'The citation copilot'
                }
                secondary={
                  lang === 'vi'
                    ? 'không bao giờ bỏ sót.'
                    : 'that never hallucinates.'
                }
              />

              {/* Subtitle (400px–430px max-width, Onest 18px Regular) */}
              <SolvaScrollReveal delayMs={190} yOffset={24} blurPx={3.5}>
                <p
                  style={{ color: 'var(--solva-muted)' }}
                  className="font-solva-sans text-[17px] sm:text-[18px] font-normal leading-[25.2px] max-w-[430px]"
                >
                  {lang === 'vi'
                    ? 'CITRA bóc tách mọi trích dẫn từ bản thảo PDF, đối chiếu siêu dữ liệu trên 15+ cơ sở dữ liệu học thuật và giải thích tường minh từng luật suy diễn.'
                    : 'CITRA parses every citation in your PDF manuscript, cross-verifies metadata across 15+ scholarly indexes, and explains every rule trace.'}
                </p>
              </SolvaScrollReveal>
            </div>

            {/* CTA Buttons */}
            <SolvaScrollReveal delayMs={260} yOffset={24} blurPx={3}>
              <div className="flex flex-wrap items-center gap-3">
                <SolvaButton
                  to={isAuthenticated ? '/upload' : '/login'}
                  variant="primary"
                >
                  {isAuthenticated
                    ? lang === 'vi'
                      ? 'Tải lên Bản thảo PDF'
                      : 'Verify Manuscript PDF'
                    : lang === 'vi'
                      ? 'Dùng thử CITRA Miễn phí'
                      : 'Try CITRA Free'}
                </SolvaButton>
                <SolvaButton href="#interactive-demo" variant="outline">
                  {lang === 'vi' ? 'Xem Trình gỡ lỗi' : 'Live Citation Debugger'}
                </SolvaButton>
              </div>
            </SolvaScrollReveal>
          </div>

          {/* Right Column: Painterly Mockup Frame (`660x521px` on Desktop) */}
          <SolvaScrollReveal
            delayMs={150}
            yOffset={36}
            scaleFrom={0.975}
            blurPx={4}
            className="w-full lg:w-[660px] shrink-0"
          >
            <SolvaPainterlyFrame
              paintingSrc="/solva/hero-bg.png"
              alt="Impressionist wildflower meadow oil painting backdrop"
              className="w-full min-h-[420px] sm:min-h-[490px] lg:h-[521px] p-4 sm:p-8 lg:p-0"
            >
              <div className="lg:absolute lg:top-[52px] lg:left-[52px] lg:right-[-24px]">
                <HeroVerificationMockup
                  lang={lang}
                  activeStep={activeStep}
                  onSelectStep={setActiveStep}
                />
              </div>
            </SolvaPainterlyFrame>
          </SolvaScrollReveal>
        </div>

        {/* Bottom Infinite Edge-Masked Scholarly API Ticker (`1200x112px`) */}
        <SolvaScrollReveal delayMs={320} yOffset={20} blurPx={2.5}>
          <div className="w-full py-[10px] sm:py-[16px] lg:py-[32px] overflow-hidden solva-ticker-mask">
            <div className="animate-solva-marquee flex items-center gap-[56px] sm:gap-[72px]">
              {[...scholarlyApis, ...scholarlyApis].map((apiName, idx) => (
                <div
                  key={`${apiName}-${idx}`}
                  style={{ color: 'var(--solva-ink)' }}
                  className="inline-flex items-center gap-2.5 shrink-0 select-none opacity-80 hover:opacity-100 transition-opacity duration-200"
                >
                  <ScholarlySourceLogo
                    name={apiName}
                    size={20}
                    className="opacity-90"
                  />
                  <span className="font-solva-sans text-[17px] sm:text-[18px] font-medium tracking-[-0.03em] whitespace-nowrap">
                    {apiName}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </SolvaScrollReveal>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 2: FEATURES (`#architecture` — "What CITRA does")
   3-Column Grid (384x433px cards with Oil Paintings + 288x288 Widgets)
   ============================================================ */
function SolvaFeaturesSection({ lang }: { lang: Lang }) {
  const features = [
    {
      painting: '/solva/feature-1-bg.png',
      title:
        lang === 'vi'
          ? 'Kiểm chứng 2 tầng trực giao (L1 × L2)'
          : 'Verify across two orthogonal layers',
      desc:
        lang === 'vi'
          ? 'Tách biệt hoàn toàn tính nhất quán nội bộ văn bản (Lớp 1: Khớp trích dẫn trong bài & Danh mục) với tính xác thực thư mục bên ngoài (Lớp 2: Tồn tại công trình thực tế).'
          : 'Cleanly decouples internal manuscript consistency (Layer 1: In-text to Bibliography mapping) from external bibliographic existence (Layer 2: Canonical truth).',
    },
    {
      painting: '/solva/feature-2-bg.png',
      title:
        lang === 'vi'
          ? 'Truy hồi song song trên 15+ CSDL học thuật'
          : 'Query 15+ scholarly indexes in parallel',
      desc:
        lang === 'vi'
          ? 'Đối chiếu đồng thời trên Crossref, OpenAlex, Semantic Scholar, PubMed, arXiv, DBLP, DOAJ và ORCID kết hợp bộ nhớ đệm cục bộ SQLite FTS5 siêu tốc.'
          : 'Queries Crossref, OpenAlex, Semantic Scholar, PubMed, arXiv, DBLP, DOAJ, and ORCID concurrently with sub-10ms SQLite FTS5 local caching.',
    },
    {
      painting: '/solva/feature-3-bg.png',
      title:
        lang === 'vi'
          ? 'Suy diễn Neuro-Symbolic & Thái độ trích dẫn'
          : 'Combine symbolic rules with neural stance',
      desc:
        lang === 'vi'
          ? 'Kết hợp 20 quy tắc suy diễn hình thức (R01–R20) với mô hình Sentence-BERT và DeBERTa-v3 NLI để kiểm tra câu trích dẫn có thực sự được bài gốc ủng hộ hay không.'
          : 'Pairs 20 formal symbolic rules (R01–R20) with Sentence-BERT embeddings and DeBERTa-v3 NLI to verify whether cited abstracts actually support the claim.',
    },
  ];

  return (
    <section
      id="architecture"
      className="scroll-mt-[84px] lg:scroll-mt-[108px] py-[32px] sm:py-[48px] lg:py-[96px] px-5 sm:px-6 lg:px-[40px]"
    >
      <div className="max-w-[1200px] mx-auto flex flex-col gap-[28px] sm:gap-[36px] lg:gap-[64px]">
        {/* Section Headline */}
        <div className="flex flex-col items-start gap-[12px] sm:gap-[16px] max-w-[620px]">
          <SolvaEyebrow>
            {lang === 'vi' ? 'Kiến trúc cốt lõi của CITRA' : 'What CITRA does'}
          </SolvaEyebrow>
          <SolvaTwoToneHeading
            primary={
              lang === 'vi'
                ? 'Ba trụ cột giúp CITRA'
                : 'Three ways CITRA'
            }
            secondary={
              lang === 'vi'
                ? 'bảo vệ tính toàn vẹn học thuật.'
                : 'audits your bibliography.'
            }
          />
        </div>

        {/* 3-Column Feature Cards (`gap: 24px`) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-[24px]">
          {features.map((feat, idx) => (
            <SolvaScrollReveal
              key={feat.title}
              delayMs={idx * 95}
              yOffset={36}
              className="flex flex-col gap-[16px] min-w-0"
            >
              {/* Top 336px Painterly Visual Box */}
              <SolvaPainterlyFrame
                paintingSrc={feat.painting}
                alt={feat.title}
                className="w-full h-[320px] sm:h-[336px] p-[24px]"
              >
                <div className="w-full h-full flex items-center justify-center">
                  <FeatureCardWidget index={idx as 0 | 1 | 2} lang={lang} />
                </div>
              </SolvaPainterlyFrame>

              {/* Bottom Title (20px Onest) + Description (16px Onest) */}
              <div className="flex flex-col gap-[8px] pt-1">
                <h3
                  style={{ color: 'var(--solva-ink)' }}
                  className="font-solva-sans text-[20px] font-normal leading-[27px] tracking-[-0.02em]"
                >
                  {feat.title}
                </h3>
                <p
                  style={{ color: 'var(--solva-muted)' }}
                  className="font-solva-sans text-[16px] font-normal leading-[23.2px]"
                >
                  {feat.desc}
                </p>
              </div>
            </SolvaScrollReveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 3: STICKY FEATURES ("Why CITRA")
   3 Scroll-Linked Sticky Stacking Cards (`scale(1)` -> `scale(0.915)`)
   ============================================================ */
function SolvaStickySection({
  lang,
  isAuthenticated,
}: {
  lang: Lang;
  isAuthenticated: boolean;
}) {
  const stickyBlocks = [
    {
      painting: '/solva/sticky-1-bg.png',
      title:
        lang === 'vi'
          ? 'Bóc tách cấu trúc bằng GROBID TEI-XML, không phụ thuộc mẫu cố định'
          : 'Parsed by GROBID TEI-XML, not brittle templates',
      desc:
        lang === 'vi'
          ? 'Hệ thống kết hợp mô hình học sâu GROBID với bộ Cross-Validator đa kiểu trích dẫn (IEEE, APA 7th, Vancouver, Harvard, ACM), tự động khóa ranh giới phần Tài liệu tham khảo và xử lý các trường hợp gộp nhóm [1]–[5].'
          : 'Combines deep-learning GROBID TEI-XML segmentation with a multi-style cross-validator (IEEE, APA 7th, Vancouver, Harvard, ACM) that locks bibliography boundaries and expands grouped ranges.',
      cta: lang === 'vi' ? 'Thử nghiệm ngay' : 'Get started',
    },
    {
      painting: '/solva/sticky-2-bg.png',
      title:
        lang === 'vi'
          ? 'Tường minh từng quy tắc cho giảng viên, tự động hóa cho sinh viên'
          : 'Formal rule traces for reviewers, instant feedback for authors',
      desc:
        lang === 'vi'
          ? 'Mỗi kết luận đều đi kèm chuỗi suy diễn luật R01–R20 và bảng so sánh từng trường (Tiêu đề, Tác giả, Năm, Tạp chí, DOI). Giảng viên có thể ghi đè nhãn (Override) kèm lưu vết Audit Log bất biến.'
          : 'Every verdict includes a deterministic R01–R20 rule trace and field-level edit distances. Instructors can override verdicts with mandatory rationale logged to an immutable audit trail.',
      cta: lang === 'vi' ? 'Khám phá luật' : 'Explore rules',
    },
    {
      painting: '/solva/sticky-3-bg.png',
      title:
        lang === 'vi'
          ? 'Phát hiện trích dẫn ảo giác AI trước khi nộp hội đồng'
          : 'Catch hallucinated references before peer review',
      desc:
        lang === 'vi'
          ? 'Nhận diện tức thì các trích dẫn "ma" do LLM tạo ra (ghép tên tạp chí thật với mã DOI không tồn tại hoặc sai lệch ngữ nghĩa) và theo dõi điểm toàn vẹn CIS qua từng phiên bản chỉnh sửa bản thảo.'
          : 'Flags synthetic LLM-generated references — such as real journal prefixes paired with fabricated DOIs — and tracks Citation Integrity Score (CIS) improvements across manuscript revisions.',
      cta: lang === 'vi' ? 'Kiểm tra bản thảo' : 'Audit manuscript',
    },
  ];

  return (
    <section className="py-[32px] sm:py-[48px] lg:py-[96px] px-5 sm:px-6 lg:px-[40px]">
      <div className="max-w-[1200px] mx-auto flex flex-col gap-[28px] sm:gap-[36px] lg:gap-[60px]">
        {/* Section Headline */}
        <div className="flex flex-col items-start gap-[12px] max-w-[580px]">
          <SolvaEyebrow>
            {lang === 'vi' ? 'Tại sao chọn CITRA' : 'Why CITRA'}
          </SolvaEyebrow>
          <SolvaTwoToneHeading
            primary={lang === 'vi' ? 'Một bản thảo.' : 'One workspace.'}
            secondary={
              lang === 'vi'
                ? 'Mọi trích dẫn đều được giải trình.'
                : 'Every citation, accounted for.'
            }
          />
        </div>

        {/* Sticky Stacking Cards Container */}
        <div className="flex flex-col gap-[20px] sm:gap-[28px] lg:gap-[96px]">
          {stickyBlocks.map((block, idx) => (
            <SolvaStickyStackCard
              key={block.title}
              index={idx}
              total={stickyBlocks.length}
            >
              <div className="grid grid-cols-1 lg:grid-cols-12 items-center">
                {/* Left Painterly Frame (667x548px equivalent on Desktop) */}
                <div className="lg:col-span-7">
                  <SolvaPainterlyFrame
                    paintingSrc={block.painting}
                    alt={block.title}
                    radiusClass="rounded-[10px]"
                    className="w-full h-[340px] sm:h-[420px] lg:h-[520px] p-6 flex items-center justify-center"
                  >
                    <div className="w-full h-full flex items-center justify-center">
                      <StickyCardWidget index={idx as 0 | 1 | 2} lang={lang} />
                    </div>
                  </SolvaPainterlyFrame>
                </div>

                {/* Right Editorial Content (509x548px equivalent, padding 48px) */}
                <div className="lg:col-span-5 p-6 sm:p-8 lg:p-[48px] flex flex-col items-start justify-center gap-[24px]">
                  <div className="flex flex-col gap-[12px]">
                    <h3
                      style={{ color: 'var(--solva-ink)' }}
                      className="font-solva-serif font-light text-[30px] sm:text-[36px] xl:text-[40px] leading-[1.15] tracking-[-0.05em] max-w-[400px]"
                    >
                      {block.title}
                    </h3>
                    <p
                      style={{ color: 'var(--solva-muted)' }}
                      className="font-solva-sans text-[16px] font-normal leading-[23.2px] max-w-[380px]"
                    >
                      {block.desc}
                    </p>
                  </div>

                  <SolvaButton
                    to={isAuthenticated ? '/upload' : '/login'}
                    variant="primary"
                  >
                    {block.cta}
                  </SolvaButton>
                </div>
              </div>
            </SolvaStickyStackCard>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 4: INTERACTIVE CITATION DEBUGGER IDE (`#interactive-demo`)
   Wrapped in Solva's Nested Bezel (`#F4F2EC` -> `#FBFAF6`)
   Preserves all E2E test selectors & accessible tab roles!
   ============================================================ */
function SolvaInteractiveDebuggerSection({ lang }: { lang: Lang }) {
  const [selectedId, setSelectedId] = useState<string>(DEMO_CITATIONS[1].id);
  const [isAutoPlaying, setIsAutoPlaying] = useState<boolean>(true);
  const { containerRef: debuggerRef, replaySeed: debuggerSeed } = useFloralCardAnimation(5600);

  const activeCitation =
    DEMO_CITATIONS.find((c) => c.id === selectedId) || DEMO_CITATIONS[0];

  useEffect(() => {
    if (!isAutoPlaying) return;
    const timer = window.setInterval(() => {
      setSelectedId((prev) => {
        const idx = DEMO_CITATIONS.findIndex((c) => c.id === prev);
        const nextIdx = (idx + 1) % DEMO_CITATIONS.length;
        return DEMO_CITATIONS[nextIdx].id;
      });
    }, 4200);
    return () => window.clearInterval(timer);
  }, [isAutoPlaying]);

  const handleSelectCitation = (id: string) => {
    setSelectedId(id);
    setIsAutoPlaying(false);
  };

  const renderFieldStatusBadge = (
    status: 'match' | 'partial' | 'mismatch' | 'missing'
  ) => {
    switch (status) {
      case 'match':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[6px] text-[11px] font-mono font-semibold bg-emerald-500/12 text-emerald-700 dark:text-emerald-300">
            <Check className="h-3 w-3" /> 100% Match
          </span>
        );
      case 'partial':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[6px] text-[11px] font-mono font-semibold bg-amber-500/12 text-amber-700 dark:text-amber-300">
            <AlertTriangle className="h-3 w-3" /> 86% Sim
          </span>
        );
      case 'mismatch':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[6px] text-[11px] font-mono font-semibold bg-red-500/12 text-red-700 dark:text-red-300">
            <XCircle className="h-3 w-3" /> Diff
          </span>
        );
      case 'missing':
        return (
          <span
            style={{
              backgroundColor: 'var(--solva-surface)',
              color: 'var(--solva-muted)',
            }}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[6px] text-[11px] font-mono font-semibold"
          >
            — Missing
          </span>
        );
    }
  };

  return (
    <section
      id="interactive-demo"
      className="scroll-mt-[84px] lg:scroll-mt-[108px] py-[32px] sm:py-[48px] lg:py-[96px] px-5 sm:px-6 lg:px-[40px]"
    >
      <div className="max-w-[1200px] mx-auto flex flex-col gap-[28px] sm:gap-[36px] lg:gap-[64px]">
        {/* Section Headline */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 sm:gap-6">
          <div className="flex flex-col items-start gap-[12px]">
            <SolvaEyebrow>
              {lang === 'vi'
                ? 'Trình gỡ lỗi trích dẫn tương tác'
                : 'Interactive Citation Debugger'}
            </SolvaEyebrow>
            <SolvaTwoToneHeading
              primary={
                lang === 'vi'
                  ? 'Soi chiếu từng trích dẫn.'
                  : 'Inspect every citation.'
              }
              secondary={
                lang === 'vi'
                  ? 'Giải thích từng quy tắc.'
                  : 'Audit every symbolic rule.'
              }
            />
          </div>
          <SolvaScrollReveal delayMs={80} yOffset={24}>
            <p
              style={{ color: 'var(--solva-muted)' }}
              className="font-solva-sans text-[16px] leading-[23.2px] max-w-[400px]"
            >
              {lang === 'vi'
                ? 'Nhấp vào bất kỳ trích dẫn mẫu nào bên dưới để xem cách CITRA đối chiếu metadata song song và kích hoạt luật suy diễn R01–R16.'
                : 'Select any sample citation below to inspect live side-by-side metadata diffs, multi-source latency, and formal symbolic rule triggers.'}
            </p>
          </SolvaScrollReveal>
        </div>

        {/* Solva Outer Bezel (`#F4F2EC`, `border-radius: 16px`, `padding: 12px`) */}
        <SolvaScrollReveal delayMs={110} yOffset={36}>
          <div
            ref={debuggerRef}
            style={{ backgroundColor: 'var(--solva-surface)' }}
            className="rounded-[16px] p-[8px] sm:p-[12px]"
          >
            <div
              style={{
                backgroundColor: 'var(--solva-bg)',
                borderColor: 'var(--solva-border)',
              }}
              className="rounded-[12px] border overflow-hidden"
            >
              {/* Top Window Bar */}
              <div
                style={{
                  backgroundColor: 'var(--solva-card-elevated)',
                  borderColor: 'var(--solva-border)',
                }}
                className="px-4 sm:px-6 py-3.5 border-b flex flex-wrap items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex items-center gap-1.5 shrink-0" aria-label="macOS window controls">
                    <span className="w-3 h-3 rounded-full bg-[#FF5F56] border border-[#E0443E]/60 shadow-2xs" />
                    <span className="w-3 h-3 rounded-full bg-[#FFBD2E] border border-[#DEA123]/60 shadow-2xs" />
                    <span className="w-3 h-3 rounded-full bg-[#27C93F] border border-[#1AAB29]/60 shadow-2xs" />
                  </div>
                <div
                  style={{ color: 'var(--solva-ink)' }}
                  className="flex items-center gap-2 font-mono text-xs min-w-0"
                >
                  <FileText className="h-3.5 w-3.5 shrink-0" />
                  <span className="font-semibold truncate">
                    thesis_neural_retrieval_2026.pdf
                  </span>
                  <span
                    style={{ color: 'var(--solva-muted)' }}
                    className="hidden sm:inline"
                  >
                    (<SolvaLiveNumber value={18} replaySeed={debuggerSeed} durationMs={1150} /> pages ·{' '}
                    <SolvaLiveNumber value={24} replaySeed={debuggerSeed} durationMs={1300} /> citations)
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsAutoPlaying((prev) => !prev)}
                  style={{
                    backgroundColor: 'var(--solva-surface)',
                    color: 'var(--solva-ink)',
                    borderColor: 'var(--solva-border)',
                  }}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[8px] border text-[11px] font-mono font-medium cursor-pointer"
                >
                  {isAutoPlaying ? (
                    <>
                      <Pause className="h-3 w-3" />
                      <span>{lang === 'vi' ? 'Tự động duyệt' : 'Auto-Tour: ON'}</span>
                    </>
                  ) : (
                    <>
                      <Play className="h-3 w-3" />
                      <span>{lang === 'vi' ? 'Tiếp tục duyệt' : 'Auto-Tour: PAUSED'}</span>
                    </>
                  )}
                </button>
                <div
                  style={{
                    backgroundColor: 'var(--solva-btn-bg)',
                    color: 'var(--solva-btn-fg)',
                  }}
                  className="px-2.5 py-1 rounded-[8px] text-[11px] font-mono font-semibold"
                >
                  CIS:{' '}
                  <SolvaLiveNumber
                    value={84.5}
                    decimals={1}
                    replaySeed={debuggerSeed}
                    durationMs={1400}
                  />{' '}
                  / 100
                </div>
              </div>
            </div>

            {/* Split-Pane Debugger Body */}
            <div className="grid lg:grid-cols-12">
              {/* Left Pane: Extracted Citations Queue (5 cols) */}
              <div
                style={{ borderColor: 'var(--solva-border)' }}
                className="lg:col-span-5 min-w-0 border-b lg:border-b-0 lg:border-r p-4 sm:p-5 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span
                      style={{ color: 'var(--solva-muted)' }}
                      className="text-xs font-mono uppercase tracking-wider font-semibold"
                    >
                      {lang === 'vi'
                        ? 'Trích dẫn bóc tách từ PDF (Chọn để khám xét)'
                        : 'Extracted Citations (Select to Inspect)'}
                    </span>
                    <span
                      style={{ color: 'var(--solva-muted)' }}
                      className="text-[11px] font-mono"
                    >
                      4 / 24 shown
                    </span>
                  </div>

                  <div className="space-y-2.5" role="listbox" aria-label="Sample Citations">
                    {DEMO_CITATIONS.map((cit) => {
                      const isSelected = cit.id === activeCitation.id;
                      return (
                        <button
                          key={cit.id}
                          type="button"
                          role="option"
                          aria-selected={isSelected}
                          onClick={() => handleSelectCitation(cit.id)}
                          style={{
                            backgroundColor: isSelected
                              ? 'var(--solva-card-elevated)'
                              : 'var(--solva-surface)',
                            borderColor: isSelected
                              ? 'var(--solva-ink)'
                              : 'var(--solva-border)',
                          }}
                          className="w-full text-left p-3.5 rounded-[10px] border transition-all duration-200 cursor-pointer"
                        >
                          <div className="flex items-center justify-between gap-2 mb-1.5">
                            <div className="flex items-center gap-2 min-w-0">
                              <span
                                style={{
                                  backgroundColor: isSelected
                                    ? 'var(--solva-btn-bg)'
                                    : 'var(--solva-bg)',
                                  color: isSelected
                                    ? 'var(--solva-btn-fg)'
                                    : 'var(--solva-ink)',
                                }}
                                className="font-mono text-xs font-bold px-2 py-0.5 rounded-[5px]"
                              >
                                {cit.marker}
                              </span>
                              <span
                                style={{ color: 'var(--solva-ink)' }}
                                className="font-medium text-sm truncate"
                              >
                                {cit.inText}
                              </span>
                            </div>
                            <span
                              style={{ color: 'var(--solva-muted)' }}
                              className="font-mono text-[11px] shrink-0"
                            >
                              {cit.page}
                            </span>
                          </div>

                          <p
                            style={{ color: 'var(--solva-muted)' }}
                            className="text-xs line-clamp-1 mb-2.5 font-solva-serif italic"
                          >
                            &ldquo;{cit.citedMeta.title}&rdquo;
                          </p>

                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span
                                className={`verdict-badge ${cit.verdictBadgeClass} text-[10px] px-2 py-0.5 font-mono`}
                              >
                                {cit.verdict}
                              </span>
                              <span
                                className={`mapping-badge ${cit.mappingBadgeClass} text-[10px] px-2 py-0.5 font-mono`}
                              >
                                {cit.mappingStatus}
                              </span>
                            </div>
                            <span
                              style={{ color: 'var(--solva-muted)' }}
                              className="font-mono text-[11px]"
                            >
                              Conf:{' '}
                              <strong style={{ color: 'var(--solva-ink)' }}>
                                <SolvaLiveNumber
                                  value={cit.confidence}
                                  suffix="%"
                                  replaySeed={debuggerSeed}
                                  durationMs={1250}
                                />
                              </strong>
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Manuscript Context Box */}
                <div
                  key={`ctx-${activeCitation.id}`}
                  style={{
                    backgroundColor: 'var(--solva-surface)',
                    borderColor: 'var(--solva-border)',
                  }}
                  className="mt-5 p-3.5 rounded-[10px] border animate-debugger-switch"
                >
                  <div
                    style={{ color: 'var(--solva-muted)' }}
                    className="flex items-center justify-between text-[11px] font-mono mb-1.5"
                  >
                    <span>MANUSCRIPT CONTEXT ({activeCitation.page})</span>
                    <span>GROBID TEI-XML</span>
                  </div>
                  <p
                    style={{ color: 'var(--solva-ink)' }}
                    className="text-xs sm:text-sm leading-relaxed"
                  >
                    {activeCitation.contextBefore}
                    <mark
                      style={{
                        backgroundColor: 'var(--solva-btn-bg)',
                        color: 'var(--solva-btn-fg)',
                      }}
                      className="px-1.5 py-0.5 rounded font-medium"
                    >
                      {activeCitation.inText}
                    </mark>
                    {activeCitation.contextAfter}
                  </p>
                </div>
              </div>

              {/* Right Pane: Reference Inspector & Symbolic Trace (7 cols) */}
              <div
                style={{ backgroundColor: 'var(--solva-card-elevated)' }}
                className="lg:col-span-7 min-w-0 p-4 sm:p-6 flex flex-col justify-between"
              >
                <div key={activeCitation.id} className="animate-debugger-switch">
                  <div
                    style={{ borderColor: 'var(--solva-border)' }}
                    className="flex flex-wrap items-start justify-between gap-4 pb-4 border-b"
                  >
                    <div className="min-w-0">
                      <div
                        style={{ color: 'var(--solva-muted)' }}
                        className="flex flex-wrap items-center gap-x-2 gap-y-1 mb-1 font-mono text-xs"
                      >
                        <span>INSPECTING REFERENCE</span>
                        <strong style={{ color: 'var(--solva-ink)' }}>
                          {activeCitation.marker}
                        </strong>
                        <span>
                          · Confidence{' '}
                          <SolvaLiveNumber
                            value={activeCitation.confidence}
                            suffix="%"
                            replaySeed={debuggerSeed}
                            durationMs={1150}
                          />
                        </span>
                      </div>
                      <h3
                        style={{ color: 'var(--solva-ink)' }}
                        className="font-solva-serif font-light text-[22px] sm:text-[26px] leading-[1.2] break-words"
                      >
                        {activeCitation.citedMeta.title}
                      </h3>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`verdict-badge ${activeCitation.verdictBadgeClass} text-xs px-3 py-1 font-mono`}
                      >
                        {activeCitation.verdict}
                      </span>
                      <span
                        className={`mapping-badge ${activeCitation.mappingBadgeClass} text-xs px-2.5 py-1 font-mono`}
                      >
                        {activeCitation.mappingStatus}
                      </span>
                    </div>
                  </div>

                  {/* Explanation Callout */}
                  <div
                    style={{
                      backgroundColor: 'var(--solva-surface)',
                      borderColor: 'var(--solva-border)',
                    }}
                    className="my-4 p-3.5 rounded-[10px] border flex items-start gap-3"
                  >
                    <Scale
                      style={{ color: 'var(--solva-ink)' }}
                      className="h-4 w-4 shrink-0 mt-0.5"
                    />
                    <div
                      style={{ color: 'var(--solva-muted)' }}
                      className="text-xs sm:text-sm leading-relaxed"
                    >
                      <strong
                        style={{ color: 'var(--solva-ink)' }}
                        className="mr-1.5"
                      >
                        {lang === 'vi' ? 'Kết luận suy diễn:' : 'Neuro-Symbolic Reasoning:'}
                      </strong>
                      {lang === 'vi'
                        ? activeCitation.explanation.vi
                        : activeCitation.explanation.en}
                    </div>
                  </div>

                  {/* Inspector Tabs (Preserves exact role="tab" labels for E2E tests!) */}
                  <Tabs defaultValue="diff" className="w-full">
                    <TabsList
                      style={{ backgroundColor: 'var(--solva-surface)' }}
                      className="grid grid-cols-1 sm:grid-cols-3 w-full p-1 rounded-[10px] h-auto gap-1"
                    >
                      <TabsTrigger
                        value="diff"
                        className="w-full text-xs font-mono py-2 sm:py-1.5 px-2.5 rounded-[8px]"
                      >
                        {lang === 'vi' ? '1. Đối chiếu Metadata' : '1. Metadata Diff'}
                      </TabsTrigger>
                      <TabsTrigger
                        value="rules"
                        className="w-full text-xs font-mono py-2 sm:py-1.5 px-2.5 rounded-[8px]"
                      >
                        {lang === 'vi'
                          ? `2. Luật Suy diễn (${activeCitation.rules.length})`
                          : `2. Symbolic Rules (${activeCitation.rules.length})`}
                      </TabsTrigger>
                      <TabsTrigger
                        value="sources"
                        className="w-full text-xs font-mono py-2 sm:py-1.5 px-2.5 rounded-[8px]"
                      >
                        {lang === 'vi' ? '3. Nguồn Truy hồi' : '3. Source Retrieval'}
                      </TabsTrigger>
                    </TabsList>

                    {/* TAB 1: Side-by-side Metadata Diff */}
                    <TabsContent value="diff" className="mt-4 animate-debugger-switch">
                      <div
                        style={{ borderColor: 'var(--solva-border)' }}
                        className="rounded-[10px] border overflow-hidden"
                      >
                        <table className="w-full text-left border-collapse block sm:table">
                          <thead className="hidden sm:table-header-group">
                            <tr
                              style={{
                                backgroundColor: 'var(--solva-surface)',
                                borderColor: 'var(--solva-border)',
                                color: 'var(--solva-muted)',
                              }}
                              className="border-b text-[11px] font-mono uppercase"
                            >
                              <th className="py-2.5 px-3 w-24">Field</th>
                              <th className="py-2.5 px-3">Cited in Manuscript</th>
                              <th className="py-2.5 px-3">Canonical Retrieved</th>
                              <th className="py-2.5 px-3 text-right">Status</th>
                            </tr>
                          </thead>
                          <tbody className="block sm:table-row-group divide-y divide-[#E7E3D9] dark:divide-[#332F26] text-xs">
                            {(
                              ['title', 'authors', 'year', 'venue', 'doi'] as const
                            ).map((field) => {
                              const status = activeCitation.fieldStatus[field];
                              const citedVal = activeCitation.citedMeta[field];
                              const retVal = activeCitation.retrievedMeta
                                ? activeCitation.retrievedMeta[field]
                                : '— Not Found in External Indexes —';

                              return (
                                <tr
                                  key={field}
                                  className="block sm:table-row p-3 sm:p-0 space-y-1.5 sm:space-y-0"
                                >
                                  <td
                                    style={{ color: 'var(--solva-muted)' }}
                                    className="block sm:table-cell sm:py-2.5 sm:px-3 font-mono uppercase text-[11px] font-semibold"
                                  >
                                    <div className="flex items-center justify-between sm:block">
                                      <span>{field}</span>
                                      <span className="sm:hidden">
                                        {renderFieldStatusBadge(status)}
                                      </span>
                                    </div>
                                  </td>
                                  <td
                                    style={{ color: 'var(--solva-ink)' }}
                                    className="block sm:table-cell sm:py-2.5 sm:px-3 break-words"
                                  >
                                    {citedVal}
                                  </td>
                                  <td
                                    style={{ color: 'var(--solva-muted)' }}
                                    className="block sm:table-cell sm:py-2.5 sm:px-3 break-words font-mono text-[11px]"
                                  >
                                    {retVal}
                                  </td>
                                  <td className="hidden sm:table-cell sm:py-2.5 sm:px-3 text-right whitespace-nowrap">
                                    {renderFieldStatusBadge(status)}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </TabsContent>

                    {/* TAB 2: Symbolic Rules */}
                    <TabsContent value="rules" className="mt-4 space-y-2.5 animate-debugger-switch">
                      {activeCitation.rules.map((rule) => (
                        <div
                          key={rule.code}
                          style={{
                            backgroundColor: 'var(--solva-surface)',
                            borderColor: 'var(--solva-border)',
                          }}
                          className="p-3.5 rounded-[10px] border flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                        >
                          <div className="space-y-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span
                                style={{ color: 'var(--solva-ink)' }}
                                className="font-mono text-xs font-bold"
                              >
                                {rule.code}
                              </span>
                              <span
                                style={{ color: 'var(--solva-ink)' }}
                                className="text-xs font-medium"
                              >
                                {rule.name}
                              </span>
                            </div>
                            <p
                              style={{ color: 'var(--solva-muted)' }}
                              className="font-mono text-[11px] break-words"
                            >
                              {rule.condition}
                            </p>
                          </div>
                          <span
                            className={`self-start sm:self-center px-2.5 py-0.5 rounded font-mono text-[10px] font-semibold uppercase shrink-0 ${
                              rule.status === 'passed'
                                ? 'bg-emerald-500/12 text-emerald-700 dark:text-emerald-300'
                                : rule.status === 'warning'
                                  ? 'bg-amber-500/12 text-amber-700 dark:text-amber-300'
                                  : 'bg-red-500/12 text-red-700 dark:text-red-300'
                            }`}
                          >
                            {rule.status}
                          </span>
                        </div>
                      ))}
                    </TabsContent>

                    {/* TAB 3: Source Retrieval */}
                    <TabsContent value="sources" className="mt-4 animate-debugger-switch">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        {activeCitation.sources.map((src) => (
                          <div
                            key={src.name}
                            style={{
                              backgroundColor: 'var(--solva-surface)',
                              borderColor: 'var(--solva-border)',
                            }}
                            className="p-3.5 rounded-[10px] border flex items-center justify-between gap-2"
                          >
                            <div className="flex items-center gap-2.5 min-w-0">
                              <span
                                style={{
                                  backgroundColor: 'var(--solva-bg)',
                                  borderColor: 'var(--solva-border)',
                                  color: 'var(--solva-ink)',
                                }}
                                className="w-8 h-8 rounded-[8px] border flex items-center justify-center shrink-0"
                              >
                                <ScholarlySourceLogo name={src.name} size={16} />
                              </span>
                              <div className="min-w-0">
                                <div
                                  style={{ color: 'var(--solva-ink)' }}
                                  className="text-sm font-medium truncate"
                                >
                                  {src.name}
                                </div>
                                <div
                                  style={{ color: 'var(--solva-muted)' }}
                                  className="text-xs font-mono"
                                >
                                  Latency: {src.latency}
                                </div>
                              </div>
                            </div>
                            <span
                              style={{ color: 'var(--solva-ink)' }}
                              className="font-mono text-xs font-semibold px-2.5 py-1 rounded bg-[#FBFAF6] dark:bg-[#141310]"
                            >
                              {src.score}
                            </span>
                          </div>
                        ))}
                      </div>
                    </TabsContent>
                  </Tabs>
                </div>
              </div>
            </div>
          </div>
          </div>
        </SolvaScrollReveal>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 5: USE CASES / PIPELINE (`#how-it-works`)
   Solva's 4-Tab Nested Bezel Box (`#F4F2EC` Outer -> `#FBFAF6` Inner Well)
   ============================================================ */
function SolvaUseCasesSection({
  lang,
  isAuthenticated,
}: {
  lang: Lang;
  isAuthenticated: boolean;
}) {
  const [activeTab, setActiveTab] = useState(0);
  const [autoCycleTabs, setAutoCycleTabs] = useState(true);

  useEffect(() => {
    if (!autoCycleTabs) return;
    const timer = window.setInterval(() => {
      setActiveTab((prev) => (prev + 1) % 4);
    }, 4600);
    return () => window.clearInterval(timer);
  }, [autoCycleTabs]);

  const tabs = [
    {
      label: lang === 'vi' ? '1. Bóc tách GROBID TEI' : 'PDF & GROBID TEI',
      icon: FileText,
      painting: '/solva/usecase-1-bg.png',
      headline:
        lang === 'vi'
          ? 'Bóc tách mọi trích dẫn và danh mục tài liệu trong tích tắc'
          : 'Every in-text marker and reference parsed in seconds',
      subFeatures: [
        {
          title:
            lang === 'vi'
              ? 'Phân vùng cấu trúc bản thảo thông minh'
              : 'Structural section segmentation',
          desc:
            lang === 'vi'
              ? 'Tự động tách phần thân bài, chú thích chân trang và khóa vùng Danh mục Tài liệu tham khảo cuối bài.'
              : 'Separates body paragraphs, footnotes, and locks bibliography boundaries automatically.',
        },
        {
          title:
            lang === 'vi'
              ? 'Hỗ trợ đa chuẩn trích dẫn học thuật'
              : 'Multi-style citation normalization',
          desc:
            lang === 'vi'
              ? 'Nhận diện chuẩn IEEE [1]–[5], APA 7th (Author, Year), Vancouver, Harvard và ACM.'
              : 'Handles IEEE numbered ranges [1]–[5], APA 7th author-year, Vancouver, and Harvard.',
        },
        {
          title:
            lang === 'vi'
              ? 'Đối chiếu Lớp 1 (Mapping Consistency)'
              : 'Layer 1 mapping consistency check',
          desc:
            lang === 'vi'
              ? 'Phát hiện ngay trích dẫn thiếu nguồn (MISSING_REFERENCE) hoặc tài liệu liệt kê nhưng không trích dẫn (UNCITED).'
              : 'Flags orphan in-text markers (MISSING_REFERENCE) and uncited bibliography entries on the spot.',
        },
      ],
    },
    {
      label: lang === 'vi' ? '2. Truy hồi 15+ API' : '15+ API Retrieval',
      icon: Database,
      painting: '/solva/usecase-2-bg.png',
      headline:
        lang === 'vi'
          ? 'Truy vấn song song trên 15+ cơ sở dữ liệu học thuật toàn cầu'
          : 'Federated lookup across 15+ global scholarly indexes',
      subFeatures: [
        {
          title:
            lang === 'vi'
              ? 'Truy hồi đa tầng theo độ ưu tiên'
              : 'Tiered asynchronous waterfall',
          desc:
            lang === 'vi'
              ? 'Ưu tiên giải mã DOI/PMID/arXiv chính xác trước khi mở rộng tìm kiếm mờ theo tiêu đề và tác giả.'
              : 'Resolves exact DOI, PMID, and arXiv IDs first before cascading to fuzzy title-author search.',
        },
        {
          title:
            lang === 'vi'
              ? 'Bộ nhớ đệm cục bộ SQLite FTS5'
              : 'Sub-10ms SQLite FTS5 local cache',
          desc:
            lang === 'vi'
              ? 'Lưu trữ kết quả đã xác thực bằng chỉ mục BM25 + Trigram giúp giảm 80% độ trễ mạng.'
              : 'Caches verified canonical works with BM25 + trigram indexing for instant repeat checks.',
        },
        {
          title:
            lang === 'vi'
              ? 'Hợp nhất & khử trùng lặp thông minh'
              : 'Cross-source entity deduplication',
          desc:
            lang === 'vi'
              ? 'Tự động gộp bản nháp arXiv và bản chính thức trên tạp chí thành một hồ sơ chuẩn duy nhất.'
              : 'Merges preprint records and published journal versions into a single canonical profile.',
        },
      ],
    },
    {
      label: lang === 'vi' ? '3. Luật Neuro-Symbolic' : 'Neuro-Symbolic Rules',
      icon: Scale,
      painting: '/solva/usecase-3-bg.png',
      headline:
        lang === 'vi'
          ? 'Suy diễn minh bạch với 20 quy tắc hình thức R01–R20'
          : 'Deterministic verification grounded in formal rules R01–R20',
      subFeatures: [
        {
          title:
            lang === 'vi'
              ? 'Đối chiếu chi tiết từng trường siêu dữ liệu'
              : 'Field-level metadata diffing',
          desc:
            lang === 'vi'
              ? 'Đo khoảng cách chỉnh sửa trên từng trường: Tiêu đề, Họ tên tác giả, Năm xuất bản, Tạp chí và DOI.'
              : 'Computes independent similarity scores for Title, Author surnames, Year, Venue, and DOI.',
        },
        {
          title:
            lang === 'vi'
              ? 'Nhận diện DOI giả mạo (Ghost DOI)'
              : 'Ghost DOI & hallucination radar',
          desc:
            lang === 'vi'
              ? 'Phát hiện thủ thuật ghép tiền tố nhà xuất bản thật với mã hậu tố không tồn tại của các mô hình LLM.'
              : 'Catches valid publisher prefixes (e.g., 10.1038) paired with fabricated article suffixes.',
        },
        {
          title:
            lang === 'vi'
              ? 'Không phán xét hộp đen'
              : 'Zero black-box guesswork',
          desc:
            lang === 'vi'
              ? 'Mọi nhãn kết luận đều chỉ rõ quy tắc nào đã kích hoạt để giảng viên dễ dàng kiểm chứng.'
              : 'Every verdict exposes the exact symbolic rule chain that fired during evaluation.',
        },
      ],
    },
    {
      label: lang === 'vi' ? '4. Ngữ nghĩa & Thái độ' : 'Semantic & NLI Stance',
      icon: Cpu,
      painting: '/solva/usecase-4-bg.png',
      headline:
        lang === 'vi'
          ? 'Kiểm tra ngữ cảnh trích dẫn có thực sự khớp với tóm tắt bài gốc'
          : 'Verify that cited abstracts actually support the manuscript claim',
      subFeatures: [
        {
          title:
            lang === 'vi'
              ? 'Bi-Encoder & Cross-Encoder Re-ranking'
              : 'Two-stage neural semantic matching',
          desc:
            lang === 'vi'
              ? 'Kết hợp all-MiniLM-L6-v2 và ms-marco-MiniLM-L-6-v2 để chấm điểm tương đồng ngữ nghĩa sâu.'
              : 'Pairs all-MiniLM-L6-v2 embeddings with ms-marco-MiniLM-L-6-v2 cross-attention re-ranking.',
        },
        {
          title:
            lang === 'vi'
              ? 'Phân loại thái độ DeBERTa-v3 NLI'
              : 'DeBERTa-v3 claim stance detection',
          desc:
            lang === 'vi'
              ? 'Xác định bài báo gốc Ủng hộ (SUPPORTS), Bác bỏ (REFUTES) hay Trung lập (NEUTRAL) với câu trích dẫn.'
              : 'Classifies whether the retrieved abstract SUPPORTS, REFUTES, or is NEUTRAL to the in-text claim.',
        },
        {
          title:
            lang === 'vi'
              ? 'Cảnh báo trích dẫn sai lệch ngữ cảnh'
              : 'Context misrepresentation alerts',
          desc:
            lang === 'vi'
              ? 'Phát hiện trường hợp bài báo có thật nhưng bị tác giả trích dẫn ngược lại kết luận gốc.'
              : 'Highlights real papers that are cited to claim the opposite of their actual findings.',
        },
      ],
    },
  ];

  const current = tabs[activeTab];

  return (
    <section
      id="how-it-works"
      className="scroll-mt-[84px] lg:scroll-mt-[108px] py-[32px] sm:py-[48px] lg:py-[96px] px-5 sm:px-6 lg:px-[40px]"
    >
      <div className="max-w-[1200px] mx-auto flex flex-col gap-[28px] sm:gap-[36px] lg:gap-[64px]">
        {/* Headline */}
        <div className="flex flex-col items-start gap-[12px] max-w-[540px]">
          <SolvaEyebrow>
            {lang === 'vi' ? 'Quy trình xử lý 4 giai đoạn' : 'Verification pipeline'}
          </SolvaEyebrow>
          <SolvaTwoToneHeading
            primary={lang === 'vi' ? 'Một nền tảng.' : 'One platform.'}
            secondary={
              lang === 'vi'
                ? 'Bốn lớp kiểm chứng khép kín.'
                : 'Every verification layer it touches.'
            }
          />
        </div>

        {/* Outer Interactive Container (`#F4F2EC`, `rounded-[16px]`) */}
        <SolvaScrollReveal delayMs={90} yOffset={36}>
          <div
            style={{ backgroundColor: 'var(--solva-surface)' }}
            className="w-full rounded-[16px] flex flex-col"
          >
            {/* Top 4-Tab Bar (`padding: 16px 40px`, `gap: 24px`) */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-[16px] lg:gap-[24px] p-3 sm:px-[24px] lg:px-[40px] sm:py-[16px]">
              {tabs.map((tab, idx) => {
                const Icon = tab.icon;
                const isActive = idx === activeTab;
                return (
                  <button
                    key={tab.label}
                    type="button"
                    onClick={() => {
                      setActiveTab(idx);
                      setAutoCycleTabs(false);
                    }}
                    style={{
                      backgroundColor: isActive ? 'var(--solva-bg)' : 'transparent',
                      color: isActive ? 'var(--solva-ink)' : 'var(--solva-muted)',
                    }}
                    className="h-[44px] px-3 rounded-[10px] font-solva-sans text-[13px] sm:text-[14px] font-medium flex items-center justify-center gap-[8px] transition-all duration-200 cursor-pointer"
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    <span className="truncate">{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Bottom Content Well (`#FBFAF6` inset with `12px` bezel) */}
            <div className="px-[8px] pb-[8px] sm:px-[12px] sm:pb-[12px]">
              <div
                key={activeTab}
                style={{ backgroundColor: 'var(--solva-bg)' }}
                className="rounded-[14px] p-3 sm:p-[12px] grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch animate-debugger-switch"
              >
                {/* Left Column (`412px` equivalent on Desktop, `padding: 28px`) */}
                <div className="lg:col-span-5 p-4 sm:p-[28px] flex flex-col justify-between gap-[32px]">
                  <div className="space-y-[28px]">
                    <h4
                      style={{ color: 'var(--solva-ink)' }}
                      className="font-solva-serif font-light text-[26px] sm:text-[30px] leading-[1.25] tracking-[-0.05em]"
                    >
                      {current.headline}
                    </h4>

                    <div className="space-y-[24px]">
                      {current.subFeatures.map((sf) => (
                        <div key={sf.title} className="flex items-start gap-3">
                          <CheckCircle2
                            style={{ color: 'var(--solva-ink)' }}
                            className="w-[18px] h-[18px] mt-1 shrink-0"
                          />
                          <div className="space-y-[4px]">
                            <h6
                              style={{ color: 'var(--solva-ink)' }}
                              className="font-solva-sans text-[17px] sm:text-[18px] font-normal leading-[25.2px]"
                            >
                              {sf.title}
                            </h6>
                            <p
                              style={{ color: 'var(--solva-muted)' }}
                              className="font-solva-sans text-[14px] font-normal leading-[21px]"
                            >
                              {sf.desc}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <SolvaButton
                    to={isAuthenticated ? '/upload' : '/login'}
                    variant="primary"
                    fullWidth
                  >
                    {lang === 'vi' ? 'Trải nghiệm quy trình này' : 'Try CITRA Free'}
                  </SolvaButton>
                </div>

                {/* Right Column (`764x501px` equivalent, Painterly Frame + Stage Card) */}
                <div className="lg:col-span-7">
                  <SolvaPainterlyFrame
                    paintingSrc={current.painting}
                    alt={current.headline}
                    radiusClass="rounded-[10px]"
                    className="w-full h-full min-h-[380px] sm:min-h-[460px] p-5 sm:p-[40px] flex items-center justify-center"
                  >
                    <div className="w-full h-full flex items-center justify-center">
                      <PipelineStageVisual tabIndex={activeTab} lang={lang} />
                    </div>
                  </SolvaPainterlyFrame>
                </div>
              </div>
            </div>
          </div>
        </SolvaScrollReveal>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 6: SECURITY & ACADEMIC COMPLIANCE
   Full-Bleed `#F4F2EC` Section Background + 4 `#FBFAF6` Cards
   ============================================================ */
function SolvaSecuritySection({ lang }: { lang: Lang }) {
  const cards = [
    {
      icon: Shield,
      title:
        lang === 'vi'
          ? 'Hỗ trợ quyết định (Decision-Support)'
          : 'Human-in-the-loop authority',
      desc:
        lang === 'vi'
          ? 'Cung cấp bằng chứng thư mục để hỗ trợ giảng viên; tuyệt đối không tự động kết luận gian lận.'
          : 'Provides verifiable bibliographic evidence; final judgment always remains with instructors.',
    },
    {
      icon: Lock,
      title:
        lang === 'vi'
          ? 'Phân quyền RBAC 3 vai trò'
          : 'Role-based access control',
      desc:
        lang === 'vi'
          ? 'Tách biệt quyền hạn chặt chẽ giữa Sinh viên, Giảng viên và Quản trị viên hệ thống.'
          : 'Capability-based isolation across Student, Teacher, and Administrator workspaces.',
    },
    {
      icon: Eye,
      title:
        lang === 'vi'
          ? 'Lưu vết Audit Log bất biến'
          : 'Immutable override audit logs',
      desc:
        lang === 'vi'
          ? 'Mọi thao tác ghi đè nhãn của giảng viên đều được ghi nhận kèm lý do và dấu thời gian.'
          : 'Every instructor verdict override and administrative action is logged with rationale.',
    },
    {
      icon: FileSearch,
      title:
        lang === 'vi'
          ? 'Bảo mật bản thảo tuyệt đối'
          : 'Manuscript privacy by default',
      desc:
        lang === 'vi'
          ? 'Bản thảo PDF của bạn không bao giờ bị sử dụng để huấn luyện các mô hình ngôn ngữ chia sẻ.'
          : 'Your uploaded manuscripts stay yours and are never used to train external models.',
    },
  ];

  return (
    <section
      style={{ backgroundColor: 'var(--solva-surface)' }}
      className="py-[40px] sm:py-[56px] lg:py-[96px] px-5 sm:px-6 lg:px-[40px]"
    >
      <div className="max-w-[1200px] mx-auto flex flex-col items-center gap-[28px] sm:gap-[36px] lg:gap-[64px]">
        {/* Centered Headline */}
        <div className="flex flex-col items-center text-center gap-[12px] max-w-[600px]">
          <SolvaEyebrow centered>
            {lang === 'vi' ? 'Tuân thủ học thuật & Bảo mật' : 'Academic compliance'}
          </SolvaEyebrow>
          <SolvaTwoToneHeading
            centered
            primary={
              lang === 'vi'
                ? 'Chuẩn mực liêm chính học thuật,'
                : 'Academic-grade integrity,'
            }
            secondary={
              lang === 'vi'
                ? 'được tích hợp từ cốt lõi.'
                : 'built in by default.'
            }
          />
          <SolvaScrollReveal delayMs={90} yOffset={20}>
            <p
              style={{ color: 'var(--solva-muted)' }}
              className="font-solva-sans text-[16px] font-normal leading-[23.2px] max-w-[380px] pt-1"
            >
              {lang === 'vi'
                ? 'Bản thảo nghiên cứu của bạn luôn thuộc về bạn. Hệ thống hỗ trợ rà soát minh bạch, không thay thế hội đồng.'
                : 'Your research manuscripts stay yours. Designed to assist scholarly review, never replace it.'}
            </p>
          </SolvaScrollReveal>
        </div>

        {/* 4 Cards (`288x192px` equivalent on Desktop, `#FBFAF6` background) */}
        <div className="w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-[16px]">
          {cards.map((card, idx) => {
            const Icon = card.icon;
            return (
              <SolvaScrollReveal
                key={card.title}
                delayMs={idx * 85}
                yOffset={30}
              >
                <div
                  style={{ backgroundColor: 'var(--solva-bg)' }}
                  className="rounded-[12px] p-[20px] sm:p-[24px] min-h-[156px] sm:min-h-[192px] h-full flex flex-col justify-between gap-[24px] sm:gap-[40px]"
                >
                  <Icon
                    style={{ color: 'var(--solva-ink)' }}
                    className="w-[18px] h-[18px]"
                  />
                  <div className="space-y-[6px]">
                    <h3
                      style={{ color: 'var(--solva-ink)' }}
                      className="font-solva-sans text-[18px] font-normal leading-[25.2px]"
                    >
                      {card.title}
                    </h3>
                    <p
                      style={{ color: 'var(--solva-muted)' }}
                      className="font-solva-sans text-[14px] font-normal leading-[21px]"
                    >
                      {card.desc}
                    </p>
                  </div>
                </div>
              </SolvaScrollReveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 7: PRICING PLANS & ACADEMIC BENEFITS (`#taxonomy`)
   3 Cards (`Basic`, `Pro Popular`, `Ultra`) + Squircle Billing Toggle
   + Radial-Masked Watercolor Floral Card (`/solva/pricing-floral.png`)
   ============================================================ */
function SolvaTaxonomyPricingSection({
  lang,
  isAuthenticated,
}: {
  lang: Lang;
  isAuthenticated: boolean;
}) {
  const [annualBilling, setAnnualBilling] = useState(false);
  const { containerRef: pricingRef, replaySeed: pricingSeed } = useFloralCardAnimation(5400);

  const tiers = [
    {
      name: lang === 'vi' ? 'Basic (Cơ bản)' : 'Basic',
      badge: null,
      metricNum: 0,
      unit: lang === 'vi' ? 'tháng · Miễn phí' : 'month',
      desc:
        lang === 'vi'
          ? 'Kiểm chứng trích dẫn 2 tầng thiết yếu dành cho sinh viên làm tiểu luận môn học và rà soát danh mục tham khảo nhanh.'
          : 'Essential two-layer citation verification for course essays, literature reviews, and quick bibliography checks.',
      includesLabel: lang === 'vi' ? 'Quyền lợi bao gồm:' : 'Includes:',
      items:
        lang === 'vi'
          ? [
              '3 tài liệu / tháng (tối đa 15 trang, 5 MB / file)',
              'Kiểm chứng tối đa 30 trích dẫn mỗi bản thảo',
              'Bóc tách GROBID TEI-XML & Đa chuẩn (IEEE, APA 7th)',
              '127K FTS5 cục bộ + Crossref, OpenAlex & Pháp luật VN',
              'Đầy đủ 15 nhãn kiểm chứng 2 tầng (L1 × L2)',
            ]
          : [
              '3 manuscripts / month (up to 15 pages, 5 MB)',
              'Up to 30 citations verified per manuscript',
              'GROBID TEI-XML & Multi-Style Cross-Validator',
              '127K Local FTS5 + Crossref, OpenAlex & VN Legal',
              'Full 15-verdict Two-Layer Orthogonal Taxonomy',
            ],
      cta: lang === 'vi' ? 'Bắt đầu miễn phí' : 'Get started free',
      to: isAuthenticated ? '/upload' : '/register',
      featured: false,
    },
    {
      name: lang === 'vi' ? 'Pro (Nghiên cứu & Luận văn)' : 'Pro',
      badge: lang === 'vi' ? 'Phổ biến' : 'Popular',
      metricNum: annualBilling ? 16 : 20,
      unit:
        lang === 'vi'
          ? annualBilling
            ? 'tháng (thanh toán năm)'
            : 'tháng'
          : annualBilling
            ? 'month (billed yearly)'
            : 'month',
      desc:
        lang === 'vi'
          ? 'Truy hồi toàn diện 15+ CSDL học thuật, so khớp ngữ nghĩa Sentence-BERT và tự động chuẩn hóa danh mục cho khóa luận & bài báo.'
          : 'Full 15+ scholarly API federation, Sentence-BERT semantic matching, and 1-Click Auto-Fix for graduation theses.',
      includesLabel:
        lang === 'vi'
          ? 'Toàn bộ quyền lợi Basic, cộng thêm:'
          : 'Everything in Basic, plus:',
      items:
        lang === 'vi'
          ? [
              '50 tài liệu / tháng (tối đa 100 trang, 25 MB / file)',
              'Tối đa 200 trích dẫn / bài + Tải lên hàng loạt (10 file)',
              'Toàn bộ 15+ API học thuật (PubMed, arXiv, DBLP, DOAJ...)',
              'Sentence-BERT ngữ nghĩa sâu & Thái độ trích dẫn DeBERTa NLI',
              '1-Click Auto-Fix (APA, IEEE, BibTeX) & Xuất báo cáo PDF',
            ]
          : [
              '50 manuscripts / month (up to 100 pages, 25 MB)',
              'Up to 200 citations / doc + Batch Upload (10 files)',
              'All 15+ Scholarly APIs (PubMed, arXiv, DBLP, DOAJ...)',
              'Sentence-BERT Deep Neural & DeBERTa-v3 NLI Stance',
              '1-Click Bibliography Auto-Fix (APA, IEEE, BibTeX) & PDF Export',
            ],
      cta: lang === 'vi' ? 'Nâng cấp gói Pro' : 'Start Pro trial',
      to: '/pricing',
      featured: true,
    },
    {
      name: lang === 'vi' ? 'Ultra (Hội đồng & Khoa Viện)' : 'Ultra',
      badge: null,
      metricNum: annualBilling ? 160 : 200,
      unit:
        lang === 'vi'
          ? annualBilling
            ? 'tháng (thanh toán năm)'
            : 'tháng'
          : annualBilling
            ? 'month (billed yearly)'
            : 'month',
      desc:
        lang === 'vi'
          ? 'Kiểm chứng quy mô hội đồng và khoa viện với Google Scholar dự phòng, quản lý lớp học và lưu vết ghi đè nhãn bất biến.'
          : 'Unlimited institutional verification, Google Scholar fallback, classroom cohort management, and instructor override logs.',
      includesLabel:
        lang === 'vi'
          ? 'Toàn bộ quyền lợi Pro, cộng thêm:'
          : 'Everything in Pro, plus:',
      items:
        lang === 'vi'
          ? [
              'Không giới hạn tài liệu (1.000/tháng, 500 trang, 100 MB)',
              'Không giới hạn số trích dẫn / bài + Batch Upload (50 file)',
              'Tích hợp SerpAPI Google Scholar dự phòng nguồn hiếm',
              'Bảng điều khiển Lớp học Giảng viên & Ghi đè nhãn (Override)',
              'Hàng đợi ưu tiên, Quản trị hệ thống & Nhật ký Audit bất biến',
            ]
          : [
              'Unlimited manuscripts (1,000/mo, up to 500 pages, 100 MB)',
              'Unlimited citations per paper + Batch Upload (50 files)',
              'SerpAPI Google Scholar Fallback for obscure monographs',
              'Teacher Classroom Cohort Dashboard & Instructor Override',
              'Admin Control Plane, Priority Queue & Immutable Audit Logs',
            ],
      cta: lang === 'vi' ? 'Xem gói Ultra & So sánh' : 'Explore Ultra plan',
      to: '/pricing',
      featured: false,
    },
  ];

  return (
    <section
      id="taxonomy"
      className="scroll-mt-[84px] lg:scroll-mt-[108px] py-[36px] sm:py-[48px] lg:py-[96px] px-5 sm:px-6 lg:px-[40px]"
    >
      <div className="max-w-[1200px] mx-auto flex flex-col items-center gap-[28px] sm:gap-[36px] lg:gap-[64px]">
        {/* Centered Headline */}
        <div className="flex flex-col items-center text-center gap-[16px] max-w-[580px]">
          <SolvaEyebrow centered>
            {lang === 'vi' ? 'Gói cước & Quyền lợi' : 'Pricing & Plans'}
          </SolvaEyebrow>
          <SolvaTwoToneHeading
            centered
            primary={
              lang === 'vi' ? 'Bảng giá minh bạch.' : 'Simple pricing.'
            }
            secondary={
              lang === 'vi' ? 'Tối ưu cho mọi quy mô học thuật.' : 'No surprises.'
            }
          />
        </div>

        {/* Toggle + 3 Cards Wrapper */}
        <div className="w-full flex flex-col items-center gap-[32px]">
          {/* Solva Squircle Switch (`48x28px`, `border-radius: 8px`, `bg: #ECE9E0`) */}
          <SolvaScrollReveal yOffset={20}>
            <div className="inline-flex items-center gap-[10px]">
              <span
                style={{ color: 'var(--solva-ink)' }}
                className="font-solva-sans text-[15px] sm:text-[16px]"
              >
                {lang === 'vi' ? 'Thanh toán tháng' : 'Monthly'}
              </span>
              <button
                type="button"
                role="switch"
                aria-checked={annualBilling}
                aria-label="Toggle billing cycle"
                onClick={() => setAnnualBilling((prev) => !prev)}
                style={{ backgroundColor: 'var(--solva-surface-alt)' }}
                className="w-[48px] h-[28px] rounded-[8px] p-[4px] flex items-center transition-colors cursor-pointer"
              >
                <span
                  style={{
                    backgroundColor: annualBilling
                      ? 'var(--solva-ink)'
                      : 'var(--solva-subtle)',
                    transform: annualBilling ? 'translateX(20px)' : 'translateX(0px)',
                  }}
                  className="w-[20px] h-[20px] rounded-[5px] transition-transform duration-200 ease-out"
                />
              </button>
              <span
                style={{ color: 'var(--solva-ink)' }}
                className="font-solva-sans text-[15px] sm:text-[16px]"
              >
                {lang === 'vi' ? 'Thanh toán năm -20%' : 'Yearly -20%'}
              </span>
            </div>
          </SolvaScrollReveal>

          {/* 3 Plan Cards (`389x483px` equivalent, `bg: #F4F2EC`, `rounded-[16px]`, `p-[32px]`) */}
          <div ref={pricingRef} className="w-full grid grid-cols-1 lg:grid-cols-3 gap-[16px]">
            {tiers.map((tier, idx) => (
              <SolvaScrollReveal
                key={tier.name}
                delayMs={idx * 95}
                yOffset={36}
                className="h-full"
              >
                <div
                  style={{ backgroundColor: 'var(--solva-surface)' }}
                  className="relative rounded-[16px] p-[28px] sm:p-[32px] flex flex-col justify-between gap-[24px] overflow-hidden min-h-[483px] h-full"
                >
                  {/* Radial-Masked Watercolor Floral Background on Middle Popular Card */}
                  {tier.featured && (
                    <div
                      className="solva-pricing-floral-mask absolute inset-0 pointer-events-none select-none z-0"
                      aria-hidden="true"
                    >
                      <img
                        src="/solva/pricing-floral.png"
                        alt=""
                        className="w-full h-full object-cover"
                      />
                    </div>
                  )}

                  <div className="relative z-10 space-y-[20px]">
                    {/* Top Tier Name + Popular Badge */}
                    <div className="flex items-center justify-between gap-2">
                      <h3
                        style={{ color: 'var(--solva-ink)' }}
                        className="font-solva-sans text-[20px] font-normal leading-[27px] tracking-[-0.02em]"
                      >
                        {tier.name}
                      </h3>
                      {tier.badge && (
                        <span
                          style={{
                            backgroundColor: 'var(--solva-btn-bg)',
                            color: 'var(--solva-btn-fg)',
                          }}
                          className="px-[8px] py-[4px] rounded-[6px] font-solva-sans text-[12px] font-medium leading-[12px]"
                        >
                          {tier.badge}
                        </span>
                      )}
                    </div>

                    {/* Price Display (`Sentient` 40px Light) */}
                    <div className="flex items-baseline gap-1.5">
                      <span
                        style={{ color: 'var(--solva-ink)' }}
                        className="font-solva-serif font-light text-[36px] sm:text-[40px] leading-[46px] tracking-[-0.05em]"
                      >
                        <SolvaLiveNumber
                          value={tier.metricNum}
                          prefix="$"
                          replaySeed={pricingSeed}
                          durationMs={1350}
                        />
                      </span>
                      <span
                        style={{ color: 'var(--solva-muted)' }}
                        className="font-solva-sans text-[14px]"
                      >
                        / {tier.unit}
                      </span>
                    </div>

                    {/* Description */}
                    <p
                      style={{ color: 'var(--solva-muted)' }}
                      className="font-solva-sans text-[15px] sm:text-[16px] leading-[23.2px]"
                    >
                      {tier.desc}
                    </p>

                    {/* Benefits Checklist */}
                    <div className="space-y-[10px] pt-1">
                      <div
                        style={{ color: 'var(--solva-muted)' }}
                        className="font-solva-sans text-[14px]"
                      >
                        {tier.includesLabel}
                      </div>
                      <ul className="space-y-[8px]">
                        {tier.items.map((item) => (
                          <li
                            key={item}
                            className="flex items-start gap-[8px] font-solva-sans text-[14px] leading-[21px]"
                          >
                            <CheckCircle2
                              style={{ color: 'var(--solva-muted)' }}
                              className="w-[17px] h-[17px] mt-[2px] shrink-0"
                            />
                            <span style={{ color: 'var(--solva-muted)' }}>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Bottom CTA Button */}
                  <div className="relative z-10 pt-2">
                    <SolvaButton
                      to={tier.to}
                      variant={tier.featured ? 'primary' : 'outline'}
                      fullWidth
                    >
                      {tier.cta}
                    </SolvaButton>
                  </div>
                </div>
              </SolvaScrollReveal>
            ))}
          </div>

          {/* Bottom Trust Strip */}
          <SolvaScrollReveal delayMs={120} yOffset={18}>
            <div className="flex flex-col items-center gap-[16px] pt-4 text-center">
              <p
                style={{ color: 'var(--solva-muted)' }}
                className="font-solva-sans text-[14px]"
              >
                {lang === 'vi'
                  ? 'Thanh toán bảo mật qua Stripe · Đối chiếu trực tiếp hơn 200 triệu công trình khoa học từ 15+ cơ sở dữ liệu uy tín'
                  : 'Secured by Stripe · Cross-referencing 200M+ canonical works across 15+ global scholarly indexes'}
              </p>
            </div>
          </SolvaScrollReveal>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 8: CLIENT RESULTS / EMPIRICAL BENCHMARK
   Split Portrait Card + Two-Tone Quote + 3 Animated Counters
   ============================================================ */
function SolvaClientResultsSection({ lang }: { lang: Lang }) {
  return (
    <section className="py-[32px] sm:py-[48px] lg:py-[96px] px-5 sm:px-6 lg:px-[40px]">
      <div className="max-w-[1200px] mx-auto flex flex-col gap-[28px] sm:gap-[36px] lg:gap-[64px]">
        {/* Headline */}
        <div className="flex flex-col items-start gap-[12px]">
          <SolvaEyebrow>
            {lang === 'vi' ? 'Kết quả thực nghiệm' : 'Real results'}
          </SolvaEyebrow>
          <SolvaTwoToneHeading
            primary={
              lang === 'vi'
                ? 'Hiệu quả rõ rệt, ngay từ bản thảo đầu tiên.'
                : 'Big results, from the first manuscript.'
            }
          />
        </div>

        {/* Main Split Card (`1200x500px` equivalent, `bg: #F4F2EC`, `rounded-[16px]`, `p-[12px]`) */}
        <SolvaScrollReveal delayMs={80} yOffset={36}>
          <div
            style={{ backgroundColor: 'var(--solva-surface)' }}
            className="w-full rounded-[16px] p-[12px] grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch"
          >
            {/* Left Interactive Cohort Case Study Frame (`442x476px` equivalent) */}
            <div className="lg:col-span-5">
              <SolvaPainterlyFrame
                paintingSrc="/solva/usecase-4-bg.png"
                alt="Impressionist botanical painting backdrop for cohort thesis audit"
                radiusClass="rounded-[10px]"
                className="w-full min-h-[380px] sm:min-h-[420px] lg:h-[476px] p-4 sm:p-6 flex items-center justify-center"
              >
                <div className="w-full flex items-center justify-center">
                  <CohortBatchAuditWidget lang={lang} />
                </div>
              </SolvaPainterlyFrame>
            </div>

            {/* Right Quote + Metrics (`734x476px` equivalent, `padding: 28px 32px 28px 40px`) */}
            <div className="lg:col-span-7 p-4 sm:p-[28px] lg:pl-[40px] flex flex-col justify-between gap-[32px]">
              {/* Top Two-Tone Quote + Attribution */}
              <div className="space-y-[24px]">
                <div className="flex flex-col sm:flex-row items-start justify-between gap-4">
                  <blockquote className="font-solva-serif font-light text-[24px] sm:text-[30px] leading-[1.25] tracking-[-0.05em] max-w-[520px]">
                    <span style={{ color: 'var(--solva-ink)' }}>
                      {lang === 'vi'
                        ? '“Chúng tôi đưa CITRA vào rà soát 120 khóa luận tốt nghiệp đầu tuần. Chỉ trong một buổi sáng, hệ thống đã chỉ ra toàn bộ các mã DOI ảo giác '
                        : '“We ran CITRA across 120 graduation theses on Monday morning. Within an hour, it pinpointed every hallucinated DOI and year drift '}
                    </span>
                    <span style={{ color: 'var(--solva-muted)' }}>
                      {lang === 'vi'
                        ? 'mà trước đây hội đồng phải mất hàng tuần tra cứu thủ công.”'
                        : 'that used to take our review committee weeks to check by hand.”'}
                    </span>
                  </blockquote>

                  <div
                    style={{ color: 'var(--solva-ink)' }}
                    className="font-solva-sans text-[16px] font-medium tracking-tight shrink-0 flex items-center gap-1.5"
                  >
                    <GraduationCap className="w-5 h-5" />
                    <span>CITRA Lab</span>
                  </div>
                </div>

                <div className="space-y-[2px]">
                  <div
                    style={{ color: 'var(--solva-ink)' }}
                    className="font-solva-sans text-[14px] font-medium leading-[21px]"
                  >
                    {lang === 'vi'
                      ? 'Hội đồng Rà soát Học thuật & Luận văn'
                      : 'Dr. Elena Rostova'}
                  </div>
                  <div
                    style={{ color: 'var(--solva-muted)' }}
                    className="font-solva-sans text-[14px] leading-[21px]"
                  >
                    {lang === 'vi'
                      ? 'Khoa Khoa học Máy tính & Trí tuệ Nhân tạo'
                      : 'Chair of Graduate Thesis Review Committee'}
                  </div>
                </div>
              </div>

              {/* Bottom 3 Count-Up Metrics (`Sentient` 40px Light) */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-[40px] pt-4 border-t border-[#E7E3D9] dark:border-[#332F26]">
                <SolvaAnimatedMetric
                  targetValue={15}
                  suffix="+"
                  decimals={0}
                  label={
                    lang === 'vi'
                      ? 'CSDL học thuật truy vấn song song'
                      : 'Scholarly APIs queried in parallel'
                  }
                />
                <SolvaAnimatedMetric
                  targetValue={96.4}
                  suffix="%"
                  decimals={1}
                  label={
                    lang === 'vi'
                      ? 'Độ chính xác khớp DOI & Tiêu đề'
                      : 'DOI & canonical title precision'
                  }
                />
                <SolvaAnimatedMetric
                  targetValue={4.9}
                  suffix="/5"
                  decimals={1}
                  label={
                    lang === 'vi'
                      ? 'Đánh giá từ Giảng viên hướng dẫn'
                      : 'Instructor review satisfaction'
                  }
                />
              </div>
            </div>
          </div>
        </SolvaScrollReveal>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 9: ROLE WORKSPACES & ACADEMIC TESTIMONIALS (`#workspaces`)
   Solva's 3-Column Staggered Grid (Middle Column Offset by `48px`)
   ============================================================ */
function SolvaRoleTestimonialsSection({ lang }: { lang: Lang }) {
  const columns = [
    // Column 1 (padding-top: 0px)
    [
      {
        roleBadge: lang === 'vi' ? 'SINH VIÊN · WORKSPACE' : 'STUDENT WORKSPACE',
        quote:
          lang === 'vi'
            ? '“Trước khi nộp khóa luận, tôi tải bản PDF lên CITRA và phát hiện 3 mục trong phần References bị lệch năm xuất bản so với bản chính thức trên IEEE Xplore.”'
            : '“Before submitting my thesis, I ran my PDF through CITRA and caught three arXiv-to-conference year mismatches in under two minutes.”',
        author: lang === 'vi' ? 'Minh Quân' : 'Marcus Chen',
        role:
          lang === 'vi'
            ? 'Sinh viên Khoa học Máy tính · Khóa luận Tốt nghiệp'
            : 'M.Sc. Computer Science Candidate',
      },
      {
        roleBadge: lang === 'vi' ? 'SINH VIÊN · LIVE SANDBOX' : 'STUDENT · LIVE SANDBOX',
        quote:
          lang === 'vi'
            ? '“Tính năng Live Sandbox cho phép tôi dán trực tiếp một đoạn văn kèm danh mục trích dẫn để kiểm tra tức thì mà không cần biên dịch lại toàn bộ file LaTeX.”'
            : '“The Live Sandbox lets me paste a single literature review section and verify every reference on the spot without compiling my full LaTeX PDF.”',
        author: lang === 'vi' ? 'Thanh Thảo' : 'Sophia Nguyen',
        role:
          lang === 'vi'
            ? 'Nghiên cứu sinh Y sinh học'
            : 'Biomedical Informatics Researcher',
      },
      {
        roleBadge: lang === 'vi' ? 'THEO DÕI TIẾN ĐỘ' : 'REVISION TRACKER',
        quote:
          lang === 'vi'
            ? '“Biểu đồ Revision Progress Tracker giúp tôi chứng minh với giảng viên hướng dẫn rằng điểm toàn vẹn trích dẫn của bài đã tăng từ 71% lên 98%.”'
            : '“The Revision Progress Tracker showed my advisor how my Citation Integrity Score improved from 71% in Draft 1 to 98% in my final submission.”',
        author: lang === 'vi' ? 'Hoàng Nam' : 'David Alverez',
        role:
          lang === 'vi'
            ? 'Tác giả bài báo khoa học'
            : 'Undergraduate Honors Thesis Author',
      },
    ],
    // Column 2 (Staggered 48px lower on Desktop: `lg:pt-[48px]`)
    [
      {
        roleBadge: lang === 'vi' ? 'GIẢNG VIÊN · CLASSROOM' : 'TEACHER CLASSROOM',
        quote:
          lang === 'vi'
            ? '“Thay vì phải mở Google Scholar tra từng bài trong 40 quyển đồ án, tôi có ngay bảng tổng hợp các trích dẫn nghi ngờ ảo giác của cả lớp.”'
            : '“Instead of manually copying titles into Google Scholar across 40 student submissions, I see cohort-wide hallucination alerts in one dashboard.”',
        author: lang === 'vi' ? 'PGS.TS. Trần Hải' : 'Prof. Arthur Pendelton',
        role:
          lang === 'vi'
            ? 'Giảng viên Hướng dẫn Luận văn'
            : 'Thesis Advisor & Faculty Reviewer',
      },
      {
        roleBadge: lang === 'vi' ? 'GIẢNG VIÊN · GHI ĐÈ NHÃN' : 'INSTRUCTOR OVERRIDE',
        quote:
          lang === 'vi'
            ? '“Khi sinh viên trích dẫn sách chuyên khảo tiếng Việt chưa có trên Crossref, tôi có thể duyệt xác nhận thủ công (Override) kèm ghi chú cho hội đồng.”'
            : '“When a student cites a print-only regional monograph, I can override the UNVERIFIABLE status with one click and attach my review note.”',
        author: lang === 'vi' ? 'TS. Lê Thu Hà' : 'Dr. Hannah Lindqvist',
        role:
          lang === 'vi'
            ? 'Chủ tịch Hội đồng Chấm Khóa luận'
            : 'Senior Lecturer in Computational Linguistics',
      },
      {
        roleBadge: lang === 'vi' ? 'KIỂM CHỨNG NGỮ NGHĨA NLI' : 'DeBERTa-v3 NLI STANCE',
        quote:
          lang === 'vi'
            ? '“Điểm đắt giá nhất là lớp kiểm tra thái độ trích dẫn DeBERTa NLI: phát hiện ngay những chỗ sinh viên trích dẫn bài báo thật nhưng nói ngược lại kết quả của tác giả.”'
            : '“DeBERTa NLI stance detection is a game changer — it flags cases where a real paper is cited, but the abstract actually refutes the student’s claim.”',
        author: lang === 'vi' ? 'TS. Nguyễn Hoàng' : 'Dr. Liam O’Connor',
        role:
          lang === 'vi'
            ? 'Phản biện Tạp chí Khoa học'
            : 'Peer Review Methodologist',
      },
    ],
    // Column 3 (padding-top: 0px)
    [
      {
        roleBadge: lang === 'vi' ? 'QUẢN TRỊ · CONTROL PANEL' : 'ADMIN CONTROL',
        quote:
          lang === 'vi'
            ? '“Bảng điều khiển Quản trị cung cấp trạng thái thời gian thực của máy chủ GROBID, độ trễ của 15 API học thuật và nhật ký Audit Log đầy đủ.”'
            : '“The Admin Control plane gives us live health diagnostics for our GROBID container, SQLite FTS5 cache hit rates, and an immutable audit trail.”',
        author: lang === 'vi' ? 'Đội ngũ Kỹ thuật CITRA' : 'Victor K.',
        role:
          lang === 'vi'
            ? 'Quản trị Hạ tầng Học thuật'
            : 'Academic Infrastructure Administrator',
      },
      {
        roleBadge: lang === 'vi' ? 'TRUY HỒI 15+ NGUỒN' : 'FEDERATED RETRIEVAL',
        quote:
          lang === 'vi'
            ? '“Kết hợp Crossref, OpenAlex, PubMed, arXiv và DBLP giúp tỷ lệ bao phủ tài liệu từ Y sinh đến Khoa học Máy tính đạt mức gần như tuyệt đối.”'
            : '“Combining Crossref, OpenAlex, PubMed, arXiv, and DBLP gives us seamless bibliographic coverage across both STEM and biomedical faculties.”',
        author: lang === 'vi' ? 'ThS. Phạm Khôi' : 'Dr. Priya Nair',
        role:
          lang === 'vi'
            ? 'Thư viện Số & Dữ liệu Học thuật'
            : 'Digital Library Systems Lead',
      },
      {
        roleBadge: lang === 'vi' ? 'KIẾN TRÚC 2 TẦNG' : 'ORTHOGONAL MODEL',
        quote:
          lang === 'vi'
            ? '“Việc tách Lớp 1 (Mapping) và Lớp 2 (Existence) giúp sinh viên phân biệt rõ đâu là lỗi trình bày danh mục, đâu là lỗi nguồn trích dẫn không tồn tại.”'
            : '“Separating Layer 1 formatting consistency from Layer 2 bibliographic existence makes feedback constructive rather than punitive.”',
        author: lang === 'vi' ? 'TS. Vũ Đăng' : 'Prof. Claire Beaumont',
        role:
          lang === 'vi'
            ? 'Ban Đảm bảo Chất lượng Giáo dục'
            : 'Director of Academic Writing Center',
      },
    ],
  ];

  return (
    <section
      id="workspaces"
      className="scroll-mt-[84px] lg:scroll-mt-[108px] py-[32px] sm:py-[48px] lg:py-[96px] px-5 sm:px-6 lg:px-[40px]"
    >
      <div className="max-w-[1200px] mx-auto flex flex-col gap-[28px] sm:gap-[36px] lg:gap-[64px]">
        {/* Headline */}
        <div className="flex flex-col items-start gap-[12px] max-w-[540px]">
          <SolvaEyebrow>
            {lang === 'vi'
              ? 'Thiết kế cho 3 vai trò học thuật'
              : 'Loved by academic teams'}
          </SolvaEyebrow>
          <SolvaTwoToneHeading
            primary={
              lang === 'vi' ? 'Giảm gánh nặng rà soát,' : 'Less busywork,'
            }
            secondary={
              lang === 'vi'
                ? 'tập trung cho chất lượng nghiên cứu.'
                : 'more breathing room.'
            }
          />
        </div>

        {/* 3-Column Staggered Masonry Grid (`gap: 12px`, Middle Column `lg:pt-[48px]`) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-[12px] items-start">
          {columns.map((col, colIdx) => (
            <div
              key={colIdx}
              className={`flex flex-col gap-[12px] ${
                colIdx === 1 ? 'lg:pt-[48px]' : ''
              }`}
            >
              {col.map((card, cardIdx) => (
                <SolvaScrollReveal
                  key={card.author}
                  delayMs={colIdx * 75 + cardIdx * 55}
                  yOffset={30}
                >
                  <div
                    style={{ backgroundColor: 'var(--solva-surface)' }}
                    className="rounded-[12px] p-[20px] sm:p-[24px] min-h-[200px] sm:min-h-[230px] lg:h-[280px] flex flex-col justify-between gap-[20px] sm:gap-[24px]"
                  >
                    <div className="space-y-[20px]">
                      <div className="flex items-center justify-between">
                        <span
                          style={{
                            backgroundColor: 'var(--solva-bg)',
                            color: 'var(--solva-muted)',
                          }}
                          className="px-2.5 py-1 rounded-[6px] font-mono text-[11px] font-medium"
                        >
                          {card.roleBadge}
                        </span>
                      </div>
                      <p
                        style={{ color: 'var(--solva-ink)' }}
                        className="font-solva-sans text-[17px] sm:text-[18px] font-normal leading-[25.2px]"
                      >
                        {card.quote}
                      </p>
                    </div>

                    <div className="space-y-[2px]">
                      <div
                        style={{ color: 'var(--solva-ink)' }}
                        className="font-solva-sans text-[14px] font-medium leading-[21px]"
                      >
                        {card.author}
                      </div>
                      <div
                        style={{ color: 'var(--solva-muted)' }}
                        className="font-solva-sans text-[14px] leading-[21px]"
                      >
                        {card.role}
                      </div>
                    </div>
                  </div>
                </SolvaScrollReveal>
              ))}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 10: FAQ (`#faq`)
   2-Column Independent Accordion (`592px` Left + `592px` Right, `gap: 16px`)
   ============================================================ */
function SolvaFAQSection({ lang }: { lang: Lang }) {
  const [openIds, setOpenIds] = useState<Record<string, boolean>>({
    'faq-0': true,
  });

  const toggleFaq = (id: string) => {
    setOpenIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const leftFaqs = [
    {
      id: 'faq-0',
      q:
        lang === 'vi'
          ? 'CITRA khác gì với các công cụ kiểm tra đạo văn truyền thống (như Turnitin)?'
          : 'How is CITRA different from traditional plagiarism checkers like Turnitin?',
      a:
        lang === 'vi'
          ? 'Các công cụ truyền thống chỉ so khớp trùng lặp chuỗi ký tự. CITRA đi sâu vào kiểm chứng tính xác thực của danh mục tài liệu tham khảo: giải mã DOI, đối chiếu chéo trên 15+ cơ sở dữ liệu học thuật để phát hiện trích dẫn ảo giác do AI sinh ra (Hallucinated Citations) và kiểm tra xem bài báo gốc có thực sự ủng hộ câu trích dẫn hay không.'
          : 'Traditional tools only check text overlap. CITRA verifies bibliographic truth: resolving DOIs, cross-checking 15+ scholarly indexes to catch AI-hallucinated references, and running DeBERTa NLI to verify whether cited abstracts actually support the in-text claim.',
    },
    {
      id: 'faq-1',
      q:
        lang === 'vi'
          ? 'Mô hình 2 tầng trực giao (Two-Layer Orthogonal Model) hoạt động như thế nào?'
          : 'How does the Two-Layer Orthogonal Output Model work?',
      a:
        lang === 'vi'
          ? 'Lớp 1 kiểm tra tính nhất quán nội bộ giữa trích dẫn trong thân bài và mục tài liệu cuối bài (7 trạng thái như MATCHED, MISSING_REFERENCE, UNCITED_REFERENCE). Lớp 2 kiểm tra độc lập sự tồn tại của tài liệu trên các CSDL khoa học quốc tế (8 nhãn như VERIFIED, METADATA_ERROR, SUSPECTED_HALLUCINATION).'
          : 'Layer 1 audits internal manuscript consistency between in-text markers and the bibliography (7 states including MATCHED, MISSING_REFERENCE, UNCITED_REFERENCE). Layer 2 independently audits external bibliographic existence across 15+ APIs (8 verdicts including VERIFIED, METADATA_ERROR, SUSPECTED_HALLUCINATION).',
    },
    {
      id: 'faq-2',
      q:
        lang === 'vi'
          ? 'Hệ thống hỗ trợ những chuẩn định dạng trích dẫn nào?'
          : 'Which academic citation styles does CITRA support?',
      a:
        lang === 'vi'
          ? 'Nhờ kết hợp GROBID TEI-XML và bộ Cross-Validator chuyên biệt, CITRA hỗ trợ đầy đủ chuẩn đánh số IEEE ([1], [2]–[5]), Vancouver, ACM cũng như chuẩn Tác giả - Năm của APA 7th, Harvard, Chicago và MLA.'
          : 'Through GROBID TEI-XML paired with our multi-style cross-validator, CITRA supports numbered styles (IEEE [1]–[5], Vancouver, ACM) as well as author-year formats (APA 7th, Harvard, Chicago, MLA).',
    },
  ];

  const rightFaqs = [
    {
      id: 'faq-3',
      q:
        lang === 'vi'
          ? 'CITRA có tự động đánh trượt hay kết luận sinh viên gian lận không?'
          : 'Does CITRA automatically accuse students of academic misconduct?',
      a:
        lang === 'vi'
          ? 'Tuyệt đối không. CITRA tuân thủ nghiêm ngặt nguyên tắc Hệ thống Hỗ trợ Ra Quyết định (Decision-Support System). Hệ thống cung cấp bằng chứng truy xuất từ cơ sở dữ liệu và chuỗi quy tắc R01–R20 để giảng viên và hội đồng xem xét; quyền quyết định cuối cùng luôn thuộc về con người.'
          : 'Never. CITRA is strictly a Decision-Support System. It surfaces verifiable bibliographic evidence and formal R01–R20 rule traces for human reviewers. Instructors can override any verdict with an audited rationale.',
    },
    {
      id: 'faq-4',
      q:
        lang === 'vi'
          ? 'Điều gì xảy ra nếu tài liệu tham khảo là sách in nội bộ hoặc tài liệu tiếng Việt chưa có DOI?'
          : 'What happens when a citation refers to an offline book or regional paper without a DOI?',
      a:
        lang === 'vi'
          ? 'Thay vì gắn nhãn ảo giác sai, quy tắc suy diễn của CITRA sẽ phân loại tài liệu đó vào trạng thái UNVERIFIABLE (Cần duyệt thủ công) để sinh viên hoặc giảng viên hướng dẫn kiểm tra và xác nhận.'
          : 'Rather than falsely flagging it as hallucinated, CITRA’s symbolic rule engine classifies offline or non-indexed works as UNVERIFIABLE, queuing them cleanly for instructor review.',
    },
    {
      id: 'faq-5',
      q:
        lang === 'vi'
          ? 'Mất bao lâu để kiểm chứng xong một quyển khóa luận hoặc bài báo PDF?'
          : 'How long does it take to verify a full PDF manuscript?',
      a:
        lang === 'vi'
          ? 'Nhờ cơ chế truy vấn bất đồng bộ song song trên 15+ API và bộ nhớ đệm SQLite FTS5, một bài báo khoa học 25–40 trích dẫn thường hoàn tất toàn bộ 4 giai đoạn kiểm chứng chỉ trong 10 đến 25 giây.'
          : 'With async parallel querying across 15+ APIs and local SQLite FTS5 caching, a standard manuscript with 25–40 references completes all four verification stages in 10 to 25 seconds.',
    },
  ];

  const renderColumn = (items: typeof leftFaqs, colOffset: number) => (
    <div className="flex-1 flex flex-col gap-[16px] w-full">
      {items.map((item, idx) => {
        const isOpen = Boolean(openIds[item.id]);
        return (
          <SolvaScrollReveal
            key={item.id}
            delayMs={colOffset + idx * 65}
            yOffset={24}
          >
            <div
              style={{ backgroundColor: 'var(--solva-surface)' }}
              className="w-full rounded-[12px] px-[24px] transition-colors duration-200"
            >
              <button
                type="button"
                onClick={() => toggleFaq(item.id)}
                aria-expanded={isOpen}
                className="w-full min-h-[73px] py-[20px] flex items-center justify-between gap-4 text-left cursor-pointer group"
              >
                <span
                  style={{ color: 'var(--solva-ink)' }}
                  className="font-solva-sans text-[17px] sm:text-[18px] font-normal leading-[25.2px]"
                >
                  {item.q}
                </span>
                <span
                  style={{ color: 'var(--solva-ink)' }}
                  className="relative w-[20px] h-[25px] flex items-center justify-center shrink-0"
                >
                  <Plus
                    className={`w-4 h-4 absolute transition-all duration-350 ease-[cubic-bezier(0.22,1,0.36,1)] ${
                      isOpen
                        ? 'rotate-90 opacity-0 scale-75'
                        : 'rotate-0 opacity-100 scale-100'
                    }`}
                  />
                  <Minus
                    className={`w-4 h-4 absolute transition-all duration-350 ease-[cubic-bezier(0.22,1,0.36,1)] ${
                      isOpen
                        ? 'rotate-0 opacity-100 scale-100'
                        : '-rotate-90 opacity-0 scale-75'
                    }`}
                  />
                </span>
              </button>
              <div
                style={{
                  gridTemplateRows: isOpen ? '1fr' : '0fr',
                  transition: 'grid-template-rows 420ms cubic-bezier(0.22, 1, 0.36, 1)',
                }}
                className="grid"
                aria-hidden={!isOpen}
              >
                <div className="overflow-hidden">
                  <div
                    style={{
                      opacity: isOpen ? 1 : 0,
                      transform: isOpen
                        ? 'translate3d(0, 0, 0)'
                        : 'translate3d(0, -10px, 0)',
                      filter: isOpen ? 'blur(0px)' : 'blur(2.5px)',
                      transition:
                        'opacity 360ms cubic-bezier(0.22, 1, 0.36, 1), transform 420ms cubic-bezier(0.22, 1, 0.36, 1), filter 320ms cubic-bezier(0.22, 1, 0.36, 1)',
                    }}
                    className="pb-[24px] pr-[24px]"
                  >
                    <p
                      style={{ color: 'var(--solva-muted)' }}
                      className="font-solva-sans text-[16px] font-normal leading-[23.2px]"
                    >
                      {item.a}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </SolvaScrollReveal>
        );
      })}
    </div>
  );

  return (
    <section
      id="faq"
      className="scroll-mt-[84px] lg:scroll-mt-[108px] py-[32px] sm:py-[48px] lg:py-[96px] px-5 sm:px-6 lg:px-[40px]"
    >
      <div className="max-w-[1200px] mx-auto flex flex-col gap-[28px] sm:gap-[36px] lg:gap-[64px]">
        {/* Headline */}
        <div className="flex flex-col items-start gap-[12px] max-w-[460px]">
          <SolvaEyebrow>FAQ</SolvaEyebrow>
          <SolvaTwoToneHeading
            primary={
              lang === 'vi' ? 'Bạn có câu hỏi.' : 'You have questions.'
            }
            secondary={
              lang === 'vi' ? 'CITRA có câu trả lời.' : 'We have answers.'
            }
          />
        </div>

        {/* 2 Independent Accordion Columns (`592px` each on Desktop, `gap: 16px`) */}
        <div className="flex flex-col lg:flex-row items-start gap-[16px]">
          {renderColumn(leftFaqs, 0)}
          {renderColumn(rightFaqs, 75)}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 11: BOTTOM CTA BANNER (`1200x400px` Split Painterly Card)
   ============================================================ */
function SolvaBottomCTASection({
  lang,
  isAuthenticated,
}: {
  lang: Lang;
  isAuthenticated: boolean;
}) {
  return (
    <section className="pt-[28px] pb-[36px] sm:py-[48px] lg:py-[96px] px-5 sm:px-6 lg:px-[40px]">
      <div className="max-w-[1200px] mx-auto">
        <SolvaScrollReveal yOffset={36}>
          <div
            style={{ backgroundColor: 'var(--solva-surface)' }}
            className="w-full rounded-[16px] p-[12px] grid grid-cols-1 lg:grid-cols-12 items-center gap-6"
          >
            {/* Left Editorial Content (`588x275px` equivalent, `padding: 24px 36px`) */}
            <div className="lg:col-span-6 p-5 sm:p-[32px] flex flex-col items-start gap-[24px]">
              <div className="space-y-[16px]">
                <SolvaTwoToneHeading
                  primary={
                    lang === 'vi'
                      ? 'Trao lại sự an tâm'
                      : 'Give your research'
                  }
                  secondary={
                    lang === 'vi'
                      ? 'cho mỗi bản thảo học thuật.'
                      : 'verifiable integrity.'
                  }
                />
                <p
                  style={{ color: 'var(--solva-muted)' }}
                  className="font-solva-sans text-[16px] font-normal leading-[23.2px] max-w-[420px]"
                >
                  {lang === 'vi'
                    ? 'Tải lên bản thảo PDF hoặc dán danh mục trích dẫn vào Live Sandbox. Nhận báo cáo kiểm chứng 2 tầng kèm đồ thị suy diễn Neuro-Symbolic ngay hôm nay.'
                    : 'Upload your PDF manuscript or paste references into the Live Sandbox. Get a complete two-layer verification report in seconds.'}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <SolvaButton
                  to={isAuthenticated ? '/upload' : '/login'}
                  variant="primary"
                >
                  {isAuthenticated
                    ? lang === 'vi'
                      ? 'Vào Workspace Kiểm chứng'
                      : 'Go to Verification Workspace'
                    : lang === 'vi'
                      ? 'Bắt đầu miễn phí'
                      : 'Get started free'}
                </SolvaButton>
                <SolvaButton to="/pricing" variant="outline">
                  {lang === 'vi' ? 'Xem các gói cước' : 'Compare plans'}
                </SolvaButton>
              </div>
            </div>

            {/* Right Painterly Frame (`588x376px` equivalent) */}
            <div className="lg:col-span-6">
              <SolvaPainterlyFrame
                paintingSrc="/solva/hero-bg.png"
                alt="Impressionist floral painting backdrop"
                radiusClass="rounded-[12px]"
                className="w-full min-h-[320px] sm:h-[376px] p-6 sm:p-8 flex items-center justify-center"
              >
                <div className="w-full max-w-[480px]">
                  <BottomCTAMockup lang={lang} />
                </div>
              </SolvaPainterlyFrame>
            </div>
          </div>
        </SolvaScrollReveal>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION 12: FOOTER (Full-Bleed `#F4F2EC`, 4 Menu Columns)
   ============================================================ */
function SolvaFooter({ lang }: { lang: Lang }) {
  const columns = [
    {
      header: lang === 'vi' ? 'Sản phẩm' : 'Product',
      links: [
        { label: lang === 'vi' ? 'Trình gỡ lỗi trích dẫn' : 'Citation Debugger', href: '#interactive-demo' },
        { label: lang === 'vi' ? 'Kiến trúc 2 tầng' : '2-Layer Architecture', href: '#architecture' },
        { label: lang === 'vi' ? 'Quy trình 4 giai đoạn' : 'Verification Pipeline', href: '#how-it-works' },
        { label: lang === 'vi' ? 'Gói cước & Quyền lợi' : 'Pricing & Benefits', href: '#taxonomy' },
      ],
    },
    {
      header: lang === 'vi' ? 'Không gian làm việc' : 'Workspaces',
      links: [
        { label: lang === 'vi' ? 'Dành cho Sinh viên' : 'Student Workspace', href: '#workspaces' },
        { label: lang === 'vi' ? 'Dành cho Giảng viên' : 'Teacher Classroom', href: '#workspaces' },
        { label: lang === 'vi' ? 'Quản trị hệ thống' : 'Admin Control', href: '#workspaces' },
        { label: lang === 'vi' ? 'Bảng giá & Gói cước' : 'Pricing Plans', to: '/pricing' },
      ],
    },
    {
      header: lang === 'vi' ? 'Công nghệ' : 'Technology',
      links: [
        { label: 'GROBID TEI-XML', href: '#how-it-works' },
        { label: '15+ Scholarly APIs', href: '#architecture' },
        { label: 'Neuro-Symbolic Rules', href: '#interactive-demo' },
        { label: 'DeBERTa-v3 NLI Stance', href: '#how-it-works' },
      ],
    },
    {
      header: lang === 'vi' ? 'Tài khoản' : 'Account',
      links: [
        { label: lang === 'vi' ? 'Đăng nhập' : 'Sign in', to: '/login' },
        { label: lang === 'vi' ? 'Tạo tài khoản' : 'Create account', to: '/register' },
        { label: lang === 'vi' ? 'Câu hỏi thường gặp' : 'FAQ', href: '#faq' },
      ],
    },
  ];

  return (
    <footer
      style={{ backgroundColor: 'var(--solva-surface)' }}
      className="pt-[36px] sm:pt-[48px] lg:pt-[96px] pb-[24px] sm:pb-[32px] px-5 sm:px-6 lg:px-[40px]"
    >
      <div className="max-w-[1200px] mx-auto flex flex-col gap-[28px] sm:gap-[36px] lg:gap-[48px]">
        {/* Top Row: Brand Info (389px) + 4 Columns (779px) */}
        <div className="flex flex-col lg:flex-row items-start justify-between gap-[28px] sm:gap-[36px] lg:gap-[32px]">
          {/* Left Brand Info */}
          <div className="w-full lg:w-[389px] flex flex-col items-start gap-[16px]">
            <Link to="/" className="inline-flex items-center gap-[10px]">
              <span className="w-[32px] h-[32px] rounded-[8px] bg-white dark:bg-[#1E1C17] border border-[#E7E3D9] dark:border-[#332F26] shadow-2xs flex items-center justify-center p-1 shrink-0 transition-colors">
                <SourceLogicLogo size={20} />
              </span>
              <span
                style={{ color: 'var(--solva-ink)' }}
                className="font-solva-sans text-[28px] font-medium tracking-[-0.02em] leading-none"
              >
                CITRA
              </span>
            </Link>

            <p
              style={{ color: 'var(--solva-muted)' }}
              className="font-solva-sans text-[16px] font-normal leading-[23.2px] max-w-[290px]"
            >
              {lang === 'vi'
                ? 'Không gian kiểm chứng nguồn trích dẫn học thuật đa nguồn dựa trên kiến trúc Neuro-Symbolic 2 tầng.'
                : 'Academic source verification workspace powered by a two-layer Neuro-Symbolic and 15+ API engine.'}
            </p>
          </div>

          {/* Right 4 Navigation Columns */}
          <div className="w-full lg:w-[779px] grid grid-cols-2 sm:grid-cols-4 gap-[24px]">
            {columns.map((col) => (
              <div key={col.header} className="flex flex-col gap-[12px]">
                <h4
                  style={{ color: 'var(--solva-ink)' }}
                  className="font-solva-sans text-[18px] font-normal leading-[25.2px]"
                >
                  {col.header}
                </h4>
                <ul className="flex flex-col gap-[10px]">
                  {col.links.map((lnk) => (
                    <li key={lnk.label}>
                      {'to' in lnk && lnk.to ? (
                        <Link
                          to={lnk.to}
                          style={{ color: 'var(--solva-muted)' }}
                          className="font-solva-sans text-[16px] font-normal leading-[23.2px] hover:opacity-75 transition-opacity"
                        >
                          {lnk.label}
                        </Link>
                      ) : (
                        <a
                          href={lnk.href}
                          style={{ color: 'var(--solva-muted)' }}
                          className="font-solva-sans text-[16px] font-normal leading-[23.2px] hover:opacity-75 transition-opacity"
                        >
                          {lnk.label}
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Copyright Bar (`border-top: 1px solid #E7E3D9`) */}
        <div
          style={{ borderColor: 'var(--solva-border)' }}
          className="pt-[20px] sm:pt-[32px] border-t flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4 font-solva-sans text-[14px] sm:text-[16px]"
        >
          <p style={{ color: 'var(--solva-muted)' }}>
            © 2026 CITRA · SourceLogic Academic Integrity Workspace. All rights reserved.
          </p>
          <p style={{ color: 'var(--solva-muted)' }}>
            {lang === 'vi'
              ? 'Hệ thống hỗ trợ rà soát học thuật — không thay thế phán quyết của giảng viên.'
              : 'Decision-Support System — assists scholarly review, never replaces human judgment.'}
          </p>
        </div>
      </div>
    </footer>
  );
}
