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
        if (!cancelled) setMessage("Could not reach the backend.");
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

  if (!state) return <p className="text-gray-300 text-center py-20">{message ?? "Loading…"}</p>;

  const lo = Number(state.parameters.alpha_range instanceof Array ? state.parameters.alpha_range[0] : 0.2);
  const hi = Number(state.parameters.alpha_range instanceof Array ? state.parameters.alpha_range[1] : 0.9);
  const pruned = Object.values(state.edges).reduce((n, e) => n + e.pruned, 0);

  return (
    <div className="space-y-6 text-white">
      <div className="glass-dark border border-white/10 rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <h3 className="text-2xl font-black text-gradient">Self-Pruning Memory</h3>
          <div className="ml-auto flex gap-2 flex-wrap">
            <button onClick={() => setReload((n) => n + 1)} className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-sm font-semibold">
              Refresh
            </button>
            <button
              disabled={pruned === 0}
              onClick={() => void act("/admin/restore-pruned", null, "Pruned edges restored.")}
              className="px-3 py-1.5 rounded-lg bg-emerald-600/80 hover:bg-emerald-600 disabled:opacity-40 text-sm font-semibold"
            >
              Restore {pruned} pruned
            </button>
            <button
              onClick={() =>
                void act(
                  "/admin/reset-feedback",
                  "Reset every learned edge weight to 0.5, alpha to 0.5 and clear the audit log?",
                  "Memory reset.",
                )
              }
              className="px-3 py-1.5 rounded-lg bg-red-600/80 hover:bg-red-600 text-sm font-semibold"
            >
              Reset learning
            </button>
          </div>
        </div>
        {message && <p className="text-sm text-cyan-300 mb-3">{message}</p>}
        {!state.feedback_enabled && <p className="text-sm text-amber-300 mb-3">Feedback is globally disabled (FEEDBACK_ENABLED=false).</p>}

        <p className="text-xs uppercase tracking-widest text-gray-400 mb-2">
          Fusion weight α — which retriever the memory currently trusts
        </p>
        <div className="relative h-3 rounded-full bg-gradient-to-r from-amber-400/60 to-sky-400/60">
          <div
            className="absolute -top-1 h-5 w-1.5 rounded bg-white shadow"
            style={{ left: `calc(${pct(state.alpha, lo, hi)}% - 3px)` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>BM25 ({lo})</span>
          <span className="text-white font-bold">α = {state.alpha.toFixed(3)}</span>
          <span>dense ({hi})</span>
        </div>
      </div>

      <div className="glass-dark border border-white/10 rounded-2xl p-6 overflow-x-auto">
        <h4 className="font-black uppercase tracking-widest text-sm mb-4">Learned edges</h4>
        {Object.keys(state.edges).length === 0 ? (
          <p className="text-gray-400 text-sm">No edges yet. Ingest papers first.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-gray-400 text-xs uppercase">
              <tr>
                <th className="text-left py-1">Type</th>
                <th className="text-right">Edges</th>
                <th className="text-right">Mean weight</th>
                <th className="text-right">Visits</th>
                <th className="text-right">Pruned</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(state.edges).map(([type, e]) => (
                <tr key={type} className="border-t border-white/10">
                  <td className="py-1.5 font-semibold">{type}</td>
                  <td className="text-right">{e.total}</td>
                  <td className="text-right">{e.avg_weight === null ? "—" : e.avg_weight.toFixed(3)}</td>
                  <td className="text-right">{e.visits}</td>
                  <td className={`text-right ${e.pruned ? "text-red-300 font-bold" : ""}`}>{e.pruned}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="text-xs text-gray-500 mt-3">
          update w ← 0.9·w + 0.1·score · explore weak edges {String(state.parameters.explore_prob)} · follow edges ≥{" "}
          {String(state.parameters.traverse_min)} · prune when w &lt; {String(state.parameters.prune_below)} after ≥{" "}
          {String(state.parameters.prune_min_visits)} visits
        </p>
      </div>

      <div className="glass-dark border border-white/10 rounded-2xl p-6 overflow-x-auto">
        <h4 className="font-black uppercase tracking-widest text-sm mb-4">Audit log (latest changes)</h4>
        {events.length === 0 ? (
          <p className="text-gray-400 text-sm">Nothing logged yet. Ask a question to start the feedback loop.</p>
        ) : (
          <table className="w-full text-xs">
            <thead className="text-gray-400 uppercase">
              <tr>
                <th className="text-left py-1">When</th>
                <th className="text-left">Change</th>
                <th className="text-left">Edge</th>
                <th className="text-right">Old</th>
                <th className="text-right">New</th>
                <th className="text-right">Score</th>
                <th className="text-left pl-3">Query</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e, i) => (
                <tr key={i} className="border-t border-white/10">
                  <td className="py-1">{new Date(e.ts * 1000).toLocaleTimeString()}</td>
                  <td className={e.kind === "prune" ? "text-red-300 font-bold" : e.kind === "alpha" ? "text-sky-300" : ""}>
                    {e.kind}
                  </td>
                  <td className="max-w-[18rem] truncate" title={`${e.src} → ${e.dst}`}>
                    {e.edge_type}: {e.src.slice(0, 18)} → {e.dst.slice(0, 18)}
                  </td>
                  <td className="text-right">{e.old_weight.toFixed(3)}</td>
                  <td className="text-right">{e.new_weight.toFixed(3)}</td>
                  <td className="text-right">{e.score.toFixed(2)}</td>
                  <td className="pl-3 max-w-[16rem] truncate" title={e.query}>
                    {e.query}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
