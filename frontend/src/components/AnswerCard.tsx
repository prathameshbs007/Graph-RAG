import { Fragment } from "react";
import { SourceChip } from "./SourceChip";
import { FigureCitation } from "./FigureCitation";
import type { Claim, QueryResult } from "../types";

interface Segment {
  text: string;
  unsupported: boolean;
}

// Split the answer so claims the verification pass could not support can be highlighted.
const markUnsupported = (answer: string, claims: Claim[]): Segment[] => {
  let parts: Segment[] = [{ text: answer, unsupported: false }];
  for (const c of claims.filter((c) => c.verdict === "unsupported")) {
    parts = parts.flatMap((p) => {
      if (p.unsupported) return [p];
      const i = p.text.indexOf(c.text);
      if (i < 0) return [p];
      return [
        { text: p.text.slice(0, i), unsupported: false },
        { text: c.text, unsupported: true },
        { text: p.text.slice(i + c.text.length), unsupported: false },
      ];
    });
  }
  return parts;
};

// Render [E1]-style citations as small pills.
const withCitations = (text: string) =>
  text.split(/(\[E\d+\])/g).map((piece, i) =>
    /^\[E\d+\]$/.test(piece) ? (
      <span
        key={i}
        className="inline-block align-baseline mx-0.5 px-1.5 py-0.5 rounded bg-cyan-400/20 text-cyan-200 border border-cyan-400/30 text-xs font-bold"
      >
        {piece.slice(1, -1)}
      </span>
    ) : (
      <Fragment key={i}>{piece}</Fragment>
    ),
  );

const Stat = ({ label, value }: { label: string; value: string | number }) => (
  <div className="bg-white/5 rounded-lg px-3 py-2 border border-white/10">
    <div className="text-[10px] uppercase tracking-widest text-gray-400">{label}</div>
    <div className="text-white font-bold">{value}</div>
  </div>
);

