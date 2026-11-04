export type Modality = "text" | "image" | "audio";

export interface Source {
  evidence_id: string;
  chunk_id: string;
  paper_id: string;
  paper_title: string;
  authors: string[];
  year?: number | null;
  chunk_text: string;
  score: number;
  modality: Modality;
  page?: number | null;
  section?: string | null;
  start_time?: number | null;
  end_time?: number | null;
  location: string;
  found_by: string[];
  via: string;
  cited: boolean;
}

export interface FigureRef {
  evidence_id: string;
  figure_id: string;
  paper_id: string;
  paper_title: string;
  page: number;
  caption: string;
  description: string;
  bbox: number[];
  url: string;
  score: number;
  cited: boolean;
}

export type Verdict = "supported" | "unsupported" | "unchecked";

export interface Claim {
  text: string;
  evidence_ids: string[];
  verdict: Verdict;
}

export interface FeedbackSummary {
  applied: boolean;
  edges_updated?: number;
  edges_pruned?: number;
  alpha_before?: number;
  alpha_after?: number;
}

export interface Diagnostics {
  query_id: string;
  system: string;
  alpha: number | null;
  fusion: string;
  bm25_hits: number;
  dense_hits: number;
  seeds: number;
  graph_reached: number;
  candidates: number;
  reranked: boolean;
  above_cutoff: number;
  feedback: FeedbackSummary;
  timings: Record<string, number>;
  notes: string[];
}

export interface QueryResult {
  query_id: string;
  answer: string;
  sources: Source[];
  figures: FigureRef[];
  graph_context: { related_papers: string[]; concepts: string[] };
  claims: Claim[];
  claim_stats: { supported: number; unsupported: number; unchecked: number; verified: boolean };
  diagnostics: Diagnostics;
}

export interface SystemInfo {
  name: string;
  description: string;
}

export interface GraphNode {
  id: string;
  label: string;
  name?: string;
  title?: string;
  mentions?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
  weight?: number;
  visits?: number;
  pruned?: boolean;
  count?: number;
  relation?: string;
}

export interface EdgeStat {
  total: number;
  pruned: number;
  avg_weight: number | null;
  visits: number;
}

export interface MemoryState {
  alpha: number;
  edges: Record<string, EdgeStat>;
  nodes: Record<string, number>;
  vector_items: number;
  feedback_enabled: boolean;
  parameters: Record<string, number | string | boolean | number[]>;
}

export interface AuditEvent {
  ts: number;
  query_id: string;
  query: string;
  kind: "edge" | "prune" | "alpha";
  edge_type: string;
  src: string;
  dst: string;
  old_weight: number;
  new_weight: number;
  visits: number;
  score: number;
}
