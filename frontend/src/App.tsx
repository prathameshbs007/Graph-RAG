import { useState } from "react";
import { UploadPanel } from "./components/UploadPanel";
import { QueryBar } from "./components/QueryBar";
import { AnswerCard } from "./components/AnswerCard";
import { GraphExplorer } from "./components/GraphExplorer";
import { ClearDBButton } from "./components/ClearDBButton";
import { useQuery } from "./hooks/useQuery";

function App() {
  const { executeQuery, data, loading, error } = useQuery();
  const [activeTab, setActiveTab] = useState<"search" | "upload" | "graph">(
    "search",
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex flex-col font-sans text-gray-900">
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200 px-8 py-4 flex justify-between items-center shadow-md">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">R</span>
          </div>
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight bg-gradient-to-r from-blue-900 to-indigo-900 bg-clip-text text-transparent">
              ResearchOS
            </h1>
            <span className="text-xs font-semibold text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded-full">
              Graph RAG v2.0
            </span>
          </div>
        </div>
        <nav className="flex gap-3 items-center">
          <button
            onClick={() => setActiveTab("search")}
            className={`px-4 py-2.5 rounded-lg font-medium transition-all duration-200 ${activeTab === "search" ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-200" : "text-gray-600 hover:bg-gray-100"}`}
          >
            🔍 Search
          </button>
          <button
            onClick={() => setActiveTab("graph")}
            className={`px-4 py-2.5 rounded-lg font-medium transition-all duration-200 ${activeTab === "graph" ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-200" : "text-gray-600 hover:bg-gray-100"}`}
          >
            📊 Graph
          </button>
          <button
            onClick={() => setActiveTab("upload")}
            className={`px-4 py-2.5 rounded-lg font-medium transition-all duration-200 ${activeTab === "upload" ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-200" : "text-gray-600 hover:bg-gray-100"}`}
          >
            📤 Ingest
          </button>
          <div className="w-px h-6 bg-gray-200"></div>
          <ClearDBButton />
        </nav>
      </header>

      <main className="flex-1 p-8 max-w-7xl mx-auto w-full">
        {activeTab === "search" && (
          <div className="flex flex-col gap-8 items-center max-w-4xl mx-auto">
            <div className="w-full text-center mb-4">
              <h2 className="text-4xl font-bold bg-gradient-to-r from-blue-900 to-indigo-900 bg-clip-text text-transparent mb-2">
                Intelligent Research Search
              </h2>
              <p className="text-gray-600">
                Ask questions about your documents, papers, and audio content
              </p>
            </div>
            <QueryBar onSearch={(txt) => executeQuery(txt)} loading={loading} />

            {error && (
              <div className="w-full">
                <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-lg">
                  <div className="flex">
                    <div className="flex-shrink-0">
                      <span className="text-xl">⚠️</span>
                    </div>
                    <div className="ml-3">
                      <p className="text-sm text-red-700 font-medium">
                        {error}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {data && !loading && (
              <div className="w-full">
                <AnswerCard data={data} />
              </div>
            )}

            {!data && !loading && !error && (
              <div className="w-full mt-12 text-center">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                    <div className="text-3xl mb-3">📚</div>
                    <h3 className="font-semibold text-gray-900 mb-2">
                      Upload Documents
                    </h3>
                    <p className="text-sm text-gray-600">
                      Add PDFs, audio files, and papers
                    </p>
                  </div>
                  <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                    <div className="text-3xl mb-3">🔍</div>
                    <h3 className="font-semibold text-gray-900 mb-2">
                      Smart Search
                    </h3>
                    <p className="text-sm text-gray-600">
                      Ask natural language questions
                    </p>
                  </div>
                  <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                    <div className="text-3xl mb-3">📊</div>
                    <h3 className="font-semibold text-gray-900 mb-2">
                      Graph Analysis
                    </h3>
                    <p className="text-sm text-gray-600">
                      Visualize connections and relationships
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "upload" && (
          <div className="mt-4">
            <UploadPanel />
          </div>
        )}

        {activeTab === "graph" && (
          <div className="mt-4">
            <GraphExplorer />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
