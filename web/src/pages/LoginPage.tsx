import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/AuthContext';
import { ThemeToggle } from '@/contexts/ThemeContext';
import {
  Eye,
  EyeOff,
  Shield,
  AlertCircle,
  Quote,
  Database,
  GitBranch,
  ArrowLeft,
  ArrowRight,
  Lock,
  User,
  KeyRound,
  Globe,
  Terminal,
  Check,
  Layers,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';

function SourceLogicBrandMark({ size = 24 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className="text-white"
    >
      <path
        d="M4 8C4 6.89543 4.89543 6 6 6H8"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <path
        d="M4 16C4 17.1046 4.89543 18 6 18H8"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <path
        d="M10 12H14M14 12L12 10M14 12L12 14"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M17 9L19 11L22 8"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function LoginPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedDemo, setCopiedDemo] = useState(false);

  const lang = i18n.language?.startsWith('vi') ? 'vi' : 'en';

  const toggleLanguage = () => {
    const next = lang === 'en' ? 'vi' : 'en';
    void i18n.changeLanguage(next);
  };

  const handleFillDemo = () => {
    setUsername('admin');
    setPassword('admin123');
    setError('');
    setCopiedDemo(true);
    window.setTimeout(() => setCopiedDemo(false), 1800);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : t('auth.loginError'));
    } finally {
      setLoading(false);
    }
  };

  const features = [
    {
      icon: Quote,
      title: t('auth.featureExtraction'),
      desc: t('auth.featureExtractionDesc'),
      tag: 'GROBID TEI · Layer 1',
      iconBox:
        'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
      tagBadge:
        'bg-emerald-50 text-emerald-700 border-emerald-200/70 dark:bg-emerald-950/70 dark:text-emerald-300 dark:border-emerald-800/70',
    },
    {
      icon: Database,
      title: t('auth.featureRetrieval'),
      desc: t('auth.featureRetrievalDesc'),
      tag: '127K ACL FTS5 + 4 APIs',
      iconBox:
        'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20',
      tagBadge:
        'bg-indigo-50 text-indigo-700 border-indigo-200/70 dark:bg-indigo-950/70 dark:text-indigo-300 dark:border-indigo-800/70',
    },
    {
      icon: GitBranch,
      title: t('auth.featureVerification'),
      desc: t('auth.featureVerificationDesc'),
      tag: 'Rules R01–R12 · CIS',
      iconBox:
        'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
      tagBadge:
        'bg-amber-50 text-amber-700 border-amber-200/70 dark:bg-amber-950/70 dark:text-amber-300 dark:border-amber-800/70',
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50/70 dark:bg-slate-950 text-slate-900 dark:text-slate-50 flex flex-col lg:flex-row selection:bg-indigo-500/20 selection:text-indigo-600 dark:selection:text-indigo-300">
      {/* ============================================================
          Left Panel — Scholarly Precision Architecture Showcase
          ============================================================ */}
      <div className="hidden lg:flex lg:w-[52%] xl:w-[55%] relative overflow-hidden bg-white dark:bg-slate-900 border-r border-slate-200/80 dark:border-slate-800/80 flex-col justify-between p-10 xl:p-14">
        {/* Architectural Dot-Grid + Radial Aura (Matches LandingPage) */}
        <div className="pointer-events-none absolute inset-0">
          <div
            className="absolute inset-0 opacity-55 dark:opacity-20"
            style={{
              backgroundImage:
                'radial-gradient(rgb(148 163 184 / 0.35) 1px, transparent 1px)',
              backgroundSize: '24px 24px',
            }}
          />
          <div className="absolute -top-24 -left-24 w-[520px] h-[380px] bg-gradient-to-tr from-indigo-500/15 via-indigo-400/5 to-emerald-500/10 blur-3xl rounded-full" />
          <div className="absolute bottom-0 right-0 w-[420px] h-[300px] bg-gradient-to-tl from-indigo-500/10 via-transparent to-transparent blur-2xl rounded-full" />
        </div>

        {/* Top Header: Brand Identity + Live Engine Pill */}
        <div className="relative z-10 flex items-center justify-between gap-4">
          <Link
            to="/"
            className="flex items-center gap-3.5 group rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo-600 to-indigo-700 flex items-center justify-center shadow-md shadow-indigo-600/20 ring-1 ring-indigo-500/30 group-hover:scale-[1.03] transition-transform">
              <SourceLogicBrandMark size={24} />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <h1 className="font-display text-xl font-bold tracking-tight text-slate-900 dark:text-white leading-none">
                  SourceLogic
                </h1>
                <Badge
                  variant="secondary"
                  className="text-[10px] font-mono px-1.5 py-0 h-4 bg-indigo-50 text-indigo-700 dark:bg-indigo-950/80 dark:text-indigo-300 border border-indigo-200/60 dark:border-indigo-800/60"
                >
                  v2.0
                </Badge>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium mt-1">
                {t('nav.academicVerification')}
              </p>
            </div>
          </Link>

          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100/90 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/80 text-[11px] font-mono text-slate-600 dark:text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>5 INDEXES READY</span>
          </div>
        </div>

        {/* Center Content: Headline + 3 Feature Pillars + Mini Debugger Trace */}
        <div className="relative z-10 my-auto py-8 space-y-6 max-w-xl">
          {/* Announcement Pill */}
          <div>
            <div className="inline-flex items-center gap-2 pl-2 pr-3 py-1 rounded-full bg-slate-100/90 dark:bg-slate-800/90 border border-slate-200/90 dark:border-slate-700/80 mb-4">
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-indigo-600 text-white">
                <Layers className="h-3 w-3" />
                NEURO-SYMBOLIC
              </span>
              <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {lang === 'vi'
                  ? 'Kiến trúc Kiểm chứng Trích dẫn Học thuật 2 Lớp'
                  : 'Two-Layer Academic Citation Debugger'}
              </span>
            </div>

            <h2 className="font-display text-3xl xl:text-4xl font-bold tracking-tight text-slate-900 dark:text-white leading-[1.12] mb-3.5">
              {t('auth.heroTitle1')}
              <br />
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 via-indigo-500 to-emerald-600 dark:from-indigo-400 dark:via-indigo-300 dark:to-emerald-400">
                {t('auth.heroTitle2')}
              </span>
            </h2>
            <p className="text-sm xl:text-base text-slate-600 dark:text-slate-400 leading-relaxed">
              {t('auth.heroDesc')}
            </p>
          </div>

          {/* 3 Feature Cards */}
          <div className="space-y-3">
            {features.map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.title}
                  className="group p-3.5 rounded-2xl bg-slate-50/85 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/90 hover:border-indigo-300 dark:hover:border-indigo-800 hover:bg-white dark:hover:bg-slate-900 transition-all shadow-2xs flex items-start gap-3.5"
                >
                  <div
                    className={`p-2.5 rounded-xl border shrink-0 mt-0.5 ${item.iconBox}`}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <h3 className="font-display font-semibold text-slate-900 dark:text-white text-sm xl:text-base">
                        {item.title}
                      </h3>
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-mono font-semibold border ${item.tagBadge}`}
                      >
                        {item.tag}
                      </span>
                    </div>
                    <p className="text-xs xl:text-sm text-slate-600 dark:text-slate-400 mt-1 leading-relaxed">
                      {item.desc}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Mini Symbolic Rule Engine Trace Preview */}
          <div className="rounded-2xl bg-slate-900 dark:bg-slate-950 border border-slate-800 p-4 font-mono text-xs text-slate-300 shadow-lg">
            <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-slate-800 text-[11px]">
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-400/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80" />
                </div>
                <span className="text-slate-400 ml-1">
                  symbolic_verifier.py · Trace Preview
                </span>
              </div>
              <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold">
                CIS: 84.5 / 100
              </span>
            </div>
            <div className="space-y-1.5 text-[11px] leading-relaxed">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-slate-300">
                  <span className="text-indigo-400 font-semibold">[1]</span>{' '}
                  Vaswani et al. (2017) · <span className="text-slate-400">R01_DOI_MATCH</span>
                </span>
                <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold shrink-0">
                  VERIFIED
                </span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-slate-300">
                  <span className="text-indigo-400 font-semibold">[4]</span>{' '}
                  Nguyen &amp; Tran (2021) · <span className="text-slate-400">R05_YEAR_DRIFT</span>
                </span>
                <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold shrink-0">
                  YEAR_MISMATCH
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Footer: Decision-Support Note + Role Capabilities */}
        <div className="relative z-10 pt-4 border-t border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between gap-4 text-xs text-slate-500 dark:text-slate-400">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
            <span>{t('auth.footerNote')}</span>
          </div>
          <div className="hidden xl:flex items-center gap-1.5 font-mono text-[11px]">
            <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              Student
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              Teacher
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              Admin
            </span>
          </div>
        </div>
      </div>

      {/* ============================================================
          Right Panel — Executive Authentication Card (shadcn/ui)
          ============================================================ */}
      <div className="flex-1 flex flex-col justify-between p-5 sm:p-8 lg:p-10 xl:p-12 relative overflow-hidden">
        {/* Subtle ambient glow for right panel */}
        <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-indigo-500/5 dark:bg-indigo-500/10 blur-3xl rounded-full -z-10" />

        {/* Main Centered Login Container (First in DOM order so #password toggle is first SVG button) */}
        <div className="order-2 my-auto w-full max-w-[440px] mx-auto py-4">
          <Card className="p-0 overflow-hidden border-slate-200/90 dark:border-slate-800/90 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm shadow-xl shadow-slate-900/5 dark:shadow-black/30 rounded-2xl">
            {/* Top Gradient Accent Bar */}
            <div className="h-1.5 w-full bg-gradient-to-r from-indigo-600 via-indigo-500 to-emerald-500" />

            <CardHeader className="space-y-2 pb-5 pt-6 px-6 sm:px-7">
              <div className="flex items-center justify-between gap-2">
                <Badge
                  variant="outline"
                  className="font-mono text-[10px] uppercase tracking-wider px-2.5 py-0.5 bg-indigo-50/80 text-indigo-700 dark:bg-indigo-950/80 dark:text-indigo-300 border-indigo-200/70 dark:border-indigo-800/70 whitespace-nowrap"
                >
                  <Lock className="h-3 w-3 mr-1 shrink-0" />
                  {lang === 'vi' ? 'Xác thực Hệ thống' : 'Workspace Sign In'}
                </Badge>
                <span className="font-mono text-[11px] text-slate-400 dark:text-slate-500 whitespace-nowrap shrink-0">
                  RBAC v2.0
                </span>
              </div>

              <CardTitle className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white pt-1">
                {t('auth.welcomeBack')}
              </CardTitle>
              <CardDescription className="text-sm text-slate-600 dark:text-slate-400">
                {t('auth.signInSubtitle')}
              </CardDescription>
            </CardHeader>

            <CardContent className="px-6 sm:px-7 pb-6">
              {/* Error Message */}
              {error && (
                <Alert variant="destructive" className="mb-5">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-xs sm:text-sm font-medium">
                    {error}
                  </AlertDescription>
                </Alert>
              )}

              {/* Login Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label
                    htmlFor="username"
                    className="text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300"
                  >
                    {t('auth.username')}
                  </Label>
                  <div className="relative">
                    <div className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500">
                      <User className="h-4 w-4" />
                    </div>
                    <Input
                      id="username"
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      required
                      autoComplete="username"
                      className="h-11 pl-10 bg-slate-50/60 dark:bg-slate-950/60 focus-visible:bg-white dark:focus-visible:bg-slate-900"
                      placeholder={t('auth.usernamePlaceholder')}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label
                    htmlFor="password"
                    className="text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300"
                  >
                    {t('auth.password')}
                  </Label>
                  <div className="relative">
                    <div className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500">
                      <KeyRound className="h-4 w-4" />
                    </div>
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      autoComplete="current-password"
                      className="h-11 pl-10 pr-11 bg-slate-50/60 dark:bg-slate-950/60 focus-visible:bg-white dark:focus-visible:bg-slate-900"
                      placeholder={t('auth.passwordPlaceholder')}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide characters' : 'Show characters'}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={loading}
                  size="lg"
                  className="w-full h-11 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-600/20 mt-2 cursor-pointer"
                >
                  {loading ? (
                    <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      <span>{t('auth.signIn')}</span>
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </Button>
              </form>
            </CardContent>

            {/* Demo Credentials Hint (Interactive Quick-Fill) */}
            {import.meta.env.VITE_DEMO_MODE === 'true' && (
              <>
                <Separator className="bg-slate-200/80 dark:bg-slate-800/80" />
                <CardFooter className="px-6 sm:px-7 py-4 bg-slate-50/80 dark:bg-slate-950/60 flex flex-col items-stretch gap-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300">
                      <Terminal className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
                      <span>{t('auth.demoCredentials')}</span>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleFillDemo}
                      className="h-7 px-2.5 text-[11px] font-mono rounded-lg border-indigo-200 dark:border-indigo-800/80 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 cursor-pointer shrink-0"
                    >
                      {copiedDemo ? (
                        <>
                          <Check className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                          <span>{lang === 'vi' ? 'Đã điền' : 'Filled'}</span>
                        </>
                      ) : (
                        <span>{lang === 'vi' ? 'Điền nhanh' : 'Quick Fill'}</span>
                      )}
                    </Button>
                  </div>

                  <div className="grid grid-cols-2 gap-2.5 font-mono">
                    <div className="px-3 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase tracking-wider text-slate-400 dark:text-slate-500">
                        {t('auth.username')}
                      </span>
                      <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                        admin
                      </span>
                    </div>
                    <div className="px-3 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 flex flex-col gap-0.5">
                      <span className="text-[10px] uppercase tracking-wider text-slate-400 dark:text-slate-500">
                        {t('auth.password')}
                      </span>
                      <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                        admin123
                      </span>
                    </div>
                  </div>
                </CardFooter>
              </>
            )}
          </Card>
        </div>

        {/* Top Utility Navigation Bar (Visually at top via order-1, placed after form in DOM) */}
        <div className="order-1 w-full max-w-[440px] lg:max-w-none mx-auto flex items-center justify-between gap-2">
          {/* Mobile Brand / Back to Home */}
          <div className="flex items-center gap-3 min-w-0">
            <Link
              to="/"
              className="lg:hidden flex items-center gap-2.5 group rounded-xl shrink-0"
            >
              <div className="w-9 h-9 bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-xl flex items-center justify-center shadow-sm shadow-indigo-500/20">
                <SourceLogicBrandMark size={20} />
              </div>
              <div>
                <span className="font-display text-base font-bold text-slate-900 dark:text-white block leading-none">
                  SourceLogic
                </span>
                <span className="hidden sm:block text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                  {t('nav.academicVerification')}
                </span>
              </div>
            </Link>

            <Link
              to="/"
              className="hidden lg:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-slate-800/70 transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>{lang === 'vi' ? 'Về trang giới thiệu' : 'Back to Overview'}</span>
            </Link>
          </div>

          {/* Right Utility Controls: Mobile Back Link + Language Switcher + ThemeToggle */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            <Link
              to="/"
              className="lg:hidden inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-slate-800 transition-colors whitespace-nowrap"
            >
              <ArrowLeft className="h-3.5 w-3.5 shrink-0" />
              <span>{lang === 'vi' ? 'Trang chủ' : 'Home'}</span>
            </Link>

            <button
              type="button"
              onClick={toggleLanguage}
              className="inline-flex items-center gap-1.5 h-8 px-2.5 rounded-lg text-xs font-mono font-semibold text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer shadow-2xs"
              title={lang === 'vi' ? 'Switch to English' : 'Chuyển sang Tiếng Việt'}
            >
              <Globe className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
              <span>{lang === 'vi' ? 'VI' : 'EN'}</span>
            </button>

            <ThemeToggle
              size="sm"
              className="h-8 w-8 bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 shadow-2xs"
            />
          </div>
        </div>

        {/* Bottom Subtle Workspace Note (order-3) */}
        <div className="order-3 w-full max-w-[440px] mx-auto pt-2 flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500">
          <span>SourceLogic Workspace</span>
          <span className="font-mono">JWT · Capability RBAC</span>
        </div>
      </div>
    </div>
  );
}
