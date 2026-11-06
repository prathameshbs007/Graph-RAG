import { Fragment, useState } from "react";
import { SourceChip } from "./SourceChip";
import { FigureCitation } from "./FigureCitation";
import type { Claim, QueryResult } from "../types";

interface Segment {
  text: string;
  unsupported: boolean;
}

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

const withCitations = (text: string) =>
  text.split(/(\[E\d+\])/g).map((piece, i) =>
    /^\[E\d+\]$/.test(piece) ? (
      <a
        key={i}
        href={`#citation-${piece.slice(1, -1)}`}
        className="inline-flex items-center px-1.5 py-0.2 mx-0.5 rounded font-mono text-xs bg-primary/20 text-primary hover:bg-primary hover:text-on-primary transition-all font-semibold cursor-pointer border border-primary/30"
      >
        {piece}
      </a>
    ) : (
      <Fragment key={i}>{piece}</Fragment>
    ),
  );

export const AnswerCard = ({ data }: { data: QueryResult }) => {
  const { claim_stats: stats, diagnostics: d } = data;
  const segments = markUnsupported(data.answer, data.claims);
  const fb = d.feedback;
  const checked = stats.supported + stats.unsupported;
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="w-full space-y-6">
      {/* Synthesis Stage: Grounded Answer & NLI Verification Header */}
      <section className="bg-surface-container-low/90 backdrop-blur-xl rounded-2xl p-6 shadow-xl relative overflow-hidden border border-surface-container-highest/40">
        {/* Top specular light ray */}
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-secondary/40 to-transparent"></div>

        {/* Metric Status Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-surface-container-highest/30">
          <div className="flex items-center gap-2.5 flex-wrap">
            {stats.verified && checked > 0 ? (
              <div
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full font-mono text-xs font-semibold uppercase tracking-wider ${
                  stats.unsupported === 0
                    ? "bg-secondary-container/20 text-secondary-fixed shadow-[0_0_12px_rgba(79,219,200,0.2)] border border-secondary/30"
                    : "bg-error-container/20 text-error shadow-[0_0_12px_rgba(255,180,171,0.2)] border border-error/30"
                }`}
              >
                <span className="material-symbols-outlined text-[1rem]">verified_user</span>
                <span>
                  {stats.unsupported === 0
                    ? `All ${stats.supported} Claims Verified`
                    : `${stats.supported} Verified · ${stats.unsupported} Unsupported`}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/20 text-primary font-mono text-xs font-semibold border border-primary/30">
                <span className="material-symbols-outlined text-[1rem]">auto_awesome</span>
                <span>Evidence Synthesis</span>
              </div>
            )}

            <div className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-surface-container-high font-mono text-xs text-on-surface-variant border border-surface-container-highest/50">
              <span className="material-symbols-outlined text-[0.875rem] text-primary">psychology</span>
              <span>{d.system || "ResearchOS Agentic"}</span>
            </div>

            {d.alpha !== null && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-container font-mono text-xs text-secondary border border-secondary/20">
                <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>
                <span>α = {d.alpha.toFixed(3)}</span>
              </div>
            )}
          </div>

          {data.claims.length > 0 && (
            <button
              onClick={() => setDrawerOpen(!drawerOpen)}
              type="button"
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-surface-container hover:bg-surface-container-high text-primary hover:text-on-surface transition-colors font-mono text-xs border border-surface-container-highest/50 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[0.95rem]">fact_check</span>
              <span>Audit Chain ({stats.supported}/{checked})</span>
              <span
                className={`material-symbols-outlined text-[0.85rem] transition-transform duration-200 ${
                  drawerOpen ? "rotate-180" : ""
                }`}
              >
                expand_more
              </span>
            </button>
          )}
        </div>

        {/* Scientific Prose with Citations */}
        <div className="py-5 text-on-surface text-base md:text-[1.05rem] leading-relaxed whitespace-pre-wrap font-sans">
          {segments.map((s, i) =>
            s.unsupported ? (
              <mark
                key={i}
                className="bg-error-container/25 text-error px-1 py-0.5 rounded font-medium underline decoration-dotted decoration-error"
                title="The verification pass could not find support for this claim in the cited evidence"
              >
                {withCitations(s.text)}
              </mark>
            ) : (
              <Fragment key={i}>{withCitations(s.text)}</Fragment>
            ),
          )}
        </div>

        {stats.unsupported > 0 && (
          <p className="mt-1 text-xs text-error font-mono flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[0.875rem]">warning</span>
            Highlighted sentences could not be fully supported by retrieved evidence chunks.
          </p>
        )}

        {/* NLI Claim Verification Drawer */}
        {drawerOpen && data.claims.length > 0 && (
          <div className="mt-4 pt-4 border-t border-surface-container-highest/30 space-y-2.5 animate-fadeIn">
            <div className="text-[11px] font-mono uppercase tracking-wider text-outline mb-2 flex items-center justify-between">
              <span>Formal Entailment Verification Matrices</span>
              <span>Premise-Hypothesis Core</span>
            </div>
            {data.claims.map((claim, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-surface-container/70 border border-surface-container-highest/30 flex flex-col md:flex-row md:items-center justify-between gap-2.5 text-xs hover:bg-surface-container transition-colors"
              >
                <div className="flex items-start gap-2.5 min-w-0">
                  <span
                    className={`material-symbols-outlined text-[1.2rem] shrink-0 mt-0.5 ${
                      claim.verdict === "supported" ? "text-secondary" : "text-error"
                    }`}
                  >
                    {claim.verdict === "supported" ? "check_circle" : "cancel"}
                  </span>
                  <div>
                    <span className="text-on-surface font-semibold">Claim {idx + 1}:</span>
                    <span className="text-on-surface-variant ml-1 font-mono">"{claim.text}"</span>
                    {claim.evidence_ids?.length > 0 && (
                      <span className="text-outline text-[11px] block md:inline md:ml-2">
                        Anchors: {claim.evidence_ids.join(", ")}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 self-end md:self-auto font-mono text-xs">
                  <span
                    className={`px-2.5 py-0.5 rounded text-[10px] uppercase font-bold ${
                      claim.verdict === "supported"
                        ? "bg-secondary/15 text-secondary border border-secondary/30"
                        : "bg-error-container/30 text-error border border-error/30"
                    }`}
                  >
                    {claim.verdict}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Multi-Modal Evidence Split View: High Density 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Column: Text & Audio Modality (7 cols) */}
        <div className="lg:col-span-7 space-y-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[1.25rem]">
                library_books
              </span>
              <h3 className="font-semibold text-sm text-on-surface">Text & Audio Evidence</h3>
            </div>
            <span className="font-mono text-xs text-outline">
              {data.sources.length} retrieved anchors
            </span>
          </div>

          <div className="space-y-3">
            {data.sources.length > 0 ? (
              data.sources.map((s) => <SourceChip key={s.evidence_id} source={s} />)
            ) : (
              <div className="p-8 rounded-xl bg-surface-container-low/60 border border-surface-container-highest/30 text-center text-xs text-outline font-mono">
                No text or audio evidence passed relevance cutoff
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Visual Evidence (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary text-[1.25rem]">
                image_search
              </span>
              <h3 className="font-semibold text-sm text-on-surface">Visual Evidence</h3>
            </div>
            <span className="font-mono text-xs text-outline">
              {data.figures.length} figures
            </span>
          </div>

          <div className="space-y-3">
            {data.figures.length > 0 ? (
              data.figures.map((f) => <FigureCitation key={f.evidence_id} figure={f} />)
            ) : (
              <div className="p-8 rounded-xl bg-surface-container-low/60 border border-surface-container-highest/30 text-center text-xs text-outline font-mono">
                No visual figures retrieved
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Reached through Knowledge Graph */}
      {((data.graph_context?.concepts?.length ?? 0) > 0 || (data.graph_context?.related_papers?.length ?? 0) > 0) && (
        <div className="p-4 rounded-xl bg-surface-container-low/90 border border-surface-container-highest/40">
          <div className="flex items-center gap-2 mb-2.5 text-xs font-mono uppercase text-outline">
            <span className="material-symbols-outlined text-[1.125rem] text-secondary">hub</span>
            <span className="font-semibold text-on-surface-variant">Reached Through Knowledge Graph Synapses</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {(data.graph_context?.concepts ?? []).slice(0, 16).map((c) => (
              <span
                key={c}
                className="text-xs px-3 py-1 rounded-full bg-secondary-container/15 text-secondary border border-secondary/25 font-mono"
              >
                {c}
              </span>
            ))}
            {(data.graph_context?.related_papers ?? []).map((p) => (
              <span
                key={p}
                className="text-xs px-3 py-1 rounded-full bg-tertiary/15 text-tertiary border border-tertiary/25 font-mono"
              >
                paper: {p}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Telemetry Bar & Hybrid Tuner Footer */}
      <section className="p-3 px-4 rounded-xl bg-surface-container-low/95 backdrop-blur-md shadow-lg flex flex-col md:flex-row items-center justify-between gap-3 font-mono text-xs text-on-surface-variant border border-surface-container-highest/40">
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center gap-1.5 text-secondary">
            <span className="material-symbols-outlined text-[1rem]">speed</span>
            <span className="font-bold">E2E {((d.timings.total_ms || 1700) / 1000).toFixed(1)}s</span>
          </div>
          <span className="text-outline">•</span>
          {Object.entries(d.timings).map(([k, v]) => (
            <span key={k} className="hidden sm:inline">
              {k.replace("_ms", "")}: <strong className="text-on-surface">{v}ms</strong>
              <span className="text-outline mx-1">•</span>
            </span>
          ))}
          <span>BM25: <strong className="text-on-surface">{d.bm25_hits}</strong></span>
          <span className="text-outline">•</span>
          <span>Dense: <strong className="text-primary">{d.dense_hits}</strong></span>
          <span className="text-outline">•</span>
          <span>Graph: <strong className="text-secondary">{d.graph_reached}</strong></span>
        </div>

        {fb.applied && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-secondary">Synapses: {fb.edges_updated ?? 0} updated</span>
            {fb.edges_pruned ? <span className="text-error">• {fb.edges_pruned} pruned</span> : null}
          </div>
        )}
      </section>
    </div>
  );
};
