import { useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { api } from '../lib/api';
import type { GraphNode, GraphEdge } from '../types';

export const GraphExplorer = () => {
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

    const getNodeColor = (node: GraphNode) => {
        switch (node.label) {
            case 'Paper': return '#a855f7';
            case 'Concept': return '#14b8a6';
            case 'Author': return '#f59e0b';
            default: return '#9ca3af';
        }
    };

    return (
        <div className="border rounded-xl bg-white shadow-sm overflow-hidden h-[600px] w-full flex flex-col">
            <div className="bg-gray-50 border-b px-4 py-3 flex justify-between items-center">
                <h3 className="font-semibold text-gray-700">Knowledge Graph Explorer</h3>
                <div className="flex gap-4 text-sm">
                    <span className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-purple-500"></div> Paper</span>
                    <span className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-teal-500"></div> Concept</span>
                    <span className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-amber-500"></div> Author</span>
                </div>
            </div>
            <div className="flex-1 relative">
                <ForceGraph2D<GraphNode, GraphEdge>
                    graphData={graphData}
                    nodeLabel={(node) => `${node.label}: ${node.title || node.name || node.id}`}
                    nodeColor={(node) => getNodeColor(node)}
                    nodeRelSize={6}
                    linkColor={() => '#e5e7eb'}
                />
            </div>
        </div>
    );
};
