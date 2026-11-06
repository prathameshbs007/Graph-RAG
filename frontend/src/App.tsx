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
      {/* Background ambient radial gradients */}
      <div className="fixed inset-0 pointer-events-none bg-[radial-gradient(ellipse_80%_50%_at_50%_-10%,rgba(128,131,255,0.12),transparent_70%)] z-0"></div>

      {/* Global Header */}
      <header className="sticky top-0 w-full z-50 bg-surface-container-lowest/85 backdrop-blur-2xl border-b border-surface-container-highest/30">
        <div className="h-16 w-full px-4 md:px-8 flex items-center justify-between gap-4 max-w-7xl mx-auto">
          {/* Brand Logo & Version */}
          <div className="flex items-center gap-4 shrink-0">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-primary shadow-[0_0_12px_rgba(192,193,255,0.25)]">
                <span className="material-symbols-outlined text-[1.25rem]">hub</span>
              </div>
              <span className="font-bold text-lg text-on-surface tracking-tight font-sans">
                ResearchOS
              </span>
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface-container-highest text-tertiary tracking-wider uppercase">
                v2.4-agentic
              </span>
            </div>

            {/* Model / DB Status Indicators */}
            <div className="hidden xl:flex items-center gap-1.5">
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container-low font-mono text-[11px] text-on-surface-variant">
                <span className="w-1.5 h-1.5 rounded-full bg-secondary shadow-[0_0_8px_#4fdbc8] animate-pulse"></span>
                <span>Groq Llama-3.3</span>
              </div>
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container-low font-mono text-[11px] text-on-surface-variant">
                <span className="w-1.5 h-1.5 rounded-full bg-secondary-container shadow-[0_0_8px_#04b4a2]"></span>
                <span>Weaviate Hybrid</span>
              </div>
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container-low font-mono text-[11px] text-on-surface-variant">
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
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
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
            {systems.length > 0 && activeTab === "search" && (
              <select
                value={system}
                onChange={(e) => setSystem(e.target.value)}
                className="bg-surface-container-low border border-surface-container-highest/60 rounded-lg px-2.5 py-1 text-on-surface font-mono text-xs focus:outline-none hidden md:block"
              >
                {systems.map((s) => (
                  <option key={s.name} value={s.name} className="bg-surface-container-high text-on-surface">
                    {s.description || s.name}
                  </option>
                ))}
              </select>
            )}
            <ClearDBButton />
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="relative z-10 w-full max-w-7xl mx-auto px-4 md:px-8 py-6">
        {activeTab === "search" && (
          <div className="flex flex-col gap-6 max-w-5xl mx-auto">
            {/* Search Omnibar */}
            <QueryBar onSearch={(txt) => executeQuery(txt, system)} loading={loading} />

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

            {/* Results Component */}
            {data && !loading && <AnswerCard data={data} />}

            {/* Empty State Showcase */}
            {!data && !loading && !error && (
              <div className="w-full mt-6 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[
                    {
                      icon: "auto_stories",
                      title: "Cross-Modal Anchoring",
                      desc: "Aligns PDF chunks, visual flowchart figures, and audio timestamps into a unified representation.",
                      accent: "text-primary border-primary/20",
                    },
                    {
                      icon: "grain",
                      title: "Self-Pruning Memory",
                      desc: "Hebbian reinforcement dynamic synapses decay and auto-prune noisy or unhelpful relations.",
                      accent: "text-secondary border-secondary/20",
                    },
                    {
                      icon: "verified_user",
                      title: "NLI Claim Entailment",
                      desc: "Verifies extracted answer claims against cited premise vectors with formal confidence scores.",
                      accent: "text-tertiary border-tertiary/20",
                    },
                  ].map((item, idx) => (
                    <div
                      key={idx}
                      className={`p-5 rounded-xl bg-surface-container-low/70 border ${item.accent} backdrop-blur shadow-md flex flex-col justify-between`}
                    >
                      <div>
                        <span className="material-symbols-outlined text-[2rem] mb-2 block">
                          {item.icon}
                        </span>
                        <h4 className="font-semibold text-sm text-on-surface mb-1">{item.title}</h4>
                        <p className="text-xs text-on-surface-variant leading-relaxed">{item.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "graph" && <GraphExplorer />}

        {activeTab === "memory" && <MemoryPanel />}

        {activeTab === "upload" && <UploadPanel />}
      </main>

      {/* Global Background Upload Notifications */}
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
