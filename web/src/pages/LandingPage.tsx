import { useState, useEffect, useRef, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  FileSearch,
  Link2,
  Database,
  Shield,
  ArrowRight,
  CheckCircle2,
  GitBranch,
  Quote,
  Search,
  Scale,
  FileQuestion,
  AlertTriangle,
  XCircle,
  Layers,
  Terminal,
  FileText,
  Users,
  GraduationCap,
  Sliders,
  Check,
  BookOpen,
  Cpu,
  ChevronRight,
  Globe,
  ArrowUpRight,
  Play,
  Pause,
  Activity,
  Menu,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { ThemeToggle } from '@/contexts/ThemeContext';

/* ============================================================
   CITRA — Scholarly Precision Landing Page (shadcn/ui)
   Academic Source Verification Workspace & Citation Debugger
   ============================================================ */

type Lang = 'en' | 'vi';

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
    contextAfter:
      ' in the Transformer architecture.',
    verdict: 'VERIFIED',
    verdictBadgeClass: 'verdict-badge-verified',
    mappingStatus: 'MATCHED',
    mappingBadgeClass: 'mapping-badge-matched',
    confidence: 98,
    citedMeta: {
      title: 'Attention Is All You Need',
      authors: 'A. Vaswani, N. Shazeer, N. Parmar, et al.',
      year: '2017',
      venue: 'Advances in Neural Information Processing Systems (NeurIPS)',
      doi: '10.48550/arXiv.1706.03762',
    },
    retrievedMeta: {
      title: 'Attention Is All You Need',
      authors: 'Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, et al.',
      year: '2017',
      venue: 'Advances in Neural Information Processing Systems 30 (NIPS 2017)',
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
      { name: 'Local ACL / ArXiv FTS5', status: 'matched', latency: '14ms', score: '0.99' },
      { name: 'DBLP', status: 'matched', latency: '145ms', score: '0.99' },
      { name: 'OpenAlex', status: 'matched', latency: '185ms', score: '0.98' },
      { name: 'Crossref', status: 'matched', latency: '240ms', score: '0.96' },
    ],
    rules: [
      {
        code: 'R01',
        name: 'EXACT_IDENTIFIER_MATCH',
        condition: 'IF doi_match == TRUE AND title_sim >= 0.95 → VERIFIED',
        status: 'passed',
      },
      {
        code: 'R03',
        name: 'AUTHOR_YEAR_CONSISTENCY',
        condition: 'IF first_author_match == TRUE AND |year_diff| == 0 → PASS',
        status: 'passed',
      },
      {
        code: 'R04',
        name: 'MULTI_SOURCE_CORROBORATION',
        condition: 'IF matched_databases >= 2 → CONFIDENCE_BOOST(+0.10)',
        status: 'passed',
      },
    ],
    explanation: {
      en: 'Exact publication verified across 4 databases. Title, primary authors, publication year (2017), and identifier match canonical records.',
      vi: 'Xác minh chính xác trên 4 cơ sở dữ liệu. Tiêu đề, nhóm tác giả, năm xuất bản (2017) và mã định danh khớp hoàn toàn với bản ghi gốc.',
    },
  },
  {
    id: 'cit-4',
    marker: '[4]',
    inText: 'Nguyen & Tran (2021) [4]',
    page: 'p. 5',
    contextBefore:
      'Prior Vietnamese NLP studies on automated reference checking demonstrated that hybrid rule systems reduce false positives, notably ',
    contextAfter:
      ' in their evaluation of university theses.',
    verdict: 'METADATA_ERROR',
    verdictBadgeClass: 'verdict-badge-metadata-error',
    mappingStatus: 'MATCHED',
    mappingBadgeClass: 'mapping-badge-matched',
    confidence: 78,
    citedMeta: {
      title: 'Deep Learning for Automatic Essay Evaluation',
      authors: 'T. H. Nguyen, P. K. Tran',
      year: '2021',
      venue: 'Journal of Artificial Intelligence Research',
      doi: 'Not provided in bibliography',
    },
    retrievedMeta: {
      title: 'Deep Learning for Automated Essay Assessment',
      authors: 'T. H. Nguyen, P. K. Tran',
      year: '2020',
      venue: 'Computers & Education',
      doi: '10.1016/j.compedu.2020.103942',
    },
    fieldStatus: {
      title: 'partial',
      authors: 'match',
      year: 'mismatch',
      venue: 'mismatch',
      doi: 'missing',
    },
    sources: [
      { name: 'Crossref', status: 'matched', latency: '195ms', score: '0.88' },
      { name: 'OpenAlex', status: 'matched', latency: '220ms', score: '0.86' },
      { name: 'DBLP', status: 'partial', latency: '165ms', score: '0.84' },
      { name: 'arXiv', status: 'none', latency: '210ms', score: '—' },
    ],
    rules: [
      {
        code: 'R02',
        name: 'HIGH_TITLE_AUTHOR_SIMILARITY',
        condition: 'IF title_sim >= 0.85 AND author_overlap >= 0.90 → CANDIDATE_FOUND',
        status: 'passed',
      },
      {
        code: 'R05',
        name: 'PUBLICATION_YEAR_DRIFT',
        condition: 'IF |cited_year - actual_year| == 1 → FLAG_METADATA_ERROR (year)',
        status: 'warning',
      },
      {
        code: 'R06',
        name: 'VENUE_DISCREPANCY',
        condition: 'IF venue_sim < 0.50 → FLAG_METADATA_ERROR (venue)',
        status: 'warning',
      },
    ],
    explanation: {
      en: 'Paper exists by Nguyen & Tran, but cited year (2021) differs from canonical publication year (2020) and journal venue is misattributed.',
      vi: 'Bài báo của Nguyen & Tran có tồn tại, nhưng năm trích dẫn (2021) lệch với năm xuất bản thực tế (2020) và sai tên tạp chí đăng tải.',
    },
  },
  {
    id: 'cit-9',
    marker: '[9]',
    inText: 'Smith, Doe & Reynolds [9]',
    page: 'p. 11',
    contextBefore:
      'Furthermore, zero-shot quantum citation synthesis was claimed to achieve 99.8% accuracy across 50 languages by ',
    contextAfter:
      ' using synthetic tensor graphs.',
    verdict: 'SUSPECTED_HALLUCINATION',
    verdictBadgeClass: 'verdict-badge-hallucinated',
    mappingStatus: 'MATCHED',
    mappingBadgeClass: 'mapping-badge-matched',
    confidence: 12,
    citedMeta: {
      title: 'Quantum Tensor Graphs for Zero-Shot Multilingual Citation Synthesis',
      authors: 'J. Smith, A. Doe, M. Reynolds',
      year: '2024',
      venue: 'International Transactions on Quantum NLP',
      doi: '10.9999/itqnlp.2024.88412',
    },
    retrievedMeta: null,
    fieldStatus: {
      title: 'mismatch',
      authors: 'mismatch',
      year: 'mismatch',
      venue: 'mismatch',
      doi: 'mismatch',
    },
    sources: [
      { name: 'Local ACL FTS5 (127K)', status: 'none', latency: '9ms', score: '0.18' },
      { name: 'Crossref', status: 'none', latency: '180ms', score: '0.00' },
      { name: 'OpenAlex', status: 'none', latency: '205ms', score: '0.14' },
      { name: 'DBLP', status: 'none', latency: '150ms', score: '0.11' },
    ],
    rules: [
      {
        code: 'R09',
        name: 'INVALID_DOI_PREFIX',
        condition: 'IF doi_prefix == "10.9999" OR doi_resolves == FALSE → INVALID_DOI',
        status: 'failed',
      },
      {
        code: 'R10',
        name: 'ZERO_CANDIDATE_MATCH',
        condition: 'IF max(candidate_similarity) < 0.45 ACROSS all_sources → NO_MATCH',
        status: 'failed',
      },
      {
        code: 'R11',
        name: 'SUSPECTED_AI_HALLUCINATION',
        condition: 'IF no_source_found AND unverified_venue → SUSPECTED_HALLUCINATION',
        status: 'failed',
      },
    ],
    explanation: {
      en: 'No matching publication found across Local ACL Anthology or 6 global scholarly APIs. DOI prefix 10.9999 is non-existent. Flagged for instructor review.',
      vi: 'Không tìm thấy công bố nào khớp trên Local ACL Anthology và 6 API học thuật quốc tế. Mã DOI 10.9999 không tồn tại. Đánh dấu cần giảng viên kiểm tra.',
    },
  },
  {
    id: 'cit-14',
    marker: '[14]',
    inText: '(LeCun et al., 2015) [14]',
    page: 'p. 14',
    contextBefore:
      'Convolutional and representation learning hierarchies follow the foundational formulation established in ',
    contextAfter:
      ' for deep neural networks.',
    verdict: 'UNRESOLVED',
    verdictBadgeClass: 'verdict-badge-unverifiable',
    mappingStatus: 'MISSING_REFERENCE',
    mappingBadgeClass: 'mapping-badge-missing',
    confidence: 45,
    citedMeta: {
      title: '[Orphan In-Text Citation — Missing from Bibliography]',
      authors: 'LeCun et al.',
      year: '2015',
      venue: 'Not listed in References section',
      doi: 'Missing bibliography entry',
    },
    retrievedMeta: {
      title: 'Deep learning (Candidate match via In-Text hint)',
      authors: 'Yann LeCun, Yoshua Bengio, Geoffrey Hinton',
      year: '2015',
      venue: 'Nature, Vol. 521, pp. 436–444',
      doi: '10.1038/nature14539',
    },
    fieldStatus: {
      title: 'missing',
      authors: 'partial',
      year: 'match',
      venue: 'missing',
      doi: 'missing',
    },
    sources: [
      { name: 'CitationLinker (Layer 1)', status: 'none', latency: '2ms', score: 'Orphan' },
      { name: 'Crossref (In-Text Hint)', status: 'partial', latency: '190ms', score: '0.74' },
    ],
    rules: [
      {
        code: 'L01',
        name: 'BIDIRECTIONAL_LINK_CHECK',
        condition: 'IF in_text_citation NOT IN bibliography_entries → MISSING_REFERENCE',
        status: 'failed',
      },
      {
        code: 'R12',
        name: 'INSUFFICIENT_BIBLIOGRAPHY_DATA',
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

function SourceLogicLogo({ size = 26 }: { size?: number }) {
  return (
    <img
      src="/citra-logo.png"
      alt="CITRA Logo"
      width={size}
      height={size}
      loading="eager"
      decoding="async"
      className="object-contain select-none"
    />
  );
}

/* ============================================================
   Scroll-Reveal Wrapper Component
   ============================================================ */
function RevealOnScroll({
  children,
  delay = 0,
  className = '',
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === 'undefined') {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.unobserve(el);
        }
      },
      { threshold: 0.08, rootMargin: '0px 0px -30px 0px' }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      style={{ transitionDelay: `${delay}ms` }}
      className={`transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] will-change-transform ${
        visible
          ? 'opacity-100 translate-y-0 scale-100'
          : 'opacity-0 translate-y-6 scale-[0.985]'
      } ${className}`}
    >
      {children}
    </div>
  );
}

export function LandingPage() {
  const { i18n } = useTranslation();
  const lang: Lang = i18n.language?.startsWith('vi') ? 'vi' : 'en';
  const isAuthenticated =
    typeof window !== 'undefined' && Boolean(localStorage.getItem('token'));

  const toggleLanguage = () => {
    const next = lang === 'en' ? 'vi' : 'en';
    void i18n.changeLanguage(next);
  };

  return (
    <div className="min-h-screen bg-slate-50/60 dark:bg-slate-950 text-slate-900 dark:text-slate-50 selection:bg-indigo-500/20 selection:text-indigo-600 dark:selection:text-indigo-300">
      <LandingHeader
        lang={lang}
        onToggleLanguage={toggleLanguage}
        isAuthenticated={isAuthenticated}
      />
      <main>
        <HeroSection lang={lang} isAuthenticated={isAuthenticated} />
        <InteractiveInspectorSection lang={lang} />
        <BentoArchitectureSection lang={lang} />
        <PipelineSection lang={lang} />
        <TaxonomySection lang={lang} />
        <RoleWorkspacesSection lang={lang} />
        <CTASection lang={lang} isAuthenticated={isAuthenticated} />
      </main>
      <LandingFooter lang={lang} />
    </div>
  );
}

/* ============================================================
   1. Sticky Glassmorphic Header with Scroll Progress & Active Spy
   ============================================================ */
function LandingHeader({
  lang,
  onToggleLanguage,
  isAuthenticated,
}: {
  lang: Lang;
  onToggleLanguage: () => void;
  isAuthenticated: boolean;
}) {
  const [scrollProgress, setScrollProgress] = useState(0);
  const [activeHash, setActiveHash] = useState<string>('');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const sectionIds = [
      'interactive-demo',
      'architecture',
      'how-it-works',
      'taxonomy',
      'workspaces',
    ];

    const handleScroll = () => {
      const scrollTop = window.scrollY;
      const docHeight =
        document.documentElement.scrollHeight - window.innerHeight;
      const pct = docHeight > 0 ? Math.min(100, Math.max(0, (scrollTop / docHeight) * 100)) : 0;
      setScrollProgress(pct);

      let currentSection = '';
      for (const id of sectionIds) {
        const el = document.getElementById(id);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= 160 && rect.bottom >= 160) {
            currentSection = `#${id}`;
            break;
          }
        }
      }
      setActiveHash(currentSection);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navItems =
    lang === 'vi'
      ? [
          { label: 'Trình gỡ lỗi', href: '#interactive-demo' },
          { label: 'Kiến trúc 2 lớp', href: '#architecture' },
          { label: 'Quy trình', href: '#how-it-works' },
          { label: 'Phân loại nhãn', href: '#taxonomy' },
          { label: 'Phân quyền', href: '#workspaces' },
        ]
      : [
          { label: 'Live Inspector', href: '#interactive-demo' },
          { label: 'Architecture', href: '#architecture' },
          { label: 'Pipeline', href: '#how-it-works' },
          { label: 'Taxonomy', href: '#taxonomy' },
          { label: 'Workspaces', href: '#workspaces' },
        ];

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 dark:border-slate-800/80 bg-white/85 dark:bg-slate-950/85 backdrop-blur-xl transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-3.5 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-2 sm:gap-4">
        {/* Brand Identity */}
        <Link to="/" className="flex items-center gap-2.5 sm:gap-3 group focus-ring rounded-xl shrink-0">
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-white dark:bg-white/95 p-1.5 flex items-center justify-center shadow-sm ring-1 ring-slate-200/90 dark:ring-white/20 group-hover:scale-105 group-hover:shadow-md transition-all duration-300">
            <SourceLogicLogo size={26} />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-display text-base sm:text-lg font-bold tracking-tight text-slate-900 dark:text-white leading-none whitespace-nowrap">
                CITRA
              </span>
            </div>
            <span className="hidden sm:block text-[11px] text-slate-500 dark:text-slate-400 font-medium mt-0.5 whitespace-nowrap">
              {lang === 'vi'
                ? 'Kiểm chứng Nguồn Học thuật'
                : 'Academic Source Verification'}
            </span>
          </div>
        </Link>

        {/* Center Navigation Pills */}
        <nav
          aria-label="Primary Navigation"
          className="hidden lg:flex items-center gap-1 p-1 rounded-xl bg-slate-100/80 dark:bg-slate-900/80 border border-slate-200/60 dark:border-slate-800/60"
        >
          {navItems.map((item) => {
            const isActive = activeHash === item.href;
            return (
              <a
                key={item.href}
                href={item.href}
                className={`whitespace-nowrap px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 font-semibold shadow-2xs ring-1 ring-slate-200/70 dark:ring-slate-700'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-white/70 dark:hover:bg-slate-800/60'
                }`}
              >
                {item.label}
              </a>
            );
          })}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          <button
            type="button"
            onClick={onToggleLanguage}
            className="inline-flex items-center gap-1 h-9 px-2 sm:px-2.5 rounded-lg text-xs font-mono font-semibold text-slate-600 dark:text-slate-300 bg-slate-100/80 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 hover:bg-slate-200/70 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            title={lang === 'vi' ? 'Switch to English' : 'Chuyển sang Tiếng Việt'}
          >
            <Globe className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
            <span>{lang === 'vi' ? 'VI' : 'EN'}</span>
          </button>

          <ThemeToggle size="sm" />

          <Separator orientation="vertical" className="h-5 hidden sm:block mx-0.5" />

          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
            <Link to="/login">Sign in</Link>
          </Button>

          <Button
            asChild
            size="sm"
            className="group rounded-lg px-2.5 sm:px-3 text-xs sm:text-sm shadow-sm shadow-indigo-500/20 bg-indigo-600 hover:bg-indigo-700 text-white btn-shimmer"
          >
            <Link to={isAuthenticated ? '/dashboard' : '/login'}>
              <span>
                {isAuthenticated
                  ? lang === 'vi'
                    ? 'Workspace'
                    : 'Workspace'
                  : lang === 'vi'
                    ? 'Bắt đầu'
                    : 'Get Started'}
              </span>
              <ArrowRight className="h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5" />
            </Link>
          </Button>

          <button
            type="button"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
            className="lg:hidden inline-flex items-center justify-center h-9 w-9 rounded-lg bg-slate-100/80 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200/70 dark:hover:bg-slate-800 transition-colors"
          >
            {mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Mobile / Tablet Navigation Drawer (< lg) */}
      {mobileMenuOpen && (
        <nav
          aria-label="Mobile Navigation"
          className="lg:hidden border-t border-slate-200/80 dark:border-slate-800/80 bg-white/95 dark:bg-slate-950/95 backdrop-blur-xl px-4 py-3 space-y-1.5 animate-fade-in"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
            {navItems.map((item) => {
              const isActive = activeHash === item.href;
              return (
                <a
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-50 dark:bg-indigo-950/80 text-indigo-600 dark:text-indigo-400 font-semibold'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-900'
                  }`}
                >
                  <span>{item.label}</span>
                  <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
                </a>
              );
            })}
          </div>
          <div className="pt-2 border-t border-slate-200/70 dark:border-slate-800/70 flex items-center gap-2 sm:hidden">
            <Button asChild variant="outline" size="sm" className="flex-1 rounded-xl">
              <Link to="/login" onClick={() => setMobileMenuOpen(false)}>
                Sign in
              </Link>
            </Button>
            <Button asChild size="sm" className="flex-1 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white">
              <Link to="/register" onClick={() => setMobileMenuOpen(false)}>
                {lang === 'vi' ? 'Đăng ký' : 'Create Account'}
              </Link>
            </Button>
          </div>
        </nav>
      )}

      {/* Scroll Progress Indicator Bar */}
      <div className="h-[2px] w-full bg-transparent overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-indigo-600 via-indigo-500 to-emerald-500 transition-[width] duration-150 ease-out"
          style={{ width: `${scrollProgress}%` }}
        />
      </div>
    </header>
  );
}

/* ============================================================
   2. Hero Section with Animated Pipeline & Metrics Strip
   ============================================================ */
function HeroSection({
  lang,
  isAuthenticated,
}: {
  lang: Lang;
  isAuthenticated: boolean;
}) {
  const [activePipelineNode, setActivePipelineNode] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActivePipelineNode((prev) => (prev + 1) % 5);
    }, 2400);
    return () => window.clearInterval(timer);
  }, []);

  const pipelineNodes = [
    { label: 'PDF Manuscript', icon: FileText },
    { label: 'GROBID TEI-XML' },
    { label: 'In-Text [N] ↔ Bib #N' },
    { label: 'ACL FTS5 + 6 APIs' },
    { label: 'VERIFIED (CIS 84.5)', isVerdict: true },
  ];

  const metrics =
    lang === 'vi'
      ? [
          {
            value: '127,000+',
            label: 'Bài báo ACL Anthology nội bộ',
            sub: 'Truy vấn SQLite FTS5 < 15ms',
          },
          {
            value: '7 Nguồn CSDL',
            label: 'ACL · Crossref · OpenAlex · DBLP · arXiv · Books · PMC',
            sub: 'Điều phối phân tầng theo miền học thuật',
          },
          {
            value: '2 Lớp Kiểm chứng',
            label: 'Liên kết In-Text ↔ Danh mục & Nguồn',
            sub: 'Phát hiện trích dẫn mồ côi & lệch năm',
          },
          {
            value: 'R01 – R12',
            label: 'Tập luật Suy diễn Neuro-Symbolic',
            sub: 'Giải thích minh bạch 100% từng kết luận',
          },
        ]
      : [
          {
            value: '127,000+',
            label: 'Local ACL Anthology Index',
            sub: 'Sub-15ms SQLite FTS5 retrieval',
          },
          {
            value: '7 Databases',
            label: 'ACL · Crossref · OpenAlex · DBLP · arXiv · Books · PMC',
            sub: 'Smart domain-aware scholarly routing',
          },
          {
            value: '2-Layer Engine',
            label: 'In-Text Linking + Source Proof',
            sub: 'Catches orphans & metadata drift',
          },
          {
            value: 'Rules R01–R12',
            label: 'Neuro-Symbolic Logic Trace',
            sub: '100% explainable evidence chains',
          },
        ];

  return (
    <section className="relative overflow-hidden pt-10 pb-12 md:pt-14 md:pb-16 border-b border-slate-200/80 dark:border-slate-800/80">
      {/* Subtle Architectural Grid + Floating Radial Glow Orbs */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div
          className="absolute inset-0 opacity-60 dark:opacity-25"
          style={{
            backgroundImage:
              'radial-gradient(rgb(148 163 184 / 0.35) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />
        <div className="absolute -top-10 left-1/2 -translate-x-1/2 w-[900px] h-[420px] bg-gradient-to-tr from-indigo-500/18 via-indigo-400/8 to-emerald-500/12 blur-3xl rounded-full animate-float-slow" />
        <div className="absolute top-24 left-1/4 w-[360px] h-[260px] bg-indigo-500/10 dark:bg-indigo-500/15 blur-3xl rounded-full animate-float-reverse" />
        <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-slate-50/90 dark:from-slate-950 to-transparent" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          {/* Top Announcement Pill */}
          <div
            style={{ animationDelay: '80ms' }}
            className="animate-hero-reveal inline-flex flex-wrap items-center justify-center gap-2 px-3 sm:pl-2.5 sm:pr-3.5 py-1.5 sm:py-1 rounded-2xl sm:rounded-full max-w-full bg-white/90 dark:bg-slate-900/90 border border-slate-200/90 dark:border-slate-800 shadow-sm hover:border-indigo-300 dark:hover:border-indigo-700 transition-all duration-300 mb-6"
          >
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] sm:text-[11px] font-mono font-semibold bg-indigo-600 text-white shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-pulse" />
              NEURO-SYMBOLIC
            </span>
            <span className="text-[11px] sm:text-xs font-medium text-slate-700 dark:text-slate-300">
              {lang === 'vi'
                ? 'Không gian Gỡ lỗi & Kiểm chứng Toàn vẹn Trích dẫn Học thuật'
                : 'Academic Source Verification Workspace & Citation Debugger'}
            </span>
            <a
              href="#interactive-demo"
              className="group inline-flex items-center gap-0.5 text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline whitespace-nowrap"
            >
              <span>{lang === 'vi' ? 'Xem Demo' : 'Live Demo'}</span>
              <ChevronRight className="h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5" />
            </a>
          </div>

          {/* Main Display Headline */}
          <h1 className="font-display text-3xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-900 dark:text-white leading-[1.1] mb-5">
            {lang === 'vi' ? (
              <>
                <span
                  style={{ animationDelay: '300ms', animationDuration: '1350ms' }}
                  className="block animate-hero-reveal"
                >
                  Kiểm chứng mọi trích dẫn.
                </span>
                <span
                  style={{ animationDelay: '680ms', animationDuration: '1450ms' }}
                  className="block animate-hero-reveal mt-1"
                >
                  <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 via-indigo-500 to-emerald-600 dark:from-indigo-400 dark:via-indigo-300 dark:to-emerald-400 animate-gradient-x">
                    Truy vết mọi nguồn học thuật.
                  </span>
                </span>
              </>
            ) : (
              <>
                <span
                  style={{ animationDelay: '300ms', animationDuration: '1350ms' }}
                  className="block animate-hero-reveal"
                >
                  Verify Every Citation.
                </span>
                <span
                  style={{ animationDelay: '680ms', animationDuration: '1450ms' }}
                  className="block animate-hero-reveal mt-1"
                >
                  <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 via-indigo-500 to-emerald-600 dark:from-indigo-400 dark:via-indigo-300 dark:to-emerald-400 animate-gradient-x">
                    Trace Every Source.
                  </span>
                </span>
              </>
            )}
          </h1>

          {/* Supporting Copy */}
          <p
            style={{ animationDelay: '1080ms', animationDuration: '1500ms' }}
            className="animate-hero-reveal text-base sm:text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto leading-relaxed mb-7"
          >
            {lang === 'vi'
              ? 'Phát hiện tài liệu tham khảo bịa đặt (AI hallucination), sai lệch metadata năm/tạp chí và trích dẫn mồ côi bằng kiến trúc kiểm chứng 2 lớp kết hợp đối chiếu đa cơ sở dữ liệu với suy diễn luật hình thức.'
              : 'Detect invalid, mismatched, and potentially hallucinated academic references with explainable two-layer verification powered by GROBID extraction, federated scholarly retrieval, and symbolic logic rules.'}
          </p>

          {/* CTA Buttons */}
          <div
            style={{ animationDelay: '1450ms', animationDuration: '1350ms' }}
            className="animate-hero-reveal flex flex-col sm:flex-row items-center justify-center gap-3.5 mb-8"
          >
            <Button
              asChild
              size="lg"
              className="group w-full sm:w-auto h-11 px-7 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-600/20 hover:shadow-xl hover:shadow-indigo-600/30 hover:-translate-y-0.5 transition-all duration-200 btn-shimmer"
            >
              <Link to={isAuthenticated ? '/upload' : '/login'}>
                <span>
                  {isAuthenticated
                    ? lang === 'vi'
                      ? 'Tải tài liệu kiểm tra ngay'
                      : 'Check a Document Now'
                    : lang === 'vi'
                      ? 'Đăng nhập để Kiểm chứng'
                      : 'Sign in to Get Started'}
                </span>
                <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" />
              </Link>
            </Button>

            <Button
              asChild
              variant="outline"
              size="lg"
              className="group w-full sm:w-auto h-11 px-6 rounded-xl text-sm font-semibold bg-white/90 dark:bg-slate-900/90 border-slate-300 dark:border-slate-700 hover:border-indigo-400 dark:hover:border-indigo-600 hover:-translate-y-0.5 transition-all duration-200"
            >
              <a href="#interactive-demo">
                <Terminal className="h-4 w-4 text-indigo-600 dark:text-indigo-400 transition-transform duration-200 group-hover:scale-110" />
                <span>
                  {lang === 'vi'
                    ? 'Trải nghiệm Citation Debugger'
                    : 'Explore Interactive Debugger'}
                </span>
              </a>
            </Button>
          </div>

          {/* Animated Pipeline Micro-Preview Pill Strip */}
          <div
            style={{ animationDelay: '1750ms', animationDuration: '1350ms' }}
            className="animate-hero-reveal relative overflow-hidden inline-flex flex-wrap items-center justify-center gap-2 px-4 py-2.5 rounded-2xl bg-white/90 dark:bg-slate-900/90 border border-slate-200/90 dark:border-slate-800 shadow-sm text-xs font-mono text-slate-600 dark:text-slate-400 mb-10"
          >
            {/* Traveling Horizontal Beam */}
            <div className="pointer-events-none absolute bottom-0 h-[2px] w-24 bg-gradient-to-r from-transparent via-indigo-500 to-emerald-500 animate-pipeline-beam" />

            {pipelineNodes.map((node, idx) => {
              const isActive = activePipelineNode === idx;
              const NodeIcon = node.icon;
              return (
                <div key={node.label} className="inline-flex items-center gap-2">
                  {node.isVerdict ? (
                    <span
                      onMouseEnter={() => setActivePipelineNode(idx)}
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border font-semibold transition-all duration-300 cursor-default ${
                        isActive
                          ? 'bg-emerald-500 text-white border-emerald-500 shadow-sm shadow-emerald-500/30 scale-105'
                          : 'bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800'
                      }`}
                    >
                      <Check className="h-3 w-3" /> {node.label}
                    </span>
                  ) : (
                    <span
                      onMouseEnter={() => setActivePipelineNode(idx)}
                      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg transition-all duration-300 cursor-default ${
                        isActive
                          ? 'bg-indigo-600 text-white font-semibold shadow-sm shadow-indigo-500/30 scale-[1.03]'
                          : idx === 0
                            ? 'text-slate-800 dark:text-slate-200 font-semibold'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      {NodeIcon && (
                        <NodeIcon
                          className={`h-3.5 w-3.5 ${
                            isActive
                              ? 'text-white'
                              : 'text-indigo-600 dark:text-indigo-400'
                          }`}
                        />
                      )}
                      {node.label}
                    </span>
                  )}
                  {idx < pipelineNodes.length - 1 && (
                    <span
                      className={`transition-colors duration-300 ${
                        activePipelineNode === idx
                          ? 'text-indigo-500 font-bold translate-x-0.5'
                          : 'text-slate-300 dark:text-slate-700'
                      }`}
                    >
                      →
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* 4 Architectural Metric Cards with Staggered Reveal & Hover Lift */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {metrics.map((m, idx) => (
            <RevealOnScroll key={idx} delay={idx * 90}>
              <div className="group relative overflow-hidden rounded-2xl bg-white dark:bg-slate-900/90 border border-slate-200/90 dark:border-slate-800 p-4 sm:p-5 shadow-sm hover:shadow-lg hover:-translate-y-1 hover:border-indigo-300 dark:hover:border-indigo-700 transition-all duration-300 h-full">
                {/* Animated Top Accent Line on Hover */}
                <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-indigo-600 via-indigo-500 to-emerald-500 scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left" />

                <div className="flex items-baseline justify-between gap-2 mb-1">
                  <span className="font-mono text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors whitespace-nowrap">
                    {m.value}
                  </span>
                  <span className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/80 px-2 py-0.5 rounded-md border border-indigo-200/50 dark:border-indigo-800/50 shrink-0 group-hover:scale-105 transition-transform">
                    0{idx + 1}
                  </span>
                </div>
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  {m.label}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  {m.sub}
                </p>
              </div>
            </RevealOnScroll>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   3. Interactive Citation Debugger IDE Preview (#interactive-demo)
   ============================================================ */
function InteractiveInspectorSection({ lang }: { lang: Lang }) {
  const [selectedId, setSelectedId] = useState<string>(DEMO_CITATIONS[1].id); // Default to METADATA_ERROR for rich diff demo
  const [isAutoPlaying, setIsAutoPlaying] = useState<boolean>(true);

  const activeCitation =
    DEMO_CITATIONS.find((c) => c.id === selectedId) || DEMO_CITATIONS[0];

  // Auto-cycle through sample citations unless paused or manually clicked
  useEffect(() => {
    if (!isAutoPlaying) return;
    const timer = window.setInterval(() => {
      setSelectedId((prev) => {
        const idx = DEMO_CITATIONS.findIndex((c) => c.id === prev);
        const nextIdx = (idx + 1) % DEMO_CITATIONS.length;
        return DEMO_CITATIONS[nextIdx].id;
      });
    }, 3800);
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
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            <Check className="h-3 w-3" /> 100% Match
          </span>
        );
      case 'partial':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
            <AlertTriangle className="h-3 w-3" /> 86% Sim
          </span>
        );
      case 'mismatch':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300 border border-red-200 dark:border-red-800">
            <XCircle className="h-3 w-3" /> Diff
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

  return (
    <section
      id="interactive-demo"
      className="py-16 md:py-24 bg-white dark:bg-slate-900/40 border-b border-slate-200/80 dark:border-slate-800/80"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Heading */}
        <RevealOnScroll>
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-6">
            <div>
              <div className="inline-flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2.5">
                <Terminal className="h-4 w-4" />
                <span>
                  {lang === 'vi'
                    ? 'Trình gỡ lỗi Trích dẫn Tương tác'
                    : 'Interactive Citation Debugger IDE'}
                </span>
              </div>
              <h2 className="font-display text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white tracking-tight">
                {lang === 'vi'
                  ? 'Soi chiếu từng trích dẫn. Giải thích từng quy tắc.'
                  : 'Inspect Every Citation. Audit Every Rule.'}
              </h2>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400 max-w-md">
              {lang === 'vi'
                ? 'Nhấp vào bất kỳ trích dẫn mẫu nào bên dưới để xem cách CITRA đối chiếu metadata song song và kích hoạt luật suy diễn R01–R12.'
                : 'Click any sample citation below to inspect live side-by-side metadata diffs, multi-source latency, and formal symbolic rule triggers.'}
            </p>
          </div>
        </RevealOnScroll>

        {/* IDE Window Mockup Container */}
        <RevealOnScroll delay={100}>
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950 shadow-xl overflow-hidden transition-shadow duration-500 hover:shadow-2xl hover:shadow-indigo-500/5">
            {/* Top Window Bar */}
            <div className="px-4 sm:px-6 py-3.5 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-red-400/80 inline-block" />
                  <span className="w-3 h-3 rounded-full bg-amber-400/80 inline-block" />
                  <span className="w-3 h-3 rounded-full bg-emerald-400/80 inline-block" />
                </div>
                <Separator orientation="vertical" className="h-4" />
                <div className="flex items-center gap-2 font-mono text-xs text-slate-700 dark:text-slate-300">
                  <FileText className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
                  <span className="font-semibold">
                    thesis_neural_retrieval_2025.pdf
                  </span>
                  <span className="hidden sm:inline text-slate-400">
                    (18 pages · 24 citations)
                  </span>
                </div>
              </div>

              {/* Right Status Bar in Chrome */}
              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsAutoPlaying((prev) => !prev)}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-mono font-semibold transition-all cursor-pointer ${
                    isAutoPlaying
                      ? 'bg-indigo-50/90 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:text-slate-900 dark:hover:text-white'
                  }`}
                  title={
                    lang === 'vi'
                      ? 'Bật/tắt tự động duyệt qua các trích dẫn mẫu'
                      : 'Toggle auto-cycling through sample citations'
                  }
                >
                  {isAutoPlaying ? (
                    <>
                      <Pause className="h-3 w-3 text-indigo-600 dark:text-indigo-400" />
                      <span>{lang === 'vi' ? 'Tự động duyệt' : 'Auto-Tour: ON'}</span>
                    </>
                  ) : (
                    <>
                      <Play className="h-3 w-3" />
                      <span>{lang === 'vi' ? 'Tiếp tục duyệt' : 'Auto-Tour: PAUSED'}</span>
                    </>
                  )}
                </button>
                <Badge
                  variant="outline"
                  className="hidden sm:inline-flex font-mono text-[11px] bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700"
                >
                  Style: IEEE / APA
                </Badge>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/90 border border-indigo-200/80 dark:border-indigo-800 text-xs font-mono">
                  <span className="text-slate-500 dark:text-slate-400">CIS:</span>
                  <span className="font-bold text-indigo-700 dark:text-indigo-300">
                    84.5 / 100
                  </span>
                </div>
              </div>
            </div>

            {/* Split-Pane Debugger Body */}
            <div className="grid lg:grid-cols-12">
              {/* Left Pane: Extracted Citations Queue (5 cols) */}
              <div className="lg:col-span-5 border-b lg:border-b-0 lg:border-r border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/50 p-4 sm:p-5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-mono uppercase tracking-wider font-semibold text-slate-500 dark:text-slate-400">
                      {lang === 'vi'
                        ? 'Trích dẫn bóc tách từ PDF (Chọn để khám xét)'
                        : 'Extracted Citations (Select to Inspect)'}
                    </span>
                    <span className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400">
                      4 / 24 shown
                    </span>
                  </div>

                  {/* Clickable Citation Cards */}
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
                          className={`group relative overflow-hidden w-full text-left p-3.5 rounded-xl border transition-all duration-300 cursor-pointer ${
                            isSelected
                              ? 'bg-indigo-50/75 dark:bg-indigo-950/50 border-indigo-500 dark:border-indigo-500 shadow-md shadow-indigo-500/10 ring-1 ring-indigo-500/30 -translate-y-0.5'
                              : 'bg-white dark:bg-slate-900 border-slate-200/90 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-800 hover:-translate-y-0.5 hover:shadow-sm'
                          }`}
                        >
                          {/* Active Left Indicator Bar */}
                          <span
                            className={`absolute left-0 top-0 bottom-0 w-1 transition-all duration-300 ${
                              isSelected
                                ? 'bg-indigo-600 dark:bg-indigo-400 opacity-100'
                                : 'bg-transparent opacity-0'
                            }`}
                          />

                          <div className="flex items-center justify-between gap-2 mb-1.5">
                            <div className="flex items-center gap-2">
                              <span
                                className={`font-mono text-xs font-bold px-2 py-0.5 rounded transition-colors ${
                                  isSelected
                                    ? 'bg-indigo-600 text-white'
                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200'
                                }`}
                              >
                                {cit.marker}
                              </span>
                              <span className="font-semibold text-sm text-slate-900 dark:text-white truncate">
                                {cit.inText}
                              </span>
                            </div>
                            <span className="font-mono text-[11px] text-slate-400 shrink-0">
                              {cit.page}
                            </span>
                          </div>

                          <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-1 mb-2.5 font-serif italic">
                            &ldquo;{cit.citedMeta.title}&rdquo;
                          </p>

                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-1.5">
                              <span
                                className={`verdict-badge ${cit.verdictBadgeClass} text-[10px] px-2.5 py-0.5 font-mono`}
                              >
                                {cit.verdict}
                              </span>
                              <span
                                className={`mapping-badge ${cit.mappingBadgeClass} text-[10px] px-2 py-0.5 font-mono`}
                              >
                                {cit.mappingStatus}
                              </span>
                            </div>
                            <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                              Conf:{' '}
                              <strong className="text-slate-800 dark:text-slate-200">
                                {cit.confidence}%
                              </strong>
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Document Context Snippet Box */}
                <div
                  key={`ctx-${activeCitation.id}`}
                  className="mt-5 p-3.5 rounded-xl bg-slate-100/80 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 animate-debugger-switch"
                >
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1.5">
                    <span>MANUSCRIPT CONTEXT ({activeCitation.page})</span>
                    <span>GROBID TEI-XML</span>
                  </div>
                  <p className="document-content text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                    {activeCitation.contextBefore}
                    <mark className="px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-900 dark:text-indigo-200 font-semibold border-b-2 border-indigo-500 transition-colors">
                      {activeCitation.inText}
                    </mark>
                    {activeCitation.contextAfter}
                  </p>
                </div>
              </div>

              {/* Right Pane: Reference Inspector & Symbolic Trace (7 cols) */}
              <div className="lg:col-span-7 p-4 sm:p-6 bg-white dark:bg-slate-950 flex flex-col justify-between">
                <div key={activeCitation.id} className="animate-debugger-switch">
                  {/* Inspector Header */}
                  <div className="flex flex-wrap items-start justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-xs text-slate-400">
                          INSPECTING REFERENCE
                        </span>
                        <span className="font-mono text-xs font-bold text-indigo-600 dark:text-indigo-400">
                          {activeCitation.marker}
                        </span>
                        <span className="font-mono text-[11px] text-slate-400">
                          · Confidence {activeCitation.confidence}%
                        </span>
                      </div>
                      <h3 className="font-display text-lg sm:text-xl font-bold text-slate-900 dark:text-white">
                        {activeCitation.citedMeta.title}
                      </h3>
                    </div>

                    <div className="flex items-center gap-2">
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

                  {/* Animated Confidence Meter Bar */}
                  <div className="mt-3 mb-4">
                    <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">
                      <span>
                        {lang === 'vi'
                          ? 'ĐỘ TIN CẬY ĐỐI CHIẾU ĐA NGUỒN'
                          : 'CROSS-SOURCE VERIFICATION CONFIDENCE'}
                      </span>
                      <span className="font-bold text-slate-800 dark:text-slate-200">
                        {activeCitation.confidence}%
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ease-out ${
                          activeCitation.confidence >= 85
                            ? 'bg-emerald-500'
                            : activeCitation.confidence >= 60
                              ? 'bg-amber-500'
                              : 'bg-red-500'
                        }`}
                        style={{ width: `${activeCitation.confidence}%` }}
                      />
                    </div>
                  </div>

                  {/* Explanation Callout */}
                  <div className="my-4 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 flex items-start gap-3">
                    <Scale className="h-4 w-4 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
                    <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                      <span className="font-semibold text-slate-900 dark:text-white mr-1.5">
                        {lang === 'vi' ? 'Kết luận suy diễn:' : 'Neuro-Symbolic Reasoning:'}
                      </span>
                      {lang === 'vi'
                        ? activeCitation.explanation.vi
                        : activeCitation.explanation.en}
                    </div>
                  </div>

                  {/* Inspector Tabs: Metadata Diff | Symbolic Rules | Federated Sources */}
                  <Tabs defaultValue="diff" className="w-full">
                    <TabsList className="w-full justify-start bg-slate-100 dark:bg-slate-900 p-1 rounded-xl h-auto flex-wrap sm:flex-nowrap gap-1">
                      <TabsTrigger value="diff" className="flex-1 text-[11px] sm:text-xs font-mono py-1.5 px-2 sm:px-3 min-w-[96px]">
                        {lang === 'vi' ? '1. Đối chiếu Metadata' : '1. Metadata Diff'}
                      </TabsTrigger>
                      <TabsTrigger value="rules" className="flex-1 text-[11px] sm:text-xs font-mono py-1.5 px-2 sm:px-3 min-w-[96px]">
                        {lang === 'vi'
                          ? `2. Luật Suy diễn (${activeCitation.rules.length})`
                          : `2. Symbolic Rules (${activeCitation.rules.length})`}
                      </TabsTrigger>
                      <TabsTrigger value="sources" className="flex-1 text-[11px] sm:text-xs font-mono py-1.5 px-2 sm:px-3 min-w-[96px]">
                        {lang === 'vi' ? '3. Nguồn Truy hồi' : '3. Source Retrieval'}
                      </TabsTrigger>
                    </TabsList>

                    {/* TAB 1: Side-by-side Metadata Diff */}
                    <TabsContent value="diff" className="mt-4 animate-debugger-switch">
                      <div className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
                        <table className="w-full text-left border-collapse block sm:table">
                          <thead className="hidden sm:table-header-group">
                            <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] font-mono uppercase text-slate-500 dark:text-slate-400">
                              <th className="py-2.5 px-3 w-24">Field</th>
                              <th className="py-2.5 px-3">Cited in Manuscript</th>
                              <th className="py-2.5 px-3">Canonical Retrieved</th>
                              <th className="py-2.5 px-3 text-right">Status</th>
                            </tr>
                          </thead>
                          <tbody className="block sm:table-row-group divide-y divide-slate-200/70 dark:divide-slate-800 text-xs">
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
                                className="flex flex-col sm:table-row p-3 sm:p-0 gap-1.5 sm:gap-0 hover:bg-slate-50/70 dark:hover:bg-slate-900/40 transition-colors"
                              >
                                <td className="py-0.5 sm:py-2.5 px-0 sm:px-3 font-mono font-semibold sm:font-medium text-slate-500 dark:text-slate-400 flex items-center justify-between sm:table-cell">
                                  <span>{label}</span>
                                  <span className="sm:hidden">
                                    {renderFieldStatusBadge(activeCitation.fieldStatus[key])}
                                  </span>
                                </td>
                                <td className="py-0.5 sm:py-2.5 px-0 sm:px-3 text-slate-800 dark:text-slate-200 font-medium break-words">
                                  <span className="sm:hidden block text-[10px] font-mono uppercase text-slate-400 mb-0.5">
                                    Cited in PDF
                                  </span>
                                  {activeCitation.citedMeta[key]}
                                </td>
                                <td className="py-0.5 sm:py-2.5 px-0 sm:px-3 font-mono text-slate-600 dark:text-slate-300 break-words">
                                  <span className="sm:hidden block text-[10px] font-mono uppercase text-slate-400 mb-0.5">
                                    Retrieved Truth
                                  </span>
                                  {activeCitation.retrievedMeta ? (
                                    activeCitation.retrievedMeta[key]
                                  ) : (
                                    <span className="text-red-500 dark:text-red-400 italic">
                                      No canonical record found
                                    </span>
                                  )}
                                </td>
                                <td className="hidden sm:table-cell py-2.5 px-3 text-right whitespace-nowrap">
                                  {renderFieldStatusBadge(activeCitation.fieldStatus[key])}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </TabsContent>

                    {/* TAB 2: Symbolic Rules Trace */}
                    <TabsContent value="rules" className="mt-4 animate-debugger-switch">
                      <div className="space-y-2.5">
                        {activeCitation.rules.map((rule) => (
                          <div
                            key={rule.code}
                            className={`p-3.5 rounded-xl border font-mono text-xs transition-all hover:-translate-y-0.5 ${
                              rule.status === 'passed'
                                ? 'bg-emerald-50/50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800/70'
                                : rule.status === 'warning'
                                  ? 'bg-amber-50/50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800/70'
                                  : 'bg-red-50/50 dark:bg-red-950/30 border-red-200 dark:border-red-800/70'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-2">
                                <span className="px-2 py-0.5 rounded bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-bold text-[11px]">
                                  {rule.code}
                                </span>
                                <span className="font-bold text-slate-900 dark:text-white">
                                  {rule.name}
                                </span>
                              </div>
                              <span
                                className={`text-[11px] font-bold uppercase ${
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
                      </div>
                    </TabsContent>

                    {/* TAB 3: Multi-Source Federation */}
                    <TabsContent value="sources" className="mt-4 animate-debugger-switch">
                      <div className="grid sm:grid-cols-2 gap-3">
                        {activeCitation.sources.map((src) => (
                          <div
                            key={src.name}
                            className={`p-3.5 rounded-xl border flex items-center justify-between transition-all hover:-translate-y-0.5 ${
                              src.status === 'matched'
                                ? 'bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800/70'
                                : src.status === 'partial'
                                  ? 'bg-amber-50/40 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800/70'
                                  : 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800'
                            }`}
                          >
                            <div>
                              <p className="text-xs font-semibold text-slate-900 dark:text-white">
                                {src.name}
                              </p>
                              <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400 mt-0.5">
                                Latency: {src.latency} · Sim: {src.score}
                              </p>
                            </div>
                            <span
                              className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded ${
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

                {/* Inspector Footer Bar */}
                <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                    <span>
                      {lang === 'vi'
                        ? 'Giảng viên có thể Ghi đè nhãn (Override Verdict) kèm lý do kiểm toán.'
                        : 'Instructors can Override Verdicts with mandatory audit logging.'}
                    </span>
                  </div>
                  <Link
                    to="/login"
                    className="group inline-flex items-center gap-1 font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    <span>
                      {lang === 'vi' ? 'Mở toàn bộ Inspector' : 'Open Full Inspector'}
                    </span>
                    <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </RevealOnScroll>
      </div>
    </section>
  );
}

/* ============================================================
   4. Bento Grid — Architectural Pillars (#architecture)
   ============================================================ */
function BentoArchitectureSection({ lang }: { lang: Lang }) {
  const [activeRuleIdx, setActiveRuleIdx] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveRuleIdx((prev) => (prev + 1) % 3);
    }, 2600);
    return () => window.clearInterval(timer);
  }, []);

  const cisWeights = [
    {
      label: lang === 'vi' ? 'Tỷ lệ Nguồn Xác thực (Verified Ratio)' : 'Verified Source Ratio',
      weight: '35%',
      value: 88,
    },
    {
      label: lang === 'vi' ? 'Độ chính xác Metadata (Title/Year/Venue)' : 'Metadata Field Accuracy',
      weight: '25%',
      value: 82,
    },
    {
      label: lang === 'vi' ? 'Nhất quán In-Text ↔ Danh mục tham khảo' : 'In-Text ↔ Bibliography Consistency',
      weight: '25%',
      value: 91,
    },
    {
      label: lang === 'vi' ? 'Chuẩn định dạng (APA / IEEE / Vancouver)' : 'Citation Style Consistency',
      weight: '10%',
      value: 95,
    },
    {
      label: lang === 'vi' ? 'Tính hợp lệ của DOI / ArXiv ID' : 'Identifier (DOI / ArXiv) Validity',
      weight: '5%',
      value: 80,
    },
  ];

  return (
    <section
      id="architecture"
      className="py-16 md:py-24 border-b border-slate-200/80 dark:border-slate-800/80"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <RevealOnScroll>
          <div className="max-w-3xl mb-12">
            <div className="inline-flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2.5">
              <Layers className="h-4 w-4" />
              <span>
                {lang === 'vi'
                  ? 'Kiến trúc Neuro-Symbolic 2 Lớp'
                  : 'Two-Layer Neuro-Symbolic Architecture'}
              </span>
            </div>
            <h2 className="font-display text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white tracking-tight mb-4">
              {lang === 'vi'
                ? 'Không phải hộp đen AI. Mọi kết luận đều có bằng chứng.'
                : 'Engineered for Scholarly Precision, Not Black-Box Guessing.'}
            </h2>
            <p className="text-base text-slate-600 dark:text-slate-400 leading-relaxed">
              {lang === 'vi'
                ? 'CITRA tách biệt rõ ràng giữa kiểm tra cấu trúc liên kết nội bộ trong văn bản (Lớp 1) và đối chiếu học thuật đa nguồn bên ngoài (Lớp 2).'
                : 'CITRA separates internal manuscript consistency (Layer 1) from external bibliographic verification (Layer 2), combining neural fuzzy matching with deterministic symbolic rules.'}
            </p>
          </div>
        </RevealOnScroll>

        {/* 12-Column Bento Grid */}
        <div className="grid lg:grid-cols-12 gap-6">
          {/* Bento Card 1: 2-Layer Verification Engine (7 cols) */}
          <RevealOnScroll className="lg:col-span-7" delay={50}>
            <Card className="h-full p-0 overflow-hidden border-slate-200/90 dark:border-slate-800 flex flex-col justify-between transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:border-indigo-300/80 dark:hover:border-indigo-700/80">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between mb-2">
                  <Badge
                    variant="outline"
                    className="font-mono text-xs bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800"
                  >
                    LAYER 1 + LAYER 2
                  </Badge>
                  <span className="font-mono text-xs text-slate-400">
                    Bidirectional Graph
                  </span>
                </div>
                <CardTitle className="text-xl sm:text-2xl">
                  {lang === 'vi'
                    ? 'Kiểm chứng Kép: Nội văn bản & Cơ sở dữ liệu Quốc tế'
                    : 'Dual-Layer Verification: Manuscript Graph + Global Indexes'}
                </CardTitle>
                <CardDescription>
                  {lang === 'vi'
                    ? 'Phát hiện đồng thời lỗi trích dẫn mồ côi trong bài và lỗi nguồn tham khảo không tồn tại.'
                    : 'Simultaneously detects structural citation orphans inside the PDF and fabricated or mismatched external publications.'}
                </CardDescription>
              </CardHeader>

              <CardContent className="pt-0">
                <div className="grid sm:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800">
                  {/* Layer 1 Box */}
                  <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 transition-transform duration-300 hover:-translate-y-0.5">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs font-bold text-indigo-600 dark:text-indigo-400">
                        LAYER 1 · INTERNAL LINKING
                      </span>
                      <Link2 className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-400 mb-3">
                      {lang === 'vi'
                        ? 'Đối chiếu hai chiều giữa trích dẫn trong câu và danh mục tài liệu cuối bài.'
                        : 'Bidirectional mapping between in-text markers and bibliography entries.'}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      <span className="mapping-badge mapping-badge-matched text-[11px] px-2 py-0.5 font-mono">
                        MATCHED
                      </span>
                      <span className="mapping-badge mapping-badge-missing text-[11px] px-2 py-0.5 font-mono">
                        MISSING_REF
                      </span>
                      <span className="mapping-badge mapping-badge-uncited text-[11px] px-2 py-0.5 font-mono">
                        UNCITED_REF
                      </span>
                      <span className="mapping-badge mapping-badge-duplicate text-[11px] px-2 py-0.5 font-mono">
                        DUPLICATE
                      </span>
                    </div>
                  </div>

                  {/* Layer 2 Box */}
                  <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 transition-transform duration-300 hover:-translate-y-0.5">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs font-bold text-emerald-600 dark:text-emerald-400">
                        LAYER 2 · EXTERNAL PROOF
                      </span>
                      <Database className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-400 mb-3">
                      {lang === 'vi'
                        ? 'Xác thực sự tồn tại và độ khớp metadata trên 7 nguồn dữ liệu học thuật.'
                        : 'Cross-validates existence and field-level accuracy across 7 scholarly indexes.'}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      <span className="verdict-badge verdict-badge-verified text-[10px] px-2.5 py-0.5 font-mono">
                        VERIFIED
                      </span>
                      <span className="verdict-badge verdict-badge-metadata-error text-[10px] px-2.5 py-0.5 font-mono">
                        METADATA_ERROR
                      </span>
                      <span className="verdict-badge verdict-badge-hallucinated text-[10px] px-2.5 py-0.5 font-mono">
                        HALLUCINATION
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </RevealOnScroll>

          {/* Bento Card 2: Citation Integrity Score (CIS) (5 cols) */}
          <RevealOnScroll className="lg:col-span-5" delay={140}>
            <Card className="h-full p-0 overflow-hidden border-slate-200/90 dark:border-slate-800 flex flex-col justify-between transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:border-indigo-300/80 dark:hover:border-indigo-700/80">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between mb-2">
                  <Badge
                    variant="outline"
                    className="font-mono text-xs bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800"
                  >
                    CIS METRIC (0–100)
                  </Badge>
                  <span className="font-mono text-xs font-bold text-slate-900 dark:text-white">
                    Weighted Formula
                  </span>
                </div>
                <CardTitle className="text-xl">
                  {lang === 'vi'
                    ? 'Điểm Toàn vẹn Trích dẫn (CIS)'
                    : 'Citation Integrity Score (CIS)'}
                </CardTitle>
                <CardDescription>
                  {lang === 'vi'
                    ? 'Định lượng độ tin cậy của danh mục tham khảo qua 5 trọng số minh bạch (không phải điểm bài văn).'
                    : 'Quantifies bibliographic reliability across 5 transparent weights — strictly a reference integrity index, never an essay grade.'}
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-3 pt-1">
                {cisWeights.map((item) => (
                  <div key={item.label} className="space-y-1 group">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-700 dark:text-slate-300 font-medium group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                        {item.label}
                      </span>
                      <span className="font-mono font-semibold text-indigo-600 dark:text-indigo-400">
                        {item.weight}
                      </span>
                    </div>
                    <Progress value={item.value} className="h-1.5" />
                  </div>
                ))}
              </CardContent>
            </Card>
          </RevealOnScroll>

          {/* Bento Card 3: Multi-Source Federation + Local ACL FTS5 (5 cols) */}
          <RevealOnScroll className="lg:col-span-5" delay={200}>
            <Card className="h-full p-0 overflow-hidden border-slate-200/90 dark:border-slate-800 flex flex-col justify-between transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:border-indigo-300/80 dark:hover:border-indigo-700/80">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between mb-2">
                  <Badge
                    variant="outline"
                    className="font-mono text-xs bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300 border-amber-200 dark:border-amber-800"
                  >
                    7 DATA SOURCES
                  </Badge>
                  <span className="font-mono text-xs text-slate-400">
                    Local FTS5 + REST
                  </span>
                </div>
                <CardTitle className="text-xl">
                  {lang === 'vi'
                    ? 'Liên hợp 127K Bài báo Nội bộ & 6 API Quốc tế'
                    : '127K Local ACL Anthology + 6 Global APIs'}
                </CardTitle>
                <CardDescription>
                  {lang === 'vi'
                    ? 'Kết hợp tìm kiếm toàn văn SQLite FTS5 tốc độ cao với điều phối phân tầng tới các CSDL học thuật lớn nhất thế giới.'
                    : 'Combines ultra-fast local SQLite FTS5 full-text indexing with smart tiered routing across global bibliographic registries.'}
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-2.5 pt-1">
                {[
                  {
                    name: 'ACL Anthology Local FTS5',
                    meta: '127,400+ CS/NLP papers · < 15ms offline lookup',
                    badge: 'LOCAL DB',
                    badgeClass:
                      'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
                  },
                  {
                    name: 'Crossref REST API',
                    meta: '150M+ DOI records, journals & conference proceedings',
                    badge: 'CROSSREF',
                    badgeClass: 'source-badge-crossref',
                  },
                  {
                    name: 'OpenAlex & Europe PMC',
                    meta: '250M+ scholarly works, PubMed & biomedical literature',
                    badge: 'OPENALEX + PMC',
                    badgeClass: 'source-badge-openalex',
                  },
                  {
                    name: 'DBLP, arXiv & OpenLibrary',
                    meta: 'CS/AI conferences, preprints & ISBN multi-edition books',
                    badge: 'DBLP · ARXIV · BOOKS',
                    badgeClass: 'source-badge-dblp',
                  },
                ].map((src) => (
                  <div
                    key={src.name}
                    className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800 transition-all duration-200 hover:border-indigo-300 dark:hover:border-indigo-700 hover:translate-x-1"
                  >
                    <div>
                      <p className="text-xs font-semibold text-slate-900 dark:text-white">
                        {src.name}
                      </p>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400">
                        {src.meta}
                      </p>
                    </div>
                    <span className={`source-badge ${src.badgeClass} text-[10px]`}>
                      {src.badge}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </RevealOnScroll>

          {/* Bento Card 4: Symbolic Rule Engine Code Block (7 cols) */}
          <RevealOnScroll className="lg:col-span-7" delay={260}>
            <Card className="h-full p-0 overflow-hidden border-slate-200/90 dark:border-slate-800 flex flex-col justify-between transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:border-indigo-300/80 dark:hover:border-indigo-700/80">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between mb-2">
                  <Badge
                    variant="outline"
                    className="font-mono text-xs bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200"
                  >
                    SYMBOLIC ENGINE · R01–R12
                  </Badge>
                  <Cpu className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                </div>
                <CardTitle className="text-xl sm:text-2xl">
                  {lang === 'vi'
                    ? 'Suy diễn Luật Hình thức Minh bạch (Explainable Rules)'
                    : 'Deterministic Symbolic Logic Over Neural Candidates'}
                </CardTitle>
                <CardDescription>
                  {lang === 'vi'
                    ? 'Mạng nơ-ron/Fuzzy matching đảm nhiệm so khớp chuỗi nhiễu từ PDF; hệ chuyên gia Symbolic quyết định nhãn cuối cùng kèm chuỗi bằng chứng.'
                    : 'Neural/fuzzy matching handles noisy PDF OCR strings, while formal IF-THEN symbolic rules guarantee reproducible, auditable verdicts.'}
                </CardDescription>
              </CardHeader>

              <CardContent className="pt-1">
                <div className="rounded-xl bg-slate-900 dark:bg-slate-950 border border-slate-800 p-4 font-mono text-xs text-slate-300 space-y-2.5 shadow-inner">
                  <div className="flex items-center justify-between text-[11px] text-slate-400 pb-2 border-b border-slate-800">
                    <span>rule_engine/symbolic_verifier.py</span>
                    <span className="inline-flex items-center gap-1.5 text-emerald-400">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                      Deterministic Evaluation
                    </span>
                  </div>
                  <div className="space-y-2 leading-relaxed">
                    <div
                      className={`p-2 rounded-lg border transition-all duration-500 ${
                        activeRuleIdx === 0
                          ? 'bg-emerald-950/50 border-emerald-500/40 shadow-sm'
                          : 'bg-transparent border-transparent opacity-75'
                      }`}
                    >
                      <span className="text-indigo-400 font-bold">RULE R01</span>{' '}
                      <span className="text-slate-400">(Exact DOI & Title):</span>{' '}
                      <span className="text-emerald-400">IF</span> doi_verified{' '}
                      <span className="text-emerald-400">AND</span> title_sim &ge; 0.92{' '}
                      <span className="text-emerald-400">THEN</span>{' '}
                      <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                        VERIFIED
                      </span>
                    </div>
                    <div
                      className={`p-2 rounded-lg border transition-all duration-500 ${
                        activeRuleIdx === 1
                          ? 'bg-amber-950/50 border-amber-500/40 shadow-sm'
                          : 'bg-transparent border-transparent opacity-75'
                      }`}
                    >
                      <span className="text-indigo-400 font-bold">RULE R05</span>{' '}
                      <span className="text-slate-400">(Year Drift):</span>{' '}
                      <span className="text-amber-400">IF</span> title_sim &ge; 0.88{' '}
                      <span className="text-amber-400">AND</span> |cited_year - pub_year| &ge; 1{' '}
                      <span className="text-amber-400">THEN</span>{' '}
                      <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300">
                        METADATA_ERROR
                      </span>
                    </div>
                    <div
                      className={`p-2 rounded-lg border transition-all duration-500 ${
                        activeRuleIdx === 2
                          ? 'bg-red-950/50 border-red-500/40 shadow-sm'
                          : 'bg-transparent border-transparent opacity-75'
                      }`}
                    >
                      <span className="text-indigo-400 font-bold">RULE R11</span>{' '}
                      <span className="text-slate-400">(Hallucination):</span>{' '}
                      <span className="text-red-400">IF</span> max_candidate_sim &lt; 0.45{' '}
                      <span className="text-red-400">ACROSS</span> 5_sources{' '}
                      <span className="text-red-400">THEN</span>{' '}
                      <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-300">
                        SUSPECTED_HALLUCINATION
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </RevealOnScroll>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   5. 4-Stage End-to-End Pipeline Section (#how-it-works)
   ============================================================ */
function PipelineSection({ lang }: { lang: Lang }) {
  const [activeStage, setActiveStage] = useState(0);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    if (isHovered) return;
    const timer = window.setInterval(() => {
      setActiveStage((prev) => (prev + 1) % 4);
    }, 2400);
    return () => window.clearInterval(timer);
  }, [isHovered]);

  const stages =
    lang === 'vi'
      ? [
          {
            step: '01',
            icon: FileSearch,
            tech: 'PyMuPDF + GROBID TEI',
            title: 'Bóc tách Cấu trúc PDF',
            desc: 'Tự động nhận diện chuẩn trích dẫn (APA, IEEE, Vancouver, Chicago, MLA), tách các cụm trích dẫn trong bài và danh mục tài liệu tham khảo.',
          },
          {
            step: '02',
            icon: Link2,
            tech: 'CitationLinker Graph',
            title: 'Liên kết Hai chiều',
            desc: 'Ánh xạ từng trích dẫn trong câu tới mục tài liệu tham khảo tương ứng; phát hiện trích dẫn thiếu nguồn hoặc nguồn liệt kê khống.',
          },
          {
            step: '03',
            icon: Database,
            tech: 'FTS5 + Smart Tiered APIs',
            title: 'Truy hồi Đa Nguồn',
            desc: 'Tra cứu phân tầng trên 127K bài báo ACL nội bộ và 6 API học thuật quốc tế (Crossref, OpenAlex, DBLP, arXiv, OpenLibrary, Europe PMC).',
          },
          {
            step: '04',
            icon: Shield,
            tech: 'Rules R01–R12 + CIS',
            title: 'Suy diễn & Báo cáo',
            desc: 'Đánh giá bằng chứng theo tập luật hình thức, tính điểm toàn vẹn CIS và xuất báo cáo chi tiết (PDF, DOCX, CSV, JSON).',
          },
        ]
      : [
          {
            step: '01',
            icon: FileSearch,
            tech: 'PyMuPDF + GROBID TEI',
            title: 'Parse & Extract',
            desc: 'Auto-detects citation style (APA, IEEE, Vancouver, Chicago, MLA) and extracts in-text occurrences alongside structured bibliography entries.',
          },
          {
            step: '02',
            icon: Link2,
            tech: 'CitationLinker Graph',
            title: 'Bidirectional Linking',
            desc: 'Maps every in-text citation to its bibliography target and flags unlinked orphans, uncited references, and duplicate entries.',
          },
          {
            step: '03',
            icon: Database,
            tech: 'FTS5 + Smart Tiered APIs',
            title: 'Federated Retrieval',
            desc: 'Queries 127K+ local ACL Anthology papers and smart-routes across Crossref, OpenAlex, DBLP, arXiv, OpenLibrary, and Europe PMC.',
          },
          {
            step: '04',
            icon: Shield,
            tech: 'Rules R01–R12 + CIS',
            title: 'Symbolic Verdict',
            desc: 'Applies 12 formal neuro-symbolic rules to produce explainable verdicts, field-level diffs, CIS scores, and exportable reports.',
          },
        ];

  return (
    <section
      id="how-it-works"
      className="py-16 md:py-24 bg-white dark:bg-slate-900/40 border-b border-slate-200/80 dark:border-slate-800/80"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <RevealOnScroll>
          <div className="text-center max-w-3xl mx-auto mb-14">
            <div className="inline-flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2.5">
              <GitBranch className="h-4 w-4" />
              <span>
                {lang === 'vi'
                  ? 'Quy trình Kiểm chứng 4 Giai đoạn'
                  : '4-Stage Verification Pipeline'}
              </span>
            </div>
            <h2 className="font-display text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white tracking-tight mb-4">
              {lang === 'vi'
                ? 'Từ bản thảo PDF đến bằng chứng học thuật minh bạch'
                : 'From Raw PDF Manuscript to Auditable Evidence'}
            </h2>
            <p className="text-base text-slate-600 dark:text-slate-400">
              {lang === 'vi'
                ? 'Quy trình tự động hóa hoàn toàn việc bóc tách, liên kết và xác thực hàng chục trích dẫn chỉ trong vài giây.'
                : 'An automated, end-to-end verification pipeline designed for academic rigor and complete traceability.'}
            </p>
          </div>
        </RevealOnScroll>

        {/* Animated Horizontal Pipeline Progress Track (Desktop) */}
        <RevealOnScroll delay={80}>
          <div className="hidden lg:block relative mb-8 px-12">
            <div className="h-1.5 w-full rounded-full bg-slate-200/80 dark:bg-slate-800 overflow-hidden relative">
              <div
                className="h-full bg-gradient-to-r from-indigo-600 via-violet-500 to-emerald-500 rounded-full transition-all duration-700 ease-out"
                style={{ width: `${((activeStage + 1) / 4) * 100}%` }}
              />
              <div className="absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-white/60 to-transparent animate-pipeline-beam" />
            </div>
          </div>
        </RevealOnScroll>

        <div
          className="grid md:grid-cols-2 lg:grid-cols-4 gap-6"
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          {stages.map((stage, idx) => {
            const isActive = activeStage === idx;
            return (
              <RevealOnScroll key={stage.step} delay={idx * 100}>
                <div
                  onMouseEnter={() => setActiveStage(idx)}
                  className={`relative h-full rounded-2xl p-6 flex flex-col justify-between transition-all duration-300 group cursor-pointer ${
                    isActive
                      ? 'bg-white dark:bg-slate-900 border-2 border-indigo-500 dark:border-indigo-500 shadow-xl shadow-indigo-500/10 -translate-y-1.5'
                      : 'bg-slate-50/70 dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-700 hover:shadow-md hover:-translate-y-1'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-6">
                      <div
                        className={`w-12 h-12 rounded-xl border flex items-center justify-center transition-all duration-300 ${
                          isActive
                            ? 'bg-indigo-600 text-white border-indigo-600 shadow-md shadow-indigo-500/30 scale-105'
                            : 'bg-indigo-600/10 dark:bg-indigo-500/15 border-indigo-500/20 text-indigo-600 dark:text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white'
                        }`}
                      >
                        <stage.icon className="h-6 w-6" />
                      </div>
                      <span
                        className={`font-mono text-2xl font-bold transition-colors ${
                          isActive
                            ? 'text-indigo-600 dark:text-indigo-400'
                            : 'text-slate-300 dark:text-slate-700'
                        }`}
                      >
                        {stage.step}
                      </span>
                    </div>

                    <span className="inline-block font-mono text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 mb-1.5">
                      {stage.tech}
                    </span>
                    <h3 className="font-display text-xl font-bold text-slate-900 dark:text-white mb-2.5">
                      {stage.title}
                    </h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                      {stage.desc}
                    </p>
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-200/70 dark:border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
                    <span className="inline-flex items-center gap-1.5">
                      {isActive && (
                        <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
                      )}
                      <span
                        className={
                          isActive
                            ? 'text-indigo-600 dark:text-indigo-400 font-semibold'
                            : ''
                        }
                      >
                        STAGE {stage.step}
                      </span>
                    </span>
                    <ArrowRight
                      className={`h-3.5 w-3.5 transition-transform text-indigo-600 dark:text-indigo-400 ${
                        isActive ? 'translate-x-1' : 'group-hover:translate-x-1'
                      }`}
                    />
                  </div>
                </div>
              </RevealOnScroll>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   6. Verification Taxonomy Section (#taxonomy)
   ============================================================ */
function TaxonomySection({ lang }: { lang: Lang }) {
  const verdicts = [
    {
      badge: 'VERIFIED',
      badgeClass: 'verdict-badge-verified',
      accentBar: 'bg-emerald-500',
      icon: CheckCircle2,
      iconColor: 'text-emerald-600 dark:text-emerald-400',
      rule: 'R01 · R02 · R04',
      title: lang === 'vi' ? 'Đã xác minh (Verified)' : 'Verified Publication',
      desc:
        lang === 'vi'
          ? 'Tìm thấy công bố khoa học khớp chính xác cả tiêu đề, tác giả, năm xuất bản và DOI/venue trên ít nhất một CSDL uy tín.'
          : 'Canonical publication found with consistent title, author list, publication year, and venue/DOI across verified registries.',
    },
    {
      badge: 'METADATA_ERROR',
      badgeClass: 'verdict-badge-metadata-error',
      accentBar: 'bg-amber-500',
      icon: AlertTriangle,
      iconColor: 'text-amber-600 dark:text-amber-400',
      rule: 'R05 · R06 · R07',
      title: lang === 'vi' ? 'Sai lệch Metadata' : 'Metadata Discrepancy',
      desc:
        lang === 'vi'
          ? 'Bài báo có thật nhưng người viết trích dẫn sai năm xuất bản, thiếu đồng tác giả, hoặc ghi nhầm tên tạp chí/hội nghị.'
          : 'Underlying publication exists, but the cited entry contains year drift, partial author mismatch, or incorrect journal/venue metadata.',
    },
    {
      badge: 'SUSPECTED_HALLUCINATION',
      badgeClass: 'verdict-badge-hallucinated',
      accentBar: 'bg-red-500',
      icon: Search,
      iconColor: 'text-red-600 dark:text-red-400',
      rule: 'R09 · R10 · R11',
      title: lang === 'vi' ? 'Nghi ngờ Bịa đặt (Hallucination)' : 'Suspected Hallucination',
      desc:
        lang === 'vi'
          ? 'Không tìm thấy bất kỳ công bố nào tương ứng trên toàn bộ hệ thống CSDL học thuật hoặc mã DOI hoàn toàn không tồn tại.'
          : 'Zero matching publications across Local ACL FTS5, Crossref, OpenAlex, DBLP, arXiv, OpenLibrary, and Europe PMC, or fabricated DOI prefix.',
    },
    {
      badge: 'UNRESOLVED',
      badgeClass: 'verdict-badge-unverifiable',
      accentBar: 'bg-slate-400',
      icon: FileQuestion,
      iconColor: 'text-slate-600 dark:text-slate-400',
      rule: 'R12 · L01',
      title: lang === 'vi' ? 'Chưa đủ Bằng chứng' : 'Unresolved / Insufficient Data',
      desc:
        lang === 'vi'
          ? 'Trích dẫn quá ngắn, bị lỗi cắt dòng PDF nghiêm trọng hoặc thiếu mục tài liệu tham khảo cuối bài nên chưa thể kết luận.'
          : 'Insufficient bibliographic fields or unlinked orphan citation requiring manual human inspection.',
    },
    {
      badge: 'RESOURCE',
      badgeClass:
        'bg-violet-50 text-violet-700 border border-violet-200 dark:bg-violet-950 dark:text-violet-300 dark:border-violet-800',
      accentBar: 'bg-violet-500',
      icon: Globe,
      iconColor: 'text-violet-600 dark:text-violet-400',
      rule: 'R-WEB · URL',
      title: lang === 'vi' ? 'Tài nguyên Web / Phần mềm' : 'Web / Software Resource',
      desc:
        lang === 'vi'
          ? 'Liên kết tới kho mã nguồn GitHub, trang tài liệu kỹ thuật hoặc website (được tách riêng khỏi thống kê bài báo học thuật).'
          : 'Non-paper URLs, GitHub repositories, documentation, or datasets — cleanly separated from academic paper statistics.',
    },
    {
      badge: 'ORPHAN / MISMATCH',
      badgeClass: 'verdict-badge-source-mismatch',
      accentBar: 'bg-orange-500',
      icon: Quote,
      iconColor: 'text-orange-600 dark:text-orange-400',
      rule: 'L01 · L02 · L03',
      title: lang === 'vi' ? 'Lỗi Nhất quán Liên kết Lớp 1' : 'Layer 1 Linking Inconsistency',
      desc:
        lang === 'vi'
          ? 'Trích dẫn trong bài nhưng quên liệt kê ở References (Missing Reference) hoặc liệt kê ở cuối bài nhưng không hề trích dẫn (Uncited).'
          : 'Catches in-text citations missing from the bibliography and uncited padding entries in the reference list.',
    },
  ];

  return (
    <section
      id="taxonomy"
      className="py-16 md:py-24 border-b border-slate-200/80 dark:border-slate-800/80"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <RevealOnScroll>
          <div className="text-center max-w-3xl mx-auto mb-14">
            <div className="inline-flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2.5">
              <Scale className="h-4 w-4" />
              <span>
                {lang === 'vi'
                  ? 'Hệ thống Phân loại Nhãn Kiểm chứng'
                  : 'Explainable Verification Taxonomy'}
              </span>
            </div>
            <h2 className="font-display text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white tracking-tight mb-4">
              {lang === 'vi'
                ? 'Phân loại rõ ràng. Ngôn ngữ học thuật chuẩn mực.'
                : 'Nuanced Verdicts With Evidence Before Judgment'}
            </h2>
            <p className="text-base text-slate-600 dark:text-slate-400">
              {lang === 'vi'
                ? 'Thay vì kết luận cảm tính, mỗi trích dẫn được gán nhãn ngữ nghĩa chuẩn xác kèm mã luật kích hoạt.'
                : 'Every reference is classified into a rigorous semantic taxonomy backed by triggered symbolic rule codes.'}
            </p>
          </div>
        </RevealOnScroll>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {verdicts.map((item, idx) => (
            <RevealOnScroll key={item.badge} delay={idx * 70}>
              <Card className="group relative h-full p-0 overflow-hidden border-slate-200/90 dark:border-slate-800 hover:-translate-y-1 hover:shadow-lg transition-all duration-300 flex flex-col justify-between">
                <div
                  className={`h-1 w-full ${item.accentBar} opacity-75 group-hover:opacity-100 transition-opacity`}
                />
                <div className="p-6 flex-1 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-4">
                      <span
                        className={`verdict-badge ${item.badgeClass} text-xs font-mono px-3 py-1`}
                      >
                        {item.badge}
                      </span>
                      <span className="font-mono text-[11px] text-slate-400">
                        {item.rule}
                      </span>
                    </div>

                    <div className="flex items-center gap-2.5 mb-2">
                      <item.icon
                        className={`h-5 w-5 ${item.iconColor} shrink-0 transition-transform duration-300 group-hover:scale-110`}
                      />
                      <h3 className="font-display text-lg font-bold text-slate-900 dark:text-white">
                        {item.title}
                      </h3>
                    </div>

                    <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                      {item.desc}
                    </p>
                  </div>
                </div>
              </Card>
            </RevealOnScroll>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   7. Role-Based Workspaces Section (#workspaces)
   ============================================================ */
function RoleWorkspacesSection({ lang }: { lang: Lang }) {
  const roles = [
    {
      key: 'student',
      icon: BookOpen,
      badge: 'ROLE: STUDENT (USER)',
      badgeColor:
        'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800',
      title: 'CITRA Workspace',
      subtitle:
        lang === 'vi'
          ? 'Dành cho Sinh viên & Nhà nghiên cứu — Tự rà soát trước khi nộp bài'
          : 'For Students & Researchers — Self-check manuscripts before submission',
      philosophy:
        lang === 'vi'
          ? '“Một nút bấm, một báo cáo minh bạch.” Giúp sinh viên phát hiện thiếu sót danh mục tham khảo và sửa lỗi năm/tạp chí trước khi nộp khóa luận.'
          : '“One upload, one clear report.” Empowers authors to catch missing bibliography entries, broken DOIs, and citation typos prior to submission.',
      capabilities:
        lang === 'vi'
          ? [
              'Tải lên file PDF bài tiểu luận / khóa luận và theo dõi tiến trình 8 bước thời gian thực',
              'Xem bảng tổng hợp kết quả kiểm chứng 2 lớp và điểm Citation Integrity Score (CIS)',
              'Kiểm tra chi tiết sự sai lệch giữa thông tin trích dẫn trong bài và bản ghi gốc',
              'Xuất báo cáo kiểm chứng ra định dạng PDF, DOCX, CSV hoặc JSON',
            ]
          : [
              'Upload single PDF manuscripts with live 8-step pipeline progress tracking',
              'Review comprehensive 2-layer Verdict Tables and Citation Integrity Score (CIS)',
              'Inspect side-by-side metadata comparisons for every flagged reference',
              'Export verification reports to PDF, DOCX, CSV, or JSON formats',
            ],
    },
    {
      key: 'teacher',
      icon: GraduationCap,
      badge: 'ROLE: TEACHER (INSTRUCTOR)',
      badgeColor:
        'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800',
      title: 'CITRA Classroom',
      subtitle:
        lang === 'vi'
          ? 'Dành cho Giảng viên hướng dẫn & Phản biện — Quản lý lớp học & Thẩm định chuyên sâu'
          : 'For Instructors & Thesis Advisors — Cohort management & deep-dive diagnostics',
      philosophy:
        lang === 'vi'
          ? '“Lớp học của tôi, quyết định của tôi.” Mở khóa toàn bộ bộ công cụ Citation Debugger và quyền Ghi đè kết quả (Override Verdict) có lưu vết.'
          : '“My cohorts, my academic judgment.” Unlocks the full Citation Debugger suite, batch class uploads, and human-in-the-loop Verdict Overrides.',
      capabilities:
        lang === 'vi'
          ? [
              'Quản lý danh sách lớp học (/teacher/classes), thêm sinh viên và tải lên hàng loạt (Batch Upload)',
              'Hàng đợi Pending Reviews tập trung các bài nộp có nghi ngờ bịa đặt hoặc lỗi metadata',
              'Mở khóa Document Inspector (Split-pane PDF), Logic Trace (R01–R12) và Orphan Detection',
              'Ghi đè nhãn kiểm chứng (Override Verdict) kèm lý do giải trình được lưu vào Audit Log',
            ]
          : [
              'Manage academic classes (/teacher/classes), student rosters, and sequential Batch Uploads',
              'Dedicated Pending Reviews queue prioritizing flagged hallucinations and metadata errors',
              'Full access to Split-Pane Document Inspector, Symbolic Logic Trace, and Orphan Detection',
              'Human-in-the-Loop Verdict Override with mandatory justification and audit persistence',
            ],
    },
    {
      key: 'admin',
      icon: Sliders,
      badge: 'ROLE: ADMINISTRATOR',
      badgeColor:
        'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950 dark:text-purple-300 dark:border-purple-800',
      title: 'CITRA Control',
      subtitle:
        lang === 'vi'
          ? 'Dành cho Quản trị viên — Giám sát dịch vụ GROBID, Tài khoản & Nhật ký Kiểm toán'
          : 'For System Administrators — Governance, system health & immutable audit trails',
      philosophy:
        lang === 'vi'
          ? '“Toàn quyền kiểm soát và minh bạch hệ thống.” Đảm bảo tính toàn vẹn của phân quyền RBAC và theo dõi trạng thái hoạt động của các dịch vụ.'
          : '“Complete institutional governance.” Manages role-based capabilities, monitors microservice health, and audits every verdict modification.',
      capabilities:
        lang === 'vi'
          ? [
              'Quản lý tài khoản người dùng và phân quyền 3 vai trò (Student / Teacher / Admin)',
              'Theo dõi trạng thái hoạt động thời gian thực của GROBID, SQLite FTS5 và các API học thuật',
              'Truy xuất Nhật ký Kiểm toán (Audit Log) ghi nhận mọi thao tác Override trong hệ thống',
              'Quyền truy cập và rà soát toàn bộ báo cáo, lớp học trên toàn hệ thống',
            ]
          : [
              'Full user lifecycle management and Capability-Based Access Control (Student / Teacher / Admin)',
              'Real-time System Health monitoring for GROBID TEI parser, SQLite FTS5, and external APIs',
              'Immutable System Audit Log tracking every instructor verdict override and administrative action',
              'Global visibility across all cohorts, verification reports, and diagnostic tools',
            ],
    },
  ];

  return (
    <section
      id="workspaces"
      className="py-16 md:py-24 bg-white dark:bg-slate-900/40 border-b border-slate-200/80 dark:border-slate-800/80"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <RevealOnScroll>
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
            <div>
              <div className="inline-flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2.5">
                <Users className="h-4 w-4" />
                <span>
                  {lang === 'vi'
                    ? 'Kiến trúc Phân quyền 3 Vai trò (RBAC)'
                    : 'Role-Based Workspace Architecture'}
                </span>
              </div>
              <h2 className="font-display text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white tracking-tight">
                {lang === 'vi'
                  ? 'Thiết kế chuyên biệt cho Sinh viên, Giảng viên & Quản trị'
                  : 'Tailored Workspaces for Every Academic Role'}
              </h2>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400 max-w-md">
              {lang === 'vi'
                ? 'Giao diện tự động thích ứng theo năng lực phân quyền (Capability-Based Access Control), giữ sự tinh gọn cho sinh viên và mở khóa bộ công cụ chẩn đoán sâu cho giảng viên.'
                : 'Capability-based access control keeps the student experience effortless while unlocking deep diagnostic and override tools for instructors and administrators.'}
            </p>
          </div>
        </RevealOnScroll>

        <RevealOnScroll delay={100}>
          <Tabs defaultValue="teacher" className="w-full">
            <TabsList className="grid grid-cols-1 sm:grid-cols-3 max-w-xl bg-slate-100 dark:bg-slate-900 p-1.5 rounded-xl h-auto mb-8 gap-1">
              <TabsTrigger value="student" className="py-2.5 text-xs sm:text-sm font-semibold">
                {lang === 'vi' ? 'Sinh viên (Workspace)' : 'Student Workspace'}
              </TabsTrigger>
              <TabsTrigger value="teacher" className="py-2.5 text-xs sm:text-sm font-semibold">
                {lang === 'vi' ? 'Giảng viên (Classroom)' : 'Teacher Classroom'}
              </TabsTrigger>
              <TabsTrigger value="admin" className="py-2.5 text-xs sm:text-sm font-semibold">
                {lang === 'vi' ? 'Quản trị (Control)' : 'Admin Control'}
              </TabsTrigger>
            </TabsList>

            {roles.map((r) => (
              <TabsContent key={r.key} value={r.key} className="animate-debugger-switch">
                <Card className="p-6 sm:p-8 border-slate-200/90 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
                  <div className="grid lg:grid-cols-12 gap-8 items-center">
                    <div className="lg:col-span-5 space-y-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold border ${r.badgeColor}`}
                      >
                        <r.icon className="h-3.5 w-3.5" />
                        {r.badge}
                      </span>
                      <h3 className="font-display text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white">
                        {r.title}
                      </h3>
                      <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">
                        {r.subtitle}
                      </p>
                      <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed italic border-l-2 border-indigo-500 pl-3.5">
                        {r.philosophy}
                      </p>
                    </div>

                    <div className="lg:col-span-7">
                      <div className="rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800 p-5 space-y-3.5">
                        <p className="text-xs font-mono uppercase tracking-wider font-semibold text-slate-500 dark:text-slate-400">
                          {lang === 'vi'
                            ? 'Năng lực & Công cụ Mở khóa'
                            : 'Unlocked Capabilities & Views'}
                        </p>
                        {r.capabilities.map((cap, idx) => (
                          <div
                            key={idx}
                            className="flex items-start gap-3 p-2 rounded-lg hover:bg-white dark:hover:bg-slate-900 transition-colors"
                          >
                            <div className="p-1 rounded-md bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0">
                              <Check className="h-3.5 w-3.5" />
                            </div>
                            <span className="text-sm text-slate-700 dark:text-slate-300">
                              {cap}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </Card>
              </TabsContent>
            ))}
          </Tabs>
        </RevealOnScroll>
      </div>
    </section>
  );
}

/* ============================================================
   8. Decision-Support Compliance & CTA Section
   ============================================================ */
function CTASection({
  lang,
  isAuthenticated,
}: {
  lang: Lang;
  isAuthenticated: boolean;
}) {
  return (
    <section className="py-16 md:py-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        {/* Mandatory Academic Decision-Support Disclaimer Banner */}
        <RevealOnScroll>
          <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 sm:p-8 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
              <div className="flex items-start gap-4">
                <div className="w-11 h-11 rounded-xl bg-indigo-50 dark:bg-indigo-950 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center shrink-0 text-indigo-600 dark:text-indigo-400">
                  <Shield className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-display text-lg font-bold text-slate-900 dark:text-white">
                      {lang === 'vi'
                        ? 'Nguyên tắc Hỗ trợ Ra Quyết định (Decision-Support System)'
                        : 'Decision-Support Principle & Academic Integrity'}
                    </h3>
                    <Badge variant="outline" className="text-[10px] font-mono">
                      COMPLIANCE
                    </Badge>
                  </div>
                  <p className="text-sm text-slate-600 dark:text-slate-400 max-w-3xl leading-relaxed">
                    {lang === 'vi'
                      ? 'CITRA cung cấp bằng chứng truy xuất từ cơ sở dữ liệu và chuỗi suy diễn luật để hỗ trợ con người rà soát. Hệ thống tuyệt đối không tự động kết luận gian lận học thuật và không chấm điểm nội dung bài viết. Quyết định cuối cùng luôn thuộc về giảng viên và hội đồng chuyên môn.'
                      : 'CITRA provides verifiable bibliographic evidence and formal rule traces to assist human reviewers. It never automatically concludes academic misconduct and is not an automated essay grader. Final judgment always remains with instructors and academic committees.'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </RevealOnScroll>

        {/* High-Contrast Dark Indigo CTA Card */}
        <RevealOnScroll delay={120}>
          <div className="relative rounded-3xl overflow-hidden bg-slate-900 dark:bg-slate-900 border border-slate-800 px-6 py-14 sm:px-12 sm:py-16 text-center shadow-2xl">
            <div
              className="pointer-events-none absolute inset-0 opacity-20"
              style={{
                backgroundImage:
                  'radial-gradient(rgb(129 140 248 / 0.6) 1px, transparent 1px)',
                backgroundSize: '24px 24px',
              }}
            />
            <div className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-indigo-600/30 blur-3xl rounded-full animate-float-slow" />

            <div className="relative max-w-2xl mx-auto">
              <Badge className="mb-5 bg-indigo-500/20 text-indigo-300 border border-indigo-400/30 font-mono text-xs px-3 py-1">
                CITRA WORKSPACE
              </Badge>
              <h2 className="font-display text-3xl sm:text-4xl lg:text-5xl font-bold text-white tracking-tight mb-5">
                {lang === 'vi'
                  ? 'Sẵn sàng kiểm chứng danh mục trích dẫn của bạn?'
                  : 'Ready to Verify Your Academic Citations?'}
              </h2>
              <p className="text-base sm:text-lg text-slate-300 mb-8 leading-relaxed">
                {lang === 'vi'
                  ? 'Tải lên bản thảo PDF và nhận báo cáo kiểm chứng 2 lớp kèm đối chiếu metadata chi tiết và đồ thị suy diễn Neuro-Symbolic.'
                  : 'Upload any PDF manuscript and receive a comprehensive two-layer verification report with field-level metadata diffs and symbolic rule traces.'}
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3.5">
                <Button
                  asChild
                  size="lg"
                  className="btn-shimmer w-full sm:w-auto h-12 px-8 rounded-xl text-base bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all hover:-translate-y-0.5"
                >
                  <Link to={isAuthenticated ? '/upload' : '/login'}>
                    <span>
                      {isAuthenticated
                        ? lang === 'vi'
                          ? 'Vào Workspace Kiểm chứng'
                          : 'Go to Verification Workspace'
                        : lang === 'vi'
                          ? 'Đăng nhập để Bắt đầu'
                          : 'Sign in to Start Verification'}
                    </span>
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
                <Button
                  asChild
                  variant="outline"
                  size="lg"
                  className="w-full sm:w-auto h-12 px-7 rounded-xl text-base bg-slate-800/80 hover:bg-slate-800 text-slate-100 border-slate-700 transition-all hover:-translate-y-0.5"
                >
                  <a href="#interactive-demo">
                    <span>
                      {lang === 'vi' ? 'Xem lại Trình gỡ lỗi' : 'Review Live Debugger'}
                    </span>
                  </a>
                </Button>
              </div>
            </div>
          </div>
        </RevealOnScroll>
      </div>
    </section>
  );
}

/* ============================================================
   9. Footer
   ============================================================ */
function LandingFooter({ lang }: { lang: Lang }) {
  return (
    <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8 pb-8 border-b border-slate-200/80 dark:border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-white dark:bg-white/95 p-1.5 flex items-center justify-center shadow-sm ring-1 ring-slate-200/90 dark:ring-white/20">
              <SourceLogicLogo size={24} />
            </div>
            <div>
              <span className="font-display text-lg font-bold text-slate-900 dark:text-white">
                CITRA
              </span>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                CITRA · Academic Source Verification Workspace
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-xs font-medium text-slate-600 dark:text-slate-400">
            <a href="#interactive-demo" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
              {lang === 'vi' ? 'Citation Debugger' : 'Citation Debugger'}
            </a>
            <a href="#architecture" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
              {lang === 'vi' ? 'Kiến trúc 2 Lớp' : '2-Layer Architecture'}
            </a>
            <a href="#how-it-works" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
              {lang === 'vi' ? 'Quy trình Xử lý' : 'Pipeline'}
            </a>
            <a href="#taxonomy" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
              {lang === 'vi' ? 'Nhãn Kiểm chứng' : 'Taxonomy'}
            </a>
            <Link to="/login" className="text-indigo-600 dark:text-indigo-400 font-semibold hover:underline">
              Sign in →
            </Link>
          </div>
        </div>

        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 dark:text-slate-400">
          <p>
            {lang === 'vi'
              ? 'Hệ thống hỗ trợ rà soát học thuật — không tự động kết luận gian lận hay chấm điểm bài viết.'
              : 'Decision-Support System for academic citation integrity — assists human review, never replaces scholarly judgment.'}
          </p>
          <p className="font-mono text-[11px]">
            Built with shadcn/ui · Radix UI · Tailwind CSS · Neuro-Symbolic AI
          </p>
        </div>
      </div>
    </footer>
  );
}
