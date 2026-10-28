import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Check,
  X,
  Sparkles,
  Zap,
  Building2,
  ShieldCheck,
  CreditCard,
  Loader2,
  ArrowLeft,
  HelpCircle,
  FileText,
  Layers,
  Database,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { api, type BillingCycle, type PlanTier } from '@/api/client';
import { useAuth } from '@/contexts/AuthContext';
import { useRole } from '@/hooks/useRole';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

/* ============================================================
   CITRA (SourceLogic) — SaaS Pricing & Plans Page (v2.2)
   3 Tiers: Basic ($0) · Pro ($20/mo | $16/mo annual) · Ultra ($200/mo | $160/mo annual)
   ============================================================ */

interface ComparisonRow {
  category_en: string;
  category_vi: string;
  basic: string | boolean;
  pro: string | boolean;
  ultra: string | boolean;
}

const COMPARISON_MATRIX: ComparisonRow[] = [
  {
    category_en: 'Monthly PDF & Word (.docx) Checks',
    category_vi: 'Số lượt tải & kiểm tra PDF / Word (.docx) / tháng',
    basic: '3 docs / mo',
    pro: '50 docs / mo',
    ultra: 'Unlimited (1,000/mo)',
  },
  {
    category_en: 'Maximum File Size (.pdf / .docx)',
    category_vi: 'Dung lượng file tối đa (.pdf / .docx)',
    basic: '5 MB',
    pro: '25 MB',
    ultra: '100 MB',
  },
  {
    category_en: 'Maximum Pages per Manuscript',
    category_vi: 'Giới hạn số trang mỗi tài liệu',
    basic: '15 pages',
    pro: '100 pages',
    ultra: '500 pages',
  },
  {
    category_en: 'Citations Verified per Document',
    category_vi: 'Số trích dẫn kiểm chứng tối đa / bài',
    basic: 'Up to 30',
    pro: 'Up to 200',
    ultra: 'Unlimited',
  },
  {
    category_en: 'Concurrent Batch Upload (.pdf / .docx)',
    category_vi: 'Tải lên hàng loạt (Batch Check)',
    basic: false,
    pro: 'Up to 10 files',
    ultra: 'Up to 50 files',
  },
  {
    category_en: 'Scholarly Databases & Legal Registry',
    category_vi: 'CSDL Học thuật & Hệ thống Pháp luật Việt Nam',
    basic: 'Local 127K + Crossref + OpenAlex + VN Legal',
    pro: '15+ Scholarly & Technical APIs (+DataCite, DOAJ, HAL, NCBI/bioRxiv, HF, RFC, Wayback, Retraction Watch)',
    ultra: 'All 15+ APIs + SerpAPI Google Scholar Fallback',
  },
  {
    category_en: '1-Click Bibliography Auto-Fix Studio (BibTeX / RIS)',
    category_vi: '1-Click Auto-Fix Studio (Chuẩn hóa APA, IEEE, TDTU, BibTeX, RIS)',
    basic: false,
    pro: true,
    ultra: true,
  },
  {
    category_en: 'Deep Neural Sentence-BERT Evidence & Stance',
    category_vi: 'Đối chiếu câu bằng chứng Sentence-BERT & Stance',
    basic: false,
    pro: true,
    ultra: true,
  },
  {
    category_en: 'Interactive PDF Page Preview (Bounding-Box)',
    category_vi: 'Document Inspector (Xem trang PDF & Highlight tọa độ)',
    basic: false,
    pro: true,
    ultra: true,
  },
  {
    category_en: 'Interactive Citation Network & Evidence DAG Graph',
    category_vi: 'Đồ thị Mạng lưới Trích dẫn & Cây suy diễn Bằng chứng',
    basic: false,
    pro: true,
    ultra: true,
  },
  {
    category_en: 'Academic Report Export Formats',
    category_vi: 'Định dạng xuất báo cáo học thuật',
    basic: 'Web View (JSON)',
    pro: 'PDF, DOCX (Word), CSV, JSON, BibTeX, RIS',
    ultra: 'PDF, DOCX, CSV, JSON, BibTeX, RIS + Class ZIP',
  },
  {
    category_en: 'Classroom Join Code (CITRA-XXXX) & Cohort Analytics',
    category_vi: 'Mã lớp học (CITRA-XXXX), Thống kê khóa luận & Ghi đè (Override)',
    basic: 'Self-Join Classes',
    pro: 'Up to 3 Classes + Cohort Analytics',
    ultra: 'Unlimited Classes & Audit Log',
  },
  {
    category_en: 'Verification History Retention',
    category_vi: 'Thời gian lưu trữ lịch sử báo cáo',
    basic: '7 days',
    pro: '1 year',
    ultra: 'Unlimited Lifetime',
  },
];

