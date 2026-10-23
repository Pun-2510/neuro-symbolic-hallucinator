/**
 * Settings Page (Scholarly Precision shadcn/ui v2.0)
 * Central configuration hub for user preferences
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Settings,
  Palette,
  Globe,
  Bell,
  Info,
  ChevronRight,
  Check,
  ShieldCheck,
  Terminal,
  AlertTriangle,
} from 'lucide-react';
import { ThemeToggle } from '@/contexts/ThemeContext';
import { useToast } from '@/contexts/ToastContext';
import { ConfirmationModal } from '@/components/ConfirmationModal';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';

// ============================================================
// Types
// ============================================================

interface SettingsState {
  notifications: boolean;
  autoVerify: boolean;
  compactView: boolean;
}

// ============================================================
// Constants
// ============================================================

const STORAGE_KEY_NOTIFICATIONS = 'settings_notifications';
const STORAGE_KEY_AUTO_VERIFY = 'settings_auto_verify';
const STORAGE_KEY_COMPACT_VIEW = 'settings_compact_view';

// ============================================================
// Component
// ============================================================

export function SettingsPage(): JSX.Element {
  const toast = useToast();
  const { t, i18n } = useTranslation();
  const [confirmClear, setConfirmClear] = useState(false);

  // Load saved settings
  const [settings, setSettings] = useState<SettingsState>(() => ({
    notifications: localStorage.getItem(STORAGE_KEY_NOTIFICATIONS) !== 'false',
    autoVerify: localStorage.getItem(STORAGE_KEY_AUTO_VERIFY) === 'true',
    compactView: localStorage.getItem(STORAGE_KEY_COMPACT_VIEW) === 'true',
  }));

  // Available languages (without flag emojis)
  const languages = [
    { code: 'vi', label: 'Tiếng Việt' },
    { code: 'en', label: 'English' },
  ];

  // Get current language from i18n (reactive) — no reload needed
  const currentLang = (i18n.resolvedLanguage || i18n.language || 'en').split('-')[0];

  // Toggle setting
  const toggleSetting = (key: keyof SettingsState): void => {
    setSettings((prev) => {
      const newValue = !prev[key];
      const storageKey = `settings_${
        key === 'autoVerify'
          ? 'auto_verify'
          : key === 'compactView'
          ? 'compact_view'
          : key
      }`;
      localStorage.setItem(storageKey, String(newValue));

      toast.success(
        t('settings.settingsSaved'),
        key === 'notifications'
          ? newValue
            ? t('settings.notificationsEnabled')
            : t('settings.notificationsDisabled')
          : key === 'autoVerify'
          ? newValue
            ? t('settings.autoVerifyEnabled')
            : t('settings.autoVerifyDisabled')
          : newValue
          ? t('settings.compactViewEnabled')
          : t('settings.compactViewDisabled')
      );

      return { ...prev, [key]: newValue };
    });
  };

  // Change language — uses i18n.changeLanguage() for SPA navigation (no reload)
  const changeLanguage = (langCode: string): void => {
    void i18n.changeLanguage(langCode);
    localStorage.setItem('language', langCode);
    localStorage.setItem('i18nextLng', langCode);
    const fixedT = i18n.getFixedT(langCode);
    toast.success(
      fixedT('settings.languageUpdated'),
      langCode === 'vi' ? 'Tiếng Việt' : 'English'
    );
  };

  // Clear local cache (only after explicit user confirmation)
  const handleClearCache = (): void => {
    localStorage.removeItem('theme');
    localStorage.removeItem('language');
    localStorage.removeItem('i18nextLng');
    void i18n.changeLanguage('en');
    toast.success(t('settings.cacheClearedSuccess'));
  };

  return (
    <div className="space-y-6 w-full max-w-4xl pb-10">
      {/* Executive Header Card */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 p-5 sm:p-6 shadow-xs">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2.5 flex-wrap mb-2.5">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200/70 dark:border-indigo-800/70 text-[11px] font-mono font-semibold text-indigo-700 dark:text-indigo-300">
                <ShieldCheck className="h-3.5 w-3.5" />
                {currentLang === 'vi'
                  ? 'CẤU HÌNH MÔI TRƯỜNG LÀM VIỆC'
                  : 'WORKSPACE ENVIRONMENT CONFIG'}
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950/70 border border-emerald-200/70 dark:border-emerald-800/70 text-[11px] font-mono text-emerald-700 dark:text-emerald-300">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                v1.11.0
              </span>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200/70 dark:border-indigo-800/70 flex items-center justify-center shrink-0">
                <Settings className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              </div>
              <div>
                <h1 className="font-display text-2xl sm:text-3xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
                  {t('settings.title')}
                </h1>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                  {t('settings.subtitle')}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Appearance Section */}
        <div className="rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm overflow-hidden flex flex-col">
          <div className="flex items-center justify-between gap-3 px-4 py-3 bg-slate-50/90 dark:bg-slate-900/90 border-b border-slate-200/80 dark:border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-400/80" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80" />
              </div>
              <Separator orientation="vertical" className="h-4" />
              <Palette className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <h2 className="text-sm font-display font-semibold text-slate-900 dark:text-slate-100">
                {t('settings.appearance')}
              </h2>
            </div>
            <span className="text-[11px] font-mono text-slate-400">01</span>
          </div>

          <div className="p-6 flex-1">
            <div>
              <Label className="input-label">{t('settings.theme')}</Label>
              <div className="mt-2.5">
                <ThemeToggle showLabel />
              </div>
              <p className="text-xs text-slate-500 mt-2.5 leading-relaxed">
                {t('settings.themeDescription')}
              </p>
            </div>
          </div>
        </div>

        {/* Language Section */}
        <div className="rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm overflow-hidden flex flex-col">
          <div className="flex items-center justify-between gap-3 px-4 py-3 bg-slate-50/90 dark:bg-slate-900/90 border-b border-slate-200/80 dark:border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-400/80" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80" />
              </div>
              <Separator orientation="vertical" className="h-4" />
              <Globe className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <h2 className="text-sm font-display font-semibold text-slate-900 dark:text-slate-100">
                {t('settings.language')}
              </h2>
            </div>
            <span className="text-[11px] font-mono text-slate-400">02</span>
          </div>

          <div className="p-6 flex-1 flex flex-col justify-center">
            <div className="grid grid-cols-2 gap-3">
              {languages.map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => changeLanguage(lang.code)}
                  className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                    currentLang === lang.code
                      ? 'border-indigo-500 bg-indigo-50/80 dark:bg-indigo-950/60 shadow-2xs'
                      : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                  }`}
                >
                  <span
                    className={`font-medium text-sm ${
                      currentLang === lang.code
                        ? 'text-indigo-700 dark:text-indigo-300'
                        : 'text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    {lang.label}
                  </span>
                  {currentLang === lang.code && (
                    <Check className="w-4 h-4 text-indigo-500 ml-auto" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Notifications Section */}
      <div className="rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-3 bg-slate-50/90 dark:bg-slate-900/90 border-b border-slate-200/80 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-400/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80" />
            </div>
            <Separator orientation="vertical" className="h-4" />
            <Bell className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            <h2 className="text-sm font-display font-semibold text-slate-900 dark:text-slate-100">
              {t('settings.notifications')}
            </h2>
          </div>
          <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
            <Terminal className="w-3 h-3" />
            workspace_preferences.json
          </span>
        </div>

        <div className="p-6 divide-y divide-slate-100 dark:divide-slate-800/80">
          <div className="pb-4">
            <ToggleSetting
              label={t('settings.enableNotifications')}
              description={t('settings.enableNotificationsDesc')}
              checked={settings.notifications}
              onChange={() => toggleSetting('notifications')}
            />
          </div>

          <div className="py-4">
            <ToggleSetting
              label={t('settings.autoVerify')}
              description={t('settings.autoVerifyDesc')}
              checked={settings.autoVerify}
              onChange={() => toggleSetting('autoVerify')}
            />
          </div>

          <div className="pt-4">
            <ToggleSetting
              label={t('settings.compactView')}
              description={t('settings.compactViewDesc')}
              checked={settings.compactView}
              onChange={() => toggleSetting('compactView')}
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* About Section */}
        <div className="rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between gap-3 px-4 py-3 bg-slate-50/90 dark:bg-slate-900/90 border-b border-slate-200/80 dark:border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-400/80" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80" />
              </div>
              <Separator orientation="vertical" className="h-4" />
              <Info className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <h2 className="text-sm font-display font-semibold text-slate-900 dark:text-slate-100">
                {t('settings.about')}
              </h2>
            </div>
            <span className="text-[11px] font-mono text-slate-400">04</span>
          </div>

          <div className="p-6 space-y-3">
            <InfoRow label={t('settings.version')} value="1.11.0" />
            <InfoRow
              label={t('settings.buildDate')}
              value={new Date().toLocaleDateString()}
            />

            <div className="pt-3 border-t border-slate-200 dark:border-slate-800">
              <a
                href="https://github.com/iannwendy/essay-integrity-checker"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-mono font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
              >
                {t('settings.viewSourceCode')}
                <ChevronRight className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="rounded-2xl border border-red-200/90 dark:border-red-900/60 bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between gap-3 px-4 py-3 bg-red-50/70 dark:bg-red-950/30 border-b border-red-200/70 dark:border-red-900/50">
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400" />
              <h2 className="text-sm font-display font-semibold text-red-700 dark:text-red-400">
                {t('settings.dangerZone')}
              </h2>
            </div>
            <span className="text-[11px] font-mono text-red-500">05</span>
          </div>

          <div className="p-6">
            <button
              onClick={() => setConfirmClear(true)}
              className="w-full flex items-center justify-between p-4 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-red-300 dark:hover:border-red-800 hover:bg-red-50/50 dark:hover:bg-red-950/20 transition-colors"
              aria-label="Clear local cache"
            >
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {t('settings.clearLocalCache')}
              </span>
              <ChevronRight className="w-4 h-4 text-slate-400" />
            </button>
          </div>
        </div>
      </div>

      <ConfirmationModal
        isOpen={confirmClear}
        title={t('settings.clearCacheConfirmTitle')}
        message={t('settings.clearCacheConfirmMessage')}
        confirmLabel={t('settings.clearCacheConfirmBtn')}
        cancelLabel={t('common.cancel')}
        variant="danger"
        onConfirm={() => {
          setConfirmClear(false);
          handleClearCache();
        }}
        onCancel={() => setConfirmClear(false)}
      />
    </div>
  );
}

// ============================================================
// Sub-components
// ============================================================

interface ToggleSettingProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: () => void;
}

function ToggleSetting({
  label,
  description,
  checked,
  onChange,
}: ToggleSettingProps): JSX.Element {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="font-medium text-sm text-slate-900 dark:text-slate-100">
          {label}
        </p>
        {description && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {description}
          </p>
        )}
      </div>
      <Switch checked={checked} onCheckedChange={onChange} />
    </div>
  );
}

interface InfoRowProps {
  label: string;
  value: string;
}

function InfoRow({ label, value }: InfoRowProps): JSX.Element {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-600 dark:text-slate-400">{label}</span>
      <span className="font-medium font-mono text-xs px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100">
        {value}
      </span>
    </div>
  );
}

export default SettingsPage;
