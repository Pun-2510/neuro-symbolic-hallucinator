import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Save, Loader2, Lock, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { AvatarUpload } from '@/components/AvatarUpload';
import { api } from '@/api/client';

export function ProfilePage() {
  const { t, i18n } = useTranslation();
  const { user: authUser, refreshUser } = useAuth();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState('');
  const [profileSuccess, setProfileSuccess] = useState(false);

  // Password change
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');

  // Init from auth user
  useEffect(() => {
    if (authUser) {
      setFullName(authUser.full_name ?? '');
      setEmail(authUser.email ?? '');
    }
  }, [authUser]);

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileError('');
    setProfileSuccess(false);
    setProfileLoading(true);
    try {
      const updated = await api.updateMe({
        full_name: fullName || undefined,
        email: email || undefined,
      });
      await refreshUser();
      // Update local email/fullName from server response
      setFullName(updated.full_name ?? '');
      setEmail(updated.email ?? '');
      setProfileSuccess(true);
      setTimeout(() => setProfileSuccess(false), 3000);
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : t('profile.failedToSave'));
    } finally {
      setProfileLoading(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');

    if (newPassword.length < 6) {
      setPasswordError(t('profile.passwordMinLengthError'));
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError(t('profile.passwordMismatchError'));
      return;
    }
    if (newPassword === currentPassword) {
      setPasswordError(t('profile.passwordSameError'));
      return;
    }

    setPasswordLoading(true);
    try {
      await api.changeMyPassword({ current_password: currentPassword, new_password: newPassword });
      setPasswordSuccess(t('profile.passwordChangedSuccess'));
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setPasswordSuccess(''), 5000);
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : t('profile.passwordChangeFailed'));
    } finally {
      setPasswordLoading(false);
    }
  };

  const dateLocale = i18n.language?.startsWith('vi') ? 'vi-VN' : 'en-US';

  return (
    <div className="space-y-6 w-full max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-slate-100">
          {t('profile.title')}
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          {t('profile.subtitle')}
        </p>
      </div>

      {/* Avatar + Basic Info */}
      <div className="card p-6">
        <div className="flex flex-col sm:flex-row sm:items-start gap-6">
          {/* Avatar upload */}
          <div className="flex flex-col items-center gap-3 shrink-0 sm:w-40">
            <AvatarUpload
              currentAvatarUrl={authUser?.avatar_url ?? null}
              onSuccess={() => {
                refreshUser();
              }}
              size="lg"
            />
            <p className="text-xs text-slate-500 dark:text-slate-400 text-center max-w-[8rem]">
              {t('profile.avatarTypes')}<br />{t('profile.avatarMax')}
            </p>
          </div>

          {/* Profile form */}
          <div className="flex-1 space-y-4 min-w-0">
            <div>
              <label className="input-label">{t('profile.username')}</label>
              <input
                type="text"
                value={authUser?.username ?? ''}
                readOnly
                disabled
                className="input opacity-60 cursor-not-allowed"
              />
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {t('profile.usernameReadonly')}
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="input-label">{t('profile.fullName')}</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  maxLength={120}
                  className="input"
                  placeholder={t('profile.fullNamePlaceholder')}
                />
              </div>

              <div>
                <label className="input-label">{t('profile.email')}</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder={t('profile.emailPlaceholder')}
                />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleProfileSave}
                disabled={profileLoading}
                className="btn-primary"
              >
                {profileLoading ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    {t('profile.saving')}
                  </>
                ) : (
                  <>
                    <Save className="h-3.5 w-3.5" />
                    {t('profile.saveChanges')}
                  </>
                )}
              </button>

              {profileSuccess && (
                <span className="flex items-center gap-1 text-sm text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="h-4 w-4" />
                  {t('profile.saved')}
                </span>
              )}

              {profileError && (
                <span className="flex items-center gap-1 text-sm text-red-600 dark:text-red-400">
                  <AlertCircle className="h-4 w-4" />
                  {profileError}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Role + meta */}
        <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700 grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-slate-500 dark:text-slate-400 text-xs mb-1">{t('profile.role')}</p>
            <p className="font-medium text-slate-900 dark:text-slate-100 capitalize">
              {authUser?.role ?? '—'}
            </p>
          </div>
          <div>
            <p className="text-slate-500 dark:text-slate-400 text-xs mb-1">{t('profile.memberSince')}</p>
            <p className="text-slate-900 dark:text-slate-100">
              {authUser?.created_at
                ? new Date(authUser.created_at).toLocaleDateString(dateLocale, {
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric',
                  })
                : '—'}
            </p>
          </div>
          <div>
            <p className="text-slate-500 dark:text-slate-400 text-xs mb-1">{t('profile.lastLogin')}</p>
            <p className="text-slate-900 dark:text-slate-100">
              {authUser?.last_login_at
                ? new Date(authUser.last_login_at).toLocaleDateString(dateLocale, {
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric',
                  })
                : '—'}
            </p>
          </div>
        </div>
      </div>

      {/* Change Password */}
      <div className="card p-6">
        <div className="flex items-center gap-2 mb-5">
          <Lock className="h-5 w-5 text-slate-600 dark:text-slate-400" />
          <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100">
            {t('profile.changePassword')}
          </h2>
        </div>

        <form onSubmit={handlePasswordChange} className="space-y-4">
          {/* Hidden username field for accessibility (WCAG 1.3.5) */}
          <input
            type="text"
            name="username"
            autoComplete="username"
            value={authUser?.username ?? ''}
            readOnly
            tabIndex={-1}
            style={{ position: 'absolute', left: '-9999px', width: '1px', height: '1px' }}
            aria-hidden="true"
          />

          {passwordSuccess && (
            <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800 flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0" />
              <p className="text-sm text-emerald-700 dark:text-emerald-300">{passwordSuccess}</p>
            </div>
          )}

          {passwordError && (
            <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
              <p className="text-sm text-red-700 dark:text-red-300">{passwordError}</p>
            </div>
          )}

          <div>
            <label className="input-label">{t('profile.currentPassword')}</label>
            <input
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              className="input"
              placeholder={t('profile.currentPasswordPlaceholder')}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="input-label">{t('profile.newPassword')}</label>
              <input
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={6}
                maxLength={128}
                className="input"
                placeholder={t('profile.newPasswordPlaceholder')}
              />
            </div>

            <div>
              <label className="input-label">{t('profile.confirmNewPassword')}</label>
              <input
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="input"
                placeholder={t('profile.confirmNewPasswordPlaceholder')}
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={passwordLoading}
              className="btn-secondary text-sm py-2 px-4"
            >
              {passwordLoading ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {t('profile.updating')}
                </>
              ) : (
                <>
                  <Lock className="h-3.5 w-3.5" />
                  {t('profile.updatePassword')}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
