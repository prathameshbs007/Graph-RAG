import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "../api";
import type { AuditEvent, MemoryState } from "../types";

const pct = (alpha: number, lo = 0.2, hi = 0.9) => Math.round(((alpha - lo) / (hi - lo)) * 100);

export const MemoryPanel = () => {
  const [state, setState] = useState<MemoryState | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      axios.get<MemoryState>(`${API}/admin/state`),
      axios.get<{ events: AuditEvent[] }>(`${API}/admin/audit`, { params: { limit: 40 } }),
    ])
      .then(([s, a]) => {
        if (cancelled) return;
        setState(s.data);
        setEvents(a.data.events);
      })
      .catch(() => {
        if (!cancelled) setMessage("Could not reach backend governance service.");
      });
    return () => {
      cancelled = true;
    };
  }, [reload]);

  const act = async (path: string, confirmText: string | null, done: string) => {
    if (confirmText && !window.confirm(confirmText)) return;
    await axios.post(`${API}${path}`, {});
    setMessage(done);
    setReload((n) => n + 1);
  };

  if (!state) return <p className="text-outline text-center py-20 font-mono text-sm">{message ?? "Loading agentic memory state…"}</p>;

  const lo = Number(state.parameters.alpha_range instanceof Array ? state.parameters.alpha_range[0] : 0.2);
  const hi = Number(state.parameters.alpha_range instanceof Array ? state.parameters.alpha_range[1] : 0.9);
  const totalEdges = Object.values(state.edges).reduce((n, e) => n + e.total, 0);
  const pruned = Object.values(state.edges).reduce((n, e) => n + e.pruned, 0);

  return (
    <div className="space-y-5 text-on-surface">
      {/* Sub-header Breadcrumb / Stream Control Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-surface-container-low/80 backdrop-blur-md px-4 py-2.5 rounded-xl border border-surface-container-highest/30">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded bg-primary-container/20 flex items-center justify-center text-primary">
            <span className="material-symbols-outlined text-[1rem]">psychology</span>
          </div>
          <div className="flex items-center gap-1.5 font-mono text-xs">
            <span className="text-on-surface-variant">WORKSPACE</span>
            <span className="text-outline">/</span>
            <span className="text-on-surface">SYNAPSE_GOVERNANCE</span>
            <span className="text-outline">/</span>
            <span className="text-secondary font-semibold">EPISODIC_HEBBIAN</span>
          </div>
        </div>

        <div className="flex items-center gap-3 font-mono text-xs">
          <div className="flex items-center gap-2 bg-surface-container-high px-2.5 py-1 rounded-lg">
            <span className="w-2 h-2 rounded-full bg-secondary shadow-[0_0_8px_#4fdbc8] animate-pulse"></span>
            <span className="text-on-surface font-medium">NEO4J BOLT // CONNECTED</span>
          </div>
        </div>
      </div>

      {/* SECTION 1: Top KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Card 1: Active Fusion Weight (α) */}
        <div className="bg-surface-container-low/90 backdrop-blur-xl p-4 rounded-xl flex flex-col justify-between shadow-lg border border-surface-container-highest/40">
          <div>
            <div className="flex items-center justify-between text-on-surface-variant font-mono text-xs">
              <span className="uppercase tracking-wider">Fusion Weight (α)</span>
              <span className="material-symbols-outlined text-[1.125rem] text-primary">tune</span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="font-sans text-3xl text-primary font-bold">{state.alpha.toFixed(3)}</span>
              <span className="font-mono text-[10px] text-secondary bg-surface-container px-1.5 py-0.5 rounded">
                BALANCED
              </span>
            </div>
            <p className="font-sans text-xs text-on-surface-variant mt-1">
              Dynamic retriever trust score (auto-calibrates via feedback).
            </p>
          </div>
          {/* Linear Gauge */}
          <div className="mt-4 pt-2 bg-surface-container-lowest/60 rounded-lg p-2 font-mono text-[11px]">
            <div className="flex justify-between text-outline mb-1 text-[10px]">
              <span>BM25 ({lo})</span>
              <span className="text-primary font-bold">α = {state.alpha.toFixed(3)}</span>
              <span>Dense ({hi})</span>
            </div>
            <div className="h-2 w-full bg-surface-container-highest rounded-full relative overflow-hidden flex items-center">
              <div
                className="absolute left-0 h-full bg-gradient-to-r from-secondary to-primary rounded-full"
                style={{ width: `${pct(state.alpha, lo, hi)}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Card 2: Total Learned Edges */}
        <div className="bg-surface-container-low/90 backdrop-blur-xl p-4 rounded-xl flex flex-col justify-between shadow-lg border border-surface-container-highest/40">
          <div>
            <div className="flex items-center justify-between text-on-surface-variant font-mono text-xs">
              <span className="uppercase tracking-wider">Learned Edges</span>
              <span className="material-symbols-outlined text-[1.125rem] text-secondary">polyline</span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="font-sans text-3xl text-on-surface font-bold">{totalEdges}</span>
              <span className="font-mono text-xs text-secondary-fixed bg-surface-container px-1.5 py-0.5 rounded font-medium">
                Active Graph
              </span>
            </div>
            <p className="font-sans text-xs text-on-surface-variant mt-1">
              Discovered and weighted across ingested corpus.
            </p>
          </div>
          <div className="mt-4 pt-2 flex items-center justify-between bg-surface-container-lowest/60 px-3 py-2 rounded-lg font-mono text-xs">
            <span className="text-outline">Relation types:</span>
            <span className="text-secondary font-bold">{Object.keys(state.edges).length}</span>
          </div>
        </div>

        {/* Card 3: Pruned Noisy Edges */}
        <div className="bg-surface-container-low/90 backdrop-blur-xl p-4 rounded-xl flex flex-col justify-between shadow-lg border border-surface-container-highest/40">
          <div>
            <div className="flex items-center justify-between text-on-surface-variant font-mono text-xs">
              <span className="uppercase tracking-wider">Pruned Noisy Edges</span>
              <span className="material-symbols-outlined text-[1.125rem] text-error">auto_delete</span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="font-sans text-3xl text-error font-bold">{pruned}</span>
              <span className="font-mono text-xs bg-error-container/30 text-error px-2 py-0.5 rounded-full font-medium">
                PRUNED
              </span>
            </div>
            <p className="font-sans text-xs text-on-surface-variant mt-1">
              Suppressed by negative feedback & low traversal weight.
            </p>
          </div>
          <div className="mt-4 pt-2 flex items-center justify-between bg-surface-container-lowest/60 px-3 py-2 rounded-lg font-mono text-xs">
            <span className="text-outline">Cutoff threshold:</span>
            <span className="text-error font-bold">w &lt; {String(state.parameters.prune_below)}</span>
          </div>
        </div>

        {/* Card 4: Learning Parameters */}
        <div className="bg-surface-container-low/90 backdrop-blur-xl p-4 rounded-xl flex flex-col justify-between shadow-lg border border-surface-container-highest/40">
          <div>
            <div className="flex items-center justify-between text-on-surface-variant font-mono text-xs">
              <span className="uppercase tracking-wider">Feedback Governance</span>
              <span className="material-symbols-outlined text-[1.125rem] text-secondary">verified</span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="font-sans text-3xl text-secondary font-bold">
                {state.feedback_enabled ? "Active" : "Disabled"}
              </span>
            </div>
            <p className="font-sans text-xs text-on-surface-variant mt-1">
              Minimum visits before pruning: {String(state.parameters.prune_min_visits)}.
            </p>
          </div>
          <div className="mt-4 pt-2 flex items-center justify-between bg-surface-container-lowest/60 px-3 py-2 rounded-lg font-mono text-xs">
            <span className="text-outline">Explore weak edges:</span>
            <span className="text-secondary font-bold">{(Number(state.parameters.explore_prob) * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* SECTION 2: Governance Bar */}
      <div className="bg-surface-container-low/90 backdrop-blur-xl p-4 rounded-xl shadow-lg border border-surface-container-highest/40 flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
        {/* Formula Pill */}
        <div className="flex-1 bg-surface-container-high/60 px-4 py-2.5 rounded-xl border border-surface-container-highest/40 flex items-center gap-3 overflow-x-auto">
          <div className="w-7 h-7 shrink-0 rounded bg-primary-container/20 flex items-center justify-center text-primary">
            <span className="material-symbols-outlined text-[1.125rem]">functions</span>
          </div>
          <div className="min-w-0 font-mono text-xs">
            <span className="text-primary font-bold uppercase tracking-wider text-[10px] block">
              Hebbian Synapse Weight Update Rule
            </span>
            <span className="text-on-surface truncate block">
              <span className="text-tertiary">w</span> ← <span className="text-secondary">0.9</span>·<span className="text-tertiary">w</span> + <span className="text-secondary">0.1</span>·<span className="text-primary">score</span> · prune when <span className="text-error">w &lt; {String(state.parameters.prune_below)}</span> after ≥ <span className="text-primary">{String(state.parameters.prune_min_visits)}</span> visits
            </span>
          </div>
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-2 flex-wrap shrink-0">
          <button
            onClick={() => void act("/admin/restore-pruned", null, "Pruned edges restored to active traversal.")}
            disabled={pruned === 0}
            type="button"
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-secondary-container/20 hover:bg-secondary-container/35 text-secondary transition-all font-mono text-xs font-semibold disabled:opacity-40"
          >
            <span className="material-symbols-outlined text-[1rem]">undo</span>
            <span>Restore {pruned} Pruned</span>
          </button>
          <button
            onClick={() =>
              void act(
                "/admin/reset-feedback",
                "Reset every learned edge weight to 0.5, alpha to 0.5, and clear the audit log?",
                "Memory reset to initial parameters.",
              )
            }
            type="button"
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-error-container/20 hover:bg-error-container/40 text-error transition-all font-mono text-xs font-semibold"
          >
            <span className="material-symbols-outlined text-[1rem]">warning</span>
            <span>Reset Learning</span>
          </button>
          <button
            onClick={() => setReload((n) => n + 1)}
            type="button"
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface transition-all font-mono text-xs font-semibold"
          >
            <span className="material-symbols-outlined text-[1rem] text-primary">sync</span>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {message && (
        <div className="p-3 bg-secondary/15 border border-secondary/30 rounded-xl text-xs font-mono text-secondary flex items-center gap-2">
          <span className="material-symbols-outlined text-[1rem]">info</span>
          <span>{message}</span>
        </div>
      )}

      {/* SECTION 3: Main Dual-Pane Data Deck */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Panel: Relation Topology Summary Table */}
        <div className="lg:col-span-5 bg-surface-container-low/90 backdrop-blur-xl rounded-xl p-4 shadow-lg border border-surface-container-highest/40 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-surface-container-highest/30">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[1.125rem]">account_tree</span>
                <span className="font-semibold text-sm text-on-surface">Relation Topology Summary</span>
              </div>
              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-surface-container text-on-surface-variant">
                {Object.keys(state.edges).length} RELATIONS
              </span>
            </div>

            <div className="overflow-x-auto mt-3">
              {Object.keys(state.edges).length === 0 ? (
                <p className="text-outline text-xs font-mono py-8 text-center">No learned relations yet.</p>
              ) : (
                <table className="w-full text-left font-mono text-xs">
                  <thead>
                    <tr className="text-outline uppercase text-[10px] border-b border-surface-container-highest/20">
                      <th className="py-2 px-2">Type</th>
                      <th className="py-2 px-2 text-right">Edges</th>
                      <th className="py-2 px-2 text-right">Mean w</th>
                      <th className="py-2 px-2 text-right">Visits</th>
                      <th className="py-2 px-2 text-right">Pruned</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-container-highest/10">
                    {Object.entries(state.edges).map(([type, e]) => (
                      <tr key={type} className="hover:bg-surface-container/50 transition-colors">
                        <td className="py-2 px-2 font-semibold text-secondary">{type}</td>
                        <td className="py-2 px-2 text-right text-on-surface">{e.total}</td>
                        <td className="py-2 px-2 text-right text-on-surface font-bold">
                          {e.avg_weight === null ? "—" : e.avg_weight.toFixed(3)}
                        </td>
                        <td className="py-2 px-2 text-right text-on-surface-variant">{e.visits}</td>
                        <td className={`py-2 px-2 text-right ${e.pruned ? "text-error font-bold" : "text-outline"}`}>
                          {e.pruned}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        {/* Right Panel: Live Memory Audit Log Stream */}
        <div className="lg:col-span-7 bg-surface-container-low/90 backdrop-blur-xl rounded-xl p-4 shadow-lg border border-surface-container-highest/40 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-surface-container-highest/30 font-mono text-xs">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-secondary shadow-[0_0_8px_#4fdbc8] animate-pulse"></span>
                <span className="font-semibold text-on-surface tracking-wider">
                  REALTIME SYNAPSE AUDIT STREAM
                </span>
              </div>
              <span className="text-outline text-[11px]">{events.length} events logged</span>
            </div>

            <div className="mt-3 space-y-2 max-h-[380px] overflow-y-auto font-mono text-xs pr-1">
              {events.length === 0 ? (
                <p className="text-outline text-xs text-center py-8">
                  No feedback events logged yet. Execute a query to trigger learning.
                </p>
              ) : (
                events.map((e, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-lg bg-surface-container-lowest/80 border border-surface-container-highest/20 hover:bg-surface-container-lowest transition-all"
                  >
                    <div className="flex items-center justify-between gap-2 text-[11px]">
                      <div className="flex items-center gap-2">
                        <span className="text-outline">{new Date(e.ts * 1000).toLocaleTimeString()}</span>
                        <span
                          className={`px-1.5 py-0.5 rounded font-bold uppercase text-[10px] ${
                            e.kind === "prune"
                              ? "bg-error-container/30 text-error"
                              : e.kind === "alpha"
                              ? "bg-primary/20 text-primary"
                              : "bg-secondary-container/20 text-secondary"
                          }`}
                        >
                          {e.kind}
                        </span>
                      </div>
                      <div className="text-outline font-semibold">
                        {(e.old_weight ?? 0).toFixed(3)} → {(e.new_weight ?? 0).toFixed(3)}
                      </div>
                    </div>

                    <div className="mt-1.5 text-on-surface text-xs truncate" title={`${e.src ?? ""} → ${e.dst ?? ""}`}>
                      <span className="text-tertiary">{e.src ?? "source"}</span>
                      <span className="text-outline mx-1">
                        —[ <strong className="text-secondary">{e.edge_type ?? "edge"}</strong> ]→
                      </span>
                      <span className="text-on-surface">{e.dst ?? "target"}</span>
                    </div>

                    {e.query && (
                      <div className="mt-1 text-[11px] text-outline truncate" title={e.query}>
                        Trigger: "{e.query}"
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
