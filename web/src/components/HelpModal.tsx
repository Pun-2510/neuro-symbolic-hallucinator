import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  X,
  Keyboard,
  Upload,
  FileText,
  AlertTriangle,
  CheckCircle,
  BookOpen,
} from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Card } from '@/components/ui/card';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function HelpModal({ isOpen, onClose }: HelpModalProps) {
  const { t } = useTranslation();
  const [activeSection, setActiveSection] = useState<string>('overview');

  // Handle Escape key to close modal
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sections = [
    { id: 'overview', label: t('help.overview'), icon: BookOpen },
    { id: 'getting-started', label: t('help.gettingStarted'), icon: Upload },
    { id: 'verdicts', label: t('help.understandingVerdicts'), icon: AlertTriangle },
    { id: 'keyboard', label: t('help.keyboardShortcuts'), icon: Keyboard },
  ];

  const shortcuts = [
    { keys: ['Ctrl', 'U'], description: t('help.shortcutUpload') },
    { keys: ['Ctrl', '/'], description: t('help.shortcutHelp') },
    { keys: ['Esc'], description: t('help.shortcutClose') },
    { keys: ['Ctrl', 'D'], description: t('help.shortcutDark') },
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={t('help.title')}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-2xl w-full max-w-4xl max-h-[85vh] overflow-hidden flex animate-scale-in">
        {/* Sidebar */}
        <div className="w-64 shrink-0 bg-slate-50/90 dark:bg-slate-800/70 border-r border-slate-200 dark:border-slate-700 p-4">
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-display font-semibold text-slate-900 dark:text-white">
              {t('help.title')}
            </h2>
            <button
              onClick={onClose}
              aria-label="Close"
              className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            >
              <X className="h-4 w-4 text-slate-500" />
            </button>
          </div>

          <nav className="space-y-1">
            {sections.map((section) => {
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm text-left whitespace-nowrap transition-colors ${
                    activeSection === section.id
                      ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/70'
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{section.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeSection === 'overview' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-3">
                  {t('help.welcomeTitle')}
                </h3>
                <p className="text-slate-600 dark:text-slate-400">
                  {t('help.welcomeDesc')}
                </p>
              </div>

              <Alert variant="info">
                <AlertTriangle className="h-5 w-5" />
                <AlertTitle>{t('help.decisionSupportTitle')}</AlertTitle>
                <AlertDescription>{t('help.decisionSupportDesc')}</AlertDescription>
              </Alert>

              <div>
                <h4 className="font-semibold text-slate-900 dark:text-white mb-2">
                  {t('help.howItWorksTitle')}
                </h4>
                <ol className="space-y-2 text-slate-600 dark:text-slate-400 list-decimal list-inside">
                  <li>{t('help.step1')}</li>
                  <li>{t('help.step2')}</li>
                  <li>{t('help.step3')}</li>
                  <li>{t('help.step4')}</li>
                  <li>{t('help.step5')}</li>
                </ol>
              </div>
            </div>
          )}

          {activeSection === 'getting-started' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                {t('help.gettingStarted')}
              </h3>

              <div className="space-y-3">
                {[1, 2, 3, 4].map((num) => (
                  <Card
                    key={num}
                    className="flex items-start gap-4 p-4 bg-slate-50/70 dark:bg-slate-800/50"
                  >
                    <div className="flex items-center justify-center w-8 h-8 bg-indigo-600 text-white rounded-full text-sm font-bold shrink-0">
                      {num}
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-900 dark:text-white">
                        {t(`help.gs${num}Title`)}
                      </h4>
                      <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                        {t(`help.gs${num}Desc`)}
                      </p>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {activeSection === 'verdicts' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                {t('help.understandingVerdicts')}
              </h3>

              <div className="space-y-3.5">
                <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-xl border border-emerald-200 dark:border-emerald-800">
                  <div className="flex items-center gap-2 mb-1.5">
                    <CheckCircle className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                    <h4 className="font-mono font-semibold text-emerald-900 dark:text-emerald-300">
                      VERIFIED
                    </h4>
                  </div>
                  <p className="text-sm text-emerald-700 dark:text-emerald-400">
                    {t('verdict.verifiedDesc')}
                  </p>
                </div>

                <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-xl border border-amber-200 dark:border-amber-800">
                  <div className="flex items-center gap-2 mb-1.5">
                    <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                    <h4 className="font-mono font-semibold text-amber-900 dark:text-amber-300">
                      METADATA_ERROR
                    </h4>
                  </div>
                  <p className="text-sm text-amber-700 dark:text-amber-400">
                    {t('verdict.metadataErrorDesc')}
                  </p>
                </div>

                <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800">
                  <div className="flex items-center gap-2 mb-1.5">
                    <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                    <h4 className="font-mono font-semibold text-red-900 dark:text-red-300">
                      SUSPECTED_HALLUCINATION
                    </h4>
                  </div>
                  <p className="text-sm text-red-700 dark:text-red-400">
                    {t('verdict.suspectedHallucinationDesc')}
                  </p>
                </div>

                <div className="p-4 bg-slate-100 dark:bg-slate-800 rounded-xl border border-slate-300 dark:border-slate-700">
                  <div className="flex items-center gap-2 mb-1.5">
                    <FileText className="h-5 w-5 text-slate-600 dark:text-slate-400" />
                    <h4 className="font-mono font-semibold text-slate-900 dark:text-slate-300">
                      UNRESOLVED
                    </h4>
                  </div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    {t('verdict.unresolvedDesc')}
                  </p>
                </div>

                <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-xl border border-purple-200 dark:border-purple-800">
                  <div className="flex items-center gap-2 mb-1.5">
                    <FileText className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                    <h4 className="font-mono font-semibold text-purple-900 dark:text-purple-300">
                      RESOURCE
                    </h4>
                  </div>
                  <p className="text-sm text-purple-700 dark:text-purple-400">
                    {t('verdict.resourceDesc')}
                  </p>
                </div>
              </div>

              <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-4 mt-6 border border-slate-200 dark:border-slate-700">
                <h4 className="font-semibold text-slate-900 dark:text-white mb-2">
                  {t('help.cisTitle')}
                </h4>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  {t('help.cisDesc')}
                </p>
              </div>
            </div>
          )}

          {activeSection === 'keyboard' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                {t('help.keyboardShortcuts')}
              </h3>

              <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700">
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                  {t('help.shortcutsIntro')}
                </p>

                <div className="space-y-3">
                  {shortcuts.map((shortcut, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between py-1"
                    >
                      <span className="text-sm text-slate-700 dark:text-slate-300">
                        {shortcut.description}
                      </span>
                      <div className="flex items-center gap-1">
                        {shortcut.keys.map((key, keyIndex) => (
                          <span key={keyIndex}>
                            <kbd className="px-2 py-1 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-md text-xs font-mono text-slate-700 dark:text-slate-200 shadow-sm">
                              {key}
                            </kbd>
                            {keyIndex < shortcut.keys.length - 1 && (
                              <span className="text-slate-400 mx-1">+</span>
                            )}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
