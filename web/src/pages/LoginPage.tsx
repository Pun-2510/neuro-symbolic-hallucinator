import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/api/client';
import { AuthSplitShell } from '@/components/AuthSplitShell';
import {
  Eye,
  EyeOff,
  AlertCircle,
  ArrowRight,
  Lock,
  User,
  KeyRound,
  Terminal,
  Check,
  CheckCircle2,
  Mail,
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

export function LoginPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [needsActivation, setNeedsActivation] = useState(false);
  const [resending, setResending] = useState(false);
  const [resentSuccess, setResentSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedDemo, setCopiedDemo] = useState(false);

  const lang = i18n.language?.startsWith('vi') ? 'vi' : 'en';
  const activatedParam = searchParams.get('activated') === '1';
  const resetParam = searchParams.get('reset') === '1';

  const handleFillDemo = () => {
    setUsername('admin');
    setPassword('admin123');
    setError('');
    setNeedsActivation(false);
    setResentSuccess('');
    setCopiedDemo(true);
    window.setTimeout(() => setCopiedDemo(false), 1800);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setNeedsActivation(false);
    setResentSuccess('');
    setLoading(true);

    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (err) {
      const msg = err instanceof Error ? err.message : t('auth.loginError');
      if (msg.includes('ACCOUNT_NOT_ACTIVATED')) {
        setNeedsActivation(true);
        setError(t('auth.accountNotActivatedDesc'));
      } else if (msg.includes('ACCOUNT_DEACTIVATED')) {
        setError(msg.replace('ACCOUNT_DEACTIVATED: ', ''));
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResendActivation = async () => {
    if (!username.trim()) return;
    setResending(true);
    setResentSuccess('');
    try {
      await api.resendActivation(username.trim(), lang);
      setResentSuccess(t('auth.activationResentSuccess'));
      setError('');
      setNeedsActivation(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to resend activation email',
      );
    } finally {
      setResending(false);
    }
  };

  return (
    <AuthSplitShell>
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
          </div>

          <CardTitle className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white pt-1">
            {t('auth.welcomeBack')}
          </CardTitle>
          <CardDescription className="text-sm text-slate-600 dark:text-slate-400">
            {t('auth.signInSubtitle')}
          </CardDescription>
        </CardHeader>

        <CardContent className="px-6 sm:px-7 pb-6">
          {/* Activated or Password Reset Success Banner */}
          {(activatedParam || resetParam || resentSuccess) && !error && (
            <Alert className="mb-5 border-emerald-200/90 dark:border-emerald-800/80 bg-emerald-50/90 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-200">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <AlertDescription className="text-xs sm:text-sm font-medium text-emerald-800 dark:text-emerald-200">
                {resentSuccess
                  ? resentSuccess
                  : activatedParam
                    ? t('auth.activatedBanner')
                    : t('auth.passwordResetBanner')}
              </AlertDescription>
            </Alert>
          )}

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
              <div className="flex items-center justify-between gap-2">
                <Label
                  htmlFor="password"
                  className="text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300"
                >
                  {t('auth.password')}
                </Label>
                <Link
                  to="/forgot-password"
                  className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 hover:underline transition-colors"
                >
                  {t('auth.forgotPasswordLink')}
                </Link>
              </div>
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

            {/* Resend Activation Action Box (placed after #password toggle in DOM) */}
            {needsActivation && (
              <div className="rounded-xl bg-amber-50/90 dark:bg-amber-950/40 border border-amber-200/90 dark:border-amber-800/70 p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5">
                <div className="text-xs text-amber-800 dark:text-amber-200 font-medium">
                  {t('auth.accountNotActivatedTitle')}
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={resending}
                  onClick={handleResendActivation}
                  className="h-8 px-3 text-xs font-semibold border-amber-300 dark:border-amber-700 text-amber-900 dark:text-amber-100 hover:bg-amber-100 dark:hover:bg-amber-900/60 cursor-pointer shrink-0"
                >
                  <Mail className="h-3.5 w-3.5 mr-1.5" />
                  <span>
                    {resending
                      ? t('auth.resendingActivation')
                      : t('auth.resendActivationBtn')}
                  </span>
                </Button>
              </div>
            )}

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

          {/* Create Account Link */}
          <div className="mt-5 pt-4 border-t border-slate-200/70 dark:border-slate-800/70 text-center text-xs sm:text-sm text-slate-600 dark:text-slate-400">
            <span>{t('auth.noAccountPrompt')} </span>
            <Link
              to="/register"
              className="font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 hover:underline transition-colors"
            >
              {t('auth.createAccountLink')}
            </Link>
          </div>
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
    </AuthSplitShell>
  );
}
