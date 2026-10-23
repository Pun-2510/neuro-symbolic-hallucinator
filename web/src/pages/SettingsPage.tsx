/**
 * Settings Page
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
} from 'lucide-react';
import { ThemeToggle } from '@/contexts/ThemeContext';
import { useToast } from '@/contexts/ToastContext';
import { ConfirmationModal } from '@/components/ConfirmationModal';
import { Card } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';

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
      const storageKey = `settings_${key === 'autoVerify' ? 'auto_verify' : key === 'compactView' ? 'compact_view' : key}`;
      localStorage.setItem(storageKey, String(newValue));

      toast.success(
        t('settings.settingsSaved'),
        key === 'notifications'
          ? newValue ? t('settings.notificationsEnabled') : t('settings.notificationsDisabled')
          : key === 'autoVerify'
          ? newValue ? t('settings.autoVerifyEnabled') : t('settings.autoVerifyDisabled')
          : newValue ? t('settings.compactViewEnabled') : t('settings.compactViewDisabled')
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
    toast.success(fixedT('settings.languageUpdated'), langCode === 'vi' ? 'Tiếng Việt' : 'English');
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
    <div className="container-page py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-12 h-12 rounded-xl bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
          <Settings className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold text-slate-900 dark:text-slate-100">
            {t('settings.title')}
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            {t('settings.subtitle')}
          </p>
        </div>
      </div>

      <div className="max-w-2xl space-y-6">
        {/* Appearance Section */}
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Palette className="w-5 h-5 text-slate-500" />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {t('settings.appearance')}
            </h2>
          </div>

          <div className="space-y-4">
            {/* Theme Selection */}
            <div>
              <Label className="input-label">{t('settings.theme')}</Label>
              <div className="mt-2">
                <ThemeToggle showLabel />
              </div>
              <p className="text-xs text-slate-500 mt-2">
                {t('settings.themeDescription')}
              </p>
            </div>
          </div>
        </Card>

        {/* Language Section */}
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Globe className="w-5 h-5 text-slate-500" />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {t('settings.language')}
            </h2>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {languages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => changeLanguage(lang.code)}
                className={`
                  flex items-center gap-3 p-4 rounded-xl border-2 transition-all
                  ${
                    currentLang === lang.code
                      ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                      : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                  }
                `}
              >
                <span className={`
                  font-medium
                  ${currentLang === lang.code
                    ? 'text-indigo-700 dark:text-indigo-300'
                    : 'text-slate-700 dark:text-slate-300'
                  }
                `}>
                  {lang.label}
                </span>
                {currentLang === lang.code && (
                  <Check className="w-5 h-5 text-indigo-500 ml-auto" />
                )}
              </button>
            ))}
          </div>
        </Card>

        {/* Notifications Section */}
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Bell className="w-5 h-5 text-slate-500" />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {t('settings.notifications')}
            </h2>
          </div>

          <div className="space-y-4">
            <ToggleSetting
              label={t('settings.enableNotifications')}
              description={t('settings.enableNotificationsDesc')}
              checked={settings.notifications}
              onChange={() => toggleSetting('notifications')}
            />

            <ToggleSetting
              label={t('settings.autoVerify')}
              description={t('settings.autoVerifyDesc')}
              checked={settings.autoVerify}
              onChange={() => toggleSetting('autoVerify')}
            />

            <ToggleSetting
              label={t('settings.compactView')}
              description={t('settings.compactViewDesc')}
              checked={settings.compactView}
              onChange={() => toggleSetting('compactView')}
            />
          </div>
        </Card>

        {/* About Section */}
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Info className="w-5 h-5 text-slate-500" />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {t('settings.about')}
            </h2>
          </div>

          <div className="space-y-3">
            <InfoRow label={t('settings.version')} value="1.11.0" />
            <InfoRow label={t('settings.buildDate')} value={new Date().toLocaleDateString()} />

            <div className="pt-3 border-t border-slate-200 dark:border-slate-700">
              <a
                href="https://github.com/iannwendy/essay-integrity-checker"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-indigo-600 dark:text-indigo-400 hover:underline"
              >
                {t('settings.viewSourceCode')}
                <ChevronRight className="w-4 h-4" />
              </a>
            </div>
          </div>
        </Card>

        {/* Danger Zone */}
        <Card className="p-6 border-red-200 dark:border-red-900/50">
          <h2 className="text-lg font-semibold text-red-700 dark:text-red-400 mb-4">
            {t('settings.dangerZone')}
          </h2>

          <div className="space-y-3">
            <button
              onClick={() => setConfirmClear(true)}
              className="w-full flex items-center justify-between p-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
              aria-label="Clear local cache"
            >
              <span className="text-slate-700 dark:text-slate-300">
                {t('settings.clearLocalCache')}
              </span>
              <ChevronRight className="w-5 h-5 text-slate-400" />
            </button>
          </div>
        </Card>
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

function ToggleSetting({ label, description, checked, onChange }: ToggleSettingProps): JSX.Element {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="font-medium text-slate-900 dark:text-slate-100">{label}</p>
        {description && (
          <p className="text-sm text-slate-500 dark:text-slate-400">{description}</p>
        )}
      </div>
      <Switch
        checked={checked}
        onCheckedChange={onChange}
      />
    </div>
  );
}

interface InfoRowProps {
  label: string;
  value: string;
}

function InfoRow({ label, value }: InfoRowProps): JSX.Element {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-600 dark:text-slate-400">{label}</span>
      <span className="font-medium font-mono text-slate-900 dark:text-slate-100">{value}</span>
    </div>
  );
}

export default SettingsPage;
