/**
 * Settings Page
 * Central configuration hub for user preferences
 */
import { useState } from 'react';
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

  // Load saved settings
  const [settings, setSettings] = useState<SettingsState>(() => ({
    notifications: localStorage.getItem(STORAGE_KEY_NOTIFICATIONS) !== 'false',
    autoVerify: localStorage.getItem(STORAGE_KEY_AUTO_VERIFY) === 'true',
    compactView: localStorage.getItem(STORAGE_KEY_COMPACT_VIEW) === 'true',
  }));

  // Available languages
  const languages = [
    { code: 'vi', label: 'Tiếng Việt', flag: '🇻🇳' },
    { code: 'en', label: 'English', flag: '🇺🇸' },
  ];

  // Get current language
  const currentLang = localStorage.getItem('language') || 'vi';

  // Toggle setting
  const toggleSetting = (key: keyof SettingsState): void => {
    setSettings((prev) => {
      const newValue = !prev[key];
      const storageKey = `settings_${key === 'autoVerify' ? 'auto_verify' : key === 'compactView' ? 'compact_view' : key}`;
      localStorage.setItem(storageKey, String(newValue));

      toast.success(
        'Settings saved',
        key === 'notifications'
          ? `Notifications ${newValue ? 'enabled' : 'disabled'}`
          : key === 'autoVerify'
          ? `Auto-verify ${newValue ? 'enabled' : 'disabled'}`
          : `Compact view ${newValue ? 'enabled' : 'disabled'}`
      );

      return { ...prev, [key]: newValue };
    });
  };

  // Change language
  const changeLanguage = (langCode: string): void => {
    localStorage.setItem('language', langCode);
    // Force page reload to apply i18n changes
    window.location.reload();
  };

  return (
    <div className="container-page py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-12 h-12 rounded-xl bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
          <Settings className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Settings
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            Customize your experience
          </p>
        </div>
      </div>

      <div className="max-w-2xl space-y-6">
        {/* Appearance Section */}
        <section className="card">
          <div className="flex items-center gap-2 mb-4">
            <Palette className="w-5 h-5 text-slate-500" />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Appearance
            </h2>
          </div>

          <div className="space-y-4">
            {/* Theme Selection */}
            <div>
              <label className="input-label">Theme</label>
              <div className="mt-2">
                <ThemeToggle showLabel />
              </div>
              <p className="text-xs text-slate-500 mt-2">
                Choose your preferred color scheme
              </p>
            </div>
          </div>
        </section>

        {/* Language Section */}
        <section className="card">
          <div className="flex items-center gap-2 mb-4">
            <Globe className="w-5 h-5 text-slate-500" />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Language
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
                <span className="text-2xl">{lang.flag}</span>
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
        </section>

        {/* Notifications Section */}
        <section className="card">
          <div className="flex items-center gap-2 mb-4">
            <Bell className="w-5 h-5 text-slate-500" />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Notifications
            </h2>
          </div>

          <div className="space-y-4">
            <ToggleSetting
              label="Enable Notifications"
              description="Show toast notifications for actions"
              checked={settings.notifications}
              onChange={() => toggleSetting('notifications')}
            />

            <ToggleSetting
              label="Auto-verify on Upload"
              description="Automatically verify citations when uploading"
              checked={settings.autoVerify}
              onChange={() => toggleSetting('autoVerify')}
            />

            <ToggleSetting
              label="Compact View"
              description="Show more content in less space"
              checked={settings.compactView}
              onChange={() => toggleSetting('compactView')}
            />
          </div>
        </section>

        {/* About Section */}
        <section className="card">
          <div className="flex items-center gap-2 mb-4">
            <Info className="w-5 h-5 text-slate-500" />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              About
            </h2>
          </div>

          <div className="space-y-3">
            <InfoRow label="Version" value="1.11.0" />
            <InfoRow label="Build Date" value={new Date().toLocaleDateString()} />

            <div className="pt-3 border-t border-slate-200 dark:border-slate-700">
              <a
                href="https://github.com/iannwendy/essay-integrity-checker"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-indigo-600 dark:text-indigo-400 hover:underline"
              >
                View Source Code
                <ChevronRight className="w-4 h-4" />
              </a>
            </div>
          </div>
        </section>

        {/* Danger Zone */}
        <section className="card border-red-200 dark:border-red-900/50">
          <h2 className="text-lg font-semibold text-red-700 dark:text-red-400 mb-4">
            Danger Zone
          </h2>

          <div className="space-y-3">
            <button
              onClick={() => {
                if (confirm('Are you sure you want to clear the cache? This will reset your preferences.')) {
                  localStorage.removeItem('theme');
                  localStorage.removeItem('language');
                  toast.success('Cache cleared successfully');
                }
              }}
              className="w-full flex items-center justify-between p-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            >
              <span className="text-slate-700 dark:text-slate-300">
                Clear Local Cache
              </span>
              <ChevronRight className="w-5 h-5 text-slate-400" />
            </button>
          </div>
        </section>
      </div>
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
      <button
        role="switch"
        aria-checked={checked}
        onClick={onChange}
        className={`
          relative inline-flex h-6 w-11 items-center rounded-full transition-colors
          ${checked ? 'bg-indigo-600' : 'bg-slate-200 dark:bg-slate-700'}
        `}
      >
        <span
          className={`
            inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform
            ${checked ? 'translate-x-6' : 'translate-x-1'}
          `}
        />
      </button>
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
      <span className="font-medium text-slate-900 dark:text-slate-100">{value}</span>
    </div>
  );
}

export default SettingsPage;
