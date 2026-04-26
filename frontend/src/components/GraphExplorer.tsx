import React, { useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import axios from 'axios';

export const GraphExplorer = () => {
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });

    useEffect(() => {
        const fetchGraph = async () => {
            try {
                const [nodesRes, edgesRes] = await Promise.all([
                    axios.get('http://localhost:8054/graph/nodes'),
                    axios.get('http://localhost:8054/graph/edges')
                ]);
                setGraphData({
                    nodes: nodesRes.data.nodes,
                    links: edgesRes.data.edges
                });
            } catch (err) {
                console.error("Failed to load graph", err);
            }
        };
        fetchGraph();
    }, []);

    const getNodeColor = (node: any) => {
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
                <ForceGraph2D
                    graphData={graphData}
                    nodeLabel={(node: any) => `${node.label}: ${node.title || node.name || node.id}`}
                    nodeColor={getNodeColor}
                    nodeRelSize={6}
                    linkColor={() => '#e5e7eb'}
                />
            </div>
        </div>
    );
};
