import { useEffect, useState } from "react";
import axios from "axios";
import { UploadPanel } from "./components/UploadPanel";
import { QueryBar } from "./components/QueryBar";
import { AnswerCard } from "./components/AnswerCard";
import { GraphExplorer } from "./components/GraphExplorer";
import { MemoryPanel } from "./components/MemoryPanel";
import { ClearDBButton } from "./components/ClearDBButton";
import { UploadNotification } from "./components/UploadNotification";
import { UploadProvider } from "./contexts/UploadContext";
import { useQuery } from "./hooks/useQuery";
import { API } from "./api";
import type { SystemInfo } from "./types";

type Tab = "search" | "graph" | "memory" | "upload";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "search", label: "Search & QA", icon: "travel_explore" },
  { id: "graph", label: "Graph Explorer", icon: "hub" },
  { id: "memory", label: "Agentic Memory", icon: "psychology" },
  { id: "upload", label: "Ingestion Studio", icon: "publish" },
];

function AppContent() {
  const { executeQuery, data, loading, error } = useQuery();
  const [activeTab, setActiveTab] = useState<Tab>("search");
  const [systems, setSystems] = useState<SystemInfo[]>([]);
  const [system, setSystem] = useState("full");

  useEffect(() => {
    axios
      .get<{ systems: SystemInfo[] }>(`${API}/query/systems`)
      .then((r) => setSystems(r.data.systems))
      .catch(() => setSystems([]));
  }, []);

  return (
    <div className="bg-surface font-sans text-on-surface min-h-screen relative overflow-x-hidden selection:bg-primary selection:text-on-primary">
      {/* Background ambient radial glow */}
      <div className="fixed inset-0 pointer-events-none bg-[radial-gradient(ellipse_80%_50%_at_50%_-10%,rgba(128,131,255,0.12),transparent_70%)] z-0"></div>

      {/* Global Header */}
      <header className="sticky top-0 w-full z-50 bg-surface-container-lowest/85 backdrop-blur-2xl border-b border-surface-container-highest/30">
        <div className="h-16 w-full px-4 md:px-8 flex items-center justify-between gap-4 max-w-7xl mx-auto">
          {/* Brand Logo & Version */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-primary shadow-[0_0_12px_rgba(192,193,255,0.25)] border border-surface-container-highest/50">
              <span className="material-symbols-outlined text-[1.25rem]">hub</span>
            </div>
            <span className="font-bold text-lg text-on-surface tracking-tight font-sans">
              ResearchOS
            </span>
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface-container-highest text-tertiary tracking-wider uppercase font-semibold">
              v2.4-agentic
            </span>

            {/* Model & DB Status Badges */}
            <div className="hidden xl:flex items-center gap-1.5 ml-3">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container-low font-mono text-[11px] text-on-surface-variant border border-surface-container-highest/40">
                <span className="w-1.5 h-1.5 rounded-full bg-secondary shadow-[0_0_8px_#4fdbc8] animate-pulse"></span>
                <span>Groq Llama-3.3</span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container-low font-mono text-[11px] text-on-surface-variant border border-surface-container-highest/40">
                <span className="w-1.5 h-1.5 rounded-full bg-secondary-container shadow-[0_0_8px_#04b4a2]"></span>
                <span>Weaviate Hybrid</span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container-low font-mono text-[11px] text-on-surface-variant border border-surface-container-highest/40">
                <span className="w-1.5 h-1.5 rounded-full bg-primary-container shadow-[0_0_8px_#8083ff]"></span>
                <span>Neo4j Bolt</span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center p-1 rounded-xl bg-surface-container-lowest/80 border border-surface-container-highest/40 gap-1">
            {TABS.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  type="button"
                  className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? "bg-surface-container-high text-primary shadow-[0_0_10px_rgba(128,131,255,0.2)] border border-primary/30"
                      : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container/60"
                  }`}
                >
                  <span className="material-symbols-outlined text-[1rem]">{tab.icon}</span>
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Right Header Utility Controls */}
          <div className="flex items-center gap-2 shrink-0">
            <ClearDBButton />
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="relative z-10 w-full max-w-7xl mx-auto px-4 md:px-8 py-6">
        {activeTab === "search" && (
          <div className="flex flex-col gap-6 w-full">
            {/* Search Omnibar Hero */}
            <QueryBar
              onSearch={(txt) => executeQuery(txt, system)}
              loading={loading}
              systems={systems}
              selectedSystem={system}
              onSelectSystem={setSystem}
            />

            {/* Error Banner */}
            {error && (
              <div className="p-4 rounded-xl bg-error-container/20 border border-error/40 text-error flex items-start gap-2.5 text-xs font-mono">
                <span className="material-symbols-outlined text-[1.25rem]">error</span>
                <div>
                  <p className="font-semibold">Query Execution Failed</p>
                  <p className="mt-0.5 text-error/90">{error}</p>
                </div>
              </div>
            )}

            {/* Answer & Evidence Synthesis */}
            {data && !loading && <AnswerCard data={data} />}

            {/* Clean Hero State when no query run yet */}
            {!data && !loading && !error && (
              <div className="w-full mt-4 p-8 rounded-2xl bg-surface-container-low/70 border border-surface-container-highest/30 backdrop-blur-xl relative overflow-hidden shadow-lg">
                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent"></div>
                <div className="max-w-2xl mx-auto text-center space-y-3">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary font-mono text-xs font-semibold">
                    <span className="material-symbols-outlined text-[0.875rem]">hub</span>
                    Cross-Modal Knowledge Engine
                  </div>
                  <h2 className="text-2xl md:text-3xl font-bold text-on-surface tracking-tight">
                    Evidence-Based Research Intelligence
                  </h2>
                  <p className="text-xs md:text-sm text-on-surface-variant leading-relaxed">
                    Query across arXiv preprints, extracted architectural flowcharts, and symposium audio. Every claim is strictly grounded in retrieved evidence chunks and audited via Natural Language Inference.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "graph" && <GraphExplorer />}

        {activeTab === "memory" && <MemoryPanel />}

        {activeTab === "upload" && <UploadPanel />}
      </main>

      {/* Background Upload Notifications */}
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
