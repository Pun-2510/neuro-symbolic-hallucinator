import { useTranslation } from 'react-i18next';
import { Badge } from '@/components/ui/badge';

export type EssayTab = 'overview' | 'citations' | 'references';

interface EssayTabNavProps {
  activeTab: EssayTab;
  onChange: (tab: EssayTab) => void;
  citationsCount: number;
  referencesCount: number;
}

const TABS: EssayTab[] = ['overview', 'citations', 'references'];

/**
 * Underlined tab navigation for the Essay report page.
 */
export function EssayTabNav({
  activeTab,
  onChange,
  citationsCount,
  referencesCount,
}: EssayTabNavProps) {
  const { t } = useTranslation();

  const tabLabels: Record<EssayTab, string> = {
    overview: t('essay.overviewTab'),
    citations: t('essay.citationsTab'),
    references: t('essay.referencesTab'),
  };

  return (
    <div className="border-b border-slate-200 dark:border-slate-800">
      <nav className="flex gap-6" aria-label="Report sections">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => onChange(tab)}
            className={`relative pb-3 text-sm font-semibold transition-colors flex items-center gap-2 ${
              activeTab === tab
                ? 'text-indigo-600 dark:text-indigo-400'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            <span>{tabLabels[tab]}</span>
            {tab === 'citations' && (
              <Badge variant="secondary" className="font-mono text-xs px-2 py-0">
                {citationsCount}
              </Badge>
            )}
            {tab === 'references' && (
              <Badge variant="secondary" className="font-mono text-xs px-2 py-0">
                {referencesCount}
              </Badge>
            )}
            {activeTab === tab && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-600 dark:bg-indigo-400 rounded-full" />
            )}
          </button>
        ))}
      </nav>
    </div>
  );
}
