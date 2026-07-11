import { useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { api } from '../lib/api';
import type { GraphNode, GraphEdge } from '../types';

const NODE_COLORS: Record<string, string> = {
    Paper: '#a855f7',
    Concept: '#14b8a6',
    Author: '#f59e0b',
};
const DEFAULT_NODE_COLOR = '#9ca3af';

export const GraphExplorer = ({ isDark }: { isDark: boolean }) => {
    const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; links: GraphEdge[] }>({ nodes: [], links: [] });

    useEffect(() => {
        const fetchGraph = async () => {
            try {
                const [nodesRes, edgesRes] = await Promise.all([
                    api.get<{ nodes: GraphNode[] }>('/graph/nodes'),
                    api.get<{ edges: GraphEdge[] }>('/graph/edges'),
                ]);
                setGraphData({
                    nodes: nodesRes.data.nodes,
                    links: edgesRes.data.edges,
                });
            } catch (err) {
                console.error("Failed to load graph", err);
            }
        };
        fetchGraph();
    }, []);

    const getNodeColor = (node: GraphNode) => NODE_COLORS[node.label] ?? DEFAULT_NODE_COLOR;

    return (
        <div className="border border-border-default rounded-xl bg-surface-raised shadow-sm overflow-hidden h-[600px] w-full flex flex-col">
            <div className="bg-surface-hover border-b border-border-default px-4 py-3 flex justify-between items-center">
                <h3 className="font-semibold text-text-default">Knowledge Graph Explorer</h3>
                <div className="flex gap-4 text-sm text-text-muted">
                    <span className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: NODE_COLORS.Paper }}></div> Paper
                    </span>
                    <span className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: NODE_COLORS.Concept }}></div> Concept
                    </span>
                    <span className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: NODE_COLORS.Author }}></div> Author
                    </span>
                </div>
            </div>
            <div className="flex-1 relative">
                <ForceGraph2D<GraphNode, GraphEdge>
                    graphData={graphData}
                    nodeLabel={(node) => `${node.label}: ${node.title || node.name || node.id}`}
                    nodeColor={(node) => getNodeColor(node)}
                    nodeRelSize={6}
                    linkColor={() => (isDark ? '#334155' : '#e2e8f0')}
                    backgroundColor={isDark ? '#0f172a' : '#ffffff'}
                />
            </div>
        </div>
    );
};
