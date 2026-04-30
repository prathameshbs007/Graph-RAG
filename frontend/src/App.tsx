import { useState } from 'react';
import { UploadPanel } from './components/UploadPanel';
import { QueryBar } from './components/QueryBar';
import { AnswerCard } from './components/AnswerCard';
import { GraphExplorer } from './components/GraphExplorer';
import { useQuery } from './hooks/useQuery';

function App() {
  const { executeQuery, data, loading, error } = useQuery();
  const [activeTab, setActiveTab] = useState<'search' | 'upload' | 'graph'>('search');
  const [isClearing, setIsClearing] = useState(false);
  const [clearMessage, setClearMessage] = useState('');

  const handleClearDatabase = async () => {
    if (!confirm('⚠️ Are you sure you want to clear all databases? This action cannot be undone.\n\nAll ingested PDFs, figures, audio, and graph nodes will be permanently deleted.')) {
      return;
    }

    setIsClearing(true);
    setClearMessage('');
    try {
      const response = await fetch('http://localhost:8054/admin/clear-db', {
        method: 'POST'
      });
      const result = await response.json();
      setClearMessage(`✓ ${result.message || 'Databases cleared successfully!'}`);
      setTimeout(() => setClearMessage(''), 3000);
    } catch (error) {
      setClearMessage('✗ Error clearing databases. Check console.');
      console.error('Clear DB error:', error);
    } finally {
      setIsClearing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex flex-col font-sans text-gray-900">
      <header className="bg-gradient-to-r from-blue-600 to-indigo-600 border-b border-blue-500/20 px-8 py-5 flex justify-between items-center shadow-lg backdrop-blur-sm">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white inline-block mr-3 drop-shadow-lg">ResearchOS</h1>
          <span className="text-sm font-semibold text-blue-100 bg-blue-500/20 px-3 py-1 rounded-full backdrop-blur-sm border border-blue-400/30">Graph RAG</span>
        </div>
        <nav className="flex gap-2 items-center">
          <button
            onClick={() => setActiveTab('search')}
            className={`px-5 py-2 rounded-lg font-semibold transition-all duration-200 ${activeTab === 'search' ? 'bg-white text-blue-600 shadow-lg' : 'text-blue-100 hover:bg-blue-500/20'}`}
          >Search</button>
          <button
            onClick={() => setActiveTab('graph')}
            className={`px-5 py-2 rounded-lg font-semibold transition-all duration-200 ${activeTab === 'graph' ? 'bg-white text-blue-600 shadow-lg' : 'text-blue-100 hover:bg-blue-500/20'}`}
          >Graph Explorer</button>
          <button
            onClick={() => setActiveTab('upload')}
            className={`px-5 py-2 rounded-lg font-semibold transition-all duration-200 ${activeTab === 'upload' ? 'bg-white text-blue-600 shadow-lg' : 'text-blue-100 hover:bg-blue-500/20'}`}
          >Ingest</button>
          
          {clearMessage && (
            <div className="text-sm font-medium px-3 py-1 rounded-lg bg-green-500/20 text-green-200 border border-green-500/30">
              {clearMessage}
            </div>
          )}
          
          <button
            onClick={handleClearDatabase}
            disabled={isClearing}
            className="ml-4 px-4 py-2 rounded-lg font-semibold bg-red-500/20 text-red-200 border border-red-500/30 hover:bg-red-500/30 transition-all duration-200 disabled:opacity-50 flex items-center gap-2"
            title="Clear all databases (Weaviate, Neo4j, figures)"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            {isClearing ? 'Clearing...' : 'Clear DB'}
          </button>
        </nav>
      </header>

      <main className="flex-1 p-8 max-w-7xl mx-auto w-full">
        {activeTab === 'search' && (
          <div className="flex flex-col gap-8 items-center max-w-4xl mx-auto mt-10">
            <QueryBar onSearch={(txt) => executeQuery(txt)} loading={loading} />

            {error && <div className="text-red-500 bg-red-50 p-4 rounded-lg w-full border border-red-200">{error}</div>}

            {data && !loading && (
              <div className="w-full">
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
