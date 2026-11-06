import { useEffect, useMemo, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { LinkObject, NodeObject } from "react-force-graph-2d";
import axios from "axios";
import { API } from "../api";
import type { GraphLink, GraphNode } from "../types";

type GNode = NodeObject<GraphNode>;
type GLink = LinkObject<GraphNode, GraphLink>;

const COLORS: Record<string, string> = {
  Paper: "#ddb7ff",
  Concept: "#4fdbc8",
  Author: "#71f8e4",
  Talk: "#b76dff",
  Chunk: "#8083ff",
  Figure: "#ffb4ab",
};

const weightColor = (w: number) => {
  if (w >= 0.5) return "#4fdbc8"; // Emerald / Cyan
  if (w >= 0.28) return "#c0c1ff"; // Indigo
  return "#ffb4ab"; // Warning / Weak
};

const endId = (end: unknown): string =>
  typeof end === "object" && end !== null ? String((end as GraphNode).id) : String(end);

export const GraphExplorer = () => {
  const [data, setData] = useState<{ nodes: GraphNode[]; links: GraphLink[] }>({ nodes: [], links: [] });
  const [includeItems, setIncludeItems] = useState(true);
  const [showPruned, setShowPruned] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

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

  // Connected edges for the selected node
  const connectedLinks = useMemo(() => {
    if (!selectedNode) return [];
    const nodeId = selectedNode.id;
    return data.links.filter(
      (l) => endId(l.source) === nodeId || endId(l.target) === nodeId
    );
  }, [selectedNode, data.links]);

  return (
    <div className="relative w-full rounded-2xl bg-surface-container-lowest border border-surface-container-highest/40 overflow-hidden shadow-2xl flex flex-col h-[740px]">
      {/* Top HUD Control Bar */}
      <div className="bg-surface-container-low/90 backdrop-blur-xl px-4 py-3 border-b border-surface-container-highest/40 flex flex-wrap items-center justify-between gap-3 z-10">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-secondary animate-ping"></span>
            <span className="font-semibold text-sm text-on-surface tracking-tight">
              Knowledge Graph Explorer
            </span>
          </div>
          <span className="text-outline-variant font-mono text-xs">/</span>
          <span className="px-2 py-0.5 rounded bg-surface-container font-mono text-[11px] text-tertiary">
            CROSS-MODAL PAPER GRAPH
          </span>
        </div>

        {/* Node Legend Badges */}
        <div className="hidden xl:flex items-center gap-2 bg-surface-container-lowest/80 px-2 py-1 rounded-lg font-mono text-xs">
          {Object.entries(COLORS).map(([label, color]) => (
            <div key={label} className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container text-on-surface">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}` }} />
              <span className="text-[11px]">{label}</span>
            </div>
          ))}
        </div>

        {/* Filter Checkboxes & Refresh */}
        <div className="flex items-center gap-3 font-mono text-xs text-on-surface-variant">
          <label className="flex items-center gap-1.5 cursor-pointer hover:text-on-surface">
            <input
              type="checkbox"
              checked={includeItems}
              onChange={(e) => setIncludeItems(e.target.checked)}
              className="accent-secondary rounded"
            />
            <span>Chunks & Figures</span>
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer hover:text-on-surface">
            <input
              type="checkbox"
              checked={showPruned}
              onChange={(e) => setShowPruned(e.target.checked)}
              className="accent-error rounded"
            />
            <span>Pruned ({prunedCount})</span>
          </label>
          <button
            onClick={() => setReload((n) => n + 1)}
            type="button"
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-surface-container hover:bg-surface-container-high text-primary hover:text-on-surface transition-colors"
          >
            <span className="material-symbols-outlined text-[1rem]">sync</span>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Main Canvas + Optional Inspector Drawer */}
      <div className="flex-1 relative flex overflow-hidden">
        {error && (
          <div className="absolute inset-0 flex items-center justify-center text-error font-mono text-xs z-20">
            {error}
          </div>
        )}
        {!error && data.nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-outline font-mono text-xs z-20">
            Knowledge graph is empty. Ingest a paper to construct the topology.
          </div>
        )}

        <div className="flex-1 h-full relative bg-surface-container-lowest">
          <ForceGraph2D<GraphNode, GraphLink>
            graphData={graph}
            backgroundColor="#060e20"
            nodeLabel={(n: GNode) =>
              `${n.label}: ${n.title || n.name || n.id}${n.mentions ? ` (${n.mentions} mentions)` : ""}`
            }
            nodeColor={(n: GNode) => COLORS[n.label] ?? "#908fa0"}
            nodeRelSize={6}
            onNodeClick={(n: GNode) => setSelectedNode(n as GraphNode)}
            linkColor={(l: GLink) =>
              l.pruned ? "#908fa0" : typeof l.weight === "number" ? weightColor(l.weight) : "#464554"
            }
            linkWidth={(l: GLink) => (typeof l.weight === "number" ? 1 + 3 * l.weight : 1.2)}
            linkLineDash={(l: GLink) => (l.pruned ? [4, 4] : null)}
            linkLabel={(l: GLink) =>
              typeof l.weight === "number"
                ? `${l.type}${l.relation ? ` (${l.relation})` : ""}: ${endId(l.source)} → ${endId(l.target)}\nweight ${l.weight.toFixed(3)} · ${l.visits ?? 0} visits${l.pruned ? " · PRUNED" : ""}`
                : l.type
            }
            linkDirectionalArrowLength={(l: GLink) => (l.type === "CITES" ? 5 : 0)}
          />

          {/* Canvas Telemetry HUD (Bottom Left) */}
          <div className="absolute bottom-3 left-3 z-10 flex items-center gap-3 bg-surface-container-low/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-surface-container-highest/40 font-mono text-[11px] text-on-surface-variant">
            <div className="flex items-center gap-1.5 text-secondary">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>
              <span>Neo4j Bolt Active</span>
            </div>
            <span className="text-outline">•</span>
            <span>Nodes: {data.nodes.length}</span>
            <span className="text-outline">•</span>
            <span>Edges: {data.links.length}</span>
            {selectedNode && (
              <>
                <span className="text-outline">•</span>
                <span className="text-primary truncate max-w-[150px]">
                  Selected: {selectedNode.title || selectedNode.name || selectedNode.id}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Right-Hand Entity Inspector Drawer */}
        {selectedNode && (
          <aside className="w-80 shrink-0 h-full bg-surface-container-low/95 backdrop-blur-2xl border-l border-surface-container-highest/40 flex flex-col z-20 shadow-2xl overflow-y-auto animate-fadeIn">
            <div className="p-3 bg-surface-container flex items-center justify-between sticky top-0 border-b border-surface-container-highest/30">
              <div className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-secondary text-[1rem]">grain</span>
                <span className="font-semibold text-xs text-on-surface">Entity Inspector</span>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-on-surface-variant hover:text-on-surface p-1 rounded"
              >
                ✕
              </button>
            </div>

            <div className="p-4 space-y-4 flex-1 font-mono text-xs">
              <div className="bg-surface-container-lowest/80 p-3 rounded-lg border border-surface-container-highest/30">
                <div className="flex items-center justify-between mb-1">
                  <span className="px-1.5 py-0.5 rounded bg-secondary/15 text-secondary text-[10px] uppercase font-bold">
                    {selectedNode.label}
                  </span>
                  <span className="text-outline text-[10px]">id: {selectedNode.id}</span>
                </div>
                <div className="font-sans font-bold text-sm text-on-surface mt-1">
                  {selectedNode.title || selectedNode.name || selectedNode.id}
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="p-2 rounded bg-surface-container">
                  <div className="text-[10px] text-outline uppercase">Mentions</div>
                  <div className="text-secondary font-bold text-sm mt-0.5">
                    {selectedNode.mentions ?? "—"}
                  </div>
                </div>
                <div className="p-2 rounded bg-surface-container">
                  <div className="text-[10px] text-outline uppercase">Neighbors</div>
                  <div className="text-primary font-bold text-sm mt-0.5">
                    {connectedLinks.length}
                  </div>
                </div>
              </div>

              {/* Connected Edges Table */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] uppercase tracking-wide text-on-surface font-semibold">
                    Connected Synapses ({connectedLinks.length})
                  </span>
                </div>
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {connectedLinks.map((l, i) => (
                    <div
                      key={i}
                      className={`p-2 rounded border text-[11px] ${
                        l.pruned
                          ? "bg-surface-container-lowest/40 border-outline/20 text-outline line-through"
                          : "bg-surface-container border-surface-container-highest/40 text-on-surface"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-secondary">{l.type}</span>
                        {typeof l.weight === "number" && (
                          <span
                            className={`font-bold ${
                              l.pruned ? "text-error" : l.weight >= 0.5 ? "text-secondary" : "text-primary"
                            }`}
                          >
                            {l.pruned ? "PRUNED" : `w=${l.weight.toFixed(3)}`}
                          </span>
                        )}
                      </div>
                      <div className="text-outline text-[10px] truncate mt-0.5">
                        {endId(l.source)} → {endId(l.target)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Cypher Query Box */}
              <div>
                <div className="text-[10px] uppercase text-outline mb-1">Neo4j Cypher Expression</div>
                <pre className="p-2 rounded bg-surface-container-lowest text-on-surface-variant text-[10px] overflow-x-auto leading-relaxed border border-surface-container-highest/20">
{`MATCH (n {id: '${selectedNode.id}'})-[r]-(target)
RETURN n, r, target LIMIT 25;`}
                </pre>
              </div>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
};
