# ResearchOS — Multi-Modal Graph RAG System

> A production-grade research intelligence platform that ingests academic papers (PDF), figures (images), and lecture audio, builds a knowledge graph of citations and concepts, and answers researcher queries with multi-modal evidence including visual figure citations.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Final Tech Stack](#2-final-tech-stack)
3. [System Architecture](#3-system-architecture)
4. [Feature List](#4-feature-list)
5. [Repository Structure](#5-repository-structure)
6. [Phase-by-Phase Build Plan](#6-phase-by-phase-build-plan)
7. [Environment Variables](#7-environment-variables)
8. [Docker Setup](#8-docker-setup)
9. [API Reference](#9-api-reference)
10. [Data Models](#10-data-models)
11. [Knowledge Graph Schema](#11-knowledge-graph-schema)
12. [Weaviate Schema](#12-weaviate-schema)
13. [GitHub Branching Strategy](#13-github-branching-strategy)
14. [Running Locally](#14-running-locally)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Project Overview

ResearchOS is a Graph RAG (Retrieval-Augmented Generation) system built for academic research. It goes beyond plain vector search by combining:

- **Vector retrieval** — semantic similarity across text chunks, image figures, and audio transcripts stored in Weaviate
- **Graph traversal** — citation links, concept co-occurrence, and author/venue relationships stored in Neo4j
- **Multi-modal context** — GPT-4o receives both retrieved text AND relevant paper figures when generating answers
- **Visual citations** — the UI shows the exact figure from the source paper that supports each answer

### What makes it Graph RAG

Plain RAG finds chunks that are *similar* to the query. Graph RAG also finds chunks that are *connected* — papers that cite each other, concepts that co-occur across papers, authors whose work forms a research lineage. The knowledge graph participates actively in retrieval, not just storage.

---

## 2. Final Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | React 18 + Vite | TypeScript, TailwindCSS |
| Graph visualizer | React Force Graph | D3-powered, interactive |
| Backend | FastAPI (Python 3.11) | Async, Pydantic v2 |
| Text embeddings | nomic-embed-text | Via Ollama — fully local, no cost |
| Image embeddings | CLIP ViT-B/32 | Via `open-clip-torch` — fully local |
| Audio transcription | OpenAI Whisper | `faster-whisper` local model |
| Vector database | Weaviate | Self-hosted in Docker |
| Graph database | Neo4j 5 | Self-hosted in Docker |
| LLM generation | llama-3.3-70b-versatile | Via Groq API (free tier) |
| Reranker | Cohere Rerank | Free tier, cross-encoder |
| PDF parsing | PyMuPDF (fitz) | Text + figure extraction |
| Orchestration | Docker Compose | 5 services |
| Version control | GitHub | Feature branch strategy |

### Why this stack stands out

- **Zero vector DB cost** — Weaviate runs locally in Docker, no Pinecone billing
- **Zero embedding cost** — nomic-embed-text and CLIP run locally via Ollama
- **Zero LLM cost** — Groq free tier is generous for demo/assignment usage
- **Only Cohere (reranker) and Groq require API keys** — both have free tiers
- **Fully reproducible** — `docker-compose up` spins everything from scratch

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                      │
│   Multi-modal upload │ Graph Explorer │ Citation Cards   │
└──────────────┬──────────────────────────────────────────┘
               │ HTTP REST
┌──────────────▼──────────────────────────────────────────┐
│                   BACKEND (FastAPI)                      │
│  Ingest Router │ Query Router │ Graph API │ Assembler    │
└──┬───────────┬──────────────┬───────────────────────────┘
   │           │              │
   ▼           ▼              ▼
INGESTION   EMBEDDING      QUERY PIPELINE
PIPELINE    LAYER
   │           │              │
   ▼           ▼              ▼
PyMuPDF    nomic-embed    Weaviate retrieval
Whisper    CLIP           Neo4j traversal
PIL        Ollama         Cohere reranker
           (local)        Groq LLM
   │           │              │
   ▼           ▼              ▼
┌──────────┐ ┌───────────┐ ┌──────────────────────────┐
│  Neo4j   │ │ Weaviate  │ │  Response with figures   │
│  Graph   │ │  Vector   │ │  + graph context         │
│  DB      │ │  DB       │ │  → Frontend              │
└──────────┘ └───────────┘ └──────────────────────────┘
```

### Ingestion flow (per document)

```
PDF upload
  └─► PyMuPDF extract text + figures
        ├─► Text chunks (512 tok, 50 overlap)
        │     └─► nomic-embed-text → Weaviate (TextChunk class)
        ├─► Figure images (PIL resize + normalize)
        │     └─► CLIP ViT-B/32 → Weaviate (FigureChunk class)
        └─► Metadata (authors, title, year, citations)
              └─► Neo4j nodes + edges

Audio upload
  └─► faster-whisper transcribe → segments
        └─► nomic-embed-text → Weaviate (AudioChunk class)
```

### Query flow

```
User query (text or text + image)
  └─► Embed query (nomic-embed-text + CLIP if image)
        └─► Weaviate hybrid search → top-10 per class
              └─► Neo4j graph traversal from hit nodes
                    └─► Merge vector + graph results
                          └─► Cohere reranker → top-5
                                └─► Context assembly (text + figures)
                                      └─► Groq llama-3.3-70b → answer
                                            └─► Response with visual citations
```

---

## 4. Feature List

### Core (required by assignment)

- [x] React frontend + FastAPI backend
- [x] Docker + docker-compose for all services
- [x] PDF ingestion with text extraction (PyMuPDF)
- [x] Image modality — figure extraction + CLIP embeddings
- [x] Audio modality — Whisper transcription + text embeddings
- [x] Vector database retrieval (Weaviate, 3 classes)
- [x] LLM response generation (Groq llama-3.3-70b)
- [x] Top-K retrieval
- [x] GitHub with feature branches and PRs

### Standout features (approved)

- [x] **Whisper audio ingestion** — lecture MP3/podcast → transcript → embeddings → Weaviate
- [x] **Cohere reranker** — cross-encoder reranking of merged results before LLM
- [x] **Interactive knowledge graph explorer** — React Force Graph, click paper nodes to explore citations and concepts
- [x] **Figure-level visual citations** — answer cards show the exact chart/figure from the source paper

### Graph RAG capabilities

- [x] **Citation graph** — Paper → CITES → Paper edges in Neo4j
- [x] **Concept graph** — Paper → HAS_CONCEPT → Concept nodes
- [x] **Entity graph** — Author → WROTE → Paper, Paper → PUBLISHED_IN → Venue
- [x] **Graph-augmented retrieval** — vector hits seed graph traversal for related nodes

---

## 5. Repository Structure

```
researchos/
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── UploadPanel.tsx         # Multi-modal file upload
│       │   ├── QueryBar.tsx            # Search input
│       │   ├── AnswerCard.tsx          # Response with citations
│       │   ├── FigureCitation.tsx      # Visual figure card
│       │   ├── GraphExplorer.tsx       # React Force Graph viewer
│       │   └── SourceChip.tsx         # Source paper pill
│       ├── hooks/
│       │   ├── useIngest.ts
│       │   └── useQuery.ts
│       └── api/
│           └── client.ts               # Axios API client
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                         # FastAPI app entry
│   ├── config.py                       # Settings (pydantic-settings)
│   ├── routers/
│   │   ├── ingest.py                   # POST /ingest/pdf, /ingest/audio
│   │   ├── query.py                    # POST /query
│   │   └── graph.py                    # GET /graph/nodes, /graph/edges
│   ├── services/
│   │   ├── pdf_extractor.py            # PyMuPDF text + figure extraction
│   │   ├── audio_transcriber.py        # faster-whisper transcription
│   │   ├── embedder.py                 # nomic-embed-text via Ollama
│   │   ├── clip_embedder.py            # CLIP ViT-B/32 image embedding
│   │   ├── weaviate_client.py          # Weaviate insert + search
│   │   ├── neo4j_client.py             # Neo4j node/edge operations
│   │   ├── retriever.py                # Hybrid vector + graph retrieval
│   │   ├── reranker.py                 # Cohere rerank
│   │   └── generator.py               # Groq llama generation
│   └── models/
│       ├── ingest.py                   # Pydantic ingest schemas
│       └── query.py                    # Pydantic query/response schemas
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 6. Phase-by-Phase Build Plan

### Phase 1 — Infrastructure & Skeleton (Day 1)

**Goal:** All Docker services running, FastAPI returns health check, React renders blank page.

Tasks:
1. Create GitHub repo, set up `main` and `dev` branches
2. Write `docker-compose.yml` with 5 services: frontend, backend, weaviate, neo4j, ollama
3. Write backend `Dockerfile` + `main.py` with `/health` endpoint
4. Write frontend `Dockerfile` + `nginx.conf` + blank React app
5. Write `config.py` with all env vars (pydantic-settings)
6. Init Weaviate schema (3 classes: TextChunk, FigureChunk, AudioChunk)
7. Init Neo4j constraints and indexes
8. Pull `nomic-embed-text` into Ollama container on startup

Branch: `feature/infrastructure`

Deliverable: `docker-compose up` → all 5 services healthy.

---

### Phase 2 — Ingestion Pipeline (Day 1–2)

**Goal:** Upload a PDF → text chunks + figures stored in Weaviate + paper node in Neo4j.

Tasks:
1. `pdf_extractor.py` — PyMuPDF text extraction + chunking (512 tok, 50 overlap)
2. `pdf_extractor.py` — figure detection + PIL preprocessing (224×224 RGB)
3. `embedder.py` — call Ollama nomic-embed-text REST API, return 768-dim vector
4. `clip_embedder.py` — load CLIP ViT-B/32 locally, embed figure images
5. `weaviate_client.py` — insert TextChunk, FigureChunk objects with metadata
6. `neo4j_client.py` — create Paper node, Author nodes, citation edges
7. `routers/ingest.py` — POST `/ingest/pdf` endpoint wiring all the above
8. Frontend `UploadPanel.tsx` — drag-and-drop PDF upload with progress bar

Branch: `feature/ingestion-pdf`

Deliverable: Upload a PDF via UI → see data in Weaviate and Neo4j dashboards.

---

### Phase 3 — Audio Ingestion (Day 2)

**Goal:** Upload an MP3 → transcript segments stored in Weaviate as AudioChunk objects.

Tasks:
1. `audio_transcriber.py` — faster-whisper model load + transcribe with timestamps
2. Chunk transcript by segment (≤512 tokens), preserve timestamps as metadata
3. `embedder.py` — reuse nomic-embed-text for transcript chunks
4. `weaviate_client.py` — insert AudioChunk objects
5. `routers/ingest.py` — POST `/ingest/audio` endpoint
6. Frontend `UploadPanel.tsx` — add audio file type support

Branch: `feature/ingestion-audio`

Deliverable: Upload an MP3 → AudioChunk objects in Weaviate with timestamp metadata.

---

### Phase 4 — Vector Retrieval + Graph Traversal (Day 2–3)

**Goal:** A query returns top-K results from Weaviate + graph-augmented results from Neo4j, merged.

Tasks:
1. `weaviate_client.py` — hybrid search across TextChunk, FigureChunk, AudioChunk
2. `neo4j_client.py` — given a paper ID, traverse 1-hop citation + concept neighbors
3. `retriever.py` — embed query → Weaviate top-10 → extract paper IDs → Neo4j traversal → merge + deduplicate
4. `reranker.py` — Cohere rerank merged results → top-5
5. `routers/query.py` — POST `/query` endpoint (no LLM yet, return raw chunks)
6. Unit test retriever with a known paper

Branch: `feature/retrieval`

Deliverable: POST `/query` returns ranked, merged multi-modal chunks.

---

### Phase 5 — LLM Generation + Response Assembly (Day 3)

**Goal:** Ranked chunks go into Groq → answer comes back with source metadata and figure references.

Tasks:
1. `generator.py` — Groq client, build system prompt + context window from chunks
2. System prompt design — instruct model to cite sources by paper ID
3. `routers/query.py` — wire reranked chunks → generator → structured response
4. `models/query.py` — `QueryResponse` schema: answer text, cited chunks, figure references
5. Figure URL serving — backend serves stored figure images at `/figures/{id}`

Branch: `feature/generation`

Deliverable: POST `/query` returns full structured answer with figure references.

---

### Phase 6 — Frontend UI (Day 3–4)

**Goal:** A polished, usable research UI with query bar, answer cards, and figure citations.

Tasks:
1. `QueryBar.tsx` — text input + optional image upload for multi-modal queries
2. `AnswerCard.tsx` — displays answer text with inline source citations
3. `FigureCitation.tsx` — shows figure image thumbnail, paper title, page number
4. `SourceChip.tsx` — clickable pill showing paper title + year
5. `useQuery.ts` — React hook wrapping the query API call with loading state
6. Loading skeleton while answer streams
7. TailwindCSS styling — clean, minimal, research tool aesthetic

Branch: `feature/frontend-ui`

Deliverable: End-to-end demo works in browser — upload PDF, ask question, see answer with figures.

---

### Phase 7 — Knowledge Graph Explorer (Day 4)

**Goal:** Interactive graph visualization in the UI showing paper citation and concept networks.

Tasks:
1. `routers/graph.py` — GET `/graph/nodes` and `/graph/edges` endpoints pulling from Neo4j
2. `GraphExplorer.tsx` — React Force Graph component rendering nodes and edges
3. Node types: Paper (purple), Concept (teal), Author (amber)
4. Click a paper node → right panel shows paper metadata + option to query it
5. Zoom, pan, node drag all built into React Force Graph
6. Connect graph explorer to query results — highlight nodes from last answer

Branch: `feature/graph-explorer`

Deliverable: Graph explorer tab shows live knowledge graph, clickable nodes.

---

### Phase 8 — Polish, Docker Finalization, GitHub cleanup (Day 4–5)

**Goal:** Everything works from a single `docker-compose up`, repo is clean.

Tasks:
1. Review all Dockerfiles — minimize image sizes, use multi-stage where helpful
2. `docker-compose.yml` — add health checks, depends_on conditions, restart policies
3. `.env.example` — document every variable
4. Ollama startup script — auto-pull `nomic-embed-text` on container start
5. Weaviate + Neo4j init scripts run on first boot, idempotent
6. README final pass
7. Clean up all feature branches → PRs → merge to `dev` → merge to `main`
8. Tag release `v1.0.0`

Branch: `chore/docker-finalization`

Deliverable: `git clone` + `cp .env.example .env` + fill 2 API keys + `docker-compose up` = working system.

---

## 7. Environment Variables

Create a `.env` file in the root directory. Only 2 external API keys are needed.

```env
# === REQUIRED — external API keys ===
GROQ_API_KEY=your_groq_api_key_here
COHERE_API_KEY=your_cohere_api_key_here

# === Weaviate (self-hosted, no key needed) ===
WEAVIATE_URL=http://weaviate:8080

# === Neo4j (self-hosted) ===
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=researchos123

# === Ollama (self-hosted) ===
OLLAMA_URL=http://ollama:11434
EMBED_MODEL=nomic-embed-text

# === Groq ===
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_MAX_TOKENS=2048

# === Cohere ===
COHERE_RERANK_MODEL=rerank-english-v3.0
COHERE_TOP_N=5

# === CLIP ===
CLIP_MODEL=ViT-B/32

# === Whisper ===
WHISPER_MODEL=base

# === Retrieval ===
RETRIEVAL_TOP_K=10
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# === Backend ===
BACKEND_PORT=8000
FIGURES_DIR=/app/figures
```

---

## 8. Docker Setup

### docker-compose.yml overview

```yaml
version: "3.9"

services:

  frontend:
    build: ./frontend
    ports: ["3000:80"]
    depends_on: [backend]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    volumes:
      - figures_data:/app/figures
    depends_on:
      weaviate: { condition: service_healthy }
      neo4j:    { condition: service_healthy }
      ollama:   { condition: service_started }

  weaviate:
    image: semitechnologies/weaviate:1.24.1
    ports: ["8080:8080"]
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"
      PERSISTENCE_DATA_PATH: /var/lib/weaviate
      DEFAULT_VECTORIZER_MODULE: none
      ENABLE_MODULES: ""
    volumes: [weaviate_data:/var/lib/weaviate]
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/v1/.well-known/ready"]
      interval: 10s
      timeout: 5s
      retries: 10

  neo4j:
    image: neo4j:5.15-community
    ports: ["7474:7474", "7687:7687"]
    environment:
      NEO4J_AUTH: neo4j/researchos123
      NEO4J_PLUGINS: '["apoc"]'
    volumes: [neo4j_data:/data]
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "researchos123", "RETURN 1"]
      interval: 15s
      timeout: 10s
      retries: 10

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: [ollama_data:/root/.ollama]
    entrypoint: ["/bin/sh", "-c", "ollama serve & sleep 5 && ollama pull nomic-embed-text && wait"]

volumes:
  weaviate_data:
  neo4j_data:
  ollama_data:
  figures_data:
```

---

## 9. API Reference

### Ingest endpoints

#### `POST /ingest/pdf`
Upload a PDF file for ingestion.

Request: `multipart/form-data`
- `file`: PDF file
- `title`: string (optional, extracted from PDF if omitted)
- `authors`: comma-separated string (optional)
- `year`: integer (optional)

Response:
```json
{
  "paper_id": "uuid",
  "chunks_created": 42,
  "figures_extracted": 7,
  "graph_nodes_created": 3,
  "status": "success"
}
```

#### `POST /ingest/audio`
Upload an audio file for transcription and ingestion.

Request: `multipart/form-data`
- `file`: MP3 / WAV / M4A file
- `title`: string
- `source_paper_id`: string (optional, links audio to a paper node)

Response:
```json
{
  "audio_id": "uuid",
  "segments": 34,
  "chunks_created": 12,
  "duration_seconds": 3420,
  "status": "success"
}
```

### Query endpoint

#### `POST /query`

Request:
```json
{
  "text": "What methods have been used to improve transformer efficiency?",
  "image_base64": null,
  "top_k": 10,
  "rerank_top_n": 5
}
```

Response:
```json
{
  "answer": "Several approaches have been proposed...",
  "sources": [
    {
      "chunk_id": "uuid",
      "paper_id": "uuid",
      "paper_title": "Efficient Transformers: A Survey",
      "authors": ["Yi Tay", "Mostafa Dehghani"],
      "year": 2022,
      "chunk_text": "Sparse attention reduces...",
      "score": 0.94,
      "modality": "text"
    }
  ],
  "figures": [
    {
      "figure_id": "uuid",
      "paper_id": "uuid",
      "paper_title": "Efficient Transformers: A Survey",
      "page": 4,
      "caption": "Figure 2: Comparison of attention patterns",
      "url": "/figures/uuid.png",
      "score": 0.87
    }
  ],
  "graph_context": {
    "related_papers": ["uuid1", "uuid2"],
    "concepts": ["sparse attention", "linear attention", "reformer"]
  }
}
```

### Graph endpoints

#### `GET /graph/nodes`
Returns all nodes for the graph explorer.

Query params: `limit` (default 200), `node_type` (Paper | Concept | Author | Venue)

#### `GET /graph/edges`
Returns all edges for the graph explorer.

Query params: `limit` (default 500), `edge_type` (CITES | HAS_CONCEPT | WROTE | PUBLISHED_IN)

#### `GET /figures/{figure_id}`
Serves a stored figure image file.

---

## 10. Data Models

### Pydantic schemas (backend/models/)

```python
# models/ingest.py
class IngestPDFResponse(BaseModel):
    paper_id: str
    chunks_created: int
    figures_extracted: int
    graph_nodes_created: int
    status: str

class IngestAudioResponse(BaseModel):
    audio_id: str
    segments: int
    chunks_created: int
    duration_seconds: float
    status: str

# models/query.py
class QueryRequest(BaseModel):
    text: str
    image_base64: Optional[str] = None
    top_k: int = 10
    rerank_top_n: int = 5

class SourceChunk(BaseModel):
    chunk_id: str
    paper_id: str
    paper_title: str
    authors: List[str]
    year: Optional[int]
    chunk_text: str
    score: float
    modality: Literal["text", "image", "audio"]

class FigureReference(BaseModel):
    figure_id: str
    paper_id: str
    paper_title: str
    page: int
    caption: str
    url: str
    score: float

class GraphContext(BaseModel):
    related_papers: List[str]
    concepts: List[str]

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
    figures: List[FigureReference]
    graph_context: GraphContext
```

---

## 11. Knowledge Graph Schema

### Neo4j node labels

```cypher
// Paper node
CREATE (p:Paper {
  id: "uuid",
  title: "string",
  abstract: "string",
  year: 2023,
  doi: "string",
  venue: "string",
  weaviate_ids: ["chunk_uuid_1", "chunk_uuid_2"]
})

// Author node
CREATE (a:Author {
  id: "uuid",
  name: "string",
  affiliation: "string"
})

// Concept node
CREATE (c:Concept {
  id: "uuid",
  name: "string",
  frequency: 1
})

// Venue node
CREATE (v:Venue {
  id: "uuid",
  name: "string",
  type: "conference | journal"
})
```

### Neo4j relationship types

```cypher
// Citation edge
(p1:Paper)-[:CITES {context: "string"}]->(p2:Paper)

// Authorship
(a:Author)-[:WROTE]->(p:Paper)

// Concept link
(p:Paper)-[:HAS_CONCEPT {weight: 0.85}]->(c:Concept)

// Venue
(p:Paper)-[:PUBLISHED_IN]->(v:Venue)
```

### Indexes and constraints

```cypher
CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE;
CREATE INDEX paper_title IF NOT EXISTS FOR (p:Paper) ON (p.title);
CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name);
```

---

## 12. Weaviate Schema

Three collections, each with a custom vector (bring-your-own-embedding, no vectorizer module needed).

```python
# TextChunk collection
{
    "class": "TextChunk",
    "vectorizer": "none",
    "properties": [
        {"name": "paper_id",    "dataType": ["text"]},
        {"name": "paper_title", "dataType": ["text"]},
        {"name": "authors",     "dataType": ["text[]"]},
        {"name": "year",        "dataType": ["int"]},
        {"name": "chunk_text",  "dataType": ["text"]},
        {"name": "chunk_index", "dataType": ["int"]},
        {"name": "page",        "dataType": ["int"]},
    ]
}

# FigureChunk collection
{
    "class": "FigureChunk",
    "vectorizer": "none",
    "properties": [
        {"name": "paper_id",    "dataType": ["text"]},
        {"name": "paper_title", "dataType": ["text"]},
        {"name": "figure_id",   "dataType": ["text"]},
        {"name": "caption",     "dataType": ["text"]},
        {"name": "page",        "dataType": ["int"]},
        {"name": "file_path",   "dataType": ["text"]},
    ]
}

# AudioChunk collection
{
    "class": "AudioChunk",
    "vectorizer": "none",
    "properties": [
        {"name": "audio_id",        "dataType": ["text"]},
        {"name": "title",           "dataType": ["text"]},
        {"name": "chunk_text",      "dataType": ["text"]},
        {"name": "start_time",      "dataType": ["number"]},
        {"name": "end_time",        "dataType": ["number"]},
        {"name": "source_paper_id", "dataType": ["text"]},
    ]
}
```

---

## 13. GitHub Branching Strategy

```
main          ← stable, tagged releases only
└── dev       ← integration branch, all features merge here first
    ├── feature/infrastructure       Phase 1
    ├── feature/ingestion-pdf        Phase 2
    ├── feature/ingestion-audio      Phase 3
    ├── feature/retrieval            Phase 4
    ├── feature/generation           Phase 5
    ├── feature/frontend-ui          Phase 6
    ├── feature/graph-explorer       Phase 7
    └── chore/docker-finalization    Phase 8
```

### Commit message convention

```
feat: add CLIP image embedding service
fix: handle missing abstract in PDF metadata
docs: update Weaviate schema in README
chore: add healthcheck to neo4j service
refactor: split retriever into vector and graph modules
test: add unit test for PDF chunk extraction
```

### PR template

Every PR should include:
- What this PR does (1–2 sentences)
- How to test it manually
- Any env vars added or changed

---

## 14. Running Locally

### Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- Git
- Groq API key (free at console.groq.com)
- Cohere API key (free at cohere.com)

### Steps

```bash
# 1. Clone
git clone https://github.com/your-username/researchos.git
cd researchos

# 2. Set up env
cp .env.example .env
# Edit .env — fill in GROQ_API_KEY and COHERE_API_KEY

# 3. Start everything
docker-compose up --build

# 4. Wait for Ollama to pull nomic-embed-text (~2 min first run)
# Watch logs: docker-compose logs -f ollama

# 5. Open in browser
# Frontend:         http://localhost:3000
# Backend docs:     http://localhost:8000/docs
# Weaviate console: http://localhost:8080
# Neo4j browser:    http://localhost:7474
```

### First run checklist

- [ ] All 5 containers show as healthy in `docker-compose ps`
- [ ] `http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] `http://localhost:8080/v1/.well-known/ready` returns `{}`
- [ ] Neo4j browser at `http://localhost:7474` connects with `neo4j / researchos123`
- [ ] Ollama logs show `nomic-embed-text` pulled successfully

---

## 15. Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Ollama container keeps restarting | Not enough RAM for model | Increase Docker memory limit to 8GB |
| Weaviate returns 404 on insert | Schema not initialized | Backend init script runs on startup — check backend logs |
| Neo4j `service_healthy` never passes | APOC plugin load delay | Increase `retries` in healthcheck to 20 |
| CLIP import error | `open-clip-torch` not installed | Check backend `requirements.txt` includes it |
| Groq rate limit error | Free tier 30 RPM | Add 2s delay between requests in `generator.py` |
| Figures not serving | Volume mount missing | Ensure `figures_data` volume is mounted at `/app/figures` |
| nomic-embed-text slow | Running on CPU | Normal — 768-dim embeddings take ~200ms per chunk on CPU |

---

*Built for the Multi-Modal Graph RAG assignment — May 2026*
