import { useState } from 'react';
import { UploadPanel } from './components/UploadPanel';
import { QueryBar } from './components/QueryBar';
import { AnswerCard } from './components/AnswerCard';
import { GraphExplorer } from './components/GraphExplorer';
import { Header, type Tab } from './components/Header';
import { useQuery } from './hooks/useQuery';
import { useDarkMode } from './hooks/useDarkMode';

function App() {
  const { executeQuery, data, compareData, loading, error } = useQuery();
  const [activeTab, setActiveTab] = useState<Tab>('search');
  const [compareMode, setCompareMode] = useState(false);
  const { isDark, toggle } = useDarkMode();

  return (
    <div className="min-h-screen bg-surface flex flex-col text-text-default">
      <Header activeTab={activeTab} onTabChange={setActiveTab} isDark={isDark} onToggleDark={toggle} />

      <main className="flex-1 px-4 sm:px-8 py-8 max-w-7xl mx-auto w-full">
        {activeTab === 'search' && (
          <div className={`flex flex-col gap-8 items-center mx-auto mt-10 ${compareData ? 'max-w-6xl' : 'max-w-4xl'}`}>
            <div className="w-full max-w-4xl">
              <QueryBar
                onSearch={(txt) => executeQuery(txt, compareMode)}
                loading={loading}
                compareMode={compareMode}
                onCompareModeChange={setCompareMode}
              />
            </div>

            {error && <div className="text-red-500 bg-red-50 p-4 rounded-lg w-full border border-red-200">{error}</div>}

            {compareData && !loading && (
              <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">With Knowledge Graph</h3>
                  <AnswerCard data={compareData.with_graph} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Vector Search Only</h3>
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
            <GraphExplorer />
          </div>
        )}
      </main>
    </div>
  )
}

export default App;
