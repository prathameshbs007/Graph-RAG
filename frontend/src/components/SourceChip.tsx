import type { Source } from "../types";

export const SourceChip = ({ source }: { source: Source }) => {
  const isAudio = source.modality === "audio";
  const found = [...source.found_by];
  if (source.via === "graph" && !found.includes("graph")) found.push("graph");

  return (
    <article
      id={`citation-${source.evidence_id}`}
      className={`p-4 rounded-xl bg-surface-container-low/90 hover:bg-surface-container transition-all group relative overflow-hidden border ${
        source.cited
          ? "border-primary/50 shadow-[0_0_16px_rgba(192,193,255,0.12)] bg-surface-container/70"
          : "border-surface-container-highest/40"
      }`}
    >
      {/* Top Header: Badge + Title + Relevance */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          <span
            className={`px-2 py-0.5 rounded font-mono text-xs font-bold shrink-0 ${
              isAudio
                ? "bg-tertiary/20 text-tertiary border border-tertiary/30"
                : "bg-primary/20 text-primary border border-primary/30"
            }`}
          >
            {source.evidence_id}
          </span>
          <span className="font-semibold text-on-surface text-sm group-hover:text-primary transition-colors truncate">
            {source.paper_title}
          </span>
        </div>
        <div className="flex items-center gap-1 shrink-0 px-2.5 py-0.5 rounded bg-surface-container-high font-mono text-xs text-secondary border border-surface-container-highest/60">
          <span className="material-symbols-outlined text-[0.875rem]">
            {isAudio ? "mic" : "fingerprint"}
          </span>
          <span>{(source.score * 100).toFixed(1)}%</span>
        </div>
      </div>

      {/* Metadata Row: Location / Section / Page */}
      <div className="flex items-center gap-2 text-outline font-mono text-xs mb-2.5 flex-wrap">
        <span>{source.location}</span>
        {!isAudio && source.authors.length > 0 && (
          <>
            <span>•</span>
            <span className="truncate max-w-[240px]">{source.authors.join(", ")} ({source.year ?? "n.d."})</span>
          </>
        )}
      </div>

      {/* Audio Waveform visualization if audio */}
      {isAudio && (
        <div className="h-5 w-full flex items-end gap-1 py-1 px-2.5 rounded bg-surface-container-lowest/80 mb-2 border border-surface-container-highest/30">
          <div className="w-1 bg-tertiary/40 h-2 rounded-t"></div>
          <div className="w-1 bg-tertiary/60 h-3.5 rounded-t"></div>
          <div className="w-1 bg-tertiary h-4 rounded-t animate-pulse"></div>
          <div className="w-1 bg-tertiary h-2.5 rounded-t"></div>
          <div className="w-1 bg-tertiary/70 h-3.5 rounded-t"></div>
          <div className="w-1 bg-tertiary/40 h-2 rounded-t"></div>
          <div className="w-1 bg-tertiary/80 h-4 rounded-t"></div>
          <div className="w-1 bg-tertiary h-3 rounded-t"></div>
          <div className="w-1 bg-tertiary/50 h-2 rounded-t"></div>
        </div>
      )}

      {/* Text Passage Quote */}
      <p className="font-body-md text-xs text-on-surface-variant leading-relaxed pl-3 relative bg-surface-container-lowest/60 p-3 rounded-lg border-l-2 border-primary/80">
        “{source.chunk_text.substring(0, 240)}{source.chunk_text.length > 240 ? "..." : ""}”
      </p>

      {/* Bottom Retriever Tags */}
      <div className="mt-3 flex items-center justify-between font-mono text-[11px] text-outline">
        <div className="flex items-center gap-1.5 flex-wrap">
          {found.map((f) => (
            <span
              key={f}
              className="px-2 py-0.5 rounded bg-surface-container-high/60 text-on-surface-variant border border-surface-container-highest/50 text-[10px] uppercase font-semibold"
            >
              {f}
            </span>
          ))}
          {source.cited && (
            <span className="px-2 py-0.5 rounded bg-primary text-on-primary text-[10px] uppercase font-bold shadow-sm">
              cited in answer
            </span>
          )}
        </div>
      </div>
    </article>
  );
};
