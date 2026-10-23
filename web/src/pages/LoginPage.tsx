import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/AuthContext';
import {
  Eye,
  EyeOff,
  Shield,
  CheckCircle2,
  AlertCircle,
  Quote,
  Database,
  GitBranch,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

function SourceLogicBrandMark({ size = 28 }: { size?: number }) {
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
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M4 16C4 17.1046 4.89543 18 6 18H8"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M10 12H14M14 12L12 10M14 12L12 14"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M17 9L19 11L22 8"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex">
      {/* Left Panel - Branding — SourceLogic UX/UI Concept */}
      <div className="hidden lg:flex lg:w-1/2 xl:w-3/5 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex-col justify-between p-10 xl:p-14">
        <div>
          {/* Logo */}
          <div className="flex items-center gap-4 mb-16">
            <div className="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <SourceLogicBrandMark size={28} />
            </div>
            <div>
              <h1 className="font-display text-2xl font-bold text-slate-900 dark:text-white">
                SourceLogic
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t('nav.academicVerification')}
              </p>
            </div>
          </div>

          {/* Hero */}
          <div className="mb-12">
            <h2 className="font-display text-3xl xl:text-4xl font-bold text-slate-900 dark:text-white mb-4 leading-tight">
              {t('auth.heroTitle1')}
              <br />
              <span className="text-indigo-600 dark:text-indigo-400">
                {t('auth.heroTitle2')}
              </span>
            </h2>
            <p className="text-base text-slate-600 dark:text-slate-400 max-w-md leading-relaxed">
              {t('auth.heroDesc')}
            </p>
          </div>

          {/* Features */}
          <div className="space-y-5">
            <div className="flex items-start gap-3.5">
              <div className="p-2.5 rounded-xl bg-emerald-50 dark:bg-emerald-950 mt-0.5 border border-emerald-200/60 dark:border-emerald-800/60">
                <Quote className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white text-base">
                  {t('auth.featureExtraction')}
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                  {t('auth.featureExtractionDesc')}
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3.5">
              <div className="p-2.5 rounded-xl bg-indigo-50 dark:bg-indigo-950 mt-0.5 border border-indigo-200/60 dark:border-indigo-800/60">
                <Database className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white text-base">
                  {t('auth.featureRetrieval')}
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                  {t('auth.featureRetrievalDesc')}
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3.5">
              <div className="p-2.5 rounded-xl bg-amber-50 dark:bg-amber-950 mt-0.5 border border-amber-200/60 dark:border-amber-800/60">
                <GitBranch className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white text-base">
                  {t('auth.featureVerification')}
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                  {t('auth.featureVerificationDesc')}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <Shield className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          <span>{t('auth.footerNote')}</span>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-slate-50 dark:bg-slate-950">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <SourceLogicBrandMark size={24} />
            </div>
            <div>
              <h1 className="font-display text-xl font-bold text-slate-900 dark:text-white">
                SourceLogic
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t('nav.academicVerification')}
              </p>
            </div>
          </div>

          {/* Form Header */}
          <div className="mb-8">
            <h2 className="font-display text-2xl font-bold text-slate-900 dark:text-white mb-2">
              {t('auth.welcomeBack')}
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {t('auth.signInSubtitle')}
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <Alert variant="destructive" className="mb-6">
              <AlertCircle className="h-5 w-5" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="username">{t('auth.username')}</Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete="username"
                className="h-11"
                placeholder={t('auth.usernamePlaceholder')}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">{t('auth.password')}</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="h-11 pr-12"
                  placeholder={t('auth.passwordPlaceholder')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide characters' : 'Show characters'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-11 text-base"
            >
              {loading ? (
                <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                t('auth.signIn')
              )}
            </Button>
          </form>

          {/* Demo credentials hint */}
          {import.meta.env.VITE_DEMO_MODE === 'true' && (
            <div className="mt-5 p-4 rounded-xl bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-2 font-medium">
                {t('auth.demoCredentials')}
              </p>
              <div className="space-y-1 text-sm font-mono">
                <p className="text-slate-600 dark:text-slate-300">
                  <span className="text-slate-400 dark:text-slate-500">
                    {t('auth.username')}:
                  </span>{' '}
                  admin
                </p>
                <p className="text-slate-600 dark:text-slate-300">
                  <span className="text-slate-400 dark:text-slate-500">
                    {t('auth.password')}:
                  </span>{' '}
                  admin123
                </p>
              </div>
            </div>
          )}

          {/* Disclaimer */}
          <Alert variant="success" className="mt-6">
            <CheckCircle2 className="h-5 w-5" />
            <AlertTitle>{t('auth.decisionSupportTitle')}</AlertTitle>
            <AlertDescription>{t('auth.decisionSupportDesc')}</AlertDescription>
          </Alert>
        </div>
      </div>
    </div>
  );
}
