import type { Source } from "../types";

const retrieverStyle: Record<string, string> = {
  bm25: "bg-surface-container-high text-on-surface-variant border-outline/30",
  dense: "bg-primary/20 text-primary border-primary/30",
  graph: "bg-secondary/20 text-secondary border-secondary/30",
};

export const SourceChip = ({ source }: { source: Source }) => {
  const isAudio = source.modality === "audio";
  const found = [...source.found_by];
  if (source.via === "graph" && !found.includes("graph")) found.push("graph");

  return (
    <article
      id={`citation-${source.evidence_id}`}
      className={`p-3.5 rounded-xl bg-surface-container/60 hover:bg-surface-container transition-all group relative overflow-hidden border ${
        source.cited ? "border-primary/50 shadow-[0_0_12px_rgba(192,193,255,0.15)]" : "border-surface-container-highest/50"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`px-2 py-0.5 rounded font-mono text-xs font-bold ${
              isAudio ? "bg-tertiary/20 text-tertiary" : "bg-primary/20 text-primary"
            }`}
          >
            {source.evidence_id}
          </span>
          <span className="font-semibold text-on-surface text-sm group-hover:text-primary transition-colors">
            {source.paper_title}
          </span>
        </div>
        <div className="flex items-center gap-1 shrink-0 px-2 py-0.5 rounded bg-surface-container-high font-mono text-[11px] text-secondary">
          <span className="material-symbols-outlined text-[0.85rem]">
            {isAudio ? "graphic_eq" : "fingerprint"}
          </span>
          <span>{(source.score * 100).toFixed(0)}%</span>
        </div>
      </div>

      <div className="flex items-center gap-2 text-outline font-mono text-xs mb-2">
        <span>{source.location}</span>
        {!isAudio && source.authors.length > 0 && (
          <>
            <span>•</span>
            <span className="truncate max-w-[200px]">{source.authors.join(", ")} ({source.year ?? "n.d."})</span>
          </>
        )}
      </div>

      <p className="font-body-md text-xs text-on-surface-variant leading-relaxed pl-3 relative bg-surface-container-lowest/60 p-2.5 rounded-lg border-l-2 border-primary">
        “{source.chunk_text.substring(0, 220)}{source.chunk_text.length > 220 ? "..." : ""}”
      </p>

      <div className="mt-2.5 flex items-center justify-between font-mono text-[11px] text-outline">
        <div className="flex items-center gap-1.5 flex-wrap">
          {found.map((f) => (
            <span
              key={f}
              className={`px-1.5 py-0.5 rounded border text-[10px] uppercase font-semibold ${
                retrieverStyle[f] ?? "bg-surface-container text-on-surface-variant border-outline/20"
              }`}
            >
              {f}
            </span>
          ))}
          {source.cited && (
            <span className="px-1.5 py-0.5 rounded bg-primary text-on-primary text-[10px] uppercase font-bold">
              cited in answer
            </span>
          )}
        </div>
      </div>
    </article>
  );
};
