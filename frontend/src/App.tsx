import { useState } from 'react';
import { UploadPanel } from './components/UploadPanel';
import { QueryBar } from './components/QueryBar';
import { AnswerCard } from './components/AnswerCard';
import { AnswerSkeleton } from './components/AnswerSkeleton';
import { SearchHero } from './components/SearchHero';
import { GraphExplorer } from './components/GraphExplorer';
import { Header, type Tab } from './components/Header';
import { useQuery } from './hooks/useQuery';
import { useDarkMode } from './hooks/useDarkMode';

function App() {
  const { executeQuery, data, compareData, loading, error } = useQuery();
  const [activeTab, setActiveTab] = useState<Tab>('search');
  const [compareMode, setCompareMode] = useState(false);
  const [queryText, setQueryText] = useState('');
  const { isDark, toggle } = useDarkMode();

  const hasResults = data !== null || compareData !== null;

  return (
    <div className="min-h-screen bg-surface flex flex-col text-text-default">
      <Header activeTab={activeTab} onTabChange={setActiveTab} isDark={isDark} onToggleDark={toggle} />

      <main className="flex-1 px-4 sm:px-8 py-8 max-w-7xl mx-auto w-full">
        {activeTab === 'search' && (
          <div className={`flex flex-col gap-8 items-center mx-auto mt-4 sm:mt-10 ${compareData ? 'max-w-6xl' : 'max-w-4xl'}`}>
            <div className="w-full max-w-4xl">
              <QueryBar
                value={queryText}
                onChange={setQueryText}
                onSearch={(txt) => executeQuery(txt, compareMode)}
                loading={loading}
                compareMode={compareMode}
                onCompareModeChange={setCompareMode}
              />
            </div>

            {error && (
              <div className="text-red-600 dark:text-red-300 bg-red-50 dark:bg-red-950 p-4 rounded-lg w-full max-w-4xl border border-red-200 dark:border-red-900">
                {error}
              </div>
            )}

            {!hasResults && !loading && !error && (
              <SearchHero onPick={setQueryText} />
            )}

            {loading && (
              compareMode ? (
                <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-6">
                  <AnswerSkeleton />
                  <AnswerSkeleton />
                </div>
              ) : (
                <div className="w-full max-w-4xl">
                  <AnswerSkeleton />
                </div>
              )
            )}

            {compareData && !loading && (
              <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-2">With Knowledge Graph</h3>
                  <AnswerCard data={compareData.with_graph} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-2">Vector Search Only</h3>
                  <AnswerCard data={compareData.without_graph} />
                </div>
              </div>
            )}

            {data && !loading && (
              <div className="w-full max-w-4xl">
                <AnswerCard data={data} />
              </div>
            )}
          </div>
        )}

        {activeTab === 'upload' && (
          <div className="mt-10">
            <UploadPanel />
          </div>
        )}

        {activeTab === 'graph' && (
          <div className="mt-4">
            <GraphExplorer isDark={isDark} />
          </div>
        )}
      </main>
    </div>
  )
}

export default App;