export function PricingPage() {
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const { planTier, quota } = useRole();

  const lang = i18n.language?.startsWith('vi') ? 'vi' : 'en';
  const [billingCycle, setBillingCycle] = useState<BillingCycle>('annual');
  const [loadingTier, setLoadingTier] = useState<'pro' | 'ultra' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const canceled = searchParams.get('canceled') === '1';

  useEffect(() => {
    if (user?.billing_cycle === 'monthly' || user?.billing_cycle === 'annual') {
      setBillingCycle(user.billing_cycle);
    }
  }, [user?.billing_cycle]);

  const handleSelectPlan = async (targetTier: PlanTier) => {
    if (targetTier === 'basic') {
      if (!user) {
        navigate('/register');
      } else {
        navigate('/upload');
      }
      return;
    }

    if (!user) {
      navigate('/login');
      return;
    }

    setLoadingTier(targetTier);
    setError(null);
    try {
      const session = await api.createCheckoutSession({
        plan_tier: targetTier,
        billing_cycle: billingCycle,
      });
      if (session.checkout_url.startsWith('http')) {
        window.location.href = session.checkout_url;
      } else {
        navigate(session.checkout_url);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : lang === 'vi'
            ? 'Không thể khởi tạo thanh toán Stripe.'
            : 'Failed to create Stripe checkout session.',
      );
    } finally {
      setLoadingTier(null);
    }
  };

  const proPrice = billingCycle === 'annual' ? 16 : 20;
  const ultraPrice = billingCycle === 'annual' ? 160 : 200;

  return (
    <div className="max-w-6xl mx-auto space-y-10 pb-14" data-testid="pricing-page">
      {/* Top Navigation if accessed publicly */}
      {!user && (
        <div className="flex items-center justify-between pt-4">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-indigo-600"
          >
            <ArrowLeft className="h-4 w-4" />
            {lang === 'vi' ? 'Quay về Trang chủ' : 'Back to Home'}
          </Link>
          <div className="flex items-center gap-3">
            <Button asChild variant="outline" size="sm" className="rounded-xl">
              <Link to="/login">{lang === 'vi' ? 'Đăng nhập' : 'Sign In'}</Link>
            </Button>
            <Button asChild size="sm" className="rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white">
              <Link to="/register">{lang === 'vi' ? 'Dùng thử miễn phí' : 'Start Free'}</Link>
            </Button>
          </div>
        </div>
      )}

      {/* Hero Header */}
      <div className="text-center max-w-3xl mx-auto space-y-4">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200/80 dark:border-indigo-800 text-xs font-mono font-semibold text-indigo-700 dark:text-indigo-300">
          <Sparkles className="h-3.5 w-3.5" />
          {lang === 'vi'
            ? 'BẢNG GIÁ HỌC THUẬT MINH BẠCH · THANH TOÁN STRIPE'
            : 'TRANSPARENT ACADEMIC PRICING · POWERED BY STRIPE'}
        </div>

        <h1 className="font-display text-3xl sm:text-5xl font-bold tracking-tight text-slate-900 dark:text-white">
          {lang === 'vi'
            ? 'Đầu tư cho sự toàn vẹn khoa học của bạn'
            : 'Invest in Rigorous Citation Integrity'}
        </h1>

        <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400 leading-relaxed">
          {lang === 'vi'
            ? 'Bắt đầu miễn phí với gói Basic cho bài tiểu luận ngắn, hoặc nâng cấp lên Pro & Ultra để mở khóa toàn bộ 15+ cơ sở dữ liệu học thuật & kỹ thuật (DataCite, DOAJ, OpenAIRE/HAL, NCBI/bioRxiv, Hugging Face, IETF RFC, Wayback Machine, Retraction Watch), Sentence-BERT Deep Neural và xuất báo cáo chuẩn hội đồng.'
            : 'Start free with Basic for course essays, or upgrade to Pro & Ultra for full 15+ scholarly & technical API retrieval (DataCite, DOAJ, OpenAIRE/HAL, NCBI/bioRxiv, Hugging Face, IETF RFC, Wayback Machine, Retraction Watch), Sentence-BERT Deep Neural verification, and academic PDF/DOCX exports.'}
        </p>

        {/* Current Plan Banner for Authenticated Users */}
        {user && (
          <div
            className="inline-flex flex-wrap items-center justify-center gap-3 px-4 py-2 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 shadow-2xs text-xs"
            data-testid="current-plan-banner"
          >
            <span className="text-slate-500 dark:text-slate-400">
              {lang === 'vi' ? 'Gói hiện tại:' : 'Current Plan:'}
            </span>
            <Badge
              className={
                planTier === 'ultra'
                  ? 'bg-violet-600 text-white font-mono uppercase'
                  : planTier === 'pro'
                    ? 'bg-indigo-600 text-white font-mono uppercase'
                    : 'bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-mono uppercase'
              }
            >
              {planTier.toUpperCase()}
            </Badge>
            <span className="text-slate-600 dark:text-slate-300 font-mono">
              {lang === 'vi'
                ? `Đã dùng ${quota.monthly_uploads_used}/${quota.monthly_uploads_limit} tài liệu tháng này`
                : `${quota.monthly_uploads_used}/${quota.monthly_uploads_limit} uploads used this month`}
            </span>
          </div>
        )}

        {/* Billing Cycle Toggle */}
        <div className="pt-2 flex flex-col items-center gap-2">
          <div
            className="inline-flex items-center p-1.5 rounded-2xl bg-slate-200/80 dark:bg-slate-900 border border-slate-300/70 dark:border-slate-800 shadow-inner"
            role="group"
            aria-label="Billing cycle selector"
          >
            <button
              type="button"
              data-testid="billing-toggle-monthly"
              onClick={() => setBillingCycle('monthly')}
              className={`px-5 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                billingCycle === 'monthly'
                  ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              {lang === 'vi' ? 'Thanh toán theo Tháng' : 'Monthly Billing'}
            </button>
            <button
              type="button"
              data-testid="billing-toggle-annual"
              onClick={() => setBillingCycle('annual')}
              className={`px-5 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all flex items-center gap-2 cursor-pointer ${
                billingCycle === 'annual'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <span>{lang === 'vi' ? 'Thanh toán theo Năm' : 'Annual Billing'}</span>
              <span className="px-2 py-0.5 rounded-full bg-emerald-500 text-white text-[11px] font-mono font-bold">
                {lang === 'vi' ? 'Tiết kiệm 20%' : 'Save 20%'}
              </span>
            </button>
          </div>
          <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
            {billingCycle === 'annual'
              ? lang === 'vi'
                ? '✨ Đang áp dụng ưu đãi trả theo năm: Tặng tương đương > 2 tháng sử dụng miễn phí!'
                : '✨ Annual discount active: Equivalent to over 2 months free!'
              : lang === 'vi'
                ? '💡 Mẹo: Chuyển sang gói theo Năm để tiết kiệm ngay $48/năm (Pro) hoặc $480/năm (Ultra).'
                : '💡 Tip: Switch to Annual billing to save $48/year on Pro or $480/year on Ultra.'}
          </p>
        </div>
      </div>

      {canceled && (
        <div className="max-w-2xl mx-auto p-4 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 flex items-center gap-3 text-sm text-amber-800 dark:text-amber-200">
          <AlertCircle className="h-5 w-5 shrink-0 text-amber-600" />
          <span>
            {lang === 'vi'
              ? 'Phiên thanh toán đã được hủy. Bạn có thể chọn lại gói cước bất cứ lúc nào.'
              : 'Checkout was canceled. You can select a plan again whenever you are ready.'}
          </span>
        </div>
      )}

      {error && (
        <div className="max-w-2xl mx-auto p-4 rounded-2xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 flex items-center gap-3 text-sm text-red-700 dark:text-red-300">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-600" />
          <span>{error}</span>
        </div>
      )}

      {/* 3 Pricing Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
        {/* 1. BASIC TIER */}
        <Card
          className="rounded-3xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:p-8 flex flex-col justify-between shadow-xs"
          data-testid="plan-card-basic"
        >
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-display text-2xl font-bold text-slate-900 dark:text-white">
                    Basic
                  </h2>
                  <p className="text-xs text-slate-500">
                    {lang === 'vi' ? 'Gói mặc định cho Sinh viên' : 'Default Student Starter'}
                  </p>
                </div>
              </div>
              <Badge variant="secondary" className="font-mono text-[10px]">
                {lang === 'vi' ? 'MẶC ĐỊNH' : 'DEFAULT'}
              </Badge>
            </div>

            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 min-h-[40px]">
              {lang === 'vi'
                ? 'Phù hợp để làm quen hệ thống và rà soát nhanh các bài tập, tiểu luận môn học ngắn.'
                : 'Ideal for exploring the platform and checking short course essays & drafts.'}
            </p>

            <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
              <div className="flex items-baseline gap-1.5">
                <span className="font-display text-4xl font-bold text-slate-900 dark:text-white">
                  $0
                </span>
                <span className="text-sm text-slate-500">
                  / {lang === 'vi' ? 'tháng' : 'month'}
                </span>
              </div>
              <p className="text-xs font-mono text-slate-500 mt-1">
                {lang === 'vi' ? 'Miễn phí trọn đời · Không cần thẻ' : 'Free forever · No credit card required'}
              </p>
            </div>

            <div className="space-y-2.5 pt-2">
              <p className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
                {lang === 'vi' ? 'Quyền lợi bao gồm:' : 'Included features:'}
              </p>
              <ul className="space-y-2.5 text-xs sm:text-sm text-slate-700 dark:text-slate-300">
                {(lang === 'vi'
                  ? [
                      '3 lượt tải & kiểm tra PDF / tháng',
                      'Dung lượng tối đa 5 MB / file PDF',
                      'Giới hạn tối đa 15 trang & 30 trích dẫn / bài',
                      'Layer 1: Đối chiếu trích dẫn trong bài & Danh mục',
                      'Tra cứu Local 127K papers, Crossref & OpenAlex',
                      'Xem điểm CIS tổng quát & Bảng kết luận cơ bản',
                    ]
                  : [
                      '3 PDF manuscript checks per month',
                      'Maximum 5 MB file size per upload',
                      'Up to 15 pages & 30 citations per document',
                      'Layer 1 In-text <-> Bibliography Linking',
                      'Local 127K DB, Crossref & OpenAlex lookup',
                      'Overall CIS Integrity Score & Verdict Table',
                    ]
                ).map((feat) => (
                  <li key={feat} className="flex items-start gap-2.5">
                    <Check className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                    <span>{feat}</span>
                  </li>
                ))}
                {(lang === 'vi'
                  ? [
                      'Không hỗ trợ xuất báo cáo PDF, DOCX, CSV',
                      'Khóa Document Inspector, Logic Trace & Đồ thị',
                      'Không hỗ trợ tải lên hàng loạt (Batch Upload)',
                    ]
                  : [
                      'No PDF, DOCX (Word), or CSV report export',
                      'No Document Inspector, Logic Trace, or Graph',
                      'No multi-file Batch Upload',
                    ]
                ).map((lim) => (
                  <li key={lim} className="flex items-start gap-2.5 text-slate-400 dark:text-slate-500">
                    <X className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                    <span>{lim}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="pt-6 mt-6 border-t border-slate-100 dark:border-slate-800">
            <Button
              type="button"
              variant="outline"
              disabled={Boolean(user && planTier === 'basic')}
              onClick={() => handleSelectPlan('basic')}
              data-testid="select-basic-btn"
              className="w-full h-11 rounded-xl font-semibold cursor-pointer"
            >
              {user && planTier === 'basic'
                ? lang === 'vi'
                  ? 'Đang sử dụng gói Basic'
                  : 'Current Active Plan'
                : lang === 'vi'
                  ? 'Bắt đầu miễn phí'
                  : 'Get Started Free'}
            </Button>
          </div>
        </Card>

        {/* 2. PRO TIER (CENTER HIGHLIGHTED — MOST POPULAR) */}
        <Card
          className="rounded-3xl border-2 border-indigo-600 dark:border-indigo-500 bg-gradient-to-b from-indigo-50/40 via-white to-white dark:from-indigo-950/30 dark:via-slate-900 dark:to-slate-900 p-6 sm:p-8 flex flex-col justify-between shadow-xl relative lg:-translate-y-2"
          data-testid="plan-card-pro"
        >
          <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
            <span className="inline-flex items-center gap-1.5 px-4 py-1 rounded-full bg-indigo-600 text-white text-xs font-mono font-bold shadow-md">
              <Sparkles className="h-3.5 w-3.5" />
              {lang === 'vi' ? 'PHỔ BIẾN NHẤT · KHUYÊN DÙNG' : 'MOST POPULAR · RECOMMENDED'}
            </span>
          </div>

          <div className="space-y-5 pt-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2.5 rounded-xl bg-indigo-600 text-white shadow-sm">
                  <Zap className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-display text-2xl font-bold text-slate-900 dark:text-white">
                    Pro
                  </h2>
                  <p className="text-xs text-indigo-600 dark:text-indigo-400 font-medium">
                    {lang === 'vi'
                      ? 'Nghiên cứu sinh, Luận văn & Giảng viên'
                      : 'Thesis Writers, Researchers & Lecturers'}
                  </p>
                </div>
              </div>
              {billingCycle === 'annual' && (
                <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 font-mono text-[11px]">
                  {lang === 'vi' ? 'Tiết kiệm $48' : 'Save $48/yr'}
                </Badge>
              )}
            </div>

            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 min-h-[40px]">
              {lang === 'vi'
                ? 'Mở khóa toàn bộ công nghệ Neuro-Symbolic, kiểm tra khóa luận/luận văn dài và xuất báo cáo chuẩn hội đồng.'
                : 'Full Neuro-Symbolic pipeline for full-length theses, research manuscripts, and lecturer grading.'}
            </p>

            <div className="pt-2 border-t border-indigo-100 dark:border-slate-800">
              <div className="flex items-baseline gap-2">
                <span
                  className="font-display text-4xl font-bold text-slate-900 dark:text-white"
                  data-testid="pro-price-display"
                >
                  ${proPrice}
                </span>
                <span className="text-sm text-slate-500">
                  / {lang === 'vi' ? 'tháng' : 'month'}
                </span>
                {billingCycle === 'annual' && (
                  <span className="text-sm line-through text-slate-400 font-mono">
                    $20
                  </span>
                )}
              </div>
              <p className="text-xs font-mono text-indigo-600 dark:text-indigo-400 mt-1">
                {billingCycle === 'annual'
                  ? lang === 'vi'
                    ? 'Thanh toán $192 / năm (Tương đương tặng >2 tháng miễn phí)'
                    : 'Billed $192 annually ($16/mo equivalent — Save 20%)'
                  : lang === 'vi'
                    ? 'Thanh toán $20 định kỳ hàng tháng (Hoặc $16/tháng khi trả năm)'
                    : 'Billed $20 monthly (Or $16/mo when billed annually)'}
              </p>
            </div>

            <div className="space-y-2.5 pt-2">
              <p className="text-xs font-mono font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                {lang === 'vi' ? 'Mọi tính năng Basic, cộng thêm:' : 'Everything in Basic, plus:'}
              </p>
              <ul className="space-y-2.5 text-xs sm:text-sm text-slate-700 dark:text-slate-300">
                {(lang === 'vi'
                  ? [
                      '50 lượt tải & kiểm tra PDF mỗi tháng (Gấp 16 lần)',
                      'Tối đa 25 MB & 100 trang / bài (Đủ cho Khóa luận & Luận văn ThS)',
                      'Kiểm chứng tới 200 trích dẫn / bài + Batch Upload 10 files',
                      'Đầy đủ 15+ nguồn học thuật & kỹ thuật (+DataCite, DOAJ, HAL, NCBI/bioRxiv, HF, RFC)',
                      'Phát hiện bài báo bị rút hồi (Retraction Watch) & cứu hộ Link Rot qua Wayback Machine',
                      'Deep Neural Sentence-BERT đối chiếu câu bằng chứng & Stance',
                      'Cầu nối ngữ nghĩa đa ngôn ngữ (Tiếng Việt ↔ Tiếng Anh)',
                      'Mở khóa Document Inspector, Logic Trace & Đồ thị trích dẫn',
                      'Xuất báo cáo chuẩn học thuật ra PDF, DOCX (Word), CSV & JSON',
                      'Quản lý tới 3 Lớp học (Classrooms) & Ghi đè kết luận (Override)',
                    ]
                  : [
                      '50 PDF manuscript checks per month (16x Basic)',
                      'Up to 25 MB & 100 pages per document (Full Master/BS Theses)',
                      'Up to 200 citations / doc + 10-file concurrent Batch Upload',
                      'All 15+ Scholarly & Technical APIs (+DataCite, DOAJ, HAL, NCBI/bioRxiv, HF, RFC)',
                      'Retraction Watch Detection & Wayback Machine Link-Rot Rescue',
                      'Deep Neural Sentence-BERT Evidence & Claim Stance verification',
                      'Cross-lingual semantic bridging (Vietnamese ↔ English)',
                      'Unlock Document Inspector, Logic Trace & Evidence Graph',
                      'Export academic reports in PDF, DOCX (Word), CSV & JSON',
                      'Manage up to 3 Classroom Cohorts & Verdict Overrides',
                    ]
                ).map((feat) => (
                  <li key={feat} className="flex items-start gap-2.5">
                    <CheckCircle2 className="h-4 w-4 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
                    <span className="font-medium">{feat}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="pt-6 mt-6 border-t border-indigo-100 dark:border-slate-800">
            <Button
              type="button"
              disabled={
                loadingTier !== null ||
                Boolean(user && planTier === 'pro' && user.billing_cycle === billingCycle)
              }
              onClick={() => handleSelectPlan('pro')}
              data-testid="select-pro-btn"
              className="w-full h-11 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-md cursor-pointer"
            >
              {loadingTier === 'pro' ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <CreditCard className="h-4 w-4 mr-2" />
              )}
              {user && planTier === 'pro' && user.billing_cycle === billingCycle
                ? lang === 'vi'
                  ? 'Đang sử dụng gói Pro này'
                  : 'Current Active Pro Plan'
                : lang === 'vi'
                  ? `Nâng cấp lên Pro · $${billingCycle === 'annual' ? '192/năm' : '20/tháng'}`
                  : `Upgrade to Pro · $${billingCycle === 'annual' ? '192/yr' : '20/mo'}`}
            </Button>
          </div>
        </Card>

        {/* 3. ULTRA TIER */}
        <Card
          className="rounded-3xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:p-8 flex flex-col justify-between shadow-xs"
          data-testid="plan-card-ultra"
        >
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2.5 rounded-xl bg-violet-600 text-white shadow-sm">
                  <Building2 className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-display text-2xl font-bold text-slate-900 dark:text-white">
                    Ultra
                  </h2>
                  <p className="text-xs text-violet-600 dark:text-violet-400 font-medium">
                    {lang === 'vi'
                      ? 'Phòng Thí Nghiệm, Bộ Môn & Hội Đồng'
                      : 'Research Labs, Faculties & Review Boards'}
                  </p>
                </div>
              </div>
              {billingCycle === 'annual' ? (
                <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 font-mono text-[11px]">
                  {lang === 'vi' ? 'Tiết kiệm $480' : 'Save $480/yr'}
                </Badge>
              ) : (
                <Badge variant="secondary" className="font-mono text-[10px]">
                  {lang === 'vi' ? 'QUY MÔ LỚN' : 'ENTERPRISE LAB'}
                </Badge>
              )}
            </div>

            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 min-h-[40px]">
              {lang === 'vi'
                ? 'Hiệu năng tối đa không giới hạn cho nhóm nghiên cứu, bộ môn đại học và hội đồng chấm luận án Tiến sĩ.'
                : 'Unrestricted verification scale for university departments, research labs, and doctoral committees.'}
            </p>

            <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
              <div className="flex items-baseline gap-2">
                <span
                  className="font-display text-4xl font-bold text-slate-900 dark:text-white"
                  data-testid="ultra-price-display"
                >
                  ${ultraPrice}
                </span>
                <span className="text-sm text-slate-500">
                  / {lang === 'vi' ? 'tháng' : 'month'}
                </span>
                {billingCycle === 'annual' && (
                  <span className="text-sm line-through text-slate-400 font-mono">
                    $200
                  </span>
                )}
              </div>
              <p className="text-xs font-mono text-violet-600 dark:text-violet-400 mt-1">
                {billingCycle === 'annual'
                  ? lang === 'vi'
                    ? 'Thanh toán $1,920 / năm (Tiết kiệm $480 / năm — Giảm 20%)'
                    : 'Billed $1,920 annually ($160/mo equivalent — Save $480)'
                  : lang === 'vi'
                    ? 'Thanh toán $200 định kỳ hàng tháng (Hoặc $160/tháng khi trả năm)'
                    : 'Billed $200 monthly (Or $160/mo when billed annually)'}
              </p>
            </div>

            <div className="space-y-2.5 pt-2">
              <p className="text-xs font-mono font-bold uppercase tracking-wider text-violet-600 dark:text-violet-400">
                {lang === 'vi' ? 'Mọi tính năng Pro, cộng thêm:' : 'Everything in Pro, plus:'}
              </p>
              <ul className="space-y-2.5 text-xs sm:text-sm text-slate-700 dark:text-slate-300">
                {(lang === 'vi'
                  ? [
                      'Không giới hạn lượt kiểm tra (Fair-use: 1.000 tài liệu/tháng)',
                      'Tối đa 100 MB & 500 trang / bài (Luận án Tiến sĩ & Sách chuyên khảo)',
                      'Không giới hạn số lượng trích dẫn trong mỗi tài liệu',
                      'Kích hoạt SerpAPI Google Scholar Fallback cho trích dẫn khó',
                      'Kiểm tra sống/chết đường dẫn DOI & URL thời gian thực',
                      'Batch Upload công suất lớn: Tối đa 50 PDF cùng lúc',
                      'Không giới hạn Lớp học, Sinh viên & Xuất báo cáo Class ZIP',
                      'Lưu trữ lịch sử vĩnh viễn & Luồng xử lý ưu tiên 24/7',
                    ]
                  : [
                      'Unlimited monthly checks (Fair-use: 1,000 manuscripts/mo)',
                      'Up to 100 MB & 500 pages (Doctoral Dissertations & Books)',
                      'Unlimited citations verified per manuscript',
                      'SerpAPI Google Scholar Fallback for obscure literature',
                      'Real-time Active DOI & URL Reachability Validator',
                      'High-throughput Batch Upload: Up to 50 PDFs at once',
                      'Unlimited Classroom Cohorts, Students & Class ZIP Export',
                      'Lifetime report retention & 24/7 priority compute queue',
                    ]
                ).map((feat) => (
                  <li key={feat} className="flex items-start gap-2.5">
                    <Check className="h-4 w-4 text-violet-600 dark:text-violet-400 shrink-0 mt-0.5" />
                    <span>{feat}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="pt-6 mt-6 border-t border-slate-100 dark:border-slate-800">
            <Button
              type="button"
              variant="outline"
              disabled={
                loadingTier !== null ||
                Boolean(user && planTier === 'ultra' && user.billing_cycle === billingCycle)
              }
              onClick={() => handleSelectPlan('ultra')}
              data-testid="select-ultra-btn"
              className="w-full h-11 rounded-xl border-violet-600/50 text-violet-700 dark:text-violet-300 hover:bg-violet-50 dark:hover:bg-violet-950/40 font-semibold cursor-pointer"
            >
              {loadingTier === 'ultra' ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <CreditCard className="h-4 w-4 mr-2" />
              )}
              {user && planTier === 'ultra' && user.billing_cycle === billingCycle
                ? lang === 'vi'
                  ? 'Đang sử dụng gói Ultra'
                  : 'Current Active Ultra Plan'
                : lang === 'vi'
                  ? `Nâng cấp lên Ultra · $${billingCycle === 'annual' ? '1,920/năm' : '200/tháng'}`
                  : `Upgrade to Ultra · $${billingCycle === 'annual' ? '1,920/yr' : '200/mo'}`}
            </Button>
          </div>
        </Card>
      </div>

      {/* Detailed Comparison Matrix */}
      <Card className="rounded-3xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:p-8 shadow-xs overflow-hidden">
        <div className="space-y-2 mb-6">
          <h3 className="font-display text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Layers className="h-5 w-5 text-indigo-600" />
            {lang === 'vi'
              ? 'Bảng So Sánh Chi Tiết Tính Năng & Hạn Mức'
              : 'Detailed Feature & Quota Comparison Matrix'}
          </h3>
          <p className="text-xs sm:text-sm text-slate-500">
            {lang === 'vi'
              ? 'So sánh minh bạch thông số kỹ thuật giữa 3 gói Basic, Pro và Ultra.'
              : 'Transparent technical specifications across Basic, Pro, and Ultra tiers.'}
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 font-mono uppercase text-[11px]">
                <th className="py-3.5 pr-4 font-semibold">
                  {lang === 'vi' ? 'Danh mục tính năng' : 'Feature / Quota'}
                </th>
                <th className="py-3.5 px-4 text-center font-semibold">Basic ($0)</th>
                <th className="py-3.5 px-4 text-center font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50/50 dark:bg-indigo-950/30 rounded-t-xl">
                  Pro (${proPrice}/mo)
                </th>
                <th className="py-3.5 pl-4 text-center font-bold text-violet-600 dark:text-violet-400">
                  Ultra (${ultraPrice}/mo)
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
              {COMPARISON_MATRIX.map((row) => (
                <tr key={row.category_en} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40">
                  <td className="py-3.5 pr-4 font-medium text-slate-800 dark:text-slate-200">
                    {lang === 'vi' ? row.category_vi : row.category_en}
                  </td>
                  <td className="py-3.5 px-4 text-center text-slate-600 dark:text-slate-400 font-mono text-xs">
                    {typeof row.basic === 'boolean' ? (
                      row.basic ? (
                        <Check className="h-4 w-4 text-emerald-500 mx-auto" />
                      ) : (
                        <X className="h-4 w-4 text-slate-300 dark:text-slate-600 mx-auto" />
                      )
                    ) : (
                      row.basic
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-center font-semibold text-indigo-700 dark:text-indigo-300 bg-indigo-50/30 dark:bg-indigo-950/20 font-mono text-xs">
                    {typeof row.pro === 'boolean' ? (
                      row.pro ? (
                        <CheckCircle2 className="h-4 w-4 text-indigo-600 dark:text-indigo-400 mx-auto" />
                      ) : (
                        <X className="h-4 w-4 text-slate-300 mx-auto" />
                      )
                    ) : (
                      row.pro
                    )}
                  </td>
                  <td className="py-3.5 pl-4 text-center font-semibold text-violet-700 dark:text-violet-300 font-mono text-xs">
                    {typeof row.ultra === 'boolean' ? (
                      row.ultra ? (
                        <CheckCircle2 className="h-4 w-4 text-violet-600 dark:text-violet-400 mx-auto" />
                      ) : (
                        <X className="h-4 w-4 text-slate-300 mx-auto" />
                      )
                    ) : (
                      row.ultra
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Trust & FAQ */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          {
            icon: ShieldCheck,
            title_vi: 'Thanh toán Stripe An toàn',
            title_en: 'Secure Stripe Checkout',
            desc_vi:
              'Hỗ trợ thẻ quốc tế Visa/Mastercard qua cổng Stripe Demo chuẩn bảo mật PCI-DSS. Nâng cấp tài khoản tức thì.',
            desc_en:
              'Instant activation via Stripe Demo Checkout with full invoice receipts and 1-click test card support.',
          },
          {
            icon: Database,
            title_vi: 'Chuyển đổi Tháng / Năm linh hoạt',
            title_en: 'Flexible Monthly & Annual Plans',
            desc_vi:
              'Nâng cấp, chuyển sang chu kỳ năm tiết kiệm 20% hoặc hủy gia hạn tự động bất cứ lúc nào trong trang Cài đặt.',
            desc_en:
              'Switch between monthly and annual billing (Save 20%) or cancel auto-renewal anytime from Settings.',
          },
          {
            icon: HelpCircle,
            title_vi: 'Đảm bảo Tính Toàn vẹn Học thuật',
            title_en: 'Academic Decision-Support',
            desc_vi:
              'Mọi kết quả kiểm chứng đều đi kèm bằng chứng truy xuất từ 7 cơ sở dữ liệu khoa học quốc tế uy tín.',
            desc_en:
              'Every verdict is backed by explainable symbolic rules (R01–R12) and live scholarly metadata.',
          },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.title_en}
              className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-5 space-y-2"
            >
              <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 font-semibold text-sm">
                <Icon className="h-4 w-4" />
                <span>{lang === 'vi' ? item.title_vi : item.title_en}</span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                {lang === 'vi' ? item.desc_vi : item.desc_en}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
