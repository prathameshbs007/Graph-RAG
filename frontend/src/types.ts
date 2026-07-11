export interface SourceChunk {
  chunk_id: string;
  paper_id: string;
  paper_title: string;
  authors: string[];
  year: number | null;
  chunk_text: string;
  score: number;
  modality: 'text' | 'image' | 'audio';
  start_time: number | null;
  end_time: number | null;
}

export interface FigureReference {
  figure_id: string;
  paper_id: string;
  paper_title: string;
  page: number;
  caption: string;
  url: string;
  score: number;
}

export interface GraphContext {
  related_papers: string[];
  concepts: string[];
}

export interface QueryResponse {
  answer: string;
  sources: SourceChunk[];
  figures: FigureReference[];
  graph_context: GraphContext;
}

export interface QueryCompareResponse {
  with_graph: QueryResponse;
  without_graph: QueryResponse;
}

export interface IngestAcceptedResponse {
  id: string;
  status: string;
}

export interface IngestStatusProcessing {
  status: 'processing';
}

export interface IngestStatusError {
  status: 'error';
  detail: string;
}

export interface IngestStatusPdfDone {
  status: 'done';
  paper_id: string;
  chunks_created: number;
  figures_extracted: number;
  graph_nodes_created: number;
}

export interface IngestStatusAudioDone {
  status: 'done';
  audio_id: string;
  segments: number;
  chunks_created: number;
  duration_seconds: number;
}

export type IngestStatus =
  | IngestStatusProcessing
  | IngestStatusError
  | IngestStatusPdfDone
  | IngestStatusAudioDone;

export interface GraphNode {
  id: string;
  label: string;
  title: string;
  name: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}
