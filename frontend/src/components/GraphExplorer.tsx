import { useEffect, useMemo, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { LinkObject, NodeObject } from "react-force-graph-2d";
import axios from "axios";
import { API } from "../api";
import type { GraphLink, GraphNode } from "../types";

type GNode = NodeObject<GraphNode>;
type GLink = LinkObject<GraphNode, GraphLink>;

const COLORS: Record<string, string> = {
  Paper: "#a855f7",
  Concept: "#14b8a6",
  Author: "#f59e0b",
  Talk: "#ec4899",
  Chunk: "#60a5fa",
  Figure: "#f87171",
};

// Learned edges carry a weight in [0, 1]; weak edges fade towards red, strong ones are green.
const weightColor = (w: number) => `hsl(${Math.round(120 * Math.min(1, Math.max(0, w)))}, 65%, 45%)`;

// react-force-graph replaces link endpoints with node objects once the layout starts.
const endId = (end: unknown): string =>
  typeof end === "object" && end !== null ? String((end as GraphNode).id) : String(end);

export const GraphExplorer = () => {
  const [data, setData] = useState<{ nodes: GraphNode[]; links: GraphLink[] }>({ nodes: [], links: [] });
  const [includeItems, setIncludeItems] = useState(false);
  const [showPruned, setShowPruned] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    axios
      .get(`${API}/graph`, { params: { include_items: includeItems } })
      .then((res) => {
        if (cancelled) return;
        setData(res.data);
        setError(null);
      })
      .catch((err) => {
        console.error("Failed to load graph", err);
        if (!cancelled) setError("Could not load the graph. Is the backend running?");
      });
    return () => {
      cancelled = true;
    };
  }, [includeItems, reload]);

  const graph = useMemo(
    () => ({
      nodes: data.nodes.map((n) => ({ ...n })),
      links: data.links.filter((l) => showPruned || !l.pruned).map((l) => ({ ...l })),
    }),
    [data, showPruned],
  );
  const prunedCount = data.links.filter((l) => l.pruned).length;

  return (
    <div className="border rounded-xl bg-white shadow-sm overflow-hidden h-[640px] w-full flex flex-col">
      <div className="bg-gray-50 border-b px-4 py-3 flex flex-wrap gap-3 justify-between items-center">
        <h3 className="font-semibold text-gray-700">Knowledge Graph Explorer</h3>
        <div className="flex flex-wrap gap-4 text-sm items-center text-gray-700">
          {Object.entries(COLORS).map(([label, color]) => (
            <span key={label} className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full" style={{ background: color }} /> {label}
            </span>
          ))}
          <label className="flex items-center gap-1 cursor-pointer">
            <input type="checkbox" checked={includeItems} onChange={(e) => setIncludeItems(e.target.checked)} />
            chunks &amp; figures
          </label>
          <label className="flex items-center gap-1 cursor-pointer">
            <input type="checkbox" checked={showPruned} onChange={(e) => setShowPruned(e.target.checked)} />
            pruned edges ({prunedCount})
          </label>
          <button
            onClick={() => setReload((n) => n + 1)}
            className="px-3 py-1 rounded bg-indigo-600 text-white text-xs font-semibold"
          >
            Refresh
          </button>
        </div>
      </div>
      <div className="px-4 py-1.5 text-xs text-gray-500 border-b bg-white">
        Edge colour and thickness show the learned weight (red = weak, green = strong). Dashed grey edges were pruned
        by the feedback loop.
      </div>
      <div className="flex-1 relative">
        {error && <p className="absolute inset-0 flex items-center justify-center text-red-500">{error}</p>}
        {!error && data.nodes.length === 0 && (
          <p className="absolute inset-0 flex items-center justify-center text-gray-400">
            The graph is empty. Ingest a paper first.
          </p>
        )}
        <ForceGraph2D<GraphNode, GraphLink>
          graphData={graph}
          nodeLabel={(n: GNode) =>
            `${n.label}: ${n.title || n.name || n.id}${n.mentions ? ` (${n.mentions} mentions)` : ""}`
          }
          nodeColor={(n: GNode) => COLORS[n.label] ?? "#9ca3af"}
          nodeRelSize={6}
          linkColor={(l: GLink) =>
            l.pruned ? "#9ca3af" : typeof l.weight === "number" ? weightColor(l.weight) : "#d1d5db"
          }
          linkWidth={(l: GLink) => (typeof l.weight === "number" ? 0.5 + 3.5 * l.weight : 1)}
          linkLineDash={(l: GLink) => (l.pruned ? [3, 3] : null)}
          linkLabel={(l: GLink) =>
            typeof l.weight === "number"
              ? `${l.type}${l.relation ? ` (${l.relation})` : ""}: ${endId(l.source)} → ${endId(l.target)}\nweight ${l.weight.toFixed(2)} · ${l.visits ?? 0} visits${l.pruned ? " · PRUNED" : ""}`
              : l.type
          }
          linkDirectionalArrowLength={(l: GLink) => (l.type === "CITES" ? 4 : 0)}
        />
      </div>
    </div>
  );
};
