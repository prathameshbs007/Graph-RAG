import React, { useState } from "react";

interface QueryBarProps {
  onSearch: (txt: string) => void;
  loading: boolean;
}

const SEED_QUERIES = [
  { text: "Table 1 indoor navigation sectors", color: "hover:text-secondary hover:shadow-[0_0_10px_rgba(79,219,200,0.15)]" },
  { text: "Figure 1 ARKit SLAM flowchart", color: "hover:text-primary hover:shadow-[0_0_10px_rgba(192,193,255,0.15)]" },
  { text: "What is Optimized Feature Experience (OFE)?", color: "hover:text-tertiary hover:shadow-[0_0_10px_rgba(221,183,255,0.15)]" },
  { text: "NavMesh A* topological latency", color: "hover:text-secondary-fixed hover:shadow-[0_0_10px_rgba(113,248,228,0.15)]" },
];

export const QueryBar: React.FC<QueryBarProps> = ({ onSearch, loading }) => {
  const [text, setText] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim() && !loading) {
      onSearch(text.trim());
    }
  };

  const handleSelectSeed = (seed: string) => {
    setText(seed);
    onSearch(seed);
  };

  return (
    <div className="w-full space-y-2">
      <form onSubmit={handleSubmit} className="relative w-full">
        <div className="relative bg-surface-container-low/90 backdrop-blur-2xl rounded-full p-2 pl-4 shadow-[0_8px_32px_-4px_rgba(0,0,0,0.5),0_0_24px_rgba(128,131,255,0.15)] flex flex-wrap md:flex-nowrap items-center gap-2 group focus-within:shadow-[0_0_36px_rgba(79,219,200,0.22)] transition-all border border-surface-container-high/60">
          <div className="flex items-center gap-2 text-primary shrink-0 pl-1">
            <span className="material-symbols-outlined text-[1.4rem] animate-pulse">
              travel_explore
            </span>
          </div>

          <div className="flex-1 min-w-[240px] relative">
            <input
              type="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Ask anything across papers, figures, and audio transcripts..."
              className="w-full bg-transparent text-on-surface font-body-lg text-sm sm:text-base placeholder:text-outline focus:outline-none tracking-tight pr-14"
              disabled={loading}
            />
            <span className="absolute right-2 top-1/2 -translate-y-1/2 font-mono text-[10px] text-outline px-1.5 py-0.5 rounded bg-surface-container-high/80 hidden sm:inline-block">
              ⌘K
            </span>
          </div>

          <div className="flex items-center gap-1.5 shrink-0 pr-1 ml-auto">
            <button
              type="submit"
              disabled={loading || !text.trim()}
              className="flex items-center justify-center gap-1.5 px-4 py-2 rounded-full bg-primary text-on-primary font-semibold text-xs sm:text-sm shadow-[0_0_18px_rgba(192,193,255,0.35)] hover:brightness-110 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined text-[1.125rem] animate-spin">
                    sync
                  </span>
                  <span>Executing...</span>
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[1.125rem]">bolt</span>
                  <span>Execute</span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Suggested Probes & Seed Vectors */}
      <div className="flex items-center gap-1.5 overflow-x-auto py-1 text-on-surface-variant font-mono text-xs no-scrollbar">
        <span className="text-outline uppercase tracking-wider text-[10px] mr-1 shrink-0 flex items-center gap-1">
          <span className="material-symbols-outlined text-[0.875rem]">auto_fix_high</span> Seed Vectors:
        </span>
        {SEED_QUERIES.map((q, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleSelectSeed(q.text)}
            className={`px-2.5 py-1 rounded-full bg-surface-container-low hover:bg-surface-container text-on-surface-variant transition-all whitespace-nowrap shrink-0 text-[11px] border border-surface-container-high/40 ${q.color}`}
          >
            {q.text}
          </button>
        ))}
      </div>
    </div>
  );
};
