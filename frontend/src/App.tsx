import React, { useState } from 'react';
import { UploadPanel } from './components/UploadPanel';
import { QueryBar } from './components/QueryBar';
import { AnswerCard } from './components/AnswerCard';
import { GraphExplorer } from './components/GraphExplorer';
import { useQuery } from './hooks/useQuery';

function App() {
  const { executeQuery, data, loading, error } = useQuery();
  const [activeTab, setActiveTab] = useState<'search' | 'upload' | 'graph'>('search');

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans text-gray-900">
      <header className="bg-white border-b px-8 py-4 flex justify-between items-center shadow-sm">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-blue-900 inline-block mr-3">ResearchOS</h1>
          <span className="text-sm font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded">Graph RAG</span>
        </div>
        <nav className="flex gap-2">
          <button
            onClick={() => setActiveTab('search')}
            className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'search' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >Search</button>
          <button
            onClick={() => setActiveTab('graph')}
            className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'graph' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >Graph Explorer</button>
          <button
            onClick={() => setActiveTab('upload')}
            className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'upload' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >Ingest</button>
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
