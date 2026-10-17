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
 * Renders an active underline via a 0.5px bottom bar; citations and references
 * show small count badges.
 */
export function EssayTabNav({
  activeTab,
  onChange,
  citationsCount,
  referencesCount,
}: EssayTabNavProps) {
  return (
    <div className="border-b border-slate-200 dark:border-slate-700">
      <nav className="flex gap-6" aria-label="Report sections">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => onChange(tab)}
            className={`relative pb-3 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'text-indigo-600 dark:text-indigo-400'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            {tab === 'citations' && (
              <span className="ml-2 text-xs bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded-full">
                {citationsCount}
              </span>
            )}
            {tab === 'references' && (
              <span className="ml-2 text-xs bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded-full">
                {referencesCount}
              </span>
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
