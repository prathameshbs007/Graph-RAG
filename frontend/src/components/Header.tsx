import { Moon, Network, Search, Sun, Upload } from 'lucide-react';

export type Tab = 'search' | 'upload' | 'graph';

const TABS: { id: Tab; label: string; icon: typeof Search }[] = [
    { id: 'search', label: 'Search', icon: Search },
    { id: 'graph', label: 'Graph Explorer', icon: Network },
    { id: 'upload', label: 'Ingest', icon: Upload },
];

export const Header = ({
    activeTab,
    onTabChange,
    isDark,
    onToggleDark,
}: {
    activeTab: Tab;
    onTabChange: (tab: Tab) => void;
    isDark: boolean;
    onToggleDark: () => void;
}) => {
    return (
        <header className="sticky top-0 z-20 bg-surface-raised/90 backdrop-blur-sm border-b border-border-default px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 shrink-0">
                <h1 className="text-lg font-semibold tracking-tight text-text-default">
                    Research<span className="text-accent-600">OS</span>
                </h1>
                <span className="hidden sm:inline text-xs font-medium text-text-muted bg-surface-hover px-2 py-0.5 rounded-full">
                    Graph RAG
                </span>
            </div>

            <nav className="flex items-center gap-1 bg-surface-hover rounded-lg p-1">
                {TABS.map(({ id, label, icon: Icon }) => (
                    <button
                        key={id}
                        type="button"
                        onClick={() => onTabChange(id)}
                        aria-current={activeTab === id ? 'page' : undefined}
                        className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-md text-sm font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 ${
                            activeTab === id
                                ? 'bg-surface-raised text-accent-700 dark:text-accent-300 shadow-xs'
                                : 'text-text-muted hover:text-text-default'
                        }`}
                    >
                        <Icon className="w-4 h-4" />
                        <span className="hidden sm:inline">{label}</span>
                    </button>
                ))}
            </nav>

            <button
                type="button"
                onClick={onToggleDark}
                aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                className="shrink-0 p-2 rounded-lg text-text-muted hover:text-text-default hover:bg-surface-hover transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500"
            >
                {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
        </header>
    );
};
