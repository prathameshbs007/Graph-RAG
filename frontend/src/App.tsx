import { useState } from "react";
import { UploadPanel } from "./components/UploadPanel";
import { QueryBar } from "./components/QueryBar";
import { AnswerCard } from "./components/AnswerCard";
import { GraphExplorer } from "./components/GraphExplorer";
import { ClearDBButton } from "./components/ClearDBButton";
import { UploadNotification } from "./components/UploadNotification";
import { UploadProvider } from "./contexts/UploadContext";
import { useQuery } from "./hooks/useQuery";

function AppContent() {
  const { executeQuery, data, loading, error } = useQuery();
  const [activeTab, setActiveTab] = useState<"search" | "upload" | "graph">(
    "search",
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 flex flex-col font-sans text-gray-900 overflow-x-hidden">
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 -left-4 w-72 h-72 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse"></div>
        <div className="absolute top-0 -right-4 w-72 h-72 bg-indigo-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" style={{ animationDelay: '2s' }}></div>
        <div className="absolute -bottom-8 left-20 w-72 h-72 bg-cyan-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" style={{ animationDelay: '4s' }}></div>
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* Premium Header */}
        <header className="sticky top-0 z-50 glass border-b border-white/10">
          <div className="px-8 py-4 flex justify-between items-center">
            {/* Logo Section */}
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur-lg opacity-75"></div>
                <div className="relative w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg">
                  <span className="text-white font-black text-xl">○</span>
                </div>
              </div>
              <div>
                <h1 className="text-3xl font-black tracking-tighter text-gradient">
                  ResearchOS
                </h1>
                <p className="text-xs font-semibold text-cyan-300 tracking-widest uppercase">
                  Knowledge Graph Intelligence
                </p>
              </div>
            </div>

            {/* Navigation */}
            <nav className="flex gap-2 items-center">
              {[
                { id: "search", label: "🔍 Search", icon: "🔍" },
                { id: "graph", label: "📊 Graph", icon: "📊" },
                { id: "upload", label: "📤 Ingest", icon: "📤" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-5 py-2.5 rounded-xl font-semibold transition-all duration-300 relative overflow-hidden group ${
                    activeTab === tab.id
                      ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/50"
                      : "text-gray-300 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <span className="relative z-10">{tab.label}</span>
                  {activeTab === tab.id && (
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-indigo-600 -z-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                  )}
                </button>
              ))}

              <div className="w-px h-8 bg-white/20 mx-2"></div>
              <ClearDBButton />
            </nav>
          </div>
        </header>

      <main className="flex-1 p-8 max-w-7xl mx-auto w-full">
        {activeTab === "search" && (
          <div className="flex flex-col gap-8 items-center max-w-4xl mx-auto">
            {/* Hero Section */}
            <div className="w-full text-center mb-8 space-y-3">
              <div className="inline-block">
                <span className="text-sm font-bold text-cyan-400 bg-cyan-400/10 px-4 py-2 rounded-full border border-cyan-400/30">
                  ✨ Powered by Knowledge Graphs
                </span>
              </div>
              <h2 className="text-5xl md:text-6xl font-black tracking-tighter">
                <span className="text-gradient">Intelligent Research</span>
                <br />
                <span className="text-white">at Your Fingertips</span>
              </h2>
              <p className="text-lg text-gray-400 max-w-2xl mx-auto">
                Explore documents, audio, and papers with AI-powered insights. Ask anything, get evidence-based answers.
              </p>
            </div>

            {/* Search Bar */}
            <QueryBar onSearch={(txt) => executeQuery(txt)} loading={loading} />

            {/* Error State */}
            {error && (
              <div className="w-full">
                <div className="glass-dark border border-red-500/30 p-4 rounded-xl">
                  <div className="flex gap-3">
                    <span className="text-2xl flex-shrink-0">⚠️</span>
                    <div>
                      <p className="text-red-300 font-semibold">Something went wrong</p>
                      <p className="text-sm text-red-200 mt-1">{error}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Results */}
            {data && !loading && (
              <div className="w-full">
                <AnswerCard data={data} />
              </div>
            )}

            {/* Empty State */}
            {!data && !loading && !error && (
              <div className="w-full mt-16 space-y-12">
                <div className="text-center space-y-3">
                  <p className="text-gray-400 text-sm uppercase tracking-widest font-semibold">Why ResearchOS?</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {[
                    {
                      icon: "📚",
                      title: "Multi-Modal Knowledge",
                      desc: "Analyze PDFs, audio transcripts, and papers simultaneously",
                      color: "from-blue-500 to-cyan-500"
                    },
                    {
                      icon: "🧠",
                      title: "Intelligent Analysis",
                      desc: "AI understands context and relationships across documents",
                      color: "from-indigo-500 to-purple-500"
                    },
                    {
                      icon: "⚡",
                      title: "Real-Time Insights",
                      desc: "Get answers with citations and visual evidence instantly",
                      color: "from-purple-500 to-pink-500"
                    },
                  ].map((item, idx) => (
                    <div
                      key={idx}
                      className="card-hover group relative overflow-hidden rounded-2xl p-8 glass-dark border border-white/10"
                    >
                      {/* Gradient Background */}
                      <div className={`absolute inset-0 opacity-0 group-hover:opacity-20 transition-opacity duration-300 bg-gradient-to-br ${item.color}`}></div>
                      
                      {/* Content */}
                      <div className="relative z-10">
                        <div className="text-4xl mb-4">{item.icon}</div>
                        <h3 className="text-xl font-bold text-white mb-2">{item.title}</h3>
                        <p className="text-gray-400 text-sm leading-relaxed">{item.desc}</p>
                      </div>

                      {/* Shine effect */}
                      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 shimmer-animation"></div>
                    </div>
                  ))}
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
      
      {/* Upload Notifications - visible across all tabs */}
      <UploadNotification />
    </div>
  );
}

function App() {
  return (
    <UploadProvider>
      <AppContent />
    </UploadProvider>
  );
}

export default App;