export const AnswerCard = ({ data }: { data: QueryResult }) => {
  const { claim_stats: stats, diagnostics: d } = data;
  const segments = markUnsupported(data.answer, data.claims);
  const fb = d.feedback;
  const checked = stats.supported + stats.unsupported;

  return (
    <div className="w-full glass-dark border border-white/10 rounded-3xl p-8 shadow-2xl shadow-blue-500/20">
      {/* Header */}
      <div className="mb-8 pb-6 border-b border-white/10">
        <div className="flex items-center gap-3 mb-2 flex-wrap">
          <span className="text-3xl">✨</span>
          <h3 className="text-3xl font-black text-gradient">Answer</h3>
          <div className="ml-auto flex gap-2 flex-wrap">
            {stats.verified && checked > 0 && (
              <span
                className={`inline-block text-xs font-bold px-3 py-1 rounded-full border ${
                  stats.unsupported === 0
                    ? "bg-emerald-400/20 text-emerald-300 border-emerald-400/30"
                    : "bg-amber-400/20 text-amber-300 border-amber-400/30"
                }`}
              >
                {stats.unsupported === 0
                  ? `✓ All ${stats.supported} claims verified`
                  : `${stats.supported} supported · ${stats.unsupported} unsupported`}
              </span>
            )}
            <span className="inline-block text-xs font-bold bg-cyan-400/20 text-cyan-300 px-3 py-1 rounded-full border border-cyan-400/30">
              Evidence-Based
            </span>
          </div>
        </div>
      </div>

      {/* Answer */}
      <div className="mb-10 p-8 bg-gradient-to-br from-white/10 to-white/5 rounded-2xl border border-white/10 backdrop-blur">
        <p className="text-white text-lg leading-relaxed whitespace-pre-wrap font-medium">
          {segments.map((s, i) =>
            s.unsupported ? (
              <mark
                key={i}
                className="bg-amber-400/25 text-amber-100 rounded px-1 underline decoration-dotted decoration-amber-300"
                title="The verification pass could not find support for this claim in the cited evidence"
              >
                {withCitations(s.text)}
              </mark>
            ) : (
              <Fragment key={i}>{withCitations(s.text)}</Fragment>
            ),
          )}
        </p>
        {stats.unsupported > 0 && (
          <p className="mt-4 text-sm text-amber-300">
            ⚠ Highlighted sentences are not supported by the cited evidence. Treat them with caution.
          </p>
        )}
      </div>

      {/* Sources and Figures Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-dark border border-white/10 rounded-2xl p-6 overflow-hidden">
          <div className="flex items-center gap-3 mb-5">
            <span className="text-2xl">📚</span>
            <h4 className="font-black text-white uppercase tracking-widest text-sm">Evidence</h4>
            {data.sources.length > 0 && (
              <span className="ml-auto bg-blue-500/30 text-blue-200 text-xs font-bold px-3 py-1.5 rounded-full border border-blue-500/50">
                {data.sources.length}
              </span>
            )}
          </div>
          <div className="flex flex-col gap-3">
            {data.sources.length > 0 ? (
              data.sources.map((s) => <SourceChip key={s.evidence_id} source={s} />)
            ) : (
              <p className="text-gray-400 italic text-center py-6">No text or audio evidence passed the relevance cutoff</p>
            )}
          </div>
        </div>

        <div className="glass-dark border border-white/10 rounded-2xl p-6 overflow-hidden">
          <div className="flex items-center gap-3 mb-5">
            <span className="text-2xl">🖼️</span>
            <h4 className="font-black text-white uppercase tracking-widest text-sm">Visual Evidence</h4>
            {data.figures.length > 0 && (
              <span className="ml-auto bg-purple-500/30 text-purple-200 text-xs font-bold px-3 py-1.5 rounded-full border border-purple-500/50">
                {data.figures.length}
              </span>
            )}
          </div>
          <div className="flex flex-col gap-4">
            {data.figures.length > 0 ? (
              data.figures.map((f) => <FigureCitation key={f.evidence_id} figure={f} />)
            ) : (
              <p className="text-gray-400 italic text-center py-6">No visual evidence retrieved</p>
            )}
          </div>
        </div>
      </div>

      {/* Graph context */}
      {((data.graph_context?.concepts?.length ?? 0) > 0 || (data.graph_context?.related_papers?.length ?? 0) > 0) && (
        <div className="mt-6 glass-dark border border-white/10 rounded-2xl p-5">
          <h4 className="font-black text-white uppercase tracking-widest text-xs mb-3">Reached through the knowledge graph</h4>
          <div className="flex flex-wrap gap-2">
            {(data.graph_context?.concepts ?? []).slice(0, 20).map((c) => (
              <span key={c} className="text-xs px-2.5 py-1 rounded-full bg-teal-500/20 text-teal-200 border border-teal-400/30">
                {c}
              </span>
            ))}
            {(data.graph_context?.related_papers ?? []).map((p) => (
              <span key={p} className="text-xs px-2.5 py-1 rounded-full bg-purple-500/20 text-purple-200 border border-purple-400/30">
                cited paper: {p}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* How this answer was produced */}
      <details className="mt-6 group">
        <summary className="cursor-pointer text-xs font-semibold text-gray-400 hover:text-white select-none">
          How this answer was retrieved ({d.system}
          {d.alpha !== null && ` · α=${d.alpha}`})
        </summary>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          <Stat label="BM25 hits" value={d.bm25_hits} />
          <Stat label="Dense hits" value={d.dense_hits} />
          <Stat label="Seeds" value={d.seeds} />
          <Stat label="Graph reached" value={d.graph_reached} />
          <Stat label="Candidates" value={d.candidates} />
          <Stat label="Above cutoff" value={d.above_cutoff} />
          <Stat label="Edges updated" value={fb.applied ? (fb.edges_updated ?? 0) : "—"} />
          <Stat label="Edges pruned" value={fb.applied ? (fb.edges_pruned ?? 0) : "—"} />
        </div>
        {fb.applied && fb.alpha_before !== undefined && fb.alpha_after !== undefined && (
          <p className="mt-3 text-xs text-gray-400">
            Fusion weight α (0 = BM25 only, 1 = dense only): {fb.alpha_before} → {fb.alpha_after}
          </p>
        )}
        <p className="mt-2 text-xs text-gray-500">
          {Object.entries(d.timings)
            .map(([k, v]) => `${k.replace("_ms", "")} ${v} ms`)
            .join(" · ")}
        </p>
        {d.notes.map((n) => (
          <p key={n} className="mt-2 text-xs text-amber-300">
            ⚠ {n}
          </p>
        ))}
      </details>

      <div className="mt-8 pt-6 border-t border-white/10 flex items-center justify-between text-xs text-gray-400 font-semibold">
        <span>✓ Answered only from numbered evidence</span>
        <span>
          {data.sources.length} sources • {data.figures.length} figures
        </span>
      </div>
    </div>
  );
};
