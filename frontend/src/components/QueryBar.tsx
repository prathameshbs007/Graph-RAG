import React, { useState } from "react";
import type { SystemInfo } from "../types";

interface QueryBarProps {
  onSearch: (txt: string) => void;
  loading: boolean;
  systems?: SystemInfo[];
  selectedSystem?: string;
  onSelectSystem?: (system: string) => void;
}

const SEED_QUERIES = [
  { text: "Table 1 indoor navigation sectors", tag: "Table 1", color: "hover:text-secondary hover:border-secondary/40" },
  { text: "Figure 1 ARKit SLAM flowchart", tag: "Fig 1", color: "hover:text-primary hover:border-primary/40" },
  { text: "What is Optimized Feature Experience (OFE)?", tag: "Concept", color: "hover:text-tertiary hover:border-tertiary/40" },
  { text: "NavMesh A* topological latency", tag: "Pathfinding", color: "hover:text-secondary-fixed hover:border-secondary-fixed/40" },
];

export const QueryBar: React.FC<QueryBarProps> = ({
  onSearch,
  loading,
  systems = [],
  selectedSystem = "full",
  onSelectSystem,
}) => {
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
    <div className="w-full space-y-2.5">
      {/* Omnibar Hero Input */}
      <form onSubmit={handleSubmit} className="relative w-full">
        <div className="relative bg-surface-container-low/95 backdrop-blur-2xl rounded-2xl md:rounded-full p-2 pl-4 shadow-[0_8px_32px_-4px_rgba(0,0,0,0.5),0_0_24px_rgba(128,131,255,0.12)] flex flex-wrap md:flex-nowrap items-center gap-2 group focus-within:shadow-[0_0_36px_rgba(79,219,200,0.2)] transition-all border border-surface-container-highest/60">
          {/* Explore Icon */}
          <div className="flex items-center gap-2 text-primary shrink-0 pl-1">
            <span className="material-symbols-outlined text-[1.4rem] animate-pulse">
              travel_explore
            </span>
          </div>

          {/* Search Input */}
          <div className="flex-1 min-w-[260px] relative">
            <input
              id="main-query-input"
              type="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Ask anything across papers, figures, and audio transcripts..."
              className="w-full bg-transparent text-on-surface text-sm md:text-base placeholder:text-outline focus:outline-none tracking-tight pr-12 font-sans"
              disabled={loading}
            />
            <span className="absolute right-2 top-1/2 -translate-y-1/2 font-mono text-[10px] text-outline px-1.5 py-0.5 rounded bg-surface-container-high/80 hidden lg:inline-block">
              ⌘K
            </span>
          </div>

          {/* Controls: Pipeline Mode & Execute */}
          <div className="flex items-center gap-2 shrink-0 w-full md:w-auto justify-end pr-1 pt-1 md:pt-0">
            {/* System / Pipeline Selector */}
            {systems.length > 0 && onSelectSystem && (
              <div className="relative">
                <select
                  value={selectedSystem}
                  onChange={(e) => onSelectSystem(e.target.value)}
                  className="appearance-none flex items-center gap-1.5 px-3 py-1.5 pr-7 rounded-full bg-surface-container-high text-on-surface font-mono text-xs hover:bg-surface-container-highest transition-colors cursor-pointer border border-surface-container-highest/60 focus:outline-none"
                >
                  {systems.map((s) => (
                    <option key={s.name} value={s.name} className="bg-surface-container-high text-on-surface">
                      {s.description || s.name}
                    </option>
                  ))}
                </select>
                <span className="material-symbols-outlined text-[1rem] text-outline absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none">
                  expand_more
                </span>
              </div>
            )}

            {/* Execute Button */}
            <button
              type="submit"
              disabled={loading || !text.trim()}
              className="flex items-center justify-center gap-1.5 px-5 py-2 rounded-full bg-primary text-on-primary font-semibold text-xs md:text-sm shadow-[0_0_18px_rgba(192,193,255,0.35)] hover:brightness-110 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed transition-all shrink-0"
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined text-[1.125rem] animate-spin">
                    sync
                  </span>
                  <span>Synthesizing...</span>
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
      <div className="flex items-center gap-2 overflow-x-auto py-1 text-on-surface-variant font-mono text-xs no-scrollbar">
        <span className="text-outline uppercase tracking-wider text-[10px] mr-1 shrink-0 flex items-center gap-1">
          <span className="material-symbols-outlined text-[0.875rem] text-secondary">auto_fix_high</span>
          Seed Vectors:
        </span>
        {SEED_QUERIES.map((q, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleSelectSeed(q.text)}
            className={`px-3 py-1 rounded-full bg-surface-container-low hover:bg-surface-container text-on-surface-variant transition-all whitespace-nowrap shrink-0 text-xs border border-surface-container-highest/40 ${q.color}`}
          >
            {q.text}
          </button>
        ))}
      </div>
    </div>
  );
};
