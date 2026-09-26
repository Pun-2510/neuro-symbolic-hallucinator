import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Eye, EyeOff, Shield, CheckCircle2, AlertCircle, Quote, Database, GitBranch, Scale, FileSearch } from 'lucide-react';

export function LoginPage() {
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
      setError(err instanceof Error ? err.message : 'Login failed');
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
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                className="text-white"
              >
                <path
                  d="M12 2L2 7L12 12L22 7L12 2Z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M2 17L12 22L22 17"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M2 12L12 17L22 12"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div>
              <h1 className="font-display text-2xl font-bold text-slate-900 dark:text-white">
                SourceLogic
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Academic Source Verification
              </p>
            </div>
          </div>

          {/* Hero */}
          <div className="mb-12">
            <h2 className="font-display text-3xl xl:text-4xl font-bold text-slate-900 dark:text-white mb-4 leading-tight">
              Verify Every Citation.
              <br />
              <span className="text-indigo-600 dark:text-indigo-400">Trace Every Source.</span>
            </h2>
            <p className="text-base text-slate-600 dark:text-slate-400 max-w-md leading-relaxed">
              Detect invalid, mismatched and potentially hallucinated academic references
              with explainable source verification.
            </p>
          </div>

          {/* Features */}
          <div className="space-y-5">
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-xl bg-emerald-50 dark:bg-emerald-950 mt-0.5">
                <Quote className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white text-base">Citation Extraction</h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                  Automatically extract in-text citations and references from documents
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-xl bg-indigo-50 dark:bg-indigo-950 mt-0.5">
                <Database className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white text-base">Multi-Source Retrieval</h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                  Query Crossref, OpenAlex, Semantic Scholar, and CORE for metadata
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-xl bg-amber-50 dark:bg-amber-950 mt-0.5">
                <GitBranch className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white text-base">Neuro-Symbolic Verification</h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                  Explainable decision logic with evidence and rule tracing
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <Shield className="h-4 w-4" />
          <span>Decision Support System — Not an automated grader</span>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-slate-50 dark:bg-slate-950">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                className="text-white"
              >
                <path
                  d="M12 2L2 7L12 12L22 7L12 2Z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M2 17L12 22L22 17"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M2 12L12 17L22 12"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div>
              <h1 className="font-display text-xl font-bold text-slate-900 dark:text-white">
                SourceLogic
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Academic Verification
              </p>
            </div>
          </div>

          {/* Form Header */}
          <div className="mb-8">
            <h2 className="font-display text-2xl font-bold text-slate-900 dark:text-white mb-2">
              Welcome back
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Sign in to access your verification workspace
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="username" className="input-label">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete="username"
                className="input"
                placeholder="Enter your username"
              />
            </div>

            <div>
              <label htmlFor="password" className="input-label">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="input pr-12"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
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

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-center py-3"
            >
              {loading ? (
                <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Demo credentials hint */}
          <div className="mt-5 p-4 rounded-xl bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-2 font-medium">Demo credentials:</p>
            <div className="space-y-1 text-sm font-mono">
              <p className="text-slate-600 dark:text-slate-300">
                <span className="text-slate-400 dark:text-slate-500">Username:</span> admin
              </p>
              <p className="text-slate-600 dark:text-slate-300">
                <span className="text-slate-400 dark:text-slate-500">Password:</span> admin123
              </p>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="mt-6 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 flex items-start gap-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="text-slate-900 dark:text-slate-100 font-medium mb-1">Academic Decision Support</p>
              <p className="text-slate-600 dark:text-slate-400">
                This system assists human review — it does not automatically conclude
                academic fraud. All verdicts require human judgment.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
